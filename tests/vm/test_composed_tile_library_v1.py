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
from unicell_automaton_v1 import N, S, W  # noqa: E402
from vm_introspection_v1 import cell_at  # noqa: E402


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


# ── run_to_quiescence's real bug, found and fixed (points.md #359) ────

def test_run_to_quiescence_catches_the_heartbeat_even_with_zero_prior_stimulus():
    # The real bug this replaced: run_to_quiescence() used to check
    # _pending BEFORE ever calling tick() once, so a grid that had
    # never been injected/delivered to (pending still legitimately
    # empty at construction) silently reported "quiescent, 0 ticks"
    # even for a grid that becomes permanently non-quiescent the moment
    # even one tick runs. Confirmed here with NO inject()/deliver()
    # call at all before run_to_quiescence() -- the exact case that was
    # broken (found via nano/vm_ai_port_v1.py's own end-to-end testing,
    # not a hypothetical edge case invented after the fact).
    tile = composed_tile_library.get("sentinel")
    records = place_composed(tile, 0, 0, {"inc": "n", "dec": "s", "clear": "s", "out": "e"},
                              {"cmp.threshold": 8})
    grid = SuperGrid(records)
    assert grid._pending == {}   # genuinely empty at construction, nothing injected yet
    try:
        grid.run_to_quiescence(max_ticks=10)
    except TimeoutError:
        pass
    else:
        raise AssertionError("expected TimeoutError even with zero prior stimulus")


def test_run_to_quiescence_still_returns_quickly_for_a_genuinely_idle_grid():
    # the other half of the fix: a grid with nothing continuously-live
    # and nothing ever fed to it must still report real quiescence, not
    # spin needlessly or falsely time out.
    from super_tile_library_v1 import super_tile_library, place
    tile = super_tile_library.get("ram_flowing")
    rec = place(tile, 0, 0, {"in": "n", "out": "e"})
    grid = SuperGrid([rec])
    ticks = grid.run_to_quiescence(max_ticks=10)
    assert ticks <= 2   # one real tick to confirm nothing's pending, not an error


# ── select/icmp_eq/icmp_ne (points.md #686) -- the real, promoted
# LLVM-frontend compositions (originally hand-inlined, #668/#674), now
# real, reusable Tier-1 tiles built on #686's own freeze/preload/
# unfreeze mechanism instead of precisely-timed live injection. ──────

def _run_composed_with_preload(tile_name, port_directions, params, deliveries, settle_ticks_before_deliveries, settle_ticks_after):
    """Real, reusable test harness matching the actual required usage
    contract for a composed tile with preload-only sub-cells: freeze
    the whole grid, seed every real preload, unfreeze, let the
    preloaded constants FULLY settle (a real, necessary step found
    empirically while building this -- one tick only OFFERS a
    preloaded value, a second tick is needed for a real neighbor to
    actually CAPTURE it, #686), THEN deliver any live/dynamic ports,
    then tick again to let the result propagate."""
    tile = composed_tile_library.get(tile_name)
    preloads = []
    records = place_composed(tile, 0, 0, port_directions, params, preloads=preloads)
    grid = SuperGrid(records)
    grid.freeze_all()
    for r, c, v in preloads:
        grid.preload_ram_flowing(r, c, v)
    grid.unfreeze_all()
    for _ in range(settle_ticks_before_deliveries):
        grid.tick()
    for (row, col), arrivals in deliveries:
        grid.cells[(row, col)].deliver(arrivals, None)
    for _ in range(settle_ticks_after):
        grid.tick()
    return grid


def test_select_composed_tile_all_four_real_truth_table_cases():
    # Real, necessary ordering, found empirically while building this:
    # the composed tile's own internal "mask = 0 - cond" subtraction
    # needs the preloaded zero constant to be the FIRST real operand
    # captured and cond (the live, dynamic external port) the SECOND --
    # matching #674's own original "north-arrives-first" convention,
    # here achieved by letting the preload settle (2 ticks) BEFORE
    # delivering cond, rather than a hand-tuned relay-based stagger.
    for cond, true_val, false_val in [(0, 42, 7), (0, 0xFFFFFFFF, 5), (1, 42, 7), (1, 0xFFFFFFFF, 5)]:
        grid = _run_composed_with_preload(
            "select", {"cond": "w", "out": "e"}, {"true_val": true_val, "false_val": false_val},
            deliveries=[((1, 0), {W: cond})],
            settle_ticks_before_deliveries=2, settle_ticks_after=10,
        )
        expected = true_val if cond else false_val
        assert cell_at(grid, 1, 2)["nano"]["out_buffer"] == expected


def test_select_rejects_missing_true_val_param():
    tile = composed_tile_library.get("select")
    try:
        place_composed(tile, 0, 0, {"cond": "w", "out": "e"}, {"false_val": 7}, preloads=[])
    except ValueError as e:
        assert "true_val" in str(e)
    else:
        raise AssertionError("expected ValueError for missing true_val")


def test_place_composed_raises_if_preload_subcell_but_no_preloads_list():
    # Real, deliberate safety check (#686): a compile-time constant
    # that never gets seeded is a correctness bug, not a cosmetic gap
    # -- omitting `preloads=` when a preload-only sub-cell exists must
    # fail loudly, never silently drop the constant.
    tile = composed_tile_library.get("select")
    try:
        place_composed(tile, 0, 0, {"cond": "w", "out": "e"}, {"true_val": 1, "false_val": 0})
    except ValueError as e:
        assert "preloads" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_icmp_eq_composed_tile_real_cases():
    for a, b in [(5, 5), (5, 7), (0, 0)]:
        # Real, necessary: TWO separate deliver() calls, not one
        # combined dict -- a single call with both W and N arrivals
        # together gets bitwise-OR'd into ONE value by the adder's own
        # real same-tick-arrival semantics, not captured as separate
        # A/B (confirmed empirically while building this: an earlier
        # version of this test passed both in one call and got None).
        grid = _run_composed_with_preload(
            "icmp_eq", {"in_a": "w", "in_b": "n", "out": "e"}, {},
            deliveries=[((0, 0), {W: a}), ((0, 0), {N: b})],
            settle_ticks_before_deliveries=0, settle_ticks_after=12,
        )
        assert cell_at(grid, 1, 1)["nano"]["out_buffer"] == int(a == b)


def test_icmp_ne_composed_tile_real_cases():
    for a, b in [(5, 5), (5, 7), (0, 0)]:
        grid = _run_composed_with_preload(
            "icmp_ne", {"in_a": "w", "in_b": "n", "out": "e"}, {},
            deliveries=[((0, 0), {W: a}), ((0, 0), {N: b})],
            settle_ticks_before_deliveries=0, settle_ticks_after=12,
        )
        assert cell_at(grid, 1, 2)["nano"]["out_buffer"] == int(a != b)


# ── apply_preloads_to_records / real file-format round trip (#687) ──

def test_apply_preloads_to_records_sets_matching_record_field():
    from composed_tile_library_v1 import apply_preloads_to_records
    tile = composed_tile_library.get("select")
    preloads = []
    records = place_composed(tile, 0, 0, {"cond": "w", "out": "e"},
                              {"true_val": 42, "false_val": 7}, preloads=preloads)
    apply_preloads_to_records(records, preloads)
    by_pos = {(r.row, r.col): r for r in records}
    for row, col, value in preloads:
        assert by_pos[(row, col)].preload_value == value
    # a non-preload subcell (e.g. the mask/subtractor) must be untouched
    assert by_pos[(1, 0)].preload_value is None


def test_apply_preloads_to_records_rejects_mismatched_position():
    from composed_tile_library_v1 import apply_preloads_to_records
    tile = composed_tile_library.get("select")
    preloads = []
    records = place_composed(tile, 0, 0, {"cond": "w", "out": "e"},
                              {"true_val": 1, "false_val": 0}, preloads=preloads)
    try:
        apply_preloads_to_records(records, [(99, 99, 5)])
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "99" in str(e)


def test_select_real_file_format_round_trip_via_icm_save_load():
    # The real, complete pipeline per #687: place -> fold preloads into
    # records -> save to a real .icm file -> load it back -> the
    # STANDARD loader (SuperGrid.from_icm()) applies freeze/preload/
    # unfreeze automatically, with no special-case caller code at all.
    import tempfile
    import os
    from composed_tile_library_v1 import apply_preloads_to_records
    import icm_v3 as v3

    tile = composed_tile_library.get("select")
    preloads = []
    records = place_composed(tile, 0, 0, {"cond": "w", "out": "e"},
                              {"true_val": 42, "false_val": 7}, preloads=preloads)
    apply_preloads_to_records(records, preloads)
    icm = v3.IcmV3File(name="select_roundtrip", records=records)

    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "select.icm")
        icm.save(path)
        loaded = v3.IcmV3File.load(path)

    grid = SuperGrid.from_icm(loaded)
    assert grid.cells[(0, 0)].freeze_in is False   # already released
    grid.tick()
    grid.tick()
    grid.cells[(1, 0)].deliver({W: 1}, None)
    for _ in range(8):
        grid.tick()
    assert cell_at(grid, 1, 2)["nano"]["out_buffer"] == 42


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
