"""
test_lane_split_recombine_v1.py — points.md #544: Alan's own real
architecture idea, checked precisely and proven both ways in the VM.

THE REAL IDEA: broadcast a 32-bit value to N cells, each masking (via
the already-real nibble_mask addon) only its own lane, then recombine
via RAM's own already-proven multi-direction OR-capture -- the same
real structural insight behind NVFP4's own shared-scale microscaling
format (points.md #543's own comparison), built here from existing
UniCell primitives with zero new RTL.

THE REAL, HARD REQUIREMENT this session's own conversation surfaced:
every path from source to the recombiner MUST have the same hop
count, or the design breaks -- not an optimization, a correctness
requirement. Confirmed directly against the real RTL: RAM's own
capture condition (`!data_valid`) blocks any arrival once one
direction has already been captured, so a staggered arrival either
stalls forever, or worse, gets silently REJECTED after the first lane
already claimed the "empty" slot -- producing a confidently wrong
answer, not a visible failure. Both failure shapes are demonstrated
directly below, not just asserted.

A real bug found and fixed while building the positive case: the
source cell was originally configured `fixed_mode=1` ("offer this
value forever," RAM's own real continuously-live semantic) rather
than `fixed_mode=0, load_data_valid=1` (a genuine ONE-SHOT preloaded
value). The former caused perpetual re-transmission -- source kept
re-broadcasting the same value every time a downstream ack freed it
up again, since a fixed_mode cell never stops offering.

Real, honest scope: proves the 2-lane (16-bit) case specifically, the
simplest real instance of Alan's own "split to 2, then split out from
there" tree idea. The fuller 4-lane/8-lane tree (RAM's own 4-port
limit needing a real 2-stage OR-tree, per the same conversation) is
real, designed, and NOT yet built -- a genuine next step, not silently
assumed solved here.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

TEST_VALUE = 0x11223344


def test_equal_hop_lanes_split_mask_and_recombine_correctly():
    """The real positive case: source(0,0) broadcasts E+W simultaneously.
    East lane keeps the high 16 bits, west lane keeps the low 16 bits.
    Both relay north then sideways into a shared merge cell at (-1,0)
    -- real cardinal-only adjacency, no diagonal shortcuts, matching
    how an actual grid works. Both lanes are EXACTLY 3 hops from
    source to merge, by construction."""
    records = [
        # fixed_mode=0, load_data_valid=1: the real one-shot fix (see
        # module docstring) -- NOT fixed_mode=1's different,
        # continuously-re-offering "constant" semantic.
        v3.IcmV3Record(cell_id="source", row=0, col=0, core="ram",
                        core_config={"downstream_mask": ["e", "w"], "upstream_mask": [],
                                     "fixed_mode": 0, "load_data_valid": 1, "init_data": TEST_VALUE}),
        v3.IcmV3Record(cell_id="branch_E", row=0, col=1, core="ram",
                        core_config={"downstream_mask": ["n"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0},
                        addon_config={"mask_en": 1, "nibble_mask": 0b00001111}),  # keep high 16 bits
        v3.IcmV3Record(cell_id="relay_NE", row=-1, col=1, core="ram",
                        core_config={"downstream_mask": ["w"], "upstream_mask": ["s"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="branch_W", row=0, col=-1, core="ram",
                        core_config={"downstream_mask": ["n"], "upstream_mask": ["e"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0},
                        addon_config={"mask_en": 1, "nibble_mask": 0b11110000}),  # keep low 16 bits
        v3.IcmV3Record(cell_id="relay_NW", row=-1, col=-1, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["s"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="merge", row=-1, col=0, core="ram",
                        core_config={"downstream_mask": [], "upstream_mask": ["e", "w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
    ]
    grid = SuperGrid(records)
    ticks = grid.run_to_quiescence(max_ticks=50)
    merge = grid.cells[(-1, 0)]
    assert merge.ram_data_reg == TEST_VALUE, f"expected 0x{TEST_VALUE:08X}, got 0x{merge.ram_data_reg:08X}"
    assert merge.ram_data_valid is True
    assert ticks < 50


def test_mismatched_hop_lanes_lose_data_and_never_quiesce():
    """The real negative case, deliberately simplified to a single row
    -- no lane masking needed to make the point: two sources with
    genuinely different values, one 2 hops from a shared merge cell,
    the other 1 hop (direct). If path length didn't matter, merge
    would hold the OR of both. It doesn't -- it holds ONLY the
    earlier-arriving (shorter-path) value, and the system never
    reaches quiescence because the later, now-permanently-rejected
    lane keeps retrying forever."""
    VALUE_A = 0xAAAA0000
    VALUE_B = 0x00005555
    records = [
        v3.IcmV3Record(cell_id="source_A", row=0, col=0, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": [],
                                     "fixed_mode": 0, "load_data_valid": 1, "init_data": VALUE_A}),
        v3.IcmV3Record(cell_id="relay_A", row=0, col=1, core="ram",
                        core_config={"downstream_mask": ["e"], "upstream_mask": ["w"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="merge", row=0, col=2, core="ram",
                        core_config={"downstream_mask": [], "upstream_mask": ["w", "e"],
                                     "fixed_mode": 0, "load_data_valid": 0, "init_data": 0}),
        v3.IcmV3Record(cell_id="source_B", row=0, col=3, core="ram",
                        core_config={"downstream_mask": ["w"], "upstream_mask": [],
                                     "fixed_mode": 0, "load_data_valid": 1, "init_data": VALUE_B}),
    ]
    grid = SuperGrid(records)
    try:
        grid.run_to_quiescence(max_ticks=30)
        quiesced = True
    except TimeoutError:
        quiesced = False

    merge = grid.cells[(0, 2)]
    correct_combined = VALUE_A | VALUE_B
    # Either real failure shape proves the point: never settling, or
    # settling on the wrong (partial) value. Both are checked, not
    # just one assumed.
    assert not quiesced or merge.ram_data_reg != correct_combined, (
        "mismatched hop counts should NOT produce the correct combined "
        "value -- if this fails, the real correctness requirement this "
        "test exists to demonstrate isn't actually real"
    )
    # The real, specific, predicted outcome: only the shorter-path
    # lane's own value survives.
    assert merge.ram_data_reg == VALUE_B
    assert not quiesced, "the longer-path lane's rejected retry should keep the grid perpetually active"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
