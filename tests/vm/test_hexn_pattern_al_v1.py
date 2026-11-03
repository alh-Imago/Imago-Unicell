"""tests/vm/test_hexn_pattern_al_v1.py -- a pattern with UN and AL tiles (generator v2, verify v2), 3 Nov 2026. Programs planned on it are loaded through the three-width chain and the output words must equal the planner's reference and the
serial VM's, at the fixed 2-tick offset. Requires iverilog."""
import json, os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_pattern_ref_v3 as R, hexn_pattern_designer_v3 as D, hexn_bases_v5 as B4, hexn_pattern_gen_v2 as P, hexn_pattern_verify_v3 as V
import hexn_icm_export_v2 as X, hexn_unit_file_v1 as U, hexn_vm_v2 as VM, hexn_wrgrid_v14 as G

N = G.Node9
RECIPE = {"n": 7, "counts": {"UN": 2, "AL": 7}, "ram": "none"}
TASKS = {
    "scale_offset": ([N("m", "shl", ["x"], k=3), N("y", "add", ["m", "z"])], ["x", "z"], ["y"]),
    "diff": ([N("y", "sub", ["x", "z"])], ["x", "z"], ["y"]),
    "diff_rev": ([N("y", "sub", ["z", "x"])], ["x", "z"], ["y"]),
    "mix": ([N("a", "and", ["x", "z"]), N("b", "xor", ["a", "x"]), N("y", "or", ["b", "z"])], ["x", "z"], ["y"]),
}
REF, _ = R.reference(RECIPE, {})


def _program(name):
    t = TASKS[name]; base = D.make_base(RECIPE); plan = B4.fits(base, t); assert plan, name
    return t, V.program_for(base, plan)


def test_generated_top_has_both_tile_kinds():
    assert not R.check_reference(REF)
    top = P.generate(REF)
    assert top.count("hexn_tile_v2 #") == 2 and top.count("hexn_tile_al_v1 #") == 7 and top.count("hexn_rcore_flag_v2 #") == 40
    assert sum(P.widths_of(REF)) == 2 * 35 + 7 * 25 + 40 * 12


def test_other_types_still_refused():
    ref, _ = R.reference({"n": 7, "counts": {"JN": 3, "AL": 1}, "ram": "none"}, {})
    with pytest.raises(ValueError, match="JN"): P.generate(ref)


@pytest.mark.parametrize("name", list(TASKS))
def test_program_matches_reference_and_serial_vm(name):
    t, prog = _program(name)
    icm = X.to_icm(prog, "demo/" + name); unit = U.unit_from_icm(icm, {}, REF["name"], pattern_id=REF["pattern_id"])
    program = X.from_icm(U.unicell_view(unit)[0])
    vm = VM.SerialVM.load(icm); rnd = random.Random(5)
    iv = {n: rnd.randrange(1 << 32) for n in t[1]}
    got = V.sim_run(REF, program, iv)
    want = G.ref9(t[0], iv); cap = vm.run(iv)
    for o in t[2]:
        assert [w for _, w in got["out"][o]] == [w for _, w in cap[o]] == want[o][1]
        assert [tk for tk, _ in got["out"][o]] == [tk - 2 for tk, _ in cap[o]]


def test_committed_pnr_record_verifies_this_reference():
    rec = json.load(open(os.path.join(ROOT, "docs/hex-n/data/pnr/J0U2_7_17000001.pnr.json")))
    ref = json.load(open(os.path.join(ROOT, "docs/hex-n/data/patterns/J0U2_7_17000001.json")))
    assert ref["content_hash"] == REF["content_hash"], "the committed reference is no longer what the designer makes"
    assert V.verified(ref, rec) and abs(rec["deviation_pct"]) <= 10 and rec["fmax_mhz"] >= 27


def test_aligned_core_cost_in_planner_v14():
    assert G.CELLTYPES["AL"][1] == 11 and G.TILE_EXTRA == 39
