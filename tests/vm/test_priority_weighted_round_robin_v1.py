"""tests/vm/test_priority_weighted_round_robin_v1.py — points.md #785:
real test of `priority`'s own third real role, `scheduling_mode=1`
(weighted round-robin / Surplus Round Robin), confirming it correctly
serves multiple continuously-competing real sources proportionally to
their configured weights, with neither starving -- genuinely different
internal behavior from strict-rank mode (`scheduling_mode=0`, where a
lower-ranked source could starve forever), but still falling under
`#777`'s own `PRIORITY` shape category, not a new one.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import vix_tile_library_v1 as vtl  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def test_weighted_round_robin_serves_proportionally_to_weight():
    a = vtl.place(vtl.TILE_RAM_CONSTANT, {"out": "s"}, params={"init_data": 1}, cell_id="a", rel_row=-1, rel_col=0)
    b = vtl.place(vtl.TILE_RAM_CONSTANT, {"out": "n"}, params={"init_data": 2}, cell_id="b", rel_row=1, rel_col=0)
    pri = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                     params={"priority_rank_n": 2, "priority_rank_s": 1,  # weight 2 vs weight 1
                             "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 1},
                     cell_id="pri", rel_row=0, rel_col=0)
    sink = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink", rel_row=0, rel_col=1)
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[a, b, pri, sink])},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="wrr_test")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    sink_cell = grid.cells[(0, 1)]
    served = []
    prev_valid = False
    for _ in range(300):
        grid.tick()
        if sink_cell.ram_data_valid and not prev_valid:
            served.append(sink_cell.ram_data_reg)
            sink_cell.ram_data_valid = False
            sink_cell.pending_ack = 0
        prev_valid = sink_cell.ram_data_valid

    # Both real sources served -- neither starves.
    assert served.count(1) > 0
    assert served.count(2) > 0
    # The real, exact cyclic pattern confirms proportional service, not
    # just "both eventually happen": weight 2 gets served twice for
    # every one time weight 1 does.
    assert served[:9] == [1, 1, 2, 1, 1, 2, 1, 1, 2]
    ratio = served.count(1) / served.count(2)
    assert 1.8 < ratio < 2.2  # real, close to the configured 2:1 weight
