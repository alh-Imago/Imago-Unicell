"""tests/vm/test_hexn_patterns_v1.py -- RAM routing cells in the planner (v12), named patterns and the weighing (hexn_bases_v3), the pattern designer (hexn_pattern_designer_v1)."""
import os, sys, json
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_wrgrid_v12 as G
import hexn_bases_v3 as B3
import hexn_pattern_designer_v1 as D

ALL = B3.B2.all_tasks()


def _ramcols(R, cols): return {(r, c) for r in range(R) for c in cols if not (r % 2 == 1 and c % 2 == 1)}


def test_v12_unchanged_without_ram_and_all_tasks_ok():
    for name, (nodes, ins, outs) in G.tasks9().items():
        P = G.plan9(nodes, ins, outs, 9, 9); ok, why = G.check_task(P, nodes, ins, outs); assert ok, (name, why)
        assert not P.g.holds


def test_ram_hold_replaces_join_and_is_correct():
    nodes, ins, outs = ALL["old/chain8"]
    plain = G.plan9(nodes, ins, outs, 11, 11); held = G.plan9(nodes, ins, outs, 11, 11, ram=_ramcols(11, [4, 8]))
    assert G.check_task(held, nodes, ins, outs)[0] and G.check_task(plain, nodes, ins, outs)[0]
    assert len(held.g.holds) >= 1
    assert list(held.modes.values()).count("join") < list(plain.modes.values()).count("join")      # holds turned joins into aligned cores
    assert all(G.HOLD_MIN <= h <= G.HOLD_MAX for h in held.g.holds.values())


def test_patterns_and_options():
    lib = B3.pattern_library((7,))
    assert {b.name.split("_")[0] for b in lib} == set(B3.PATTERNS)
    t = ALL["old/scale_offset"]
    opts = B3.options(lib, t, current="math_7")
    assert opts[0][2].startswith("program on the loaded") and opts[0][0] < 1.0                # no swap: microseconds to milliseconds
    assert any(o[2].startswith("NEW") for o in opts) and [o for o in opts if o[2].startswith("NEW")][0][0] > 300     # a new bitstream costs the build time
    for sec, slots, kind, b, P in opts[:3]: assert G.check_task(P, *t)[0]


def test_designer_small_workload():
    sub = {k: ALL[k] for k in ("old/scale_offset", "old/mid", "old/diff_abs", "new/merge_two", "new/prio3", "old/chain8")}
    workload = {k: (v, 3 if k.startswith("old/") else 1) for k, v in sub.items()}
    chosen, left = D.design_patterns(workload, budget=20000, K=3, sizes=(7, 9, 11))
    assert 1 <= len(chosen) <= 3
    hosted = set()
    for r, gain in chosen:
        b = D.make_base(r); assert b.cost() <= 20000
        for nm in gain: assert B3.fits(b, workload[nm][0]), (r, nm)                         # what it claims to host, it hosts
        hosted |= set(gain)
    assert hosted | set(left) == set(workload) and not (hosted & set(left))
    pf = D.pattern_file(chosen[0][0]); s = json.dumps(pf)
    assert pf["format"] == "hexn-pattern-v1" and "tang" not in s.lower() and "kintex" not in s.lower()      # card-agnostic
    rep = D.session_report(workload, chosen, left, list(workload) * 2, "kintex")
    assert rep["tailored_seconds"] > rep["pattern_seconds"] or left                         # on a Kintex a build per design costs hours
