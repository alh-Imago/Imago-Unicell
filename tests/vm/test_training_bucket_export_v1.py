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
