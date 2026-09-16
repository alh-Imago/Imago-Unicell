"""tests/vm/test_reduction_tree_hand_built_v1.py — points.md #759: the
first hand-built, N=4 reduction tree using `priority` at every real
convergence point (t = a+b+c+d, via two levels of priority-arbitrated
pairwise adds), built specifically to explore what a general
composition/matching placement algorithm would need to handle --
per Alan's own direct framing, treating solved pairs as the next
"whole piece" to be matched against the next pair in the chain.

Real, honest purpose: this is exploratory, hand-traced work (matching
`#750`'s own real precedent), not a general algorithm -- three
genuine geometric lessons surfaced building it, each recorded in
`points.md` #759 and in the comments below, directly relevant to
whatever composition/matching system gets built next.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import vix_tile_library_v1 as vtl  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def _combine_unit(row, col, uid, out_dir="e"):
    """One real 'combine' primitive: a priority cell arbitrating two
    real inputs arriving from N and S, feeding one adder from the
    west. Real lesson #1 (#759): priority only arbitrates N/S (as
    configured here) -- its own two real sources must be DIRECTLY
    north/south of it, same column, not offset. Real lesson #3: the
    adder's own real output direction must be explicitly chosen to
    match wherever the next real consumer actually sits -- it is
    never safe to assume a default."""
    pri = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                     params={"priority_rank_n": 0, "priority_rank_s": 1,
                             "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 0},
                     cell_id=f"pri_{uid}", rel_row=row, rel_col=col)
    add = vtl.place(vtl.TILE_ADDER, {"in_a": "w", "in_b": "w", "out": out_dir},
                     cell_id=f"add_{uid}", rel_row=row, rel_col=col + 1)
    return [pri, add]


def _relay(row, col, in_dir, out_dir, uid):
    return vtl.place(vtl.TILE_RAM_FLOWING, {"in": in_dir, "out": out_dir},
                      cell_id=f"relay_{uid}", rel_row=row, rel_col=col)


def _build_reduce4(leaves):
    """Real lesson #2 (#759): a naive, perfectly-adjacent binary tree
    layout does not work past N=2 -- level-1's own two results land
    too far apart (4 rows) for level-2's priority cell to directly
    sandwich (which needs them exactly 2 apart). Bridging the gap
    needs a real relay chain -- and since a relay can only go straight
    (one real direction in, another out; it cannot turn a corner in a
    single hop), bridging a genuinely diagonal offset needs TWO relay
    hops, not one."""
    cells = []
    cells.append(vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="leaf_0", rel_row=0, rel_col=0, preload_value=leaves[0]))
    cells.append(vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="leaf_1", rel_row=2, rel_col=0, preload_value=leaves[1]))
    cells.append(vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="leaf_2", rel_row=4, rel_col=0, preload_value=leaves[2]))
    cells.append(vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="leaf_3", rel_row=6, rel_col=0, preload_value=leaves[3]))
    cells += _combine_unit(row=1, col=0, uid="L1a", out_dir="s")
    cells += _combine_unit(row=5, col=0, uid="L1b", out_dir="n")
    cells.append(_relay(2, 1, "n", "e", "a1"))
    cells.append(_relay(2, 2, "w", "s", "a2"))
    cells.append(_relay(4, 1, "s", "e", "b1"))
    cells.append(_relay(4, 2, "w", "n", "b2"))
    cells += _combine_unit(row=3, col=2, uid="L2")
    return vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                           placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                           name="reduce4")


def test_reduce4_sums_four_leaves_correctly():
    leaves = [10, 20, 30, 40]
    icm = _build_reduce4(leaves)
    assert icm.check_connections() == []
    assert icm.check_known_gotchas() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(20):
        grid.tick()
    result = grid.cells[(3, 3)]
    assert result.adder_data_valid is True
    assert result.adder_out_buffer == sum(leaves)


def test_reduce4_with_different_values():
    leaves = [1, 2, 3, 4]
    icm = _build_reduce4(leaves)
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(20):
        grid.tick()
    assert grid.cells[(3, 3)].adder_out_buffer == 10
