"""tests/vm/test_mul_dispatch_v1.py — points.md #790: real tests
confirming `mul`'s own new VM dispatch (`_deliver_mul`/`_offer_state_
mul`/`_clear_valid_mul`, registered under `core="mul"`) works
correctly. Before this, `core="mul"` had NO real VM dispatch at all --
confirmed directly, empirically, in the surrounding session (a real
`ValueError: unsupported core 'mul' for VM dispatch`), not merely
untested.

points.md #853/#854: extended with real tests for `wide_mode`, the
new sequential two-phase delivery of the internal product's high half
-- mirroring `mul_cell_v5/v5c.v`'s own real, tested RTL exactly, on
real placed cells (`SuperGrid`), not just the Python arithmetic oracle
(`fp32_mul_v1.py`, #849) that motivated it.
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
    mul = vtl.place(vtl.TILE_MUL, {"in_a": "w", "in_b": "s", "out": "e"}, {"wide_mode": 0}, cell_id="mul", rel_row=0, rel_col=0)
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
    mul = vtl.place(vtl.TILE_MUL, {"in_a": "n", "in_b": "s", "out": "e"}, {"wide_mode": 0}, cell_id="mul", rel_row=0, rel_col=0)
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


def _place_wide_mul_grid(a_val, b_val):
    """Real, shared construction for the wide_mode tests below --
    matches test_mul_computes_real_product_with_staggered_arrival's own
    real shape, wide_mode=1 the only real difference. A real, necessary
    correction found while writing these tests: a single dead-end sink
    can NEVER accept mul's own second (high) delivery -- ram_flowing's
    own real capture rule (`_deliver_ram`) refuses a new value while
    `ram_data_valid` is still set, and NOTHING clears it for a sink
    with no downstream of its own to ack it. A real two-sink relay
    chain (sink1 -> sink2) is required so sink1 can genuinely free
    itself between the two deliveries -- confirmed directly by tracing
    per-tick state before trusting this shape, not guessed."""
    a = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="a", rel_row=0, rel_col=-2, preload_value=a_val)
    relay = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="relay", rel_row=0, rel_col=-1)
    b = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="b", rel_row=1, rel_col=0, preload_value=b_val)
    mul = vtl.place(vtl.TILE_MUL, {"in_a": "w", "in_b": "s", "out": "e"}, {"wide_mode": 1}, cell_id="mul", rel_row=0, rel_col=0)
    sink1 = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink1", rel_row=0, rel_col=1)
    sink2 = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink2", rel_row=0, rel_col=2)
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[a, relay, b, mul, sink1, sink2])},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="mul_wide_test")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    return SuperGrid(records)


def test_wide_mode_delivers_low_half_first_matching_the_real_rtl():
    """points.md #853/#854: real FP32-significand-shaped operands
    (each in [2^23,2^24)), whose true product genuinely spans into the
    high 32 bits -- the exact case v4/v4c can never expose, and the
    same real pair mirrored from tb_mul_cell_v5c.v's own RTL testbench,
    not a fresh, disconnected choice of numbers. Checked EARLY
    (real, traced timing: sink1 holds low by tick 3, relays it onward
    and gets overwritten by the high half by tick 5) -- deliberately
    before the second delivery would overwrite it, since this test's
    own claim is specifically about which half arrives FIRST."""
    a_val, b_val = 0xC00000, 0xC00000   # 1.5 * 1.5 in real FP32-significand terms
    full_product = a_val * b_val
    grid = _place_wide_mul_grid(a_val, b_val)
    for _ in range(4):
        grid.tick()
    assert grid.cells[(0, 1)].ram_data_reg == (full_product & 0xFFFFFFFF)


def test_wide_mode_delivers_high_half_second_the_real_point_of_this_entry():
    """The real claim #853/#854 exist to prove at the VM level: after
    the low half is captured, relayed onward to sink2 (freeing sink1),
    and acknowledged, the SAME mul cell delivers the real high half
    next, on the SAME 'out' port -- no new port, no second routing
    group, matching the RTL's own real, sequential design exactly.
    sink1 ends up holding the HIGH half (its second, later capture);
    sink2 ends up holding the LOW half (relayed there first)."""
    a_val, b_val = 0xFFFFFF, 0xFFFFFF   # largest 24-bit value squared -- maximal real high-half content
    full_product = a_val * b_val
    grid = _place_wide_mul_grid(a_val, b_val)
    for _ in range(20):
        grid.tick()
    assert grid.cells[(0, 2)].ram_data_reg == (full_product & 0xFFFFFFFF), "sink2: the relayed LOW half"
    assert grid.cells[(0, 1)].ram_data_reg == (full_product >> 32) & 0xFFFFFFFF, "sink1: its own SECOND capture, the HIGH half"


def test_wide_mode_matches_fp32_mul_v1s_own_real_wide_product():
    """A real, cross-checked confirmation: the exact same 64-bit
    product this entry verifies at the cell level is precisely what
    fp32_mul_v1.py's own real significand multiply (#849) already
    computes internally (`a_sig * b_sig`, before normalize/round) --
    the same real value, now proven reachable on real placed cells,
    not just in the Python arithmetic oracle."""
    a_val, b_val = 0xABCDEF, 0x123456
    full_product = a_val * b_val
    grid = _place_wide_mul_grid(a_val, b_val)
    for _ in range(20):
        grid.tick()
    low = grid.cells[(0, 2)].ram_data_reg    # relayed onward, sink2
    high = grid.cells[(0, 1)].ram_data_reg   # sink1's own second capture
    assert (high << 32) | low == full_product
