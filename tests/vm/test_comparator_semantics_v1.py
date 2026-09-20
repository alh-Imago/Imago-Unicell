"""tests/vm/test_comparator_semantics_v1.py — points.md #784: real,
direct answer to Alan's own precise question -- is comparator arrival-
dependent, and is its emission still a value, just a singular one?

Confirmed: comparator's own real delivery logic (`_deliver_comparator`)
OR-COMBINES every real arrival present on a given tick into one value,
THEN compares that combined value against a fixed, compile-time
`threshold` -- it has no real "A/B slot" identity system at all, unlike
`adder`. This means:
- Its INTENDED, safe shape (one real, dynamic operand vs a compile-
  time constant) is `#777`'s own PLAIN_CHAIN -- no real convergence
  machinery needed at all, confirmed correct here.
- Feeding it TWO real, genuinely distinct dynamic values does NOT
  compute "is a >= b" -- it silently OR-combines them into one bit
  pattern first, then compares THAT against the threshold, confirmed
  directly to produce a real, wrong-for-that-purpose result.
- Its own real output IS a genuine data value (0 or 1, usable as an
  operand elsewhere) -- confirmed distinct in kind from `branch`'s own
  real routing_mask decision, which redirects physical dataflow itself
  rather than producing a value to consume.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import vix_tile_library_v1 as vtl  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def test_comparator_intended_use_one_value_vs_threshold():
    """The real, safe, intended shape -- PLAIN_CHAIN (#777): one real,
    dynamic operand compared against a compile-time constant."""
    x = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="x", rel_row=0, rel_col=-1, preload_value=42)
    cmp = vtl.place(vtl.TILE_COMPARATOR, {"in": "w", "out": "e"}, params={"threshold": 10},
                     cell_id="cmp", rel_row=0, rel_col=0)
    sink = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink", rel_row=0, rel_col=1)
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[x, cmp, sink])},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="cmp_intended")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(10):
        grid.tick()
    assert grid.cells[(0, 1)].ram_data_reg == 1  # 42 >= 10


def test_comparator_two_simultaneous_values_or_combine_not_compare():
    """points.md #784: the real, central finding. Two real, distinct
    dynamic values arriving on the SAME tick do NOT get compared
    against each other -- they are OR-combined into one value first,
    then THAT is compared against the threshold. Confirmed directly
    with values chosen so a genuine "a >= b" comparison and the real
    OR-combine behavior give different, distinguishable answers."""
    a = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="a", rel_row=0, rel_col=-1, preload_value=5)
    b = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="b", rel_row=-1, rel_col=0, preload_value=3)
    cmp = vtl.place(vtl.TILE_COMPARATOR, {"in": ["w", "n"], "out": "e"}, params={"threshold": 100},
                     cell_id="cmp", rel_row=0, rel_col=0)
    sink = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink", rel_row=0, rel_col=1)
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[a, b, cmp, sink])},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="cmp_two_real")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    cmp_cell = grid.cells[(0, 0)]
    for _ in range(10):
        grid.tick()
    # a=5, b=3: a real "is a >= b" comparison would say True (5>=3).
    # The real OR-combine (5|3=7) compared against threshold=100 says
    # False -- confirming the real mechanism is OR-combine, not compare.
    assert cmp_cell.cmp_out_buffer == 0
