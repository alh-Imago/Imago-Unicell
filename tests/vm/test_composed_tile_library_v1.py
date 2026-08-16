"""
test_composed_tile_library_v1.py — verifies Tier 1's first composed
tile (the sentinel) both structurally and, most importantly, by
replaying the EXACT proven behavior sequence
`top_sentinel_discrete_test_v2.v`'s own self-test FSM already confirmed
on real Quartus-fitted hardware (points.md #291-#298/#306-#308): feed
past threshold (latch sets), collect back below threshold WITHOUT
unfreezing (latch stays sticky-set -- the honest gap #295 found and
#297 closed), then genuine external clear (latch clears). If this
composed tile's real grid-adjacency layout doesn't reproduce that same
sequence correctly, the "same proven topology, just placed for real"
claim in the module's own docstring would be false.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from composed_tile_library_v1 import composed_tile_library, place_composed  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from unicell_automaton_v1 import N, S  # noqa: E402


def test_place_composed_rejects_missing_port():
    tile = composed_tile_library.get("sentinel")
    try:
        place_composed(tile, 0, 0, {"inc": "n"}, {"cmp.threshold": 8})
    except ValueError as e:
        assert "missing" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_place_composed_rejects_unknown_port():
    tile = composed_tile_library.get("sentinel")
    try:
        place_composed(tile, 0, 0,
                        {"inc": "n", "dec": "s", "clear": "s", "out": "e", "bogus": "n"},
                        {"cmp.threshold": 8})
    except ValueError as e:
        assert "unexpected" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_place_composed_rejects_missing_namespaced_param():
    tile = composed_tile_library.get("sentinel")
    try:
        place_composed(tile, 0, 0, {"inc": "n", "dec": "s", "clear": "s", "out": "e"})
    except ValueError as e:
        assert "missing required param" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_place_composed_rejects_unknown_param():
    tile = composed_tile_library.get("sentinel")
    try:
        place_composed(tile, 0, 0, {"inc": "n", "dec": "s", "clear": "s", "out": "e"},
                        {"cmp.threshold": 8, "acc.bogus": 1})
    except ValueError as e:
        assert "unknown param" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_sentinel_produces_three_records_at_correct_relative_positions():
    tile = composed_tile_library.get("sentinel")
    records = place_composed(tile, 5, 10, {"inc": "n", "dec": "s", "clear": "s", "out": "e"},
                              {"cmp.threshold": 8})
    assert len(records) == 3
    positions = {(r.row, r.col): r.core for r in records}
    assert positions == {(5, 10): "accumulator", (5, 11): "comparator", (5, 12): "latch"}


def test_internal_wiring_uses_grid_correct_directions_not_the_original_testbeds():
    # The proven RTL wired CMP's capture to its own "n" port label
    # (an artifact of hand-wiring, not real adjacency). This composed
    # tile MUST use "w" instead, since cmp sits physically east of acc.
    tile = composed_tile_library.get("sentinel")
    records = place_composed(tile, 0, 0, {"inc": "n", "dec": "s", "clear": "s", "out": "e"},
                              {"cmp.threshold": 8})
    by_core = {r.core: r for r in records}
    assert by_core["comparator"].core_config["upstream_mask"] == ["w"]
    assert by_core["accumulator"].core_config["downstream_mask"] == ["e"]
    assert by_core["latch"].core_config["set_dir"] == ["w"]


# ── The real acceptance test: replay the exact proven behavior sequence ──

def test_sentinel_replays_the_proven_feed_collect_unfreeze_sequence():
    tile = composed_tile_library.get("sentinel")
    records = place_composed(tile, 0, 0, {"inc": "n", "dec": "s", "clear": "s", "out": "e"},
                              {"cmp.threshold": 8})
    grid = SuperGrid(records)
    acc = grid.cells[(0, 0)]
    lat = grid.cells[(0, 2)]

    # ── Phase 1: feed past threshold -- confirm the latch sets ──
    for _ in range(9):
        acc.deliver({N: 1}, None)
    assert acc.acc_total == 9
    for _ in range(15):
        grid.tick()
    assert lat.latch_state is True, "latch should be SET once acc (9) crossed threshold (8)"

    # ── Phase 2: collect back below threshold WITHOUT unfreezing --
    # confirm genuinely sticky (the real gap #295 found, #297 closed) ──
    for _ in range(5):
        acc.deliver({S: 1}, None)
    assert acc.acc_total == 4   # comfortably below threshold=8, safe margin
    for _ in range(15):
        grid.tick()
    assert lat.latch_state is True, "latch must STAY set -- sticky, not cleared just by acc dropping"

    # ── Phase 3: genuine external clear -- confirm it actually clears ──
    lat.deliver({S: 1}, None)   # the composed tile's own 'clear' port, direction 's'
    assert lat.latch_state is False, "an explicit clear must actually clear the latch"


def test_sentinel_never_falsely_sets_below_threshold():
    tile = composed_tile_library.get("sentinel")
    records = place_composed(tile, 0, 0, {"inc": "n", "dec": "s", "clear": "s", "out": "e"},
                              {"cmp.threshold": 8})
    grid = SuperGrid(records)
    acc = grid.cells[(0, 0)]
    lat = grid.cells[(0, 2)]
    for _ in range(3):   # well below threshold=8
        acc.deliver({N: 1}, None)
    for _ in range(15):
        grid.tick()
    assert lat.latch_state is False


# ── Second Tier-1 tile: dual_threshold_monitor -- tests FAN-OUT and
# non-linear (L-shaped) placement, neither exercised by the sentinel. ──

def test_dual_threshold_monitor_produces_five_records_no_collisions():
    tile = composed_tile_library.get("dual_threshold_monitor")
    records = place_composed(tile, 0, 0, {"inc": "n", "dec": "s",
                                           "clear_low": "s", "out_low": "w",
                                           "clear_high": "n", "out_high": "e"},
                              {"cmp_low.threshold": 3, "cmp_high.threshold": 10})
    assert len(records) == 5
    positions = [(r.row, r.col) for r in records]
    assert len(set(positions)) == 5   # no two sub-cells collide
    assert set(positions) == {(0, 0), (1, 0), (1, 1), (0, 1), (0, 2)}


def test_dual_threshold_monitor_accumulator_fans_out_both_directions():
    tile = composed_tile_library.get("dual_threshold_monitor")
    records = place_composed(tile, 0, 0, {"inc": "n", "dec": "s",
                                           "clear_low": "s", "out_low": "w",
                                           "clear_high": "n", "out_high": "e"},
                              {"cmp_low.threshold": 3, "cmp_high.threshold": 10})
    acc_rec = next(r for r in records if r.core == "accumulator")
    assert acc_rec.core_config["downstream_mask"] == ["e", "s"]   # real fan-out, both bits set


def test_dual_threshold_monitor_independent_alarms_from_one_shared_source():
    # The real generality test: ONE accumulator feeds TWO wholly
    # independent comparator->latch chains with DIFFERENT thresholds.
    # Crossing only the low threshold must set lat_low but NOT lat_high;
    # crossing both must set both, independently.
    tile = composed_tile_library.get("dual_threshold_monitor")
    records = place_composed(tile, 0, 0, {"inc": "n", "dec": "s",
                                           "clear_low": "s", "out_low": "w",
                                           "clear_high": "n", "out_high": "e"},
                              {"cmp_low.threshold": 3, "cmp_high.threshold": 10})
    grid = SuperGrid(records)
    acc = grid.cells[(0, 0)]
    lat_low = grid.cells[(1, 1)]
    lat_high = grid.cells[(0, 2)]

    # Cross the LOW threshold only (5 >= 3, 5 < 10)
    for _ in range(5):
        acc.deliver({N: 1}, None)
    for _ in range(15):
        grid.tick()
    assert lat_low.latch_state is True
    assert lat_high.latch_state is False

    # Now also cross the HIGH threshold (12 >= 10)
    for _ in range(7):
        acc.deliver({N: 1}, None)
    for _ in range(15):
        grid.tick()
    assert acc.acc_total == 12
    assert lat_low.latch_state is True
    assert lat_high.latch_state is True

    # Each latch clears independently -- clearing low must not touch high
    lat_low.deliver({S: 1}, None)
    assert lat_low.latch_state is False
    assert lat_high.latch_state is True   # untouched by the other latch's clear


# ── Nested composition (points.md #342): a composed tile built from
# OTHER composed tiles, not just Tier-0 primitives. ──────────────────

def test_twin_sentinel_produces_six_records_no_collisions():
    tile = composed_tile_library.get("twin_sentinel")
    records = place_composed(tile, 0, 0, {
        "s1_inc": "n", "s1_dec": "s", "s1_clear": "s", "s1_out": "e",
        "s2_inc": "n", "s2_dec": "s", "s2_clear": "s", "s2_out": "e",
    }, {"s1.cmp.threshold": 8, "s2.cmp.threshold": 4})
    assert len(records) == 6   # two full sentinels, 3 cells each
    positions = [(r.row, r.col) for r in records]
    assert len(set(positions)) == 6
    assert set(positions) == {(0, 0), (0, 1), (0, 2), (2, 0), (2, 1), (2, 2)}


def test_twin_sentinel_double_namespaced_params_reach_the_right_comparator():
    tile = composed_tile_library.get("twin_sentinel")
    records = place_composed(tile, 0, 0, {
        "s1_inc": "n", "s1_dec": "s", "s1_clear": "s", "s1_out": "e",
        "s2_inc": "n", "s2_dec": "s", "s2_clear": "s", "s2_out": "e",
    }, {"s1.cmp.threshold": 8, "s2.cmp.threshold": 4})
    by_pos = {(r.row, r.col): r for r in records}
    assert by_pos[(0, 1)].core == "comparator"
    assert by_pos[(0, 1)].core_config["threshold"] == 8   # s1's own comparator
    assert by_pos[(2, 1)].core == "comparator"
    assert by_pos[(2, 1)].core_config["threshold"] == 4   # s2's own comparator, independently


def test_twin_sentinel_instances_behave_independently_in_a_real_grid():
    # The real acceptance test for nesting: two nested sentinels, each
    # replaying (a shortened version of) the same proven behavior
    # sequence independently, confirming s1's own state never leaks
    # into s2's, and vice versa.
    tile = composed_tile_library.get("twin_sentinel")
    records = place_composed(tile, 0, 0, {
        "s1_inc": "n", "s1_dec": "s", "s1_clear": "s", "s1_out": "e",
        "s2_inc": "n", "s2_dec": "s", "s2_clear": "s", "s2_out": "e",
    }, {"s1.cmp.threshold": 8, "s2.cmp.threshold": 4})
    grid = SuperGrid(records)
    s1_acc, s1_lat = grid.cells[(0, 0)], grid.cells[(0, 2)]
    s2_acc, s2_lat = grid.cells[(2, 0)], grid.cells[(2, 2)]

    # Cross s2's LOWER threshold (4) but stay under s1's (8) -- only s2 should set
    for _ in range(5):
        s2_acc.deliver({N: 1}, None)
    for _ in range(15):
        grid.tick()
    assert s2_lat.latch_state is True
    assert s1_lat.latch_state is False   # s1 completely untouched by s2's activity

    # Now cross s1's own threshold too
    for _ in range(9):
        s1_acc.deliver({N: 1}, None)
    for _ in range(15):
        grid.tick()
    assert s1_lat.latch_state is True
    assert s2_lat.latch_state is True   # s2 still set, unaffected by s1's own activity

    # Clearing s1 must not affect s2
    s1_lat.deliver({S: 1}, None)
    assert s1_lat.latch_state is False
    assert s2_lat.latch_state is True


# ── Circular reference guard (points.md #350): a hand-crafted tile
# (bypassing define's own construction-time protection) can create a
# real cycle -- confirmed as a genuine RecursionError before the fix,
# not assumed. ──────────────────────────────────────────────────────

def test_self_referencing_tile_raises_clear_error_not_recursion_error():
    from composed_tile_library_v1 import ComposedTileSpec, SubCellPlacement, ComposedTileLibrary
    lib = ComposedTileLibrary(parent=composed_tile_library)
    cyclic = ComposedTileSpec(
        name="cyclic", description="",
        subcells=[SubCellPlacement(name="self_ref", offset=(0, 0), tile_name="cyclic",
                                    internal_directions={})],
        external_ports={"out": ("self_ref", "out")},
    )
    lib.register(cyclic)
    try:
        place_composed(cyclic, 0, 0, {"out": "e"}, composed_library=lib)
    except ValueError as e:
        assert "circular" in str(e)
        assert "cyclic -> cyclic" in str(e)
    else:
        raise AssertionError("expected ValueError, tile was self-referencing")


def test_indirect_two_tile_cycle_raises_clear_error():
    from composed_tile_library_v1 import ComposedTileSpec, SubCellPlacement, ComposedTileLibrary
    lib = ComposedTileLibrary(parent=composed_tile_library)
    tile_a = ComposedTileSpec(
        name="cycle_a", description="",
        subcells=[SubCellPlacement(name="b_ref", offset=(0, 0), tile_name="cycle_b",
                                    internal_directions={})],
        external_ports={"out": ("b_ref", "out")},
    )
    tile_b = ComposedTileSpec(
        name="cycle_b", description="",
        subcells=[SubCellPlacement(name="a_ref", offset=(0, 0), tile_name="cycle_a",
                                    internal_directions={})],
        external_ports={"out": ("a_ref", "out")},
    )
    lib.register(tile_a)
    lib.register(tile_b)
    try:
        place_composed(tile_a, 0, 0, {"out": "e"}, composed_library=lib)
    except ValueError as e:
        assert "circular" in str(e)
        assert "cycle_a -> cycle_b -> cycle_a" in str(e)
    else:
        raise AssertionError("expected ValueError, tiles cycle A -> B -> A")


def test_non_cyclic_repeated_use_of_the_same_tile_still_works():
    # a real, important non-regression: using the SAME tile twice at
    # DIFFERENT positions (not nested inside itself) must still work --
    # the cycle guard tracks the CURRENT recursion chain, not "has this
    # tile name ever been used anywhere in this whole compile."
    from composed_tile_library_v1 import ComposedTileSpec, SubCellPlacement, ComposedTileLibrary
    lib = ComposedTileLibrary(parent=composed_tile_library)
    wrapper = ComposedTileSpec(
        name="uses_sentinel_twice", description="",
        subcells=[
            SubCellPlacement(name="s1", offset=(0, 0), tile_name="sentinel"),
            SubCellPlacement(name="s2", offset=(3, 0), tile_name="sentinel"),
        ],
        external_ports={
            "s1_inc": ("s1", "inc"), "s1_dec": ("s1", "dec"),
            "s1_clear": ("s1", "clear"), "s1_out": ("s1", "out"),
            "s2_inc": ("s2", "inc"), "s2_dec": ("s2", "dec"),
            "s2_clear": ("s2", "clear"), "s2_out": ("s2", "out"),
        },
    )
    lib.register(wrapper)
    records = place_composed(wrapper, 0, 0, {
        "s1_inc": "n", "s1_dec": "s", "s1_clear": "s", "s1_out": "e",
        "s2_inc": "n", "s2_dec": "s", "s2_clear": "s", "s2_out": "e",
    }, {"s1.cmp.threshold": 8, "s2.cmp.threshold": 4}, composed_library=lib)
    assert len(records) == 6   # two full, independent sentinels -- no false-positive cycle


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
