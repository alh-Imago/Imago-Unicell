import json, os, sys, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
import hexn_unit_file_v1 as U

W = json.load(open(os.path.join(os.path.dirname(__file__), "..", "..", "docs", "hex-n", "data", "judge_v4_h64_weights.json")))
PROG = dict(bitstream="b1", cells={"1,1": dict(type="AL", kind="add", mode=0, k=0, cfg={}, ins=[0, 1], outs=[0])}, routing={"1,2": {"E": "W"}}, pads_in={"a": [1, 0]}, pads_out={"s": [1, 3]})
OKS = dict(header=0, program=0, weights=0)


def unit():
    return U.make_unit("demo", "tang-base-1", "math-1", PROG, dict(judge_a=W))


def test_round_trip_file(tmp_path):
    u = unit(); p = str(tmp_path / "u.json"); U.save(u, p)
    v = U.load(p)
    assert v == json.loads(json.dumps(u)) and U.check(v, "tang-base-1", "math-1") == OKS
    assert v["header"]["load_order"] == ["wipe", "program", "weights", "data"]


def test_bad_part_is_isolated():
    u = unit(); u["weights"]["judge_a"]["b1"][0] += 1
    assert U.check(u) == dict(header=0, program=0, weights=U.BAD_SUM)
    u = unit(); u["program"]["routing"]["1,2"]["E"] = "N"
    assert U.check(u) == dict(header=0, program=U.BAD_SUM, weights=0)


def test_wrong_target_missing_and_magic():
    u = unit()
    assert U.check(u, base="other")["program"] == U.WRONG_TARGET and U.check(u, pattern="other")["program"] == U.WRONG_TARGET
    assert U.check(u, base="other")["weights"] == 0
    del u["weights"]; assert U.check(u)["weights"] == U.MISSING
    u = unit(); u["header"]["format"] = "x"; assert U.check(u)["header"] == U.BAD_MAGIC
    assert U.check({})["header"] == U.BAD_MAGIC


def test_unicell_adapter_ignores_weights():
    u = unit()
    prog, rep = U.unicell_view(u, "tang-base-1", "math-1")
    assert prog == json.loads(json.dumps(PROG)) and rep["weights_skipped"] == 1 and rep["program"] == 0
    u["weights"]["judge_a"]["b1"][0] += 1                      # damaged weights must not matter to UniCell
    assert U.unicell_view(u)[0] is not None
    assert U.unicell_view(U.make_unit("e", "b", "p", PROG, {}))[1]["weights_skipped"] == 0     # empty holding place is fine
    u = unit(); u["program"]["routing"]["1,2"]["E"] = "N"
    assert U.unicell_view(u)[0] is None                        # a damaged program is still refused
    assert U.unicell_view({})[0] is None


LIB = {("tang-base-1", "math-1"): dict(file="math1.fs", judges=["judge_a", "judge_b"]),
       ("tang-base-1", "logic-1"): dict(file="logic1.fs", judges=["judge_a"])}


def test_loader_plan():
    u = unit()
    s, p = U.load_plan(u, ("tang-base-1", "logic-1"), LIB)                      # wrong pattern on the card: load the right one first
    assert p == [] and s == ["load bitstream math1.fs", "wipe all cells", "load program", "load weights", "ready for data"]
    s, p = U.load_plan(u, ("tang-base-1", "math-1"), LIB)                       # already there: no bitstream load
    assert p == [] and s == ["wipe all cells", "load program", "load weights", "ready for data"]
    assert U.load_plan(u, None, LIB)[0][0] == "load bitstream math1.fs"


def test_loader_refuses_and_loads_nothing():
    u = unit()
    s, p = U.load_plan(u, None, {}); assert s == [] and "no bitstream" in p[0]
    u2 = U.make_unit("x", "tang-base-1", "logic-1", PROG, dict(judge_b=W))     # logic bitstream holds only judge_a
    s, p = U.load_plan(u2, None, LIB); assert s == [] and "judge_b" in p[0]
    u3 = unit(); u3["program"]["routing"]["1,2"]["E"] = "N"
    s, p = U.load_plan(u3, None, LIB); assert s == [] and "program part refused" in p[0]
    assert U.load_plan({}, None, LIB)[0] == []


def test_pattern_id_word_and_card_read():
    assert U.pack_id(0x00A1, 3) == 0x00A10003 and U.unpack_id(0x00A10003) == (0x00A1, 3)
    lib = {("tang-base-1", "math-1"): dict(file="math1.fs", judges=["judge_a"], pattern_id=U.pack_id(0xA1, 3))}
    u = U.make_unit("d", "tang-base-1", "math-1", PROG, dict(judge_a=W), pattern_id=U.pack_id(0xA1, 3))
    assert U.load_plan(u, None, lib, card_pattern_id=U.pack_id(0xA1, 3))[0][0] == "wipe all cells"            # the card says it is already there
    assert U.load_plan(u, ("tang-base-1", "math-1"), lib, card_pattern_id=U.pack_id(0xA1, 2))[0][0] == "load bitstream math1.fs"   # old version on the card: the card's word wins over the host's record
    assert U.load_plan(u, None, lib, card_pattern_id=0)[0][0] == "load bitstream math1.fs"                      # nothing recognisable on the card
    u2 = U.make_unit("d", "tang-base-1", "math-1", PROG, dict(judge_a=W), pattern_id=U.pack_id(0xA1, 4))      # unit built for version 4, library has 3
    s, p = U.load_plan(u2, None, lib, card_pattern_id=U.pack_id(0xA1, 3)); assert s == [] and "pattern id" in p[0]


def _lib(file=None, ref="math-1.pattern.json", card="tang20k"):
    return {card: {("tang-base-1", "math-1"): dict(pattern_id=U.pack_id(0x19, 1), reference=ref, file=file, judges=["judge_a"])}}


def _unit():
    return U.make_unit("d", "tang-base-1", "math-1", PROG, dict(judge_a=W), pattern_id=U.pack_id(0x19, 1))


def test_plan_load_all_four_outcomes():
    ID = U.pack_id(0x19, 1)
    r = U.plan_load(_unit(), "tang20k", ID, _lib(file="m.fs"))                                   # already on the card
    assert r["steps"] == ["bitstream already on the card", "wipe all cells", "load program", "load weights", "ready for data"]
    r = U.plan_load(_unit(), "tang20k", 0, _lib(file="m.fs"))                                    # wrong or nothing: pull it
    assert r["steps"][0].startswith("pull bitstream m.fs") and r["steps"][-1] == "ready for data"
    r = U.plan_load(_unit(), "tang20k", 0, _lib(file=None), can_build=True)                      # not in library: build from the reference
    assert r["steps"][0].startswith("build the bitstream") and r["steps"][1] == "load the new bitstream"
    r = U.plan_load(_unit(), "tang20k", 0, _lib(file=None))                                      # cannot build: tell the user, load nothing
    assert r["steps"] == [] and "needs to be in place" in r["problems"][0] and r["needs"] == ["bitstream for pattern 'math-1' on card 'tang20k'"]


def test_plan_load_is_per_card_and_refuses_the_rest():
    ID = U.pack_id(0x19, 1)
    r = U.plan_load(_unit(), "kintex", ID, _lib(file="m.fs"))                                    # the library only has the Tang: unknown here
    assert r["steps"] == [] and "not known for card" in r["problems"][0]
    r = U.plan_load(_unit(), "tang20k", ID, _lib(file=None, ref=None))                           # no reference, no bitstream, but it is on the card
    assert r["steps"][0] == "bitstream already on the card"
    r = U.plan_load(_unit(), "tang20k", 0, _lib(file=None, ref=None), can_build=True)            # nothing to build from
    assert r["steps"] == [] and "no a reference file" not in r["problems"][0] and "no" in r["problems"][0]
    u = _unit(); u["weights"]["judge_a"]["b1"][0] += 1
    assert U.plan_load(u, "tang20k", ID, _lib(file="m.fs"))["steps"] == []                       # a damaged part: nothing loads
    u2 = U.make_unit("d", "tang-base-1", "math-1", PROG, dict(judge_a=W), pattern_id=U.pack_id(0x19, 2))
    assert "pattern id" in U.plan_load(u2, "tang20k", ID, _lib(file="m.fs"))["problems"][0]
