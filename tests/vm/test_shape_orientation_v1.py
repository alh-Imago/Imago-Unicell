"""tests/vm/test_shape_orientation_v1.py — points.md #778: real, direct
proof of Alan's own question -- does a library shape's fixed port
orientation matter, or can it always be routed around cheaply?
Confirmed: it matters, measurably. The same real convergence (two
preloaded sources, one west of the target, one south) costs 12 real
cells / 8 relay hops when the `priority` cell's own ports are oriented
to match where its real neighbors sit, versus 18 real cells / 14 relay
hops when forced into this session's own previously-hardcoded, fixed
N/S orientation and routed around via a real detour -- both produce
the correct result, but the mismatched orientation costs 50% more.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import vix_tile_library_v1 as vtl  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from rats_nest_router_v1 import manhattan_route  # noqa: E402


def _build_matched_orientation():
    """priority oriented to accept from W and S -- matching where the
    two real sources actually sit."""
    occ = {}
    cells = []
    src_w = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="src_w", rel_row=0, rel_col=-5, preload_value=7)
    cells.append(src_w)
    occ[(0, -5)] = "src_w"
    route_w = manhattan_route((0, -5), "e", (0, -1), "e", "rw", occ)
    cells += route_w

    src_s = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="src_s", rel_row=5, rel_col=0, preload_value=3)
    cells.append(src_s)
    occ[(5, 0)] = "src_s"
    route_s = manhattan_route((5, 0), "n", (1, 0), "n", "rs", occ)
    cells += route_s

    pri = vtl.place(vtl.TILE_PRIORITY, {"in": ["w", "s"], "out": "e"},
                     params={"priority_rank_w": 0, "priority_rank_s": 1,
                             "priority_rank_n": 0, "priority_rank_e": 0, "scheduling_mode": 0},
                     cell_id="pri", rel_row=0, rel_col=0)
    cells.append(pri)
    occ[(0, 0)] = "pri"
    add = vtl.place(vtl.TILE_ADDER, {"in_a": "w", "in_b": "w", "out": "e"}, cell_id="add", rel_row=0, rel_col=1)
    cells.append(add)
    occ[(0, 1)] = "add"
    return cells, len(route_w) + len(route_s)


def _build_fixed_orientation_forced_detour():
    """priority FIXED to accept from N/S only (this session's own
    previously-hardcoded default, `#759`-`#767`) -- forcing the real
    west source into a real, 3-segment detour to reach the wrong-facing
    north port instead."""
    occ = {}
    cells = []
    src_w = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="src_w", rel_row=0, rel_col=-5, preload_value=7)
    cells.append(src_w)
    occ[(0, -5)] = "src_w"
    src_s = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="src_s", rel_row=5, rel_col=0, preload_value=3)
    cells.append(src_s)
    occ[(5, 0)] = "src_s"
    pri = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                     params={"priority_rank_n": 0, "priority_rank_s": 1,
                             "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 0},
                     cell_id="pri", rel_row=0, rel_col=0)
    cells.append(pri)
    occ[(0, 0)] = "pri"
    add = vtl.place(vtl.TILE_ADDER, {"in_a": "w", "in_b": "w", "out": "e"}, cell_id="add", rel_row=0, rel_col=1)
    cells.append(add)
    occ[(0, 1)] = "add"

    # Real detour: north (clear of row 0, avoiding a collision with
    # pri itself), then east, then south into pri's own north face.
    seg1 = manhattan_route((0, -5), "n", (-3, -5), "e", "rw1", occ)
    cells += seg1
    seg2 = manhattan_route((-3, -5), "e", (-3, 0), "s", "rw2", occ)
    cells += seg2
    seg3 = manhattan_route((-3, 0), "s", (-1, 0), "s", "rw3", occ)
    cells += seg3
    route_w_total = len(seg1) + len(seg2) + len(seg3)

    route_s = manhattan_route((5, 0), "n", (1, 0), "n", "rs", occ)
    cells += route_s
    return cells, route_w_total + len(route_s)


def test_orientation_mismatch_measurably_costs_more_cells_and_hops():
    matched_cells, matched_hops = _build_matched_orientation()
    fixed_cells, fixed_hops = _build_fixed_orientation_forced_detour()

    matched_icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=matched_cells)},
                                  placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                                  name="matched")
    fixed_icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=fixed_cells)},
                                placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                                name="fixed")
    assert matched_icm.check_connections() == []
    assert fixed_icm.check_connections() == []

    matched_records, _ = matched_icm.flatten()
    fixed_records, _ = fixed_icm.flatten()
    matched_grid = SuperGrid(matched_records)
    fixed_grid = SuperGrid(fixed_records)
    for _ in range(30):
        matched_grid.tick()
        fixed_grid.tick()

    # Both real layouts compute the correct result...
    assert matched_grid.cells[(0, 1)].adder_out_buffer == 10  # 7 + 3
    assert fixed_grid.cells[(0, 1)].adder_out_buffer == 10

    # ...but the mismatched orientation costs measurably more.
    assert len(fixed_cells) > len(matched_cells)
    assert fixed_hops > matched_hops
    assert len(matched_cells) == 12
    assert len(fixed_cells) == 18
