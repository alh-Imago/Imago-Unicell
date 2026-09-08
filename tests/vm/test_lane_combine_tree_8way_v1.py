"""
test_lane_combine_tree_8way_v1.py — points.md #693: the 8-lane (4-bit
each) extension of `#692`'s own recursive lane-combine tree, per
Alan's own explicit call: this doubling structure is "the basis for
the combinational tree... not cheap in cell usage but it's safe and
specific." Built as a strict nesting of the SAME 2-input combine+
optional-shift primitive at every level, not a flatter "gather 4 at
once" shortcut RAM's real port count would technically allow -- a
deliberate choice, matching Alan's own stated preference for a single,
uniform, always-provably-correct building block over a cheaper but
less general special case.

THE REAL STRUCTURE, three real levels deep:

  Level 0 (4 "inner" gatherer cells) -- each combines 2 independent
  4-bit (nibble) sources into a local 8-bit pattern, using #544's own
  proven mechanism exactly (one source at local position 0, one
  shifted by 4 to local position 1, OR-gathered with no addon on the
  gatherer itself).

  Level 1 (2 "outer" gatherer cells, `#692`'s own real shape) -- each
  combines 2 level-0 outputs into a local 16-bit pattern. The
  "unshifted" side (gathererA/gathererB) offers its local pattern
  as-is; the "shifted" side (gatherer_2cd/gatherer_4gh) additionally
  shifts its own already-combined 8-bit local pattern by 8 before
  offering it into its own parent.

  Level 2 (1 final merge) -- combines gathererA's own local 16-bit
  pattern (unshifted) with gathererB's own local 16-bit pattern
  (additionally shifted by 16 at gathererB itself) into the final,
  real 32-bit, 8-lane (4-bit each) word.

Every one of the 8 nibble sources is exactly 3 hops from the final
merge cell, by construction -- confirmed directly below, matching
`#544`'s own hard equal-hop-count requirement at every level, not just
checked once at the top.

Real, honest scope: this is genuinely more cells (15) for less payload
per lane than a flatter design might use, exactly as Alan named --
deliberately kept safe and specific (a single, uniform, already-proven
2-input primitive nested three levels deep) rather than optimized for
cell count. No real RTL testbench exists yet either, matching `#544`'s
and `#692`'s own scope discipline exactly.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

# Eight real, independent 4-bit values -- chosen so the final expected
# word (0x87654321) is immediately, visually self-checking.
NIBBLE_A, NIBBLE_B = 0x1, 0x2   # -> gatherer_1ab -> bits[7:0]
NIBBLE_C, NIBBLE_D = 0x3, 0x4   # -> gatherer_2cd -> bits[15:8] (local +8 shift)
NIBBLE_E, NIBBLE_F = 0x5, 0x6   # -> gatherer_3ef -> bits[23:16] (gathererB's own +16 shift)
NIBBLE_G, NIBBLE_H = 0x7, 0x8   # -> gatherer_4gh -> bits[31:24] (local +8, then gathererB's +16)
EXPECTED = 0x87654321


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
        # Level 0, "1ab" (feeds gathererA, unshifted side) --------------
        _one_shot("nibbleA", 2, -1, ["n"], NIBBLE_A),
        _one_shot("nibbleB", 1, -2, ["e"], NIBBLE_B,
                  addon_config={"shift_en": 1, "direction": 0, "shift_amt": 4}),
        _relay("gatherer_1ab", 1, -1, ["s", "w"], ["e"]),

        # Level 0, "2cd" (feeds gathererA, the +8 local side) ----------
        _one_shot("nibbleC", 2, 1, ["n"], NIBBLE_C),
        _one_shot("nibbleD", 1, 2, ["w"], NIBBLE_D,
                  addon_config={"shift_en": 1, "direction": 0, "shift_amt": 4}),
        _relay("gatherer_2cd", 1, 1, ["s", "e"], ["w"],
               addon_config={"shift_en": 1, "direction": 0, "shift_amt": 8}),

        # Level 1: gathererA combines 1ab (bits[7:0]) + 2cd (bits[15:8])
        _relay("gathererA", 1, 0, ["w", "e"], ["n"]),

        # Level 0, "3ef" (feeds gathererB, unshifted side) -------------
        _one_shot("nibbleE", -2, -1, ["s"], NIBBLE_E),
        _one_shot("nibbleF", -1, -2, ["e"], NIBBLE_F,
                  addon_config={"shift_en": 1, "direction": 0, "shift_amt": 4}),
        _relay("gatherer_3ef", -1, -1, ["n", "w"], ["e"]),

        # Level 0, "4gh" (feeds gathererB, the +8 local side) ----------
        _one_shot("nibbleG", -2, 1, ["s"], NIBBLE_G),
        _one_shot("nibbleH", -1, 2, ["w"], NIBBLE_H,
                  addon_config={"shift_en": 1, "direction": 0, "shift_amt": 4}),
        _relay("gatherer_4gh", -1, 1, ["n", "e"], ["w"],
               addon_config={"shift_en": 1, "direction": 0, "shift_amt": 8}),

        # Level 1: gathererB combines 3ef (local bits[7:0]) + 4gh
        # (local bits[15:8]), THEN shifts its OWN already-combined
        # 16-bit local pattern up by 16 -- #692's own real mechanism,
        # one level further out.
        _relay("gathererB", -1, 0, ["w", "e"], ["s"],
               addon_config={"shift_en": 1, "direction": 0, "shift_amt": 16}),

        # Level 2: final merge -- plain OR-capture, no addon.
        _relay("merge", 0, 0, ["n", "s"], []),
    ]
    return SuperGrid(records)


def test_eight_independent_nibbles_combine_via_the_three_level_tree():
    grid = _build_grid()
    ticks = grid.run_to_quiescence(max_ticks=50)
    merge = grid.cells[(0, 0)]
    assert merge.ram_data_reg == EXPECTED, (
        f"expected 0x{EXPECTED:08X}, got 0x{merge.ram_data_reg:08X}"
    )
    assert merge.ram_data_valid is True
    assert ticks < 50


def test_every_source_reaches_merge_in_exactly_the_same_tick():
    """Real, direct confirmation of #544's own hard equal-hop-count
    requirement, now checked THREE real levels deep, not just at the
    top: `merge` must settle all at once, not staggered."""
    grid = _build_grid()
    for _ in range(3):
        assert grid.cells[(0, 0)].ram_data_valid is False
        grid.tick()
    grid.tick()
    assert grid.cells[(0, 0)].ram_data_valid is True
    assert grid.cells[(0, 0)].ram_data_reg == EXPECTED


def test_each_quarter_produces_the_correct_real_intermediate_value():
    """Isolates each of the 4 real inner gatherer cells' own local
    combine, independent of the outer shifts -- confirms the tree's
    own real correctness level by level, not just at the final root."""
    grid = _build_grid()
    for _ in range(2):
        grid.tick()
    assert grid.cells[(1, -1)].ram_data_reg == (NIBBLE_A | (NIBBLE_B << 4))
    assert grid.cells[(1, 1)].ram_data_reg == (NIBBLE_C | (NIBBLE_D << 4))
    assert grid.cells[(-1, -1)].ram_data_reg == (NIBBLE_E | (NIBBLE_F << 4))
    assert grid.cells[(-1, 1)].ram_data_reg == (NIBBLE_G | (NIBBLE_H << 4))


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
