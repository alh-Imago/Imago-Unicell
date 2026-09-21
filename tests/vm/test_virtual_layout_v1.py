"""tests/vm/test_virtual_layout_v1.py — points.md #800: the virtual-space
layout + global router (`vix_virtual_layout_v1`).

The design under test (Alan): while a design is being created it sits in a
virtual space, not yet lowered to an ICM; the optimiser must be able to change
the CARDINALITY of each route's endpoints (which face a value leaves/enters
by); folding to fit a bounded card then requires those cardinal outs to be
re-chosen, and a tightening pass shrinks the result. Every positive test runs
the compiled fabric through the real VM against an independent Python model.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import llvm_dag_frontend_v1 as F  # noqa: E402
import vix_virtual_layout_v1 as V  # noqa: E402

M = 0xFFFFFFFF
HERE = os.path.dirname(os.path.abspath(__file__))


def s32(v):
    v &= M
    return v - (1 << 32) if v >> 31 else v


def _ir(body, args="i32 %x"):
    return f"define i32 @f({args}) {{\nentry:\n{body}\n}}\n"


def _compile(src, **kw):
    res, diags = F.compile_llvm_via_dag(src, **kw)
    assert diags == [], [d.problem for d in diags]
    return res


PROOF = _ir("  %a = add i32 %x, 5\n  %b = sub i32 %a, 3\n  ret i32 %b")
DIAMOND = _ir("  %t1 = add i32 %x, 5\n  %t2 = add i32 %t1, 10\n  %t3 = add i32 %t1, %t2\n  ret i32 %t3")
SEL_COMPUTED = _ir("  %a = add i32 %x, 1\n  %b = shl i32 %x, 2\n  %c = icmp eq i32 %x, 5\n"
                   "  %r = select i1 %c, i32 %a, i32 %b\n  ret i32 %r")
CLAMP = _ir("  %c1 = icmp slt i32 %x, 10\n  %a = select i1 %c1, i32 10, i32 %x\n  %c2 = icmp sgt i32 %a, 20\n"
            "  %r = select i1 %c2, i32 20, i32 %a\n  ret i32 %r")
ARMS_AND_COND = _ir("  %a = mul i32 %x, 3\n  %b = xor i32 %y, 255\n  %d = sub i32 %x, %y\n  %c = icmp slt i32 %d, 0\n"
                    "  %r = select i1 %c, i32 %a, i32 %b\n  ret i32 %r", args="i32 %x, i32 %y")
VALUES = [0, 1, 5, 6, 100, 0x7FFFFFFF, 0x80000000, M]


def test_proof_case_and_diamond_under_the_routed_placer():
    res = _compile(PROOF, placer="routed")
    assert res.placer == "routed"
    for x in VALUES:
        assert F.run_in_vm(res, {"x": x}) == (x + 2) & M
    res = _compile(DIAMOND, placer="routed")
    for x in VALUES:
        assert F.run_in_vm(res, {"x": x}) == ((x + 5) + (x + 15)) & M


def test_shapes_the_growth_placer_could_not_place_now_work():
    res = _compile(SEL_COMPUTED, placer="routed")
    for x in VALUES:
        assert F.run_in_vm(res, {"x": x}) == ((x + 1) if x == 5 else (x << 2)) & M, hex(x)
    res = _compile(CLAMP, placer="routed")
    for x in (0, 9, 10, 15, 20, 21, 99, M):
        assert F.run_in_vm(res, {"x": x}) == min(max(s32(x), 10), 20) & M, hex(x)
    res = _compile(ARMS_AND_COND, placer="routed")
    for a in (0, 3, 50, 100):
        for b in (0, 7, 60, 99):
            assert F.run_in_vm(res, {"x": a, "y": b}) == ((a * 3) if s32(a - b) < 0 else (b ^ 255)) & M, (a, b)


def test_routed_layout_is_tighter_than_growth_where_both_place():
    """The router chooses the shortest routes over the whole occupancy map; growth
    pads straight out of every frontier. (Asserted only for these two shapes -- it is
    not a guarantee in general.)"""
    for src in (PROOF, DIAMOND):
        g = _compile(src, placer="growth")
        r = _compile(src, placer="routed")
        assert len(r.records) <= len(g.records), (len(r.records), len(g.records))
    assert len(_compile(DIAMOND, placer="routed").records) < len(_compile(DIAMOND, placer="growth").records)


def _syms(src):
    fn, _ = F.extract_llvm_function(src)
    return fn.arguments, fn.instrs


@pytest.mark.parametrize("src", [PROOF, DIAMOND, SEL_COMPUTED, CLAMP, ARMS_AND_COND])
def test_no_foreign_cell_feeds_a_nano_gate(src):
    """Hazard invariant. A `nano_gate` accepts from ANY wired neighbour, so the only
    cell allowed to point at one is its own designated feeder (the priority cell in
    front of it) or the last relay of a route that ends at it. Holds by construction
    (a relay only ever offers to its own next cell, and the router only assigns faces
    that belong to a route); this checks it on every lowered layout so a future change
    to lowering cannot quietly break it."""
    res = _compile(src, placer="routed")
    by_pos = {(r.row, r.col): r for r in res.records}
    step = {"n": (-1, 0), "s": (1, 0), "e": (0, 1), "w": (0, -1)}
    for rec in res.records:
        if rec.core != "nano":
            continue
        for d, (dr, dc) in step.items():
            nb = by_pos.get((rec.row + dr, rec.col + dc))
            if nb is None:
                continue
            opp = {"n": "s", "s": "n", "e": "w", "w": "e"}[d]
            outs = nb.core_config.get("downstream_mask") or nb.core_config.get("routing_mask") or []
            outs = [o for o in outs] if isinstance(outs, list) else []
            if opp in outs:
                # the neighbour points AT the gate: it must be a cell that exists to feed it
                assert nb.cell_id.startswith(("main.pri_", "main.rt")), (rec.cell_id, nb.cell_id)


def test_non_planar_program_fails_loudly_never_with_a_wrong_answer():
    """A program whose dataflow has a K3,3 minor cannot be embedded on a plane with no
    crossover cell. The router must refuse it, precisely."""
    src = _ir("  %p = add i32 %x, 1\n  %q = add i32 %y, 2\n  %r = add i32 %z, 3\n"
              "  %t1 = add i32 %p, %q\n  %c1 = add i32 %t1, %r\n"
              "  %t2 = sub i32 %p, %q\n  %c2 = add i32 %t2, %r\n"
              "  %t3 = xor i32 %p, %q\n  %c3 = add i32 %t3, %r\n"
              "  %s = add i32 %c1, %c2\n  %o = add i32 %s, %c3\n  ret i32 %o",
              args="i32 %x, i32 %y, i32 %z")
    res, diags = F.compile_llvm_via_dag(src, placer="routed")
    assert res is None
    assert diags and diags[0].stage == "place"


def test_a_value_with_more_than_three_consumers_fails_loudly_on_the_router():
    src = _ir("  %a = add i32 %x, 1\n  %b = add i32 %a, 1\n  %c = add i32 %a, 2\n  %d = add i32 %a, 3\n"
              "  %e = add i32 %a, 4\n  %s1 = add i32 %b, %c\n  %s2 = add i32 %d, %e\n  %r = add i32 %s1, %s2\n  ret i32 %r")
    res, diags = F.compile_llvm_via_dag(src, placer="routed")
    assert res is None and diags[0].stage == "place"


# ---------------------------------------------------------------------------
# Fold to fit a bounded canvas; the cardinal orientation of shapes flips per band.
# ---------------------------------------------------------------------------

LONG_CHAIN = _ir("\n".join(
    [f"  %v{i} = {op} i32 {'%x' if i == 0 else f'%v{i-1}'}, {k}"
     for i, (op, k) in enumerate([("add", 3), ("xor", 5), ("add", 7), ("shl", 1), ("xor", 9), ("add", 11),
                                  ("lshr", 1), ("add", 13), ("xor", 3), ("add", 1)])]) + "\n  ret i32 %v9")


def _long_chain_ref(x):
    v = (x + 3) & M
    v ^= 5
    v = (v + 7) & M
    v = (v << 1) & M
    v ^= 9
    v = (v + 11) & M
    v >>= 1
    v = (v + 13) & M
    v ^= 3
    return (v + 1) & M


def _extent(res):
    rows = [r.row for r in res.records]
    cols = [r.col for r in res.records]
    return max(rows) - min(rows) + 1, max(cols) - min(cols) + 1


def test_folding_bounds_the_width_and_stays_correct():
    flat = _compile(LONG_CHAIN, placer="routed")
    folded = _compile(LONG_CHAIN, placer="routed", fold_width=4)
    for x in (0, 1, 100, 0x7FFFFFFF, M):
        assert F.run_in_vm(flat, {"x": x}) == _long_chain_ref(x), hex(x)
        assert F.run_in_vm(folded, {"x": x}) == _long_chain_ref(x), hex(x)
    (fh, fw), (uh, uw) = _extent(folded), _extent(flat)
    assert fw < uw and fh > uh, ((fh, fw), (uh, uw))     # narrower, taller: it folded


def test_folding_flips_the_cardinal_orientation_of_shapes_on_alternate_bands():
    """The point of Alan's requirement: once a design folds, its cells' cardinal outs
    must be RE-CHOSEN. In a flat layout every priority->op pair points east; in a
    folded one alternate bands must point west."""
    def pair_dirs(res):
        out = set()
        step = {"n": (-1, 0), "s": (1, 0), "e": (0, 1), "w": (0, -1)}
        by_pos = {(r.row, r.col): r for r in res.records}
        for r in res.records:
            if r.cell_id.startswith("main.pri_"):
                for d, (dr, dc) in step.items():
                    nb = by_pos.get((r.row + dr, r.col + dc))
                    if nb is not None and nb.cell_id == r.cell_id.replace("pri_", "", 1):
                        out.add(d)
        return out
    assert pair_dirs(_compile(SEL_COMPUTED, placer="routed")) == {"e"}
    folded = _compile(SEL_COMPUTED, placer="routed", fold_width=4)
    assert pair_dirs(folded) == {"e", "w"}
    for x in VALUES:
        assert F.run_in_vm(folded, {"x": x}) == ((x + 1) if x == 5 else (x << 2)) & M, hex(x)


def test_folding_a_branching_design_too_narrowly_fails_loudly_known_limitation():
    """Measured (points.md #800): a chain or a diamond folds down to 2 columns per band, but
    the branching `select` needs >= 4 -- with fewer, the long edges between bands cannot all
    be routed. It must be a precise `place` refusal, never a wrong layout. If the router
    learns to fold branching designs tighter, FLIP this."""
    for narrow in (2, 3):
        res, diags = F.compile_llvm_via_dag(SEL_COMPUTED, placer="routed", fold_width=narrow)
        assert res is None and diags[0].stage == "place", narrow
    assert _compile(SEL_COMPUTED, placer="routed", fold_width=4).placer == "routed"


def test_chain_and_diamond_fold_down_to_two_columns_per_band():
    for src, ref in ((DIAMOND, lambda x: ((x + 5) + (x + 15)) & M), (PROOF, lambda x: (x + 2) & M)):
        res = _compile(src, placer="routed", fold_width=2)
        for x in VALUES:
            assert F.run_in_vm(res, {"x": x}) == ref(x), hex(x)


def test_tightening_searches_for_the_smallest_workable_spacing():
    loose = _compile(DIAMOND, placer="routed", spacing=12)
    tight = _compile(DIAMOND, placer="routed")            # spacing=None -> tighten by search
    assert len(tight.records) <= len(loose.records)
    for x in VALUES:
        assert F.run_in_vm(loose, {"x": x}) == F.run_in_vm(tight, {"x": x})


# ---------------------------------------------------------------------------
# The whole verified frontend corpus, re-run under the routed placer as an oracle.
# ---------------------------------------------------------------------------

def test_entire_frontend_corpus_passes_under_the_routed_placer():
    """~100 programs already verified against independent models with the growth placer
    (shifts, every icmp predicate, select, ashr, numbered values, ...) are re-run with
    IMAGO_PLACER=routed. Only the tests that pin the GROWTH placer's own limitation are
    excluded -- they are about growth, by name."""
    env = dict(os.environ, IMAGO_PLACER="routed", PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         os.path.join(HERE, "test_llvm_dag_frontend_v1.py"),
         os.path.join(HERE, "test_dag_frontend_opcode_ports_v1.py"),
         "-k", "not growth_placer_limit and not growth_cannot_place"],
        capture_output=True, text=True, env=env)
    assert proc.returncode == 0, proc.stdout[-1500:] + proc.stderr[-500:]


# ---------------------------------------------------------------------------
# The nano gate has no input gating (points.md #802).
# ---------------------------------------------------------------------------

def _routed_xor():
    return _compile(_ir("  %r = xor i32 %x, 12\n  ret i32 %r"), placer="routed")


def _add_stray_next_to_gate(res, point_at_gate):
    import vix_tile_library_v1 as vtl
    step = {"n": (-1, 0), "s": (1, 0), "e": (0, 1), "w": (0, -1)}
    opp = {"n": "s", "s": "n", "e": "w", "w": "e"}
    gate = [r for r in res.records if r.core == "nano"][0]
    taken = {(r.row, r.col) for r in res.records}
    for face, (dr, dc) in step.items():
        pos = (gate.row + dr, gate.col + dc)
        if pos not in taken:
            cell = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": opp[face] if point_at_gate else face}, cell_id="stray",
                             rel_row=pos[0], rel_col=pos[1], preload_value=0xFF)
            res.icm.patterns["main"].cells.append(cell)
            res.records, _ = res.icm.flatten()
            return res
    raise AssertionError("no free face next to the gate")


def test_a_neighbour_that_does_not_point_at_a_nano_gate_is_harmless_one_that_does_corrupts_it():
    """Documents the semantics behind `audit_gate_feeders`: the gate accepts from ANY wired
    neighbour, so what matters is only whether something OFFERS toward it."""
    for x in (0, 5, 100):
        away = _add_stray_next_to_gate(_routed_xor(), point_at_gate=False)
        at = _add_stray_next_to_gate(_routed_xor(), point_at_gate=True)
        assert F.run_in_vm(away, {"x": x}) == (x ^ 12)                 # untouched
        assert F.run_in_vm(at, {"x": x}) != (x ^ 12)                   # silently wrong


def test_the_gate_feeder_audit_catches_a_stray_and_passes_every_routed_layout():
    for src in (PROOF, DIAMOND, SEL_COMPUTED, CLAMP, ARMS_AND_COND):
        res = _compile(src, placer="routed")
        # `res.icm` cells are the pre-lowered HierCells; the audit must be clean on all of them
        assert V.audit_gate_feeders(res.icm.patterns["main"].cells) == []
    bad = _add_stray_next_to_gate(_routed_xor(), point_at_gate=True)
    assert V.audit_gate_feeders(bad.icm.patterns["main"].cells)
    ok = _add_stray_next_to_gate(_routed_xor(), point_at_gate=False)
    assert V.audit_gate_feeders(ok.icm.patterns["main"].cells) == []
