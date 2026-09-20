"""tests/vm/test_nano_hold_trigger_semantics_v1.py — points.md #786:
real, direct test of `nano_hold_trigger`'s own real role -- confirming
the intended "hold the first arrival, release it unchanged on a later,
separate trigger" behavior, and confirming it shares `#770`'s own
rank-vs-timing operand-order hazard (subtract's own hazard) rather
than needing a new one: whichever real value arrives FIRST becomes the
"held" one, regardless of which physical source was intended to play
that role.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import vix_tile_library_v1 as vtl  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from rats_nest_router_v1 import manhattan_route  # noqa: E402


def test_intended_order_holds_first_value_releases_on_trigger():
    occ = {}
    cells = []
    hold_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="hold_src", rel_row=-1, rel_col=0,
                          preload_value=77)
    cells.append(hold_src)
    occ[(-1, 0)] = "hold_src"
    gate = vtl.place(vtl.TILE_NANO_HOLD_TRIGGER, {"out": "e"}, cell_id="gate", rel_row=0, rel_col=0)
    cells.append(gate)
    occ[(0, 0)] = "gate"
    trig_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="trig_src", rel_row=5, rel_col=0,
                          preload_value=999)
    cells.append(trig_src)
    occ[(5, 0)] = "trig_src"
    cells += manhattan_route((5, 0), "n", (1, 0), "n", "rtrig", occ)
    sink = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink", rel_row=0, rel_col=1)
    cells.append(sink)
    occ[(0, 1)] = "sink"

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="hold_trigger_intended")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(15):
        grid.tick()
    # The held value (77) is released unchanged; the trigger's own
    # payload (999) is discarded entirely -- only its arrival matters.
    assert grid.cells[(0, 1)].ram_data_reg == 77


def test_order_sensitive_shares_770_hazard_not_a_new_one():
    """points.md #786: confirms the "hold"/"trigger" roles are decided
    purely by arrival order, not by which physical source was intended
    to play which role -- the exact same #770 hazard subtract has, not
    a new, gate-specific one."""
    occ = {}
    cells = []
    trig_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="trig_src", rel_row=-1, rel_col=0,
                          preload_value=999)
    cells.append(trig_src)
    occ[(-1, 0)] = "trig_src"
    gate = vtl.place(vtl.TILE_NANO_HOLD_TRIGGER, {"out": "e"}, cell_id="gate", rel_row=0, rel_col=0)
    cells.append(gate)
    occ[(0, 0)] = "gate"
    hold_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="hold_src", rel_row=5, rel_col=0,
                          preload_value=77)
    cells.append(hold_src)
    occ[(5, 0)] = "hold_src"
    cells += manhattan_route((5, 0), "n", (1, 0), "n", "rhold", occ)
    sink = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink", rel_row=0, rel_col=1)
    cells.append(sink)
    occ[(0, 1)] = "sink"

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="hold_trigger_reversed")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(15):
        grid.tick()
    # The physically-closer source (999, intended as the trigger) wins
    # the "held" slot instead, since it simply arrived first.
    assert grid.cells[(0, 1)].ram_data_reg == 999
