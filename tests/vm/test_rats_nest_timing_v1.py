"""tests/vm/test_rats_nest_timing_v1.py — points.md #764: real tests
for the symbolic timing model, each one confirmed directly against an
actual VM run, not just internal self-consistency.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import vix_tile_library_v1 as vtl  # noqa: E402
import icm_vix_v1 as vix  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from rats_nest_router_v1 import manhattan_route  # noqa: E402
from rats_nest_timing_v1 import symbolic_arrival_tick, would_collide, min_safe_hop_count  # noqa: E402


def _build_and_run(hop_a, hop_b, val_a=5, val_b=10, ticks=15):
    """Real, direct construction: two preloaded sources, real relay
    chains of the given hop counts, converging on one plain adder (no
    priority) -- the exact shape the timing model covers."""
    occ = {}
    cells = []
    target_a, target_b = (0, -1), (-1, 0)
    src_a_pos = (0, -1 - hop_a)
    src_b_pos = (-1 - hop_b, 0)

    src_a = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "e"}, cell_id="src_a",
                       rel_row=src_a_pos[0], rel_col=src_a_pos[1], preload_value=val_a)
    cells.append(src_a)
    if src_a_pos != target_a:
        occ[src_a_pos] = "src_a"
        cells += manhattan_route(src_a_pos, "e", target_a, "e", "ra", occ)

    src_b = vtl.place(vtl.TILE_RAM_PRELOAD, {"out": "s"}, cell_id="src_b",
                       rel_row=src_b_pos[0], rel_col=src_b_pos[1], preload_value=val_b)
    cells.append(src_b)
    if src_b_pos != target_b:
        occ[src_b_pos] = "src_b"
        cells += manhattan_route(src_b_pos, "s", target_b, "s", "rb", occ)

    add = vtl.place(vtl.TILE_ADDER, {"in_a": "w", "in_b": "n", "out": "e"}, cell_id="add", rel_row=0, rel_col=0)
    cells.append(add)

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=cells)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="timing_test")
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    a_tick = None
    b_tick = None
    for t in range(1, ticks + 1):
        grid.tick()
        add_cell = grid.cells[(0, 0)]
        if add_cell.adder_a_arrived and a_tick is None:
            a_tick = t
        if add_cell.adder_data_valid and b_tick is None:
            b_tick = t
    return a_tick, b_tick, grid.cells[(0, 0)].adder_out_buffer


def test_symbolic_model_matches_real_vm_for_zero_and_one_hop():
    a_tick, b_tick, result = _build_and_run(hop_a=0, hop_b=1)
    assert a_tick == symbolic_arrival_tick(0)
    assert b_tick == symbolic_arrival_tick(1)
    assert result == 15
    assert not would_collide(0, 1)


def test_symbolic_model_matches_real_vm_for_larger_gap():
    a_tick, b_tick, result = _build_and_run(hop_a=0, hop_b=3)
    assert a_tick == symbolic_arrival_tick(0)
    assert b_tick == symbolic_arrival_tick(3)
    assert result == 15
    assert not would_collide(0, 3)


def test_symbolic_model_correctly_predicts_a_real_collision():
    """The real, central claim: would_collide() correctly predicts the
    real #750-style hazard BEFORE running the VM -- confirmed here by
    running the VM anyway and showing it really does fail exactly as
    predicted."""
    assert would_collide(0, 0)
    a_tick, b_tick, result = _build_and_run(hop_a=0, hop_b=0)
    assert result != 15  # the real, wrong, collided result
    assert b_tick is None  # adder never becomes valid at all


def test_min_safe_hop_count_never_recommends_a_colliding_value():
    for fixed in range(5):
        for other in range(5):
            safe = min_safe_hop_count(fixed, other)
            if safe is not None:
                assert not would_collide(fixed, safe)
                assert safe >= 0


def test_tighten_pair_with_timing_avoids_the_real_collision():
    """points.md #764: the real, central proof -- tightening BOTH
    connections into a plain, two-arrival consumer (no priority), with
    the timing check applied after the structural check, produces a
    real, correct result -- confirmed with genuinely different hop
    counts."""
    import vix_tile_library_v1 as vtl
    import icm_vix_v1 as vix
    from unicell_super_automaton_v1 import SuperGrid
    from rats_nest_tighten_v1 import tighten_pair_with_timing

    occ = {}
    add = vtl.place(vtl.TILE_ADDER, {"in_a": "w", "in_b": "n", "out": "e"}, cell_id="add", rel_row=15, rel_col=15)
    occ[(15, 15)] = "add"

    final_a, final_b, chain = tighten_pair_with_timing(
        leaf_value_a=5, start_a=(15, 0), leaf_value_b=10, start_b=(0, 15),
        consumer_pos=(15, 15), occupied=occ, uid_prefix="p")

    hops_a = len([c for c in chain if "p_a_r" in c.cell_id])
    hops_b = len([c for c in chain if "p_b_r" in c.cell_id])
    assert hops_a != hops_b  # the real, central requirement -- timing forced them apart

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[add] + chain)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="pair_test")
    assert icm.check_connections() == []
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(30):
        grid.tick()
    result = grid.cells[(15, 15)]
    assert result.adder_data_valid is True
    assert result.adder_out_buffer == 15


def test_naive_uncoordinated_tightening_really_does_collide():
    """The real, necessary NEGATIVE proof: independently tightening
    both connections with NO timing awareness (using the already-
    proven, structural-only tighten_leaf_connection_fast() for each,
    with no coordination between them) really does produce the exact
    real #750-style collision -- confirming the timing check in
    tighten_pair_with_timing() is genuinely necessary, not a
    precaution against a hypothetical."""
    import vix_tile_library_v1 as vtl
    import icm_vix_v1 as vix
    from unicell_super_automaton_v1 import SuperGrid
    from rats_nest_tighten_v1 import tighten_leaf_connection_fast

    occ = {}
    add = vtl.place(vtl.TILE_ADDER, {"in_a": "w", "in_b": "n", "out": "e"}, cell_id="add", rel_row=15, rel_col=15)
    occ[(15, 15)] = "add"

    _, chain_a = tighten_leaf_connection_fast(5, (15, 0), (15, 14), "e", occ, "na")
    _, chain_b = tighten_leaf_connection_fast(10, (0, 15), (14, 15), "s", occ, "nb")

    icm = vix.IcmVixFile(patterns={"main": vix.HierPattern(cells=[add] + chain_a + chain_b)},
                          placements=[vix.HierPlacement(instance="main", pattern="main", at=(0, 0))],
                          name="naive_test")
    assert icm.check_connections() == []  # structurally perfect -- and still wrong
    records, _ = icm.flatten()
    grid = SuperGrid(records)
    for _ in range(30):
        grid.tick()
    result = grid.cells[(15, 15)]
    assert result.adder_out_buffer != 15  # the real, silent, wrong collision
