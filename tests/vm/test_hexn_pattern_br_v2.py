"""tests/vm/test_hexn_pattern_br_v1.py -- a pattern with UN, AL, JN and BR (branch) tiles (generator v4, verify v7, planner v16), 3 Nov 2026. Programs planned on it are loaded from unit files; output words (and which outputs stay EMPTY because a branch
did not route there) must equal the planner's reference and the serial VM's, at the usual constant -2 tick offset. Inputs include equal words and signed cases (negative against positive). Requires iverilog."""
import json, os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_pattern_ref_v6 as R, hexn_pattern_designer_v6 as D, hexn_bases_v8 as B, hexn_pattern_gen_v4 as P, hexn_pattern_verify_v8 as V
import hexn_icm_export_v2 as X, hexn_unit_file_v1 as U, hexn_vm_v3 as VM, hexn_wrgrid_v17 as G

N = G.Node9
RECIPE = {"n": 7, "counts": {"UN": 2, "AL": 2, "BR": 2, "JN": 3}, "ram": "none"}
REF, _ = R.reference(RECIPE, {})
BR = lambda **c: [N("br", "branch", ["x", "y"], ["lo", "hi"], cfg=c)]
TASKS = {
    "diff_both_ways": (BR(route_lt=1, route_eq=1, route_gt=2, emit=3), ["x", "y"], ["lo", "hi"]),
    "a_to_both": (BR(route_lt=3, route_eq=3, route_gt=3, emit=1), ["x", "y"], ["lo", "hi"]),
    "b_lt_only": (BR(route_lt=1, route_eq=0, route_gt=0, emit=2), ["x", "y"], ["lo", "hi"]),
    "fixed_eq_hi": (BR(route_lt=0, route_eq=2, route_gt=0, emit=0, fixed=0xCAFEF00D), ["x", "y"], ["lo", "hi"]),
    "drop_all": (BR(route_lt=0, route_eq=0, route_gt=0, emit=1), ["x", "y"], ["lo", "hi"]),
}
CASES = {"random": None, "equal": (0x12345678, 0x12345678), "neg_vs_pos": (0xFFFFFFF0, 5), "pos_vs_neg": (5, 0xFFFFFFF0), "both_neg": (0x80000001, 0xFFFFFFFF)}


def _program(name):
    t = TASKS[name]; base = D.make_base(RECIPE); plan = B.fits(base, t); assert plan, name
    return t, V.program_for(base, plan)


def test_generated_top_and_widths():
    assert not R.check_reference(REF)
    top = P.generate(REF)
    assert top.count("hexn_tile_br_v1 #") == 2 and top.count("hexn_tile_jn_v1 #") == 3 and top.count("hexn_tile_al_v1 #") == 2 and top.count("hexn_tile_v2 #") == 2
    assert sum(P.widths_of(REF)) == 2 * 35 + 5 * 25 + 2 * 66 + 40 * 12


def test_other_types_still_refused():
    ref, _ = R.reference({"n": 7, "counts": {"MG": 2, "BR": 1}, "ram": "none"}, {})
    with pytest.raises(ValueError, match="MG"): P.generate(ref)


@pytest.mark.parametrize("case", list(CASES))
@pytest.mark.parametrize("name", list(TASKS))
def test_branch_program_matches_reference_and_serial_vm(name, case):
    t, prog = _program(name)
    icm = X.to_icm(prog, "demo/" + name); unit = U.unit_from_icm(icm, {}, REF["name"], pattern_id=REF["pattern_id"])
    program = X.from_icm(U.unicell_view(unit)[0])
    vm = VM.SerialVM.load(icm)
    if CASES[case] is None:
        rnd = random.Random(8); iv = {n: rnd.randrange(1 << 32) for n in t[1]}
    else:
        iv = dict(zip(t[1], CASES[case]))
    got = V.sim_run(REF, program, iv)
    want = G.ref9(t[0], iv); cap = vm.run(iv)
    for o in t[2]:
        assert [w for _, w in got["out"][o]] == [w for _, w in cap[o]] == want[o][1], (name, case, o)
        assert [tk for tk, _ in got["out"][o]] == [tk - 2 for tk, _ in cap[o]], (name, case, o)


def test_committed_pnr_record_verifies_this_reference():
    n = "%s_%s" % (REF["name"], REF["pattern_id_hex"])
    rec = json.load(open(os.path.join(ROOT, "docs/hex-n/data/pnr/%s.pnr.json" % n)))
    ref = json.load(open(os.path.join(ROOT, "docs/hex-n/data/patterns/%s.json" % n)))
    assert ref["content_hash"] == REF["content_hash"], "the committed reference is no longer what the designer makes"
    assert V.verified(ref, rec) and abs(rec["deviation_pct"]) <= 10 and rec["fmax_mhz"] >= 27


def test_branch_cost_in_planner_v17():
    assert G.CELLTYPES["BR"][1] == 237 and G.CELLTYPES["JN"][1] == 223
