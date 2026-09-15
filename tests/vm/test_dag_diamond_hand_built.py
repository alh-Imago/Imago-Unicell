"""
test_dag_diamond_hand_built.py — verifies nano/examples/dag_diamond_
hand_built.py (points.md #750): the smallest real DAG that isn't a
linear chain, confirming the correct, staggered-path solution keeps
working, not just that it worked once when traced by hand.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano", "examples"))

from dag_diamond_hand_built import build_dag  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def _run(a, b, c, d, ticks=10):
    records = build_dag(a, b, c, d)
    grid = SuperGrid(records)
    t3 = grid.cells[(1, 0)]
    for _ in range(ticks):
        grid.tick()
    return t3


def test_diamond_dag_computes_correct_sum():
    t3 = _run(3, 5, 10, 20)
    assert t3.adder_out_buffer == 38  # (3+5) + (10+20)


def test_diamond_dag_t1_arrives_before_t2_confirming_the_stagger():
    """Real, direct confirmation the padding actually works as
    intended, not just that the final sum happens to be right: t1's
    own value (8) must be captured as t3's own 'A' operand, proving it
    genuinely arrived first."""
    records = build_dag(3, 5, 10, 20)
    grid = SuperGrid(records)
    t3 = grid.cells[(1, 0)]
    for _ in range(4):
        grid.tick()
    assert t3.adder_a_arrived is True
    assert t3.adder_a_reg == 8  # t1's own value, not t2's


def test_diamond_dag_with_different_real_values():
    """A second, different set of real values -- confirms the fix
    isn't an artifact of one specific lucky set of numbers."""
    t3 = _run(1, 2, 100, 200)
    assert t3.adder_out_buffer == 303  # (1+2) + (100+200)
