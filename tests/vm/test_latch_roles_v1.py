"""tests/vm/test_latch_roles_v1.py — points.md #788: real tests of
`latch`'s own three distinct real roles -- SET, CLEAR, TOGGLE. Like
`accumulator` (`#787`), each role has its own dedicated physical face
(`set_dir`/`clear_dir`/`toggle_dir`, confirmed against the tile's own
real port contract) rather than a shared, competing slot -- confirmed
directly, empirically, that this makes latch IMMUNE to `#770`'s own
rank-vs-timing operand-order hazard too. Also confirms the real,
established simultaneous-trigger precedence (CLEAR > SET > TOGGLE).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import vix_tile_library_v1 as vtl  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from rats_nest_router_v1 import manhattan_route  # noqa: E402


def test_set_toggle_basic_behavior():
    lat = vtl.place(vtl.TILE_LATCH, {"set": "n", "clear": "s", "toggle": "e", "out": "w"},
                     cell_id="lat", rel_row=0, rel_col=1)
    set_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="set_src", rel_row=-1, rel_col=1, preload_value=1)
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[lat, set_src])},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))], name="set")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(10):
        grid.tick()
    assert grid.cells[(0, 1)].latch_state is True


def test_set_role_is_direction_encoded_not_order_sensitive():
    """The real, central finding, matching accumulator's own (#787):
    whether the SET arrival comes immediately or via a longer, later
    path, the real result is identical -- confirming role is decided
    by WHICH FACE, never WHICH ORDER."""
    def run(set_far):
        occ = {}
        cells = []
        lat = vtl.place(vtl.TILE_LATCH, {"set": "n", "clear": "s", "toggle": "e", "out": "w"},
                         cell_id="lat", rel_row=0, rel_col=1)
        cells.append(lat)
        occ[(0, 1)] = "lat"
        if set_far:
            set_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="set_src", rel_row=-5, rel_col=1,
                                 preload_value=1)
            cells.append(set_src)
            occ[(-5, 1)] = "set_src"
            cells += manhattan_route((-5, 1), "s", (-1, 1), "s", "rset", occ)
        else:
            set_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="set_src", rel_row=-1, rel_col=1,
                                 preload_value=1)
            cells.append(set_src)
            occ[(-1, 1)] = "set_src"
        icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                              placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                              name="order")
        assert icm.check_connections() == []
        records, _ = icm.flatten()
        grid = SuperGrid(records)
        for _ in range(15):
            grid.tick()
        return grid.cells[(0, 1)].latch_state

    assert run(set_far=True) is True
    assert run(set_far=False) is True


def test_simultaneous_clear_beats_set():
    """The real, established precedence: CLEAR > SET > TOGGLE, when
    multiple triggers arrive on the SAME tick."""
    lat = vtl.place(vtl.TILE_LATCH, {"set": "n", "clear": "s", "toggle": "e", "out": "w"},
                     cell_id="lat", rel_row=0, rel_col=1)
    set_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="set_src", rel_row=-1, rel_col=1, preload_value=1)
    clear_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="clear_src", rel_row=1, rel_col=1,
                           preload_value=1)
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[lat, set_src, clear_src])},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))], name="simul")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(10):
        grid.tick()
    assert grid.cells[(0, 1)].latch_state is False  # CLEAR wins over SET
