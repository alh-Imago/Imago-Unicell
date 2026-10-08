"""ledger #986: one shift number in the ICM; the target says whether it can make it (flex: any 0..31; std: coarse taps + fine; sub: coarse taps only)."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "nano"))
from icm_v3 import IcmV3Record  # noqa: E402
import target_capabilities_v1 as tc  # noqa: E402


def rec(**ad):
    return IcmV3Record(cell_id="r", row=0, col=0, core="ram", core_config={}, addon_config=dict({"shift_en": 1}, **ad))


def test_flex_any_amount_std_taps_sub_coarse_only():
    for n in range(1, 32):
        assert tc.check_records([rec(shift_amt=n)], "flex") == []
    assert tc.check_records([rec(shift_amt=5)], "std") and tc.check_records([rec(shift_amt=5)], "sub")
    for n in tc.COARSE_TAPS:
        assert tc.check_records([rec(shift_amt=n)], "std") == [] and tc.check_records([rec(shift_amt=n)], "sub") == []
    assert tc.check_records([rec(shift_amt=4, shift_fine=1)], "std") == []
    assert "fine" in tc.check_records([rec(shift_amt=4, shift_fine=1)], "sub")[0]
    assert tc.check_records([rec(shift_amt=5)], None) == []
    assert tc.check_records([IcmV3Record(cell_id="r", row=0, col=0, core="ram", core_config={}, addon_config={"shift_en": 0, "shift_amt": 5})], "sub") == []
