"""tests/vm/test_rats_nest_router_v1.py — points.md #760: real tests
for the general Manhattan router, plus the first full, loose "rat's
nest" reduction tree, confirming the loose-placement half of Alan's
own proposed rat's-nest approach works end to end.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import vix_tile_library_v1 as vtl  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from rats_nest_router_v1 import manhattan_route  # noqa: E402


def test_straight_line_route_delivers_correctly():
    occ = {}
    src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="src", rel_row=0, rel_col=0, preload_value=7)
    cells = manhattan_route((0, 0), "e", (0, 5), "e", "r", occ)
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[src] + cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="straight")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(10):
        grid.tick()
    assert grid.cells[(0, 5)].ram_data_reg == 7
    assert grid.cells[(0, 5)].ram_data_valid is True


def test_l_shaped_turning_route_delivers_correctly():
    """Real, direct regression for bug #1 this router's own build
    surfaced: the turning relay's own 'in' must be the direction it
    actually receives from, not inferred from its own new direction."""
    occ = {}
    src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="src", rel_row=0, rel_col=0, preload_value=42)
    cells = manhattan_route((0, 0), "e", (4, 5), "e", "r", occ)
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[src] + cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="turning")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(15):
        grid.tick()
    assert grid.cells[(4, 5)].ram_data_reg == 42
    assert grid.cells[(4, 5)].ram_data_valid is True


def _combine_unit(row, col, uid, out_dir="e"):
    pri = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                     params={"priority_rank_n": 0, "priority_rank_s": 1,
                             "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 0},
                     cell_id=f"pri_{uid}", rel_row=row, rel_col=col)
    add = vtl.place(vtl.TILE_ADDER, {"in_a": "w", "in_b": "w", "out": out_dir},
                     cell_id=f"add_{uid}", rel_row=row, rel_col=col + 1)
    return [pri, add]


def test_loose_reduction_tree_with_generous_slack_still_computes_correctly():
    """The real payoff: a full N=4 reduction tree built with generous,
    loose spacing (leaves and combine units placed far apart, no
    attempt at a compact layout at all) still computes correctly, using
    the general router to bridge every gap -- confirming the 'loose,
    easy to get right' half of the rat's-nest approach genuinely
    works. The 'tighten toward minimum' half is real, separate,
    NOT YET built (points.md #760)."""
    occ = {}
    cells = []
    leaves = [10, 20, 30, 40]
    leaf_pos = [(0, 0), (10, 0), (20, 0), (30, 0)]
    for i, (v, (r, c)) in enumerate(zip(leaves, leaf_pos)):
        cells.append(vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id=f"leaf_{i}", rel_row=r, rel_col=c, preload_value=v))
        occ[(r, c)] = f"leaf_{i}"

    L1a = _combine_unit(row=5, col=20, uid="L1a", out_dir="e")
    L1b = _combine_unit(row=25, col=20, uid="L1b", out_dir="e")
    cells += L1a + L1b
    for c in L1a + L1b:
        occ[(c.rel_row, c.rel_col)] = c.cell_id

    cells += manhattan_route(leaf_pos[0], "e", (4, 20), "s", "r0", occ)
    cells += manhattan_route(leaf_pos[1], "e", (6, 20), "n", "r1", occ)
    cells += manhattan_route(leaf_pos[2], "e", (24, 20), "s", "r2", occ)
    cells += manhattan_route(leaf_pos[3], "e", (26, 20), "n", "r3", occ)

    L2 = _combine_unit(row=15, col=50, uid="L2", out_dir="e")
    cells += L2
    for c in L2:
        occ[(c.rel_row, c.rel_col)] = c.cell_id

    cells += manhattan_route((5, 21), "e", (14, 50), "s", "rA", occ)
    cells += manhattan_route((25, 21), "e", (16, 50), "n", "rB", occ)

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="reduce4_loose")
    assert icm.check_connections() == []
    assert icm.check_known_gotchas() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(100):
        grid.tick()
    result = grid.cells[(15, 51)]
    assert result.adder_data_valid is True
    assert result.adder_out_buffer == sum(leaves)
