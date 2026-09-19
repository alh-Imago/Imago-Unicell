"""tests/vm/test_fanout_via_rats_nest_v1.py — points.md #776: real,
direct proof of Alan's own architectural insight -- rather than
retrofitting genuine DAG shapes into the old frontend's own rigid,
fixed-port, immediately-adjacent placement model (which is what
forced `#700`-`#717`'s own elaborate relay/tap/drop/trigger machinery
to exist in the first place), treat each operation as a real library
tile with a known shape/ports/timing contract, place instances LOOSELY
(no premature geometric commitment), connect them via the already-
proven general router, then tighten. Confirmed here for fan-out (one
producer, two consumers) -- the exact shape `#700`-`#717` built a
whole, separate mechanism for.

Real, honest finding along the way, not glossed over: fan-out via
ordinary multicast + routing still needs the SAME real timing
discipline `#750`/`#764` already established -- two real values
arriving on the SAME tick at a shared-capture consumer collide and one
is silently lost, confirmed here to apply even when the two colliding
values arrive from TWO DIFFERENT physical directions (not just the
same one, as `#750`'s own original case tested). Staggering one path
by a single real relay hop fixes it, the same real technique already
proven throughout this project.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import vix_tile_library_v1 as vtl  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from rats_nest_router_v1 import manhattan_route  # noqa: E402


def test_two_different_upstream_directions_colliding_on_the_same_tick_loses_one():
    """The real, genuine hazard found while building the fan-out proof
    below -- confirmed in isolation first. Two real values arriving on
    the SAME tick at a shared-upstream adder (via TWO DIFFERENT
    physical directions, not the same one) still collide: one is
    captured, the other's own real offer is acked and silently lost,
    never retried. The same real class of hazard `#750`/`#764` already
    found for same-direction collisions, now confirmed to apply
    regardless of which two directions are actually involved."""
    x_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="x", rel_row=0, rel_col=-1, preload_value=1)
    five = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="five", rel_row=-1, rel_col=0, preload_value=5)
    t1 = vtl.place(vtl.TILE_ADDER, {"in_a": "w", "in_b": "n", "out": "e"}, cell_id="t1", rel_row=0, rel_col=0)
    sink = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink", rel_row=0, rel_col=1)

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[x_src, five, t1, sink])},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="collision_check")
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(8):
        grid.tick()
    t1_cell = grid.cells[(0, 0)]
    # x's own value (1) never combines -- silently lost, not the real,
    # correct sum (6).
    assert t1_cell.adder_out_buffer != 6
    assert t1_cell.adder_data_valid is False


def test_staggering_by_one_hop_fixes_the_cross_direction_collision():
    x_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="x", rel_row=0, rel_col=-2, preload_value=1)
    relay = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="relay", rel_row=0, rel_col=-1)
    five = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="five", rel_row=-1, rel_col=0, preload_value=5)
    t1 = vtl.place(vtl.TILE_ADDER, {"in_a": "w", "in_b": "n", "out": "e"}, cell_id="t1", rel_row=0, rel_col=0)
    sink = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink", rel_row=0, rel_col=1)

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[x_src, relay, five, t1, sink])},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="collision_fixed")
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(8):
        grid.tick()
    assert grid.cells[(0, 0)].adder_out_buffer == 6


def test_fanout_via_ordinary_multicast_and_routing_needs_no_special_machinery():
    """points.md #776: the real, central proof. t1 = x+5 feeds TWO
    separate, real consumers (t2 = t1+10, t3 = t1+20) -- the exact
    real shape `#700`-`#717` built a whole, dedicated relay/tap/drop/
    trigger mechanism for. Here, built using ONLY ordinary tools
    already proven for other purposes this session: a real, multicast
    `downstream_mask` (`#17`'s own original finding, confirmed still
    true) offering to both real consumers at once, and the general
    Manhattan router (`#760`) connecting each to wherever it actually
    sits, however far away. No relay/tap/drop/trigger machinery of any
    kind. Confirmed correct end to end."""
    occ = {}
    cells = []

    x_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="x", rel_row=0, rel_col=-2, preload_value=1)
    cells.append(x_src)
    occ[(0, -2)] = "x"
    relay = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="relay", rel_row=0, rel_col=-1)
    cells.append(relay)
    occ[(0, -1)] = "relay"
    five = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="five", rel_row=-1, rel_col=0, preload_value=5)
    cells.append(five)
    occ[(-1, 0)] = "five"
    t1 = vtl.place(vtl.TILE_ADDER, {"in_a": "w", "in_b": "n", "out": ["e", "s"]}, cell_id="t1", rel_row=0, rel_col=0)
    cells.append(t1)
    occ[(0, 0)] = "t1"

    route_t1_to_t2 = manhattan_route((0, 0), "e", (0, 10), "e", "rt1a", occ)
    cells += route_t1_to_t2
    ten = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="ten", rel_row=-1, rel_col=11, preload_value=10)
    cells.append(ten)
    occ[(-1, 11)] = "ten"
    t2 = vtl.place(vtl.TILE_ADDER, {"in_a": "w", "in_b": "n", "out": "e"}, cell_id="t2", rel_row=0, rel_col=11)
    cells.append(t2)
    occ[(0, 11)] = "t2"

    route_t1_to_t3 = manhattan_route((0, 0), "s", (10, 0), "s", "rt1b", occ)
    cells += route_t1_to_t3
    twenty = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="twenty", rel_row=11, rel_col=-1, preload_value=20)
    cells.append(twenty)
    occ[(11, -1)] = "twenty"
    t3 = vtl.place(vtl.TILE_ADDER, {"in_a": "n", "in_b": "w", "out": "e"}, cell_id="t3", rel_row=11, rel_col=0)
    cells.append(t3)
    occ[(11, 0)] = "t3"

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="fanout_via_rats_nest")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(30):
        grid.tick()
    assert grid.cells[(0, 0)].adder_out_buffer == 6     # t1 = 1 + 5
    assert grid.cells[(0, 11)].adder_out_buffer == 16   # t2 = t1 + 10
    assert grid.cells[(11, 0)].adder_out_buffer == 26   # t3 = t1 + 20
