"""tests/vm/test_hexn_pattern_prsq_v1.py -- a pattern with UN, AL, PR (priority) and SQ (sequencer) tiles (generator v8, verify v15, planner v19), 3 Nov 2026, Alan 10:07. Programs planned on it are loaded from unit files; the output words in ORDER and their start ticks must equal the serial VM's (constant -2 tick offset), and the words equal the planner's reference. Requires iverilog."""
import json, os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_pattern_ref_v9 as R, hexn_pattern_designer_v9 as D, hexn_bases_v11 as B, hexn_pattern_gen_v8 as P, hexn_pattern_verify_v15 as V
import hexn_icm_export_v3 as X, hexn_unit_file_v1 as U, hexn_vm_v4 as VM, hexn_wrgrid_v19 as G

N = G.Node9
RECIPE = {"n": 7, "counts": {"UN": 1, "AL": 1, "PR": 1, "SQ": 1}, "ram": "none"}
REG = json.load(open(os.path.join(ROOT, "docs/hex-n/data/patterns/registry.json")))
REF, _ = R.reference(RECIPE, REG)
PR = lambda **c: [N("p", "prio", ["x", "y", "z"], cfg=c)]
TASKS = {
    "strict_xyz": (PR(mask=7, ranks=(0, 1, 2, 3), mode=0), ["x", "y", "z"], ["p"]),
    "strict_yzx": (PR(mask=7, ranks=(2, 0, 1, 3), mode=0), ["x", "y", "z"], ["p"]),
    "masked_y": (PR(mask=5, ranks=(0, 1, 2, 3), mode=0), ["x", "y", "z"], ["p"]),
    "weighted": (PR(mask=7, ranks=(1, 2, 3, 0), mode=1), ["x", "y", "z"], ["p"]),
    "sequenced_yxz": (PR(mask=7, ranks=(0, 0, 0, 0), mode=2, len=3, order=(1, 0, 2, 0)), ["x", "y", "z"], ["p"]),
}
RECIPE_J = {"n": 7, "counts": {"JN": 4, "PR": 1}, "ram": "none"}       # a priority's output order is dynamic: only a JOIN tile can take it on (found in the planner: UN or AL after a priority has no plan)
REF_J, _ = R.reference(RECIPE_J, REG)
T_JOIN = ([N("p", "prio", ["x", "y", "z"], cfg=dict(mask=7, ranks=(0, 1, 2, 3), mode=0)), N("r", "add", ["p", "k"])], ["x", "y", "z", "k"], ["r"])


def _program(t, recipe=None):
    base = D.make_base(recipe or RECIPE); plan = B.fits(base, t); assert plan
    return V.program_for(base, plan)


def _load(prog, name):
    icm = X.to_icm(prog, "demo/" + name); unit = U.unit_from_icm(icm, {}, REF["name"], pattern_id=REF["pattern_id"])
    return icm, X.from_icm(U.unicell_view(unit)[0])


def test_generated_top_and_widths():
    assert not R.check_reference(REF)
    top = P.generate(REF)
    assert top.count("hexn_tile_pr_v1 #") == 1 and top.count("hexn_tile_sq_v1 #") == 1 and top.count("hexn_tile_al_v2 #") == 6
    assert sum(P.widths_of(REF)) == 35 + 6 * 25 + 41 + 150 + 40 * 12


def test_other_types_still_refused():
    ref, _ = R.reference({"n": 7, "counts": {"BR": 1, "MG": 1}, "ram": "none"}, {})
    P.generate(ref)                                                         # fine: those have tiles
    ref["work_cells"][0]["type"] = "XX"
    with pytest.raises(ValueError, match="XX"): P.generate(ref)


@pytest.mark.parametrize("seed", [3, 4])
@pytest.mark.parametrize("name", list(TASKS))
def test_priority_matches_reference_and_serial_vm(name, seed):
    t = TASKS[name]; prog = _program(t); icm, program = _load(prog, name)
    vm = VM.SerialVM.load(icm); rnd = random.Random(seed)
    iv = {n: rnd.randrange(1 << 32) for n in t[1]}
    got = V.sim_run(REF, program, iv); want = G.ref9(t[0], iv); cap = vm.run(iv)
    for o in t[2]:
        gw = [w for _, w in got["out"][o]]
        assert gw == [w for _, w in cap[o]], (name, o, got["out"][o], cap[o])
        assert sorted(gw) == sorted(want[o][1]), (name, o)
        assert [tk for tk, _ in got["out"][o]] == [tk - 2 for tk, _ in cap[o]], (name, o)


def test_priority_then_join_add_matches_serial_vm():
    t = T_JOIN; base = D.make_base(RECIPE_J); plan = B.fits(base, t); assert plan; prog = V.program_for(base, plan)
    icm = X.to_icm(prog, "demo/pj"); unit = U.unit_from_icm(icm, {}, REF_J["name"], pattern_id=REF_J["pattern_id"]); program = X.from_icm(U.unicell_view(unit)[0])
    rnd = random.Random(5); iv = {n: rnd.randrange(1 << 32) for n in t[1]}
    got = V.sim_run(REF_J, program, iv); cap = VM.SerialVM.load(icm).run(iv)
    assert [w for _, w in got["out"]["r"]] == [w for _, w in cap["r"]] and got["out"]["r"], (got["out"], cap)
    assert [tk for tk, _ in got["out"]["r"]] == [tk - 2 for tk, _ in cap["r"]]


def test_sequencer_values_and_timing_match_serial_vm():
    t = ([N("s", "seq", ["trig"], cfg=dict(vals=[1000, 2000, 3000, 4000], len=3))], ["trig"], ["s"])
    prog = _program(t); icm, program = _load(prog, "seq")
    got = V.sim_run(REF, program, {"trig": 0x12345678}); cap = VM.SerialVM.load(icm).run({"trig": 0x12345678})
    assert [w for _, w in got["out"]["s"]] == [w for _, w in cap["s"]] == [1000]
    assert [tk for tk, _ in got["out"]["s"]] == [tk - 2 for tk, _ in cap["s"]]


def test_sequencer_steps_through_its_values_and_wraps():
    t = ([N("s", "seq", ["trig"], cfg=dict(vals=[1000, 2000, 3000, 4000], len=3))], ["trig"], ["s"])
    prog = _program(t); icm, program = _load(prog, "seq")
    steps = [("words", {"trig": 7}), ("idle", 10)] * 4
    res = V.sim_session(REF, program, steps, tail=160)
    assert [w for _, w in res["out"]["s"]] == [1000, 2000, 3000, 1000]                  # len 3: wraps after the third value


def test_wipe_resets_sequencer_position():
    t = ([N("s", "seq", ["trig"], cfg=dict(vals=[1000, 2000, 3000, 4000], len=3))], ["trig"], ["s"])
    prog = _program(t); icm, program = _load(prog, "seq")
    res = V.sim_session(REF, program, [("words", {"trig": 7}), ("idle", 10), ("words", {"trig": 7}), ("idle", 10), ("clear", 140), ("idle", 3), ("words", {"trig": 7}), ("idle", 10)], tail=160)
    assert [w for _, w in res["out"]["s"]] == [1000, 2000, 1000]                          # after the wipe the position is value 0 again


def test_wipe_drops_a_waiting_priority_word():
    t = PR(mask=7, ranks=(0, 0, 0, 0), mode=2, len=3, order=(1, 0, 2, 0)), ["x", "y", "z"], ["p"]
    prog = _program(t); icm, program = _load(prog, "pw")
    xn, yn, zn = 0x11111111, 0x22222222, 0x33333333
    res = V.sim_session(REF, program, [("words", {"x": 0xAAAAAAAA}), ("idle", 40), ("clear", 140), ("idle", 3), ("words", {"x": xn, "y": yn, "z": zn})], tail=300)
    assert [w for _, w in res["out"]["p"]] == [yn, xn, zn]                                  # the old x (waiting for its turn) is gone, the turn is back at y


@pytest.mark.parametrize("ref", ["REF", "REF_J"])
def test_committed_pnr_record_verifies_this_reference(ref):
    rf = globals()[ref]
    n = "%s_%s" % (rf["name"], rf["pattern_id_hex"])
    rec = json.load(open(os.path.join(ROOT, "docs/hex-n/data/pnr/%s.pnr.json" % n)))
    f = json.load(open(os.path.join(ROOT, "docs/hex-n/data/patterns/%s.json" % n)))
    assert f["content_hash"] == rf["content_hash"], "the committed reference is no longer what the designer makes"
    assert V.verified(f, rec) and abs(rec["deviation_pct"]) <= 10 and rec["fmax_mhz"] >= 27


def test_costs_in_planner_v19():
    assert G.CELLTYPES["PR"][1] == 720 and G.CELLTYPES["SQ"][1] == 157 and G.CELLTYPES["LT"][1] == 3 and G.CELLTYPES["MG"][1] == 146
