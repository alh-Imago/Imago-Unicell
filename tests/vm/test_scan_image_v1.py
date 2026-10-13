"""Ledger #1156: the single self-describing state file (tools/scan_image_v1.py) is lossless against a real card image, and unpack refuses a design that does not fit."""
import copy, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest, scan_image_v1 as si  # noqa: E402
K = os.path.join(ROOT, "fpga", "board_tests_scan_latex")
SM = json.load(open(os.path.join(K, "SCAN_MAP.json")))
RAW = json.load(open(os.path.join(K, "images", "real_card_cut_3_3_0.json")))


def test_pack_unpack_is_byte_identical_and_names_every_register():
    st = si.pack(RAW, SM, "f")
    assert sum(r["bits"] for c in st["cells"] for r in c["registers"]) == SM["total_bits"] == 678
    assert si.unpack(st, SM)["image"] == RAW["image"] and st["layout"] == RAW["layout"]


def test_unpack_refuses_changed_width_missing_cell_and_wrong_format():
    st = si.pack(RAW, SM)
    bad = copy.deepcopy(st); bad["cells"][-1]["registers"][0]["bits"] += 1
    with pytest.raises(SystemExit) as e: si.unpack(bad, SM)
    assert "REFUSED" in str(e.value)
    bad = copy.deepcopy(st); del bad["cells"][3]
    with pytest.raises(SystemExit) as e: si.unpack(bad, SM)
    assert "does not have" in str(e.value) or "the target design has cell" in str(e.value)
    with pytest.raises(SystemExit): si.unpack(dict(st, format="x"), SM)


def test_value_edit_by_name_reaches_the_right_bits():
    st = si.pack(RAW, SM)
    st["cells"][10]["registers"][1]["value"] ^= 1          # one bit of the multiplier's pending_hi/out_buffer area
    assert si.unpack(st, SM)["image"] != RAW["image"]
    assert bin(int(si.unpack(st, SM)["image"], 16) ^ int(RAW["image"], 16)).count("1") == 1


def test_kit_copy_is_the_same_file_and_load_any_reads_both_kinds(tmp_path):
    assert open(os.path.join(K, "scan_image.py")).read() == open(os.path.join(ROOT, "tools", "scan_image_v1.py")).read()
    p = tmp_path / "s.json"; si.save_state(RAW, SM, "f", str(p))
    assert si.load_any(str(p), SM)["image"] == RAW["image"]
    q = tmp_path / "r.json"; q.write_text(json.dumps(RAW))
    assert si.load_any(str(q), SM)["image"] == RAW["image"]
