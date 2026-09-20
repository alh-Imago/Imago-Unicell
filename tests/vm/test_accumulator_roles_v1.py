"""tests/vm/test_accumulator_roles_v1.py — points.md #787: real tests
of `accumulator`'s own three distinct real roles -- increment,
decrement, and pulse-mode threshold-crossing. The real, central
finding: `inc`/`dec` are genuinely separate, dedicated physical
directions (not a shared, competing slot the way `adder`'s `in_a`/
`in_b` are) -- confirmed directly that this makes accumulator IMMUNE
to `#770`'s own rank-vs-timing operand-order hazard, unlike every
other order-sensitive role tested this session (`subtract`,
`nano_gate`'s 4 topologies, `nano_hold_trigger`). The role here is
decided by WHICH FACE an arrival comes from, never by WHICH ONE
ARRIVES FIRST.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import vix_tile_library_v1 as vtl  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
import icm_v3 as v3  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from rats_nest_router_v1 import manhattan_route  # noqa: E402


def _run(inc_far):
    occ = {}
    cells = []
    acc = vtl.place(vtl.TILE_ACCUMULATOR, {"inc": "n", "dec": "s", "out": "e"},
                     params={"step_amount": 5}, cell_id="acc", rel_row=0, rel_col=0)
    cells.append(acc)
    occ[(0, 0)] = "acc"
    sink = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink", rel_row=0, rel_col=1)
    cells.append(sink)
    occ[(0, 1)] = "sink"

    if inc_far:
        inc_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="inc_src", rel_row=-5, rel_col=0,
                             preload_value=1)
        cells.append(inc_src)
        occ[(-5, 0)] = "inc_src"
        cells += manhattan_route((-5, 0), "s", (-1, 0), "s", "rinc", occ)
        dec_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="dec_src", rel_row=1, rel_col=0,
                             preload_value=1)
        cells.append(dec_src)
        occ[(1, 0)] = "dec_src"
    else:
        inc_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="inc_src", rel_row=-1, rel_col=0,
                             preload_value=1)
        cells.append(inc_src)
        occ[(-1, 0)] = "inc_src"
        dec_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="dec_src", rel_row=5, rel_col=0,
                             preload_value=1)
        cells.append(dec_src)
        occ[(5, 0)] = "dec_src"
        cells += manhattan_route((5, 0), "n", (1, 0), "n", "rdec", occ)

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="acc_test")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(20):
        grid.tick()
    return grid.cells[(0, 0)].acc_total


def test_inc_dec_role_is_direction_encoded_not_order_sensitive():
    """The real, central finding: regardless of which physical source
    (inc or dec) arrives first, the net result is correct (+5-5=0),
    confirming the real role is decided by WHICH FACE the arrival
    comes from, never by arrival order -- immune to #770's hazard."""
    assert _run(inc_far=True) == 0
    assert _run(inc_far=False) == 0


def test_pulse_mode_resets_and_latches_on_threshold_crossing():
    """accumulator's own third role, direct core_config construction
    (not yet exposed via the tile, per its own documented scope):
    once the running total crosses a real, configured threshold, it
    resets to 0 and latches the real crossing value as its own real
    output, offering it downstream."""
    records = [
        v3.IcmV3Record(cell_id="inc_src", row=-1, col=0, core="ram",
                        core_config={"downstream_mask": ["s"], "fixed_mode": 1, "load_data_valid": 1},
                        preload_value=1),
        v3.IcmV3Record(cell_id="acc", row=0, col=0, core="accumulator",
                        core_config={"inc_dir": ["n"], "dec_dir": [], "downstream_mask": ["e"],
                                     "step_amount": 4, "pulse_mode": 1, "threshold": 10}),
        v3.IcmV3Record(cell_id="sink", row=0, col=1, core="ram",
                        core_config={"upstream_mask": ["w"], "downstream_mask": ["e"]}),
    ]
    grid = SuperGrid(records)
    acc_cell = grid.cells[(0, 0)]
    sink_cell = grid.cells[(0, 1)]
    for _ in range(6):
        grid.tick()
    # Total crossed 10 at 12 (0->4->8->12), reset to 0, latched 12.
    assert acc_cell.acc_out_buffer == 12
    assert sink_cell.ram_data_reg == 12
