import json, os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_bases_v2 as B, hexn_wrgrid_v11 as G, hexn_icm_export_v2 as X
import pytest

ALL = B.all_tasks()
NAMES = ("old/scale_offset", "old/diff_abs", "new/merge_two", "new/prio3", "new/branch_route", "new/seq_add")


def _prog(nm):
    t = ALL[nm]; b = B.tailored(t); P = B.fits(b, t)
    return b, t, B.program_of(b, P, t)


@pytest.mark.parametrize("nm", NAMES)
def test_round_trip_and_replay(nm):
    b, t, prog = _prog(nm)
    d = X.to_icm(prog, nm)
    d = json.loads(json.dumps(d))                                   # only what survives being written as text
    back = X.from_icm(d)
    assert json.loads(json.dumps(prog)) == json.loads(json.dumps(back))
    rnd = random.Random(5)
    for _ in range(3):                                               # the rebuilt program runs on the twin and equals the reference
        iv = {n: rnd.randrange(1 << 20) for n in t[1]}
        cap = B.run_program(b, back, t, iv); ref = G.ref9(t[0], iv)
        for o in t[2]:
            got = [w for _, w in cap[o]]; ordd, want = ref[o]
            assert (got == want) if ordd else (sorted(got) == sorted(want))


def test_damage_and_faces_and_report():
    b, t, prog = _prog("old/scale_offset")
    d = json.loads(json.dumps(X.to_icm(prog, "x")))
    rep = X.report(d); assert sum(rep["routing_by_core"].values()) == len(prog["routing"]) and rep["work_cells"] == len(prog["cells"])
    d2 = json.loads(json.dumps(d)); d2["records"][0]["col"] += 1
    with pytest.raises(ValueError): X.from_icm(d2)
    with pytest.raises(NotImplementedError): X.to_icm(prog, "x", faces=6)


def test_native_tiles_are_used_and_counted():
    tot = {}
    for nm in NAMES:
        b, t, prog = _prog(nm)
        for k, v in X.report(json.loads(json.dumps(X.to_icm(prog, nm))))["routing_by_core"].items(): tot[k] = tot.get(k, 0) + v
    assert tot.get("cross", 0) > 0 and tot.get("corner", 0) > 0                     # the native cores are really used
    assert sum(v for k, v in tot.items() if k != "route") > sum(tot.get("route", 0) for _ in [0])   # most cells need no private core


def test_bridge_record_and_unit_tie():
    import hexn_unit_file_v1 as U
    b, t, prog = _prog("old/scale_offset")
    pad = prog["pads_out"]["y"]
    d = json.loads(json.dumps(X.to_icm(prog, "so", bridges=[dict(name="y_out", pad=pad, direction="to_unicell", unicell_io="input_0")])))
    assert d["io"]["bridges"][0]["unicell_io"] == "input_0" and X.from_icm(d) == X.from_icm(json.loads(json.dumps(X.to_icm(prog, "so"))))   # a bridge changes no cell
    with pytest.raises(ValueError): X.to_icm(prog, "so", bridges=[dict(name="z", pad=[99, 99], direction="to_unicell")])
    with pytest.raises(ValueError): X.to_icm(prog, "so", bridges=[dict(name="z", pad=pad, direction="sideways")])
    u = U.unit_from_icm(d, {"judge_a": {"w": [1]}}, "math-1")
    assert u["header"]["name"] == "so" and u["header"]["base"] == d["bitstream"] and U.check(u) == dict(header=0, program=0, weights=0)
    assert U.unicell_view(u)[0] == d
