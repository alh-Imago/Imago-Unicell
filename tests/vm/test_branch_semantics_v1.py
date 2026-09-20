"""tests/vm/test_branch_semantics_v1.py — points.md #789: real tests
of `branch`'s own genuinely different real shape (`#742`'s own finding,
confirmed here empirically) -- it emits a real, physical ROUTING
decision (`br_active_route`), not just a data value, and it shares the
same `#770` rank-vs-timing operand-order hazard as `subtract`/`nano_
gate`'s 4 order-sensitive topologies/`nano_hold_trigger`: whichever
real value arrives FIRST on its own single, fixed `upstream_dir`
becomes the held comparison reference, regardless of which physical
source was intended to play that role.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import vix_tile_library_v1 as vtl  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from rats_nest_router_v1 import manhattan_route  # noqa: E402


def _run_branch(compare_value, ref_value=10):
    """A priority cell (rank 0=ref, rank 1=cmp) sequences ref first,
    then compare second, into branch's own single, real upstream_dir --
    the intended, documented "sequenced delivery" pattern."""
    ref_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="ref_src", rel_row=-1, rel_col=0,
                         preload_value=ref_value)
    cmp_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="cmp_src", rel_row=1, rel_col=0,
                         preload_value=compare_value)
    pri = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                     params={"priority_rank_n": 0, "priority_rank_s": 1,
                             "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 0},
                     cell_id="pri", rel_row=0, rel_col=0)
    branch = vtl.place(vtl.TILE_BRANCH, {"in": "w", "route_low": "s", "route_equal": "e", "route_high": "n"},
                        params={"value_source_low": 0, "value_source_equal": 0, "value_source_high": 0,
                                "emit_low": 1, "emit_equal": 1, "emit_high": 1, "rolling_mode": 0},
                        cell_id="branch", rel_row=0, rel_col=1)
    sink_eq = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink_eq", rel_row=0, rel_col=2)
    sink_low = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "n", "out": "e"}, cell_id="sink_low", rel_row=1, rel_col=1)
    sink_high = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "s", "out": "e"}, cell_id="sink_high", rel_row=-1, rel_col=1)
    cells = [ref_src, cmp_src, pri, branch, sink_eq, sink_low, sink_high]
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="branch_test")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(20):
        grid.tick()
    return {"eq": (grid.cells[(0, 2)].ram_data_reg, grid.cells[(0, 2)].ram_data_valid),
            "low": (grid.cells[(1, 1)].ram_data_reg, grid.cells[(1, 1)].ram_data_valid),
            "high": (grid.cells[(-1, 1)].ram_data_reg, grid.cells[(-1, 1)].ram_data_valid)}


def test_low_equal_high_route_correctly_with_sequenced_delivery():
    low = _run_branch(compare_value=5, ref_value=10)
    assert low["low"] == (5, True)
    assert low["eq"] == (0, False)
    assert low["high"] == (0, False)

    equal = _run_branch(compare_value=10, ref_value=10)
    assert equal["eq"] == (10, True)
    assert equal["low"] == (0, False)
    assert equal["high"] == (0, False)

    high = _run_branch(compare_value=20, ref_value=10)
    assert high["high"] == (20, True)
    assert high["eq"] == (0, False)
    assert high["low"] == (0, False)


def test_reference_role_stolen_by_whichever_arrives_first():
    """points.md #789: confirms #742's own documented finding
    empirically -- the intended reference source (rank 0) placed far
    away loses its own role to the intended compare source (rank 1)
    placed adjacent, simply because it arrives first. The exact same
    #770 hazard, not a new one."""
    occ = {}
    cells = []
    pri = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                     params={"priority_rank_n": 0, "priority_rank_s": 1,
                             "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 0},
                     cell_id="pri", rel_row=0, rel_col=0)
    branch = vtl.place(vtl.TILE_BRANCH, {"in": "w", "route_low": "s", "route_equal": "e", "route_high": "n"},
                        params={"value_source_low": 0, "value_source_equal": 0, "value_source_high": 0,
                                "emit_low": 1, "emit_equal": 1, "emit_high": 1, "rolling_mode": 0},
                        cell_id="branch", rel_row=0, rel_col=1)
    cells += [pri, branch]
    occ[(0, 0)] = "pri"
    occ[(0, 1)] = "branch"

    ref_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="ref_src", rel_row=-5, rel_col=0,
                         preload_value=10)
    cells.append(ref_src)
    occ[(-5, 0)] = "ref_src"
    cells += manhattan_route((-5, 0), "s", (-1, 0), "s", "rref", occ)
    cmp_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="cmp_src", rel_row=1, rel_col=0,
                         preload_value=20)
    cells.append(cmp_src)
    occ[(1, 0)] = "cmp_src"

    sink_low = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "n", "out": "e"}, cell_id="sink_low", rel_row=1, rel_col=1)
    cells.append(sink_low)
    occ[(1, 1)] = "sink_low"

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="branch_race")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(20):
        grid.tick()
    # 20 (physically closer, intended as compare) arrives first and
    # becomes the reference; 10 then compares as 10<20 -> LOW, not the
    # intended 20>10 -> HIGH.
    assert grid.cells[(1, 1)].ram_data_reg == 10
    assert grid.cells[(1, 1)].ram_data_valid is True
