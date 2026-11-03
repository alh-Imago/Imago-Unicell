"""tests/vm/test_hexn_pattern_jn_v2.py -- a pattern with UN, AL and JN (join) tiles (generator v3, verify v6, planner v16 with lt / min / max on the RTL's timing), 3 Nov 2026. Programs planned on it are loaded through the chain and the output words must equal the planner's reference and the serial VM's,
at a constant offset per task (-2 for the add family; lt and min/max differ, see TASKS). Requires iverilog."""
import json, os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_pattern_ref_v5 as R, hexn_pattern_designer_v5 as D, hexn_bases_v7 as B5, hexn_pattern_gen_v3 as P, hexn_pattern_verify_v6 as V
import hexn_icm_export_v2 as X, hexn_unit_file_v1 as U, hexn_vm_v3 as VM, hexn_wrgrid_v16 as G

N = G.Node9
RECIPE = {"n": 7, "counts": {"UN": 2, "AL": 3, "JN": 4}, "ram": "none"}
# v16: the model now follows the RTL for lt / min / max (hexn_wrgrid_v8b), so the offset RTL minus serial VM is the same constant -2 for EVERY task (v1 test: lt -1, min/max +1 against the old model).
TASKS = {
    "lt": ([N("y", "lt", ["x", "z"])], ["x", "z"], ["y"], -2),
    "min": ([N("y", "min", ["x", "z"])], ["x", "z"], ["y"], -2),
    "min_swapped": ([N("y", "min", ["z", "x"])], ["x", "z"], ["y"], -2),
    "late_add": ([N("m", "shl", ["x"], k=3), N("y", "add", ["m", "z"])], ["x", "z"], ["y"], -2),
    "lt_late": ([N("m", "shl", ["x"], k=3), N("y", "lt", ["m", "z"])], ["x", "z"], ["y"], -2),
    "max_late": ([N("m", "shl", ["x"], k=1), N("y", "max", ["z", "m"])], ["x", "z"], ["y"], -2),
    "max_sub": ([N("a", "max", ["x", "z"]), N("y", "sub", ["a", "z"])], ["x", "z"], ["y"], -2),
    "lt_then_add": ([N("a", "lt", ["x", "z"]), N("y", "add", ["a", "z"])], ["x", "z"], ["y"], -2),
}
REF, _ = R.reference(RECIPE, {})


def _program(name):
    t = TASKS[name]; base = D.make_base(RECIPE); plan = B5.fits(base, t[:3]); assert plan, name
    return t, V.program_for(base, plan)


def test_generated_top_has_all_three_tile_kinds():
    assert not R.check_reference(REF)
    top = P.generate(REF)
    assert top.count("hexn_tile_v2 #") == 2 and top.count("hexn_tile_al_v1 #") == 3 and top.count("hexn_tile_jn_v1 #") == 4
    assert sum(P.widths_of(REF)) == 2 * 35 + 7 * 25 + 40 * 12


def test_other_types_still_refused():
    ref, _ = R.reference({"n": 7, "counts": {"BR": 2, "JN": 1}, "ram": "none"}, {})
    with pytest.raises(ValueError, match="BR"): P.generate(ref)


@pytest.mark.parametrize("name", list(TASKS))
def test_program_matches_reference_and_serial_vm(name):
    t, prog = _program(name)
    icm = X.to_icm(prog, "demo/" + name); unit = U.unit_from_icm(icm, {}, REF["name"], pattern_id=REF["pattern_id"])
    program = X.from_icm(U.unicell_view(unit)[0])
    vm = VM.SerialVM.load(icm); rnd = random.Random(6)
    iv = {n: rnd.randrange(1 << 32) for n in t[1]}
    got = V.sim_run(REF, program, iv)
    want = G.ref9(t[0], iv); cap = vm.run(iv)
    for o in t[2]:
        assert [w for _, w in got["out"][o]] == [w for _, w in cap[o]] == want[o][1]
        assert [tk for tk, _ in got["out"][o]] == [tk + t[3] for tk, _ in cap[o]]


def test_committed_pnr_record_verifies_this_reference():
    n = "%s_%s" % (REF["name"], REF["pattern_id_hex"])
    rec = json.load(open(os.path.join(ROOT, "docs/hex-n/data/pnr/%s.pnr.json" % n)))
    ref = json.load(open(os.path.join(ROOT, "docs/hex-n/data/patterns/%s.json" % n)))
    assert ref["content_hash"] == REF["content_hash"], "the committed reference is no longer what the designer makes"
    assert V.verified(ref, rec) and abs(rec["deviation_pct"]) <= 10 and rec["fmax_mhz"] >= 27


def test_join_cost_in_planner_v15():
    assert G.CELLTYPES["JN"][1] == 223 and G.CELLTYPES["AL"][1] == 11


def test_core_model_delay_for_buffered_ops():
    import hexn_wrgrid_v8b as M, hexn_wrgrid_v8 as M0
    for op, late in (("lt", 1), ("min", 3), ("max", 3)):
        assert M.delta(op, "join") == M0.delta(op, "join") + late
    for op in ("add", "sub", "and", "or", "xor"):
        assert M.delta(op, "join") == M0.delta(op, "join")


def _aligned_after_buffered(planner_chain):
    """lt (+1) and min (+3) feed an AL xor: the planner may only place it ALIGNED if it knows the true arrival ticks. Returns (RTL words, reference words, kinds placed)."""
    D_, B_, V_, G_, R_ = planner_chain
    rec = {"n": 9, "counts": {"JN": 2, "UN": 3, "AL": 6}, "ram": "none"}
    base = D_.make_base(rec); ref, _ = R_.reference(rec, {})
    nn = G_.Node9; t = ([nn("a", "lt", ["x", "z"]), nn("b", "min", ["x", "z"]), nn("y", "xor", ["a", "b"])], ["x", "z"], ["y"])
    plan = B_.fits(base, t); assert plan
    pr = V_.program_for(base, plan)
    icm = X.to_icm(pr, "demo/ab"); unit = U.unit_from_icm(icm, {}, ref["name"], pattern_id=ref["pattern_id"]); program = X.from_icm(U.unicell_view(unit)[0])
    rnd = random.Random(1); iv = {n: rnd.randrange(1 << 32) for n in t[1]}
    got = V_.sim_run(ref, program, iv)
    return [w for _, w in got["out"]["y"]], G_.ref9(t[0], iv)["y"][1], sorted((v["type"], v["kind"], v["mode"]) for v in pr["cells"].values())


def test_aligned_consumer_after_lt_and_min_is_right_with_v16():
    got, want, kinds = _aligned_after_buffered((D, B5, V, G, R))
    assert ("AL", "xor", "aligned") in kinds and got == want


def test_old_planner_v15_misaligned_the_same_task():
    """the bug this version fixes, kept as a regression record: with the v15 timing the planner also placed the xor ALIGNED, and the RTL gave a different word"""
    import hexn_pattern_ref_v4 as R4, hexn_pattern_designer_v4 as D4, hexn_bases_v6 as B6, hexn_pattern_verify_v5 as V5, hexn_wrgrid_v15 as G15
    got, want, kinds = _aligned_after_buffered((D4, B6, V5, G15, R4))
    assert ("AL", "xor", "aligned") in kinds and got != want
