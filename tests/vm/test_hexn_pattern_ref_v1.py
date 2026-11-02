import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_pattern_ref_v1 as R
import hexn_unit_file_v1 as U

R9 = dict(n=9, counts={"JN": 2, "BR": 1}, ram="none")
R7 = dict(n=7, counts={"UN": 1}, ram="none")
R11 = dict(n=11, counts={"JN": 3}, ram="lead2")


def test_kinds_ids_and_sequence():
    assert [R.kind_of(x) for x in (R9, R7, R11, dict(n=9, counts={"JN": 2}, ram="none"), dict(n=9, counts={}, ram="every4"))] == ["mixed", "math", "ram2", "logic", "banded"]
    reg = {}; a, reg = R.reference(R9, reg); b, reg = R.reference(dict(n=9, counts={"JN": 1, "SQ": 1}, ram="none"), reg); c, reg = R.reference(R7, reg)
    assert a["pattern_id_hex"] == "39000001" and b["pattern_id_hex"] == "39010001" and c["pattern_id_hex"] == "17000001"   # mixed 9: 3 9 00 and 3 9 01; math 7
    assert R.unpack_id(a["pattern_id"]) == (0x3900, 1) and R.pack_id(0x3900, 1) == U.pack_id(0x3900, 1)                    # same word as the loader's


def test_version_changes_only_with_content():
    ref1, reg = R.reference(R9, {})
    ref2, reg2 = R.reference(R9, reg)
    assert ref2["pattern_id"] == ref1["pattern_id"] and reg2 == reg                                  # unchanged content, same id
    ref3, reg3 = R.reference(R9, reg, judges=("judge_a",))                                           # the judges the bitstream holds changed: new content, new version
    assert R.unpack_id(ref3["pattern_id"]) == (R.unpack_id(ref1["pattern_id"])[0], 2)


def test_check_reference_catches_damage():
    ref, _ = R.reference(R11, {})
    assert R.check_reference(json.loads(json.dumps(ref))) == []
    bad = json.loads(json.dumps(ref)); bad["work_cells"][0]["type"] = "BR"
    assert "content hash" in R.check_reference(bad)[0]
    bad = json.loads(json.dumps(ref)); bad["pattern_id"] = R.pack_id(0x1100, 1)
    assert any("kind digit" in p for p in R.check_reference(bad)) and any("size digit" in p for p in R.check_reference(bad))
    assert R.check_reference({"format": "x"}) == ["not a hexn-pattern-v2 file"]


def test_reference_feeds_the_loader_plan():
    ref, _ = R.reference(R9, {}); W = {"judge_a": {"w": [1]}}
    lib = {"tang20k": {("tang-base-1", ref["name"]): dict(pattern_id=ref["pattern_id"], reference=ref["name"] + ".pattern.json", file=None, judges=ref["judges"])}}
    u = U.make_unit("d", "tang-base-1", ref["name"], {"x": 1}, W, pattern_id=ref["pattern_id"])
    r = U.plan_load(u, "tang20k", 0, lib, can_build=True)
    assert r["steps"][0].startswith("build the bitstream") and ref["name"] in r["steps"][0]
