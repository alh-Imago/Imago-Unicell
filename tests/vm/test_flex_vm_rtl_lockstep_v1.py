"""Ledger #1095: the FlexGrid VM and the assembler-generated flex RTL (iverilog) run side by side on the open-ring looped CORDIC; their states are the same register for register whenever the loop value
sits in the feedback relays or a stage's gather relay (94 of 157 ticks), differ by a one-clock skew only in the stage work cells (branch, adders, turn relays) while a value passes through them, and the
two places where the VM keeps state the RTL does not have (adder first operand = a constant, branch reference = a constant) hold exactly the constants."""
import os
import shutil
import sys

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))


def test_vm_and_rtl_states_agree_whenever_the_value_sits_in_a_relay():
    if not (shutil.which("iverilog") and shutil.which("vvp")):
        pytest.fail("iverilog missing: this test must not pass by skipping")
    import flex_vm_rtl_lockstep_v1 as X
    r = X.lockstep(158)
    eq = set(r["equal_ticks"])
    assert r["n_compared"] == 157 and r["n_equal"] == 94
    for lo, hi in ((20, 40), (60, 80), (100, 120), (140, 158)):          # the value is in the 20-relay way back: every compared cell agrees
        assert set(range(lo + 1 if lo == 20 else lo, hi + 1)) <= eq
    assert all(c.split(".")[1] in ("branch", "add_neg", "add_pos", "turn_neg", "turn_pos") for c in r["mismatch_cells"])      # no relay (fb*, gather) ever disagrees
    assert r["merge_rr_differs_at_equal_ticks"] == []
    assert r["branch_ref_loaded_in_rtl"] == ["0"] and r["branch_ref_valid_in_vm"] == [True]      # the VM's loaded reference has no RTL register: the reference is the constant source
    assert r["n_adder_waiting_non_constant"] == 0                                                 # the only first operand an adder ever holds in the VM here is a constant (no RTL register either)
