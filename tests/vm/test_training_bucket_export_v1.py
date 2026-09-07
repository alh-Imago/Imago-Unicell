"""tests/vm/test_training_bucket_export_v1.py -- points.md #681: real
tests for the AI training bucket exporter, the minimal first slice
scoped in `docs/stripped-cell/design-notes/ai_training_buckets_scope.
md` (`#676`-`#680`). Confirms real, actually-executed VM traces (not
fabricated), the honest metadata-only path for non-runnable bucket
kinds, and the one-file-per-bucket manifest structure `#680` decided.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import workbench_v1  # noqa: E402
from tile_source_registry_v1 import all_sources  # noqa: E402
import training_bucket_export_v1 as tbe  # noqa: E402


# ── _assign_directions ──────────────────────────────────────────────

def test_assign_directions_cycles_n_s_e_w_in_port_order():
    result = tbe._assign_directions(["in_a", "in_b", "out"])
    assert result == {"in_a": "n", "in_b": "s", "out": "e"}


def test_assign_directions_handles_exactly_four_ports():
    result = tbe._assign_directions(["a", "b", "c", "d"])
    assert result == {"a": "n", "b": "s", "c": "e", "d": "w"}


def test_assign_directions_rejects_more_than_four_ports():
    try:
        tbe._assign_directions(["a", "b", "c", "d", "e"])
        assert False, "expected ValueError"
    except ValueError as e:
        assert "4" in str(e)


# ── export_tier0_tile: real, actually-executed traces ───────────────

def test_export_adder_produces_a_real_correct_trace():
    workbench_v1  # ensure registration side-effects have run
    source = next(s for s in all_sources() if "adder" in s.library.names())
    record = tbe.export_tier0_tile(source, "adder")
    assert record["bucket"] == "tiles"
    assert record["name"] == "adder"
    assert record["trace"] is not None
    final_state = record["trace"][-1]["state"]
    # Real, correct arithmetic: the two real test values assigned to
    # in_a/in_b (5 and 3) must genuinely sum to 8 in the actual VM,
    # not just be recorded as if they did.
    assert final_state["adder"]["out_buffer"] == 8
    assert final_state["adder"]["data_valid"] is True


def test_export_accumulator_shows_a_real_stuck_at_zero_total_with_no_step_amount_param():
    # Real, honest finding: the registered accumulator TILE (super_
    # tile_library_v1.py) declares no `step_amount` param, so its real
    # default (0) means every inc/dec genuinely moves the total by
    # zero -- confirmed as a real, correct property of the CURRENT
    # tile registration, not a bug in this exporter. A future tile
    # update exposing step_amount would change this bucket's own
    # trace the next time it's regenerated, exactly the point of
    # #680's per-bucket regeneration.
    source = next(s for s in all_sources() if "accumulator" in s.library.names())
    record = tbe.export_tier0_tile(source, "accumulator")
    final_state = record["trace"][-1]["state"]
    assert final_state["accumulator"]["step_amount"] == 0
    assert final_state["accumulator"]["total"] == 0


def test_export_nano_gate_does_not_crash_and_records_topology():
    # Real regression test: nano_gate's own routing_mask/cardinal_edge
    # fields are NOT in icm_v3._DIR_FIELDS (6-bit, 3D-ready, not a
    # plain 4-bit one-hot) -- calling icm_record.to_dict() directly on
    # the raw place() result used to crash with a real TypeError before
    # this was found and fixed.
    source = next(s for s in all_sources() if "nano_gate" in s.library.names())
    record = tbe.export_tier0_tile(source, "nano_gate")
    assert record["name"] == "nano_gate"
    assert record["trace"] is not None
    assert record["icm_record"]["core"] == "nano"


def test_export_branch_does_not_crash():
    # Same real bug class as nano_gate -- branch's route_low/equal/high
    # fields are also outside _DIR_FIELDS.
    source = next(s for s in all_sources() if "branch" in s.library.names())
    record = tbe.export_tier0_tile(source, "branch")
    assert record["name"] == "branch"
    assert record["trace"] is not None


def test_export_tile_with_a_required_param_uses_a_real_valid_default():
    source = next(s for s in all_sources() if "comparator" in s.library.names())
    record = tbe.export_tier0_tile(source, "comparator")
    assert record["params"] == {"threshold": 0}
    assert record["trace"] is not None


# ── export_tier0_tile: honest metadata-only scope for other buckets ─

def test_export_dsp_wrapper_tile_is_metadata_only_not_faked():
    source = next(s for s in all_sources() if s.bucket == "dsp_wrapper_records")
    name = sorted(source.library.names())[0]
    record = tbe.export_tier0_tile(source, name)
    assert record["trace"] is None
    assert "real, honest scope" in record["trace_note"]
    # Real, static metadata still present even without a trace.
    assert record["ports"]
    assert record["source_kind"] == "dsp-wrapper"


# ── export_demo ──────────────────────────────────────────────────────

def test_export_demo_sentinel_compiles_and_reports_real_cell_count():
    record = tbe.export_demo("sentinel")
    assert record["bucket"] == "demos"
    assert record["compiles"] is True
    assert record["cell_count"] == 3


def test_export_demo_python_ast_example_compiles():
    record = tbe.export_demo("python_ast_example")
    assert record["compiles"] is True
    assert record["language"] == "python"


def test_export_demo_reports_a_real_compile_failure_honestly(monkeypatch):
    broken = {
        "description": "deliberately broken for this test",
        "language": "dsl",
        "source": "program broken { place r1 as ram_constant at (0,0) { } }",
    }
    monkeypatch.setitem(workbench_v1.DEMOS, "_test_broken_demo", broken)
    record = tbe.export_demo("_test_broken_demo")
    assert record["compiles"] is False
    assert record["compile_error"]


# ── export_all: the real, one-file-per-bucket manifest structure ───

def test_export_all_writes_one_file_per_tile_and_demo(tmp_path):
    manifest = tbe.export_all(str(tmp_path))

    real_tile_count = sum(len(s.library.names()) for s in all_sources())
    real_demo_count = len(workbench_v1.DEMOS)
    assert len(manifest["tiles"]) == real_tile_count
    assert len(manifest["demos"]) == real_demo_count

    for entry in manifest["tiles"]:
        assert os.path.exists(os.path.join(str(tmp_path), entry["file"]))
    for entry in manifest["demos"]:
        assert os.path.exists(os.path.join(str(tmp_path), entry["file"]))

    manifest_on_disk = json.load(open(os.path.join(str(tmp_path), "manifest.json")))
    assert manifest_on_disk == manifest


def test_export_all_is_safe_to_run_twice(tmp_path):
    # Real, honest requirement: regenerating a bucket must not require
    # deleting the directory first (matches the project's own real
    # "regenerated fresh every run" discipline, #558).
    tbe.export_all(str(tmp_path))
    manifest2 = tbe.export_all(str(tmp_path))
    assert len(manifest2["tiles"]) > 0


# ── Tier-1 composed tiles (#682) ─────────────────────────────────────

def test_composed_tile_buckets_pure_super_records_for_sentinel():
    tile = tbe.composed_tile_library.get("sentinel")
    assert tbe._composed_tile_buckets(tile) == {"super_records"}


def test_composed_tile_buckets_detects_mixed_bucket_kinds():
    tile = tbe.composed_tile_library.get("dsp_add_and_hold")
    buckets = tbe._composed_tile_buckets(tile)
    assert buckets == {"super_records", "dsp_wrapper_records"}


def test_required_composed_params_sentinel_only_needs_threshold():
    # step_amount is fixed via fixed_params on the acc subcell, so it
    # must NOT appear as a required top-level param -- only
    # cmp.threshold, matching sentinel's own real registered spec.
    tile = tbe.composed_tile_library.get("sentinel")
    assert tbe._required_composed_params(tile) == ["cmp.threshold"]


def test_required_composed_params_dual_threshold_monitor():
    tile = tbe.composed_tile_library.get("dual_threshold_monitor")
    assert set(tbe._required_composed_params(tile)) == {
        "cmp_low.threshold", "cmp_high.threshold",
    }


def test_required_composed_params_twin_sentinel_double_namespaced():
    # Real, nested double-namespacing: s1/s2 are each a full sentinel,
    # so each one's own inner "cmp.threshold" need surfaces prefixed
    # with its own subcell name at this outer level.
    tile = tbe.composed_tile_library.get("twin_sentinel")
    assert set(tbe._required_composed_params(tile)) == {
        "s1.cmp.threshold", "s2.cmp.threshold",
    }


def test_assign_composed_directions_groups_by_subcell_not_globally():
    # sentinel has 4 external ports total, but they belong to only 2
    # real subcells (acc: inc/dec: 2 ports; lat: clear/out: 2 ports) --
    # each group must get its own real, distinct directions.
    tile = tbe.composed_tile_library.get("sentinel")
    directions = tbe._assign_composed_directions(tile)
    assert directions["inc"] != directions["dec"]
    assert directions["clear"] != directions["out"]


def test_resolve_port_absolute_leaf_subcell():
    tile = tbe.composed_tile_library.get("sentinel")
    row, col, direction, kind = tbe._resolve_port_absolute(tile, "inc", 0, 0, "n")
    assert (row, col, kind) == (0, 0, "in")
    row, col, direction, kind = tbe._resolve_port_absolute(tile, "out", 0, 0, "e")
    assert (row, col, kind) == (0, 2, "out")


def test_resolve_port_absolute_recurses_through_nested_composed_subcell():
    # twin_sentinel's "s2_inc" maps into the NESTED "s2" sentinel, at
    # real offset (2, 0) -- must resolve all the way down to s2's own
    # leaf accumulator cell, not stop at the intermediate composed
    # sub-cell.
    tile = tbe.composed_tile_library.get("twin_sentinel")
    row, col, direction, kind = tbe._resolve_port_absolute(tile, "s2_inc", 0, 0, "e")
    assert (row, col, kind) == (2, 0, "in")


def test_export_tier1_sentinel_real_multicell_trace():
    record = tbe.export_tier1_tile("sentinel")
    assert record["bucket"] == "tiles_composed"
    assert record["trace"] is not None
    final = record["trace"][-1]["state"]["cells"]
    # Real, verified outcome (fixed step_amount=1, default threshold=0):
    # one real inc and one real dec net the accumulator back to zero,
    # and since 0 >= a threshold of 0 is always true, the comparator
    # keeps re-asserting SET -- a real, correct property of THIS
    # specific default parameter choice, confirmed by actually running
    # it, not assumed.
    assert final["0,0"]["accumulator"]["total"] == 0
    assert final["0,1"]["comparator"]["out_buffer"] == 1
    assert final["0,2"]["latch"]["state"] is True


def test_export_tier1_twin_sentinel_both_branches_reach_the_same_real_state():
    record = tbe.export_tier1_tile("twin_sentinel")
    final = record["trace"][-1]["state"]["cells"]
    # s1 occupies rows 0-0..2, s2 occupies rows 2-2..2 (offset by 2,
    # per the tile's own real registration) -- both must independently
    # reach the same real outcome sentinel does alone.
    assert final["0,0"]["accumulator"]["total"] == 0
    assert final["0,2"]["latch"]["state"] is True
    assert final["2,0"]["accumulator"]["total"] == 0
    assert final["2,2"]["latch"]["state"] is True


def test_export_tier1_dual_threshold_monitor_both_alarms_fire():
    record = tbe.export_tier1_tile("dual_threshold_monitor")
    final = record["trace"][-1]["state"]["cells"]
    # Real fan-out: one shared accumulator feeds two independent
    # comparator->latch chains (south and east) -- both must reach a
    # real, correct set state.
    assert final["0,0"]["accumulator"]["total"] == 0
    assert final["0,1"]["comparator"]["out_buffer"] == 1  # cmp_high
    assert final["1,0"]["comparator"]["out_buffer"] == 1  # cmp_low
    assert final["0,2"]["latch"]["state"] is True
    assert final["1,1"]["latch"]["state"] is True


def test_export_tier1_dsp_add_and_hold_is_metadata_only_not_faked():
    record = tbe.export_tier1_tile("dsp_add_and_hold")
    assert record["trace"] is None
    assert "real, honest scope" in record["trace_note"]
    assert "dsp_wrapper_records" in record["trace_note"]
    # Real, static metadata still present even without a trace.
    assert record["external_ports"]
    assert set(record["subcell_tile_names"]) == {"dsp_add", "ram_flowing"}


def test_export_all_includes_a_tiles_composed_bucket_per_registered_tile(tmp_path):
    manifest = tbe.export_all(str(tmp_path))
    real_composed_count = len(tbe.composed_tile_library.names())
    assert len(manifest["tiles_composed"]) == real_composed_count
    names = {entry["name"] for entry in manifest["tiles_composed"]}
    assert names == {"sentinel", "dual_threshold_monitor", "twin_sentinel", "dsp_add_and_hold"}
    for entry in manifest["tiles_composed"]:
        assert os.path.exists(os.path.join(str(tmp_path), entry["file"]))
