"""tests/vm/test_div_core_vm_v1.py -- ledger #1069: the division core on the STANDARD grid (SuperGrid; v4/v4c-style: one output, the remainder as a second word).

Operand order is the adder/mul convention: the first arrival is the dividend, the second the divisor. The 32-tick busy time is a design figure
of the VM model; it must be re-checked against RTL when the RTL exists."""
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "nano"))

import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

M = 0xFFFFFFFF


def grid(**cfg):
    div = {"upstream_mask": ["w", "n"], "downstream_mask": ["e"]}
    div.update(cfg)
    cells = [vix.HierCell(cell_id="D", rel_row=1, rel_col=1, core="div", core_config=div),
             vix.HierCell(cell_id="S", rel_row=1, rel_col=2, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": []})]
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                         placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))], name="d")
    return SuperGrid(icm.flatten()[0])


def divide(a, b, **cfg):
    """Returns (words seen at the sink in order, ticks from the second operand to the first word)."""
    g = grid(**cfg)
    sink = g.cells[(1, 2)]
    g.inject(1, 1, a); g.tick()
    g.inject(1, 1, b)
    words, first_tick = [], None
    for t in range(1, 200):
        g.tick()
        if sink.ram_data_valid:
            words.append(sink.ram_data_reg)
            if first_tick is None:
                first_tick = t
            sink.ram_data_valid = False
    return words, first_tick


def test_quotient_matches_python():
    pairs = [(23, 7), (21, 7), (3, 7), (0, 5), (7, 1), (M, 1), (M, M), (M, 2), (1 << 31, 3), (M - 1, M)]
    rnd = random.Random(7)
    pairs += [(rnd.getrandbits(rnd.choice([8, 16, 32])), max(1, rnd.getrandbits(rnd.choice([4, 12, 32])))) for _ in range(60)]
    for a, b in pairs:
        assert divide(a, b)[0] == [a // b], (a, b)


def test_divide_by_zero_gives_all_ones_and_remainder_the_dividend():
    assert divide(5, 0)[0] == [M]
    assert divide(5, 0, second_output=1, remainder_primary=1)[0] == [5, M]


def test_second_output_sends_the_remainder_after_the_quotient():
    for a, b in [(23, 7), (100, 9), (6, 3), (3, 7), (M, 12345)]:
        assert divide(a, b, second_output=1)[0] == [a // b, a % b], (a, b)


def test_remainder_primary_swaps_the_order():
    assert divide(23, 7, remainder_primary=1)[0] == [2]
    assert divide(23, 7, second_output=1, remainder_primary=1)[0] == [2, 3]


def test_the_result_arrives_only_after_the_busy_time():
    ticks = {divide(a, b)[1] for a, b in [(23, 7), (M, 3), (0, 9)]}
    assert len(ticks) == 1 and ticks.pop() >= 32          # same delay whatever the values: fixed latency


def test_run_to_quiescence_waits_for_a_busy_divider():
    g = grid()
    sink = g.cells[(1, 2)]
    g.inject(1, 1, 100); g.tick(); g.inject(1, 1, 7)
    g.run_to_quiescence(max_ticks=500)
    assert sink.ram_data_valid and sink.ram_data_reg == 14


def test_flexgrid_refuses_the_division_core_until_a_flex_version_exists():
    """The flex family is a separate grid with its own port shape; the std handler must not run there silently."""
    import pytest
    import flex_grid_v1 as FG
    cells = [vix.HierCell(cell_id="D", rel_row=1, rel_col=1, core="div", core_config={"upstream_mask": ["w", "n"], "downstream_mask": ["e"]})]
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                         placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))], name="d")
    with pytest.raises(ValueError, match="not built for the flex family"):
        FG.FlexGrid(icm.flatten()[0])
