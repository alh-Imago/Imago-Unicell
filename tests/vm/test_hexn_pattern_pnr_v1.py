"""tests/vm/test_hexn_pattern_pnr_v1.py -- the committed place-and-route VERIFICATION RECORD of the unary 7 x 7 pattern (docs/hex-n/data/pnr/), tied to its reference file (docs/hex-n/data/patterns/).
Fast checks always run: the reference regenerates to the SAME content hash and ID, the record is for it, the verdict is PASS and its numbers are consistent with the planner. The real place and route is only re-run when HEXN_RUN_PNR=1 (minutes)."""
import json, os, sys
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_pattern_ref_v2 as R, hexn_pattern_verify_v1 as V

RECIPE = {"n": 7, "counts": {"UN": 9}, "ram": "none"}
REFP = os.path.join(ROOT, "docs", "hex-n", "data", "patterns", "J0U9_7_17000001.json")
RECP = os.path.join(ROOT, "docs", "hex-n", "data", "pnr", "J0U9_7_17000001.pnr.json")


def test_committed_reference_regenerates_and_record_is_tied_to_it():
    if not os.path.exists(RECP): pytest.skip("no verification record committed yet")
    ref = json.load(open(REFP)); rec = json.load(open(RECP))
    assert not R.check_reference(ref)
    again, _ = R.reference(RECIPE, {})
    assert again == ref                                                    # the file is exactly what the designer makes today
    assert V.verified(ref, rec)


def test_record_numbers_are_consistent():
    if not os.path.exists(RECP): pytest.skip("no verification record committed yet")
    ref = json.load(open(REFP)); rec = json.load(open(RECP))
    assert rec["verdict"] == "PASS" and not rec["reasons"]
    s, p = rec["synth_alone"], rec["placed_with_wrapper"]
    assert s["slots"] == s["lut"] + s["alu"] and p["slots"] == p["lut4"] + p["alu"]
    est = ref["slots_estimate"]
    assert abs(rec["deviation_synth_pct"] - 100 * (s["slots"] - est) / est) < 0.01
    assert rec["placed_pattern_slots"] == p["slots"] - rec["wrapper_synth_slots"]
    assert abs(rec["deviation_pct"] - 100 * (rec["placed_pattern_slots"] - est) / est) < 0.01 and abs(rec["deviation_pct"]) <= 100 * V.TOL
    assert abs(rec["packing_overhead_pct"] - 100 * (rec["placed_pattern_slots"] - s["slots"]) / s["slots"]) < 0.01
    assert rec["fmax_mhz"] >= rec["freq_target_mhz"] and p["lut4"] <= p["lut4_available"]


def test_real_place_and_route_rerun_only_on_request():
    if os.environ.get("HEXN_RUN_PNR") != "1":
        return
    ref = json.load(open(REFP)); rec = V.pnr_run(ref)
    assert V.verified(ref, rec), rec["reasons"]
