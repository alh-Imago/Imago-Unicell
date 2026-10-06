"""tests/vm/test_flex_grid_cascade_v1.py -- two pulse-mode accumulators in cascade on FlexGrid (ledger #975).

I (ram) -> A1 (pulse accumulator, threshold T1) -> A2 (pulse accumulator, threshold T2). One input event per injection. A2 must fire exactly once per T1*T2 input
events -- the same period the REAL cells give in sub/verilog/tb_acc_cascade_v4sa.v (tests/vm/test_flex_second_port_v1.py runs it): a count past the 16-bit
threshold field one accumulator has (65535 x 3 and 1000 x 1000 in the RTL bench; 300 x 300 and 7 x 5 here at the other widths). Needs no iverilog.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import flex_grid_v1 as fg  # noqa: E402
from icm_v3 import IcmV3Record  # noqa: E402


def cascade_fire_events(w, t1, t2, n_events):
    """Returns the 1-based input-event numbers after which A2 offered a value."""
    recs = [IcmV3Record(cell_id="I", row=1, col=0, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["e"]}),
            IcmV3Record(cell_id="A1", row=1, col=1, core="accumulator", core_config={"inc_dir": ["w"], "step_amount": 1, "pulse_mode": 1, "threshold": t1, "downstream_mask": ["e"]}),
            IcmV3Record(cell_id="A2", row=1, col=2, core="accumulator", core_config={"inc_dir": ["w"], "step_amount": 1, "pulse_mode": 1, "threshold": t2, "downstream_mask": []})]
    g = fg.FlexGrid(recs, width=w)
    a2 = g.cells[(1, 2)]
    fires = []
    for n in range(1, n_events + 1):
        g.inject(1, 0, 1)
        for _ in range(8):
            g.tick()
        if a2.acc_pulse_pending:
            fires.append(n)
            a2.acc_pulse_pending = False
    return fires


@pytest.mark.parametrize("w,t1,t2", [(4, 7, 5), (8, 10, 10), (18, 30, 40), (32, 300, 3), (36, 13, 17)])
def test_cascade_fires_once_per_product(w, t1, t2):
    period = t1 * t2
    fires = cascade_fire_events(w, t1, t2, 2 * period + 3)
    assert fires == [period, 2 * period], (w, t1, t2, fires)


def test_one_stage_cannot_count_that_far():
    """A single accumulator's threshold is a 16-bit field: 70000 does not fit (it is cut to 4464), the cascade 280 x 250 = 70000 does."""
    assert 70000 & 0xFFFF == 4464
    fires = cascade_fire_events(32, 280, 250, 70000 + 2)
    assert fires == [70000], fires
