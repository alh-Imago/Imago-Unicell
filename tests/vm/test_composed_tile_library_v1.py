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


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
