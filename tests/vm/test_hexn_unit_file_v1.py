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
