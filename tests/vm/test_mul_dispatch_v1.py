"""tests/vm/test_mul_dispatch_v1.py — points.md #790: real tests
confirming `mul`'s own new VM dispatch (`_deliver_mul`/`_offer_state_
mul`/`_clear_valid_mul`, registered under `core="mul"`) works
correctly. Before this, `core="mul"` had NO real VM dispatch at all --
confirmed directly, empirically, in the surrounding session (a real
`ValueError: unsupported core 'mul' for VM dispatch`), not merely
untested.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import vix_tile_library_v1 as vtl  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def test_mul_computes_real_product_with_staggered_arrival():
    a = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="a", rel_row=0, rel_col=-2, preload_value=6)
    relay = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="relay", rel_row=0, rel_col=-1)
    b = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="b", rel_row=1, rel_col=0, preload_value=7)
    mul = vtl.place(vtl.TILE_MUL, {"in_a": "w", "in_b": "s", "out": "e"}, cell_id="mul", rel_row=0, rel_col=0)
    sink = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink", rel_row=0, rel_col=1)
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[a, relay, b, mul, sink])},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="mul_test")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(10):
        grid.tick()
    assert grid.cells[(0, 1)].ram_data_reg == 42  # 6 * 7


def test_mul_shares_the_known_simultaneous_arrival_collision():
    """The same real hazard #750/#764/#776 already found for any
    2-arrival, shared-upstream-mask core: two real values arriving on
    the SAME tick collide, one is silently lost -- confirmed here to
    apply to mul too, not a new, mul-specific bug."""
    a = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="a", rel_row=-1, rel_col=0, preload_value=6)
    b = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="b", rel_row=1, rel_col=0, preload_value=7)
    mul = vtl.place(vtl.TILE_MUL, {"in_a": "n", "in_b": "s", "out": "e"}, cell_id="mul", rel_row=0, rel_col=0)
    sink = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink", rel_row=0, rel_col=1)
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[a, b, mul, sink])},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="mul_collision")
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(10):
        grid.tick()
    # Not the real product (42) -- one value was lost to the collision.
    assert grid.cells[(0, 1)].ram_data_reg != 42
