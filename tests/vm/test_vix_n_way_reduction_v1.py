"""tests/vm/test_vix_n_way_reduction_v1.py — points.md #765: real
tests for the general N-way reduction compiler, confirmed for N=2, 4,
8, and 16 -- N=4 cross-checked against `#763`'s own hand-built result
exactly (same cell count, same answer); N=8 and N=16 are genuinely new
territory, never hand-built, proving real generalization.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

from vix_n_way_reduction_v1 import compile_n_way_reduction  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def _run(leaves, ticks):
    icm, result_pos = compile_n_way_reduction(leaves)
    assert icm.check_connections() == []
    assert icm.check_known_gotchas() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(ticks):
        grid.tick()
    result = grid.cells[result_pos]
    return result.adder_data_valid, result.adder_out_buffer, len(records)


def test_n_equals_2():
    valid, total, _ = _run([5, 10], ticks=20)
    assert valid is True
    assert total == 15


def test_n_equals_4_matches_the_hand_built_763_result_exactly():
    """Real, direct cross-check: the general compiler reproduces
    #763's own hand-built result exactly, both the answer and the
    real, final cell count (34), confirming the generalization doesn't
    lose any of the tightening quality the hand-built version achieved."""
    valid, total, n_cells = _run([10, 20, 30, 40], ticks=40)
    assert valid is True
    assert total == 100
    assert n_cells == 34


def test_n_equals_8_genuinely_new_territory():
    leaves = list(range(1, 9))
    valid, total, _ = _run(leaves, ticks=60)
    assert valid is True
    assert total == sum(leaves)


def test_n_equals_16_genuinely_new_territory():
    leaves = list(range(1, 17))
    valid, total, _ = _run(leaves, ticks=100)
    assert valid is True
    assert total == sum(leaves)


def test_rejects_non_power_of_two():
    import pytest
    with pytest.raises(ValueError):
        compile_n_way_reduction([1, 2, 3])


def test_rejects_too_few_leaves():
    import pytest
    with pytest.raises(ValueError):
        compile_n_way_reduction([1])
