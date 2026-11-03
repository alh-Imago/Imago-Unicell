"""tests/vm/test_hexn_pattern_mg_v1.py -- a pattern with UN, AL, JN, BR and MG (merge) tiles (generator v5, verify v10, planner v18), 3 Nov 2026. Programs planned on it are loaded from unit files; the output words in ORDER (a merge in arbitrate mode may send several
words down one output, in arrival order) and their start ticks must equal the planner's reference and the serial VM's, at the usual constant -2 tick offset. Requires iverilog."""
import json, os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_pattern_ref_v7 as R, hexn_pattern_designer_v7 as D, hexn_bases_v9 as B, hexn_pattern_gen_v5 as P, hexn_pattern_verify_v10 as V
import hexn_icm_export_v2 as X, hexn_unit_file_v1 as U, hexn_vm_v3 as VM, hexn_wrgrid_v18 as G

N = G.Node9
RECIPE = {"n": 7, "counts": {"UN": 2, "AL": 2, "BR": 1, "MG": 2, "JN": 2}, "ram": "none"}
REG = json.load(open(os.path.join(ROOT, "docs/hex-n/data/patterns/registry.json")))      # ids come from the registry: the same kind and size must not get the same id twice
REF, _ = R.reference(RECIPE, REG)
MG = lambda mode: [N("m", "merge", ["x", "y"], cfg=dict(mode=mode))]
TASKS = {
    "arbitrate": (MG(2), ["x", "y"], ["m"]),
    "a_only": (MG(0), ["x", "y"], ["m"]),
    "b_only": (MG(1), ["x", "y"], ["m"]),
    "join_or": (MG(3), ["x", "y"], ["m"]),
    "or_join_after_add_and_shift": ([N("u", "add", ["x", "k"]), N("v", "shl", ["y"], k=3), N("z", "merge", ["u", "v"], cfg=dict(mode=3))], ["x", "k", "y"], ["z"]),
    "branch_merge_add": ([N("br", "branch", ["x", "y"], ["lo", "hi"], cfg=dict(route_lt=1, route_eq=1, route_gt=2, emit=3)), N("m", "merge", ["lo", "hi"], cfg=dict(mode=2)), N("r", "add", ["m", "c"])], ["x", "y", "c"], ["r"]),
}


def _program(name):
    t = TASKS[name]; base = D.make_base(RECIPE); plan = B.fits(base, t); assert plan, name
    return t, V.program_for(base, plan)


def test_generated_top_and_widths():
    assert not R.check_reference(REF)
    top = P.generate(REF)
    assert top.count("hexn_tile_mg_v1 #") == 2 and top.count("hexn_tile_br_v1 #") == 1 and top.count("hexn_tile_jn_v1 #") == 2
    assert sum(P.widths_of(REF)) == 2 * 35 + 4 * 25 + 1 * 66 + 2 * 24 + 40 * 12


def test_other_types_still_refused():
    ref, _ = R.reference({"n": 7, "counts": {"PR": 1, "MG": 2}, "ram": "none"}, {})
    with pytest.raises(ValueError, match="PR"): P.generate(ref)


@pytest.mark.parametrize("seed", [8, 9])
@pytest.mark.parametrize("name", list(TASKS))
def test_merge_program_matches_reference_and_serial_vm(name, seed):
    t, prog = _program(name)
    icm = X.to_icm(prog, "demo/" + name); unit = U.unit_from_icm(icm, {}, REF["name"], pattern_id=REF["pattern_id"])
    program = X.from_icm(U.unicell_view(unit)[0])
    vm = VM.SerialVM.load(icm); rnd = random.Random(seed)
    iv = {n: rnd.randrange(1 << 32) for n in t[1]}
    got = V.sim_run(REF, program, iv)
    want = G.ref9(t[0], iv); cap = vm.run(iv)
    for o in t[2]:
        assert [w for _, w in got["out"][o]] == [w for _, w in cap[o]] == want[o][1], (name, o)
        assert [tk for tk, _ in got["out"][o]] == [tk - 2 for tk, _ in cap[o]], (name, o)
        assert len(got["out"][o]) == (2 if name == "arbitrate" else 1), (name, len(got["out"][o]))      # arbitrate sends both words, in arrival order


def test_committed_pnr_record_verifies_this_reference():
    n = "%s_%s" % (REF["name"], REF["pattern_id_hex"])
    rec = json.load(open(os.path.join(ROOT, "docs/hex-n/data/pnr/%s.pnr.json" % n)))
    ref = json.load(open(os.path.join(ROOT, "docs/hex-n/data/patterns/%s.json" % n)))
    assert ref["content_hash"] == REF["content_hash"], "the committed reference is no longer what the designer makes"
    assert V.verified(ref, rec) and abs(rec["deviation_pct"]) <= 10 and rec["fmax_mhz"] >= 27


def test_merge_cost_in_planner_v18():
    assert G.CELLTYPES["MG"][1] == 146 and G.CELLTYPES["BR"][1] == 237 and G.CELLTYPES["JN"][1] == 223
