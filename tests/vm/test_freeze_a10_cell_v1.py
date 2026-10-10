"""tests/vm/test_freeze_a10_cell_v1.py -- ledger #1036 addendum 67: one Arria 10 line cell (adder_cell_v4c), freeze window of 8 cycles at every start cycle 0..30.
  outputs always equal the un-frozen run; registers hold at all but the start cycle where a neighbour's ack is already high (that ack still clears data_valid and pending_ack: the v4c
  freeze gates captures, firing, offers and ready, it is NOT a clock enable on every register as in the flex cells). Requires iverilog."""
import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import freeze_a10_cell_v1 as t  # noqa: E402


def test_v4c_adder_freeze_outputs_equal_and_registers_mostly_held():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    assert t.main() == 0
    held, changed, same_out, diff_out, bad = t.main.result
    assert diff_out == 0 and same_out == 31
    assert held + changed == 31 and held >= 29     # the known exception: an ack arriving during the freeze still clears the offer
