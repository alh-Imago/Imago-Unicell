"""tests/vm/test_nano_gate_convergence_v1.py — points.md #781: real,
direct test of whether `#718`'s own old-frontend corruption hazard
(nano_gate has no `upstream_mask` at all -- accepts unconditionally
from any physically-wired neighbor, confirmed directly against its own
tile registration) is a fundamental property of `nano_gate` itself, or
an artifact specific to the old frontend's rigid, tightly-packed
geometry (where an unrelated, incidentally-adjacent chain wire could
silently win the race against an intended DAG-relayed value).

Confirmed directly: when nano_gate is fed via a real `priority` cell
(sequencing both real operands one at a time onto its single, real
physical face) and NOTHING ELSE is placed adjacent to it -- the exact
discipline the growing-frontier dispatcher (`#780`) enforces by
construction -- nano_gate correctly computes the real, full bitwise
AND/OR of its two real, sequentially-arriving operands. `#718`'s own
corruption required a second, UNRELATED real neighbor to be physically
adjacent at the same time; that situation cannot arise in a design
built by the growing-frontier dispatcher, since nothing incidental is
ever placed next to a target cell.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import vix_tile_library_v1 as vtl  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def _build_gate_test(topology, cell_id_suffix=""):
    a = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id=f"a{cell_id_suffix}", rel_row=-1, rel_col=0,
                  preload_value=0b1100)
    b = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id=f"b{cell_id_suffix}", rel_row=1, rel_col=0,
                  preload_value=0b1010)
    pri = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                     params={"priority_rank_n": 0, "priority_rank_s": 1,
                             "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 0},
                     cell_id=f"pri{cell_id_suffix}", rel_row=0, rel_col=0)
    gate = vtl.place(vtl.TILE_NANO_GATE, {"out": "e"}, params={"topology": topology},
                      cell_id=f"gate{cell_id_suffix}", rel_row=0, rel_col=1)
    sink = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id=f"sink{cell_id_suffix}",
                      rel_row=0, rel_col=2)
    cells = [a, b, pri, gate, sink]
    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name=f"nano_gate_test{cell_id_suffix}")
    return icm


def test_nano_gate_and_via_priority_convergence_no_unrelated_neighbor():
    icm = _build_gate_test(0x007)  # TOPO_AND
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(20):
        grid.tick()
    sink_cell = grid.cells[(0, 2)]
    assert sink_cell.ram_data_reg == (0b1100 & 0b1010)  # 8


def test_nano_gate_or_via_priority_convergence_no_unrelated_neighbor():
    icm = _build_gate_test(0x024)  # TOPO_OR
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(20):
        grid.tick()
    sink_cell = grid.cells[(0, 2)]
    assert sink_cell.ram_data_reg == (0b1100 | 0b1010)  # 14


def test_nano_gate_xor_via_priority_convergence_no_unrelated_neighbor():
    icm = _build_gate_test(0x0BC)  # TOPO_XOR
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(20):
        grid.tick()
    sink_cell = grid.cells[(0, 2)]
    assert sink_cell.ram_data_reg == (0b1100 ^ 0b1010)  # 6


def test_all_twelve_topologies_correct_via_priority_when_rank_matches_arrival():
    """points.md #782: Alan's own direct claim -- nano_gate has 12
    real topology states; all should be covered by the same real
    mechanism. Confirmed directly, comprehensively, against `unicell_
    gate_core.py`'s own `compute_gate()` as ground truth: all 12 real
    topologies compute correctly via the same priority-based
    convergence, when the configured rank order matches which real
    operand actually arrives first."""
    import unicell_gate_core as gc

    a_val, b_val = 0b1100, 0b1010
    topologies = [gc.TOPO_PASS_A, gc.TOPO_NOT_A, gc.TOPO_NOT_B, gc.TOPO_NOR, gc.TOPO_AND,
                  gc.TOPO_ZERO, gc.TOPO_XNOR, gc.TOPO_OR, gc.TOPO_NAND, gc.TOPO_PASS_B,
                  gc.TOPO_ONE, gc.TOPO_XOR]
    assert len(topologies) == 12

    for topo in topologies:
        icm = _build_gate_test(topo, cell_id_suffix=f"_{topo}")
        assert icm.check_connections() == []
        records, _ = icm.flatten()
        grid = SuperGrid(records)
        for _ in range(20):
            grid.tick()
        actual = grid.cells[(0, 2)].ram_data_reg
        expected = gc.compute_gate(topo, a_val, b_val)  # a=first-arrival (rank n=0), b=second (rank s=1)
        assert actual == expected, f"topology 0x{topo:03X}: expected {expected}, got {actual}"


def test_order_sensitive_topology_shares_770_hazard_not_a_new_one():
    """points.md #782: the real, necessary caveat to "same mechanism
    covers all 12" -- PASS_A/PASS_B/NOT_A/NOT_B are genuinely order-
    sensitive (compute_gate()'s own real "a=first-arrival,
    b=second-arrival" contract), exactly like subtract's own operand
    identity. Confirmed directly: PASS_A hits the EXACT SAME #770
    rank-vs-timing hazard subtract did -- when the rank-0 ('a')
    source's own real path is longer than the rank-1 ('b') source's,
    the physically closer one wins regardless of configured rank. Not
    a new, gate-specific hazard -- the same one, requiring the same
    real fix (#777's STAGGER or SEQUENCER, never plain PRIORITY, for
    these 4 topologies specifically)."""
    import unicell_gate_core as gc
    from rats_nest_router_v1 import manhattan_route

    occ = {}
    cells = []
    pri = vtl.place(vtl.TILE_PRIORITY, {"in": ["n", "s"], "out": "e"},
                     params={"priority_rank_n": 0, "priority_rank_s": 1,
                             "priority_rank_e": 0, "priority_rank_w": 0, "scheduling_mode": 0},
                     cell_id="pri", rel_row=0, rel_col=0)
    gate = vtl.place(vtl.TILE_NANO_GATE, {"out": "e"}, params={"topology": gc.TOPO_PASS_A},
                      cell_id="gate", rel_row=0, rel_col=1)
    sink = vtl.place(vtl.TILE_RAM_FLOWING, {"in": "w", "out": "e"}, cell_id="sink", rel_row=0, rel_col=2)
    cells += [pri, gate, sink]
    occ[(0, 0)] = "pri"
    occ[(0, 1)] = "gate"
    occ[(0, 2)] = "sink"

    a_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="a_src", rel_row=-4, rel_col=0, preload_value=0b1100)
    cells.append(a_src)
    occ[(-4, 0)] = "a_src"
    cells += manhattan_route((-4, 0), "s", (-1, 0), "s", "ra", occ)
    b_src = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "n"}, cell_id="b_src", rel_row=1, rel_col=0, preload_value=0b1010)
    cells.append(b_src)
    occ[(1, 0)] = "b_src"

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="pass_a_race")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(20):
        grid.tick()
    # The physically closer source (b, rank 1) wins the "a" slot
    # despite its lower configured rank -- confirming the real hazard
    # is present here too, not just for subtract.
    assert grid.cells[(0, 2)].ram_data_reg == 0b1010
