"""tests/vm/test_hexn_wipe_v1.py -- the GENERAL WIPE (3 Nov 2026, Alan 09:50 'then the general wipe command'). Every cell of the generated pattern (generator v7: hexn_tile_v3, _al_v2, _jn_v2, _br_v2, _mg_v2, hexn_rcore_flag_v3, hexn_ramhold_v1) has a `clear` input; the wipe is `clear` held high
(at least 130 clocks if RAM hold cells are present). It clears words in flight, FIFO 'have' flags, counters, carries and state machines; the configuration chain is NOT touched.
The hazard it answers: a word STRANDED in a join / branch / merge cell (one operand arrived, the partner never came). Without a wipe the next run pairs the stale word with the new partner and gives a wrong answer; with the wipe it gives the right one.
Each case is run twice on the same loaded pattern: with the wipe (right answer, equal to the planner's reference) and without it (the control: the stale pairing, a DIFFERENT answer - proving the wipe is what fixes it). Requires iverilog."""
import json, os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_pattern_ref_v8 as R, hexn_pattern_designer_v8 as D, hexn_bases_v10 as B, hexn_pattern_gen_v7 as P, hexn_pattern_verify_v13 as V
import hexn_icm_export_v3 as X, hexn_unit_file_v1 as U, hexn_vm_v4 as VM, hexn_wrgrid_v18 as G

N = G.Node9
RECIPE = {"n": 7, "counts": {"UN": 2, "AL": 2, "BR": 1, "MG": 2, "JN": 2}, "ram": "none"}
REG = json.load(open(os.path.join(ROOT, "docs/hex-n/data/patterns/registry.json")))
REF, _ = R.reference(RECIPE, REG)
WIPE = 140
# name: (task, stale x word, new x word, new second word)
CASES = {
    "join_lt": (([N("y", "lt", ["x", "z"])], ["x", "z"], ["y"]), 0x00000001, 0xF0000000, 0x80000000),
    "merge_join_or": (([N("m", "merge", ["x", "z"], cfg=dict(mode=3))], ["x", "z"], ["m"]), 0x0000000F, 0x000000F0, 0x00000100),
    "branch": (([N("br", "branch", ["x", "z"], ["lo", "hi"], cfg=dict(route_lt=1, route_eq=1, route_gt=2, emit=1))], ["x", "z"], ["lo", "hi"]), 9, 1, 5),
}


def _loaded(name):
    t = CASES[name][0]; base = D.make_base(RECIPE); plan = B.fits(base, t); assert plan, name
    prog = V.program_for(base, plan)
    icm = X.to_icm(prog, "demo/wipe_" + name); unit = U.unit_from_icm(icm, {}, REF["name"], pattern_id=REF["pattern_id"])
    return t, prog, X.from_icm(U.unicell_view(unit)[0])


def _words(res, outs, after):
    return {o: [w for tk, w in res["out"][o] if tk >= after] for o in outs}


def _session(program, x_stale, x_new, z_new, wipe):
    steps = [("words", {"x": x_stale}), ("idle", 6)] + ([("clear", WIPE), ("idle", 3)] if wipe else [("idle", WIPE + 3)]) + [("words", {"x": x_new, "z": z_new})]
    res = V.sim_session(REF, program, steps, tail=160)
    return res, res["starts"][-1]


@pytest.mark.parametrize("name", ["join_lt", "merge_join_or", "branch"])
def test_wipe_clears_a_stranded_word(name):
    t, prog, program = _loaded(name)
    assert {c["type"] for c in prog["cells"].values()} & {"JN", "BR", "MG"}
    _, xs, xn, zn = CASES[name]
    want = G.ref9(t[0], {"x": xn, "z": zn})
    res, last = _session(program, xs, xn, zn, True)
    ctl, last2 = _session(program, xs, xn, zn, False)
    for o in t[2]:
        assert not [1 for tk, w in res["out"][o] if tk < last], "nothing may come out before the second operand"      # only x was sent in phase 1
        assert not [1 for tk, w in ctl["out"][o] if tk < last2]
    assert _words(res, t[2], last) == {o: want[o][1] for o in t[2]}, "with the wipe the answer must equal the planner's reference for the NEW words"
    assert _words(ctl, t[2], last2) != _words(res, t[2], last), "the control (no wipe) must give a different answer: the stale word pairs with the new partner"


def test_wipe_does_not_disturb_a_clean_run_and_keeps_the_timing():
    t, prog, program = _loaded("join_lt")
    _, xs, xn, zn = CASES["join_lt"]
    plain = V.sim_session(REF, program, [("words", {"x": xn, "z": zn})], tail=160)
    wiped = V.sim_session(REF, program, [("clear", WIPE), ("idle", 3), ("words", {"x": xn, "z": zn})], tail=160)
    a = [(tk, w) for tk, w in plain["out"]["y"]]; b = [(tk - WIPE - 3, w) for tk, w in wiped["out"]["y"]]
    assert a == b and a, (a, b)


def test_two_wipes_in_a_row_and_wipe_with_nothing_loaded_data():
    t, prog, program = _loaded("join_lt")
    _, xs, xn, zn = CASES["join_lt"]
    want = G.ref9(t[0], {"x": xn, "z": zn})["y"][1]
    res = V.sim_session(REF, program, [("words", {"x": xs}), ("clear", WIPE), ("clear", WIPE), ("words", {"x": xn, "z": zn})], tail=160)
    assert [w for tk, w in res["out"]["y"]] == want


def test_ram_pattern_wipe_leaves_holds_working():
    rec = {"n": 7, "counts": {"UN": 2, "AL": 7}, "ram": "lead2"}
    reg = json.load(open(os.path.join(ROOT, "docs/hex-n/data/patterns/registry.json")))
    ref, _ = R.reference(rec, reg)
    t = ([N("m", "shl", ["x"], k=3), N("y", "add", ["m", "z"])], ["x", "z"], ["y"])
    base = D.make_base(rec); plan = B.fits(base, t); prog = V.program_for(base, plan); assert prog["holds"]
    icm = X.to_icm(prog, "demo/wipe_ram"); unit = U.unit_from_icm(icm, {}, ref["name"], pattern_id=ref["pattern_id"]); program = X.from_icm(U.unicell_view(unit)[0])
    rnd = random.Random(5); iv = {n: rnd.randrange(1 << 32) for n in t[1]}
    want = G.ref9(t[0], iv)["y"][1]
    plain = V.sim_session(ref, program, [("words", iv)], tail=200)
    wiped = V.sim_session(ref, program, [("words", {"x": 0xFFFFFFFF, "z": 0xFFFFFFFF}), ("clear", WIPE), ("idle", 3), ("words", iv)], tail=200)
    assert [w for tk, w in plain["out"]["y"]] == want
    assert [w for tk, w in wiped["out"]["y"] if tk >= wiped["starts"][-1]] == want
    assert [(tk - plain["starts"][0]) for tk, w in plain["out"]["y"]] == [(tk - wiped["starts"][-1]) for tk, w in wiped["out"]["y"] if tk >= wiped["starts"][-1]]
