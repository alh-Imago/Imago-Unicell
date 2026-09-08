"""
test_lane_combine_tree_v1.py — points.md #692: Alan's own real
recursive lane-combine tree idea, proven in the VM.

THE REAL IDEA, restated precisely: rather than a flat, single-level
OR-tree (the "real 2-stage OR-tree" `#544` predicted 8-lane would
need, without pinning its exact shape down), build N-lane combination
from a recursive DOUBLING structure, reusing the SAME already-proven
2-input gather cell (`test_lane_split_recombine_v1.py`, `#544`) at
every level: each pair of independent sources is masked/shifted to its
own natural position and OR-gathered at one cell; a SECOND identical
sub-tree does the same, then applies ONE ADDITIONAL shift to its own
already-combined output before the two sub-trees are OR-combined at a
final merge cell.

THE REAL, CRITICAL PROPERTY CHECKED BEFORE BUILDING, not assumed: the
addon chain (mask -> shift -> invert) applies INSIDE a cell's own
ordinary offer step, the exact same tick it would have offered its raw
value anyway (confirmed directly against `unicell_super_automaton_v1.
apply_addons()`, called from within the offer pass itself, not a
separate pipeline stage). This means adding a shift to one branch of
the tree costs ZERO extra hop-count/tick delay relative to an
unshifted branch -- the single hardest real constraint `#544` found
(every path to a recombiner needs the SAME hop count, or the design
silently breaks) is NOT violated by this doubling structure. That
property is exactly what this test confirms empirically, not just
argues for.

Real, concrete layout (7 cells, cardinal-only adjacency, no diagonal
shortcuts): two independent 2-source "gather" sub-trees (matching
`#544`'s own proven mechanism exactly -- one source shifted to its own
local low byte, one to its own local high byte, OR-gathered with NO
addon on the gatherer itself), placed symmetrically north/south of a
shared merge cell. The SOUTH sub-tree's own gatherer applies ONE
EXTRA shift-left-by-16 to its already-combined 16-bit local pattern
before offering it north -- exactly "cell 2... shifts the entire
combined pattern up by 16" from Alan's own description. Every source
is exactly 2 hops from the merge cell, by construction, matching
`#544`'s own hard equal-hop-count requirement.

    source1(1,-1) --e--> \\
                           gathererA(1,0) --n--> \\
    source2(1,1)  --w--> /                        \\
                                                     merge(0,0)
    source3(-1,-1)--e--> \\                        /
                           gathererB(-1,0) --s--> /
    source4(-1,1) --w--> /   [+shift left 16]

Real, honest scope: proves the recursive doubling mechanism for a
4-lane (8-bit each) word, built from two real 2-lane sub-trees. The
fuller 8-lane (4-bit each) case -- a further recursive level, or four
independent nibble sources gathered directly since RAM's own 4 real
cardinal ports allow it in one level -- is the same real mechanism,
one level deeper; not built here, a genuine, ready-to-pick-up next
step, matching `#544`'s own original scope discipline.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

VALUE1 = 0x11   # -> bits[7:0]    (gathererA, no shift)
VALUE2 = 0x22   # -> bits[15:8]   (gathererA, shift left 8)
VALUE3 = 0x33   # -> bits[23:16]  (gathererB, shift left 8, then +16 from gathererB itself)
VALUE4 = 0x44   # -> bits[31:24]  (gathererB, shift left 8+8=16 -> effectively 24 total)
EXPECTED = 0x44332211


def _one_shot(cell_id, row, col, downstream, init_data=0, addon_config=None):
    return v3.IcmV3Record(
        cell_id=cell_id, row=row, col=col, core="ram",
        core_config={"downstream_mask": downstream, "upstream_mask": [],
                     "fixed_mode": 0, "load_data_valid": 1, "init_data": init_data},
        addon_config=addon_config or {},
    )


def _relay(cell_id, row, col, upstream, downstream, addon_config=None):
    return v3.IcmV3Record(
        cell_id=cell_id, row=row, col=col, core="ram",
        core_config={"downstream_mask": downstream, "upstream_mask": upstream,
                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0},
        addon_config=addon_config or {},
    )


def _build_grid():
    records = [
        # North sub-tree: gathererA combines source1 (natural, no shift)
        # and source2 (shifted left 8 -> local bits[15:8]) -- exactly
        # #544's own already-proven 2-lane mechanism, unmodified.
        _one_shot("source1", 1, -1, ["e"], VALUE1),
        _one_shot("source2", 1, 1, ["w"], VALUE2,
                  addon_config={"shift_en": 1, "direction": 0, "shift_amt": 8}),
        _relay("gathererA", 1, 0, ["w", "e"], ["n"]),

        # South sub-tree: identical internal shape to the north one
        # (source3 natural, source4 shifted left 8), but gathererB
        # ALSO shifts its own already-combined 16-bit pattern left by
        # 16 before offering north -- Alan's own real "cell 2 shifts
        # the entire combined pattern up by 16."
        _one_shot("source3", -1, -1, ["e"], VALUE3),
        _one_shot("source4", -1, 1, ["w"], VALUE4,
                  addon_config={"shift_en": 1, "direction": 0, "shift_amt": 8}),
        _relay("gathererB", -1, 0, ["w", "e"], ["s"],
               addon_config={"shift_en": 1, "direction": 0, "shift_amt": 16}),

        # Final merge -- plain OR-capture, no addon, matching #544's
        # own merge cell exactly. Every source is exactly 2 hops away.
        _relay("merge", 0, 0, ["n", "s"], []),
    ]
    return SuperGrid(records)


def test_four_independent_sources_combine_via_the_recursive_doubling_tree():
    grid = _build_grid()
    ticks = grid.run_to_quiescence(max_ticks=50)
    merge = grid.cells[(0, 0)]
    assert merge.ram_data_reg == EXPECTED, (
        f"expected 0x{EXPECTED:08X}, got 0x{merge.ram_data_reg:08X}"
    )
    assert merge.ram_data_valid is True
    assert ticks < 50


def test_every_source_reaches_merge_in_exactly_the_same_tick():
    """Real, direct confirmation of the property the whole design
    depends on -- not just that the final answer happens to be right,
    but that it's right BECAUSE every path has the same real hop
    count, matching #544's own hard requirement exactly. Checked by
    ticking one step at a time and confirming `merge` settles all at
    once (not partially, not staggered) once it does."""
    grid = _build_grid()
    for _ in range(2):
        assert grid.cells[(0, 0)].ram_data_valid is False
        grid.tick()
    grid.tick()
    assert grid.cells[(0, 0)].ram_data_valid is True
    assert grid.cells[(0, 0)].ram_data_reg == EXPECTED


def test_shifted_subtree_alone_produces_the_correct_high_half():
    """Isolates the real, new part of this design (not #544's already-
    proven half): gathererB's own extra shift-by-16 must relocate its
    already-combined LOCAL 16-bit pattern (source3 at bits[7:0],
    source4 at bits[15:8]) up to bits[31:16] intact, not corrupt or
    truncate it."""
    grid = _build_grid()
    for _ in range(3):
        grid.tick()
    gatherer_b_local_pattern = VALUE3 | (VALUE4 << 8)
    expected_high_half = (gatherer_b_local_pattern << 16) & 0xFFFFFFFF
    merge = grid.cells[(0, 0)]
    assert (merge.ram_data_reg & 0xFFFF0000) == expected_high_half


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
