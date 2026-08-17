"""
tests/vm/test_pipeline_compile.py

Tests for FormatRegistry.compile_pipeline_icm() — auto-placement of bridge
tiles in pipeline .icm files exported by the Region Connector.

Coverage:
  - Empty pipeline: returns empty records, no bridges
  - Direct connection (no bridge placeholder): region records passed through
  - Bridge placeholder with auto_place bridge: expanded to GS_PASS cell
  - Bridge placeholder with warn_and_place bridge: expanded with warning
  - Bridge placeholder with require_verification: CompilePipelineError raised
  - Bridge placeholder with reject policy: CompilePipelineError raised
  - Strict mode: warn_and_place also raises CompilePipelineError
  - Record structure: gs=0, in/out correct, meta carries provenance
  - Mixed: some direct + some bridged records
  - CompilePipelineError message contains bridge name and error text
  - bridge_count in result matches number of bridge tiles placed
  - Non-placeholder records are passed through unchanged (gs preserved)
"""

import pytest
from cell_format import FormatRegistry, CompilePipelineError

GS_PASS            = 0x00000000
BRIDGE_PLACEHOLDER = 0x00000001


# ── Helpers ────────────────────────────────────────────────────────────────

def _region(rid, fmt, ctx=""):
    return {"id": rid, "format": fmt, "model": rid, "context": ctx, "domain": "T"}

def _pipeline(records, connections=None, regions=None):
    return {
        "regions":     regions or [],
        "connections": connections or [],
        "records":     records,
    }

def _bridge_record(from_addr, to_addr, bridge_name, confidence, formula=""):
    return {
        "gs":         BRIDGE_PLACEHOLDER,
        "in":         from_addr,
        "out":        to_addr,
        "init":       None,
        "bridge":     bridge_name,
        "confidence": confidence,
        "formula":    formula,
        "verified":   "2026-06-15",
    }

def _region_record(gs, in_addr, out_addr):
    return {"gs": gs, "in": in_addr, "out": out_addr, "init": None}


@pytest.fixture
def reg():
    return FormatRegistry.get_default()


# ── Empty / trivial cases ──────────────────────────────────────────────────

def test_empty_pipeline(reg):
    result = reg.compile_pipeline_icm(_pipeline([]))
    assert result["records"]      == []
    assert result["bridge_count"] == 0
    assert result["warnings"]     == []


def test_no_bridge_placeholders_passed_through(reg):
    """Region placeholder records (gs != 0x1) are passed through unchanged."""
    records = [
        _region_record(0x00000000, 0x10000, 0x10001),
        _region_record(0x12345678, 0x11000, 0x11001),
    ]
    result = reg.compile_pipeline_icm(_pipeline(records))
    assert result["bridge_count"] == 0
    assert len(result["records"]) == 2
    assert result["records"][0]["gs"] == 0x00000000
    assert result["records"][1]["gs"] == 0x12345678


# ── Auto-place (conf >= 0.95) ──────────────────────────────────────────────

def test_auto_place_bridge_expands_to_pass_cell(reg):
    """
    A bridge with confidence=1.0 (auto_place) should be expanded to GS_PASS.
    """
    regions = [
        _region("A", "SI_Physics", "gravitational"),
        _region("B", "SI_Physics", "thermal_quantum"),
    ]
    connections = [{
        "from": "A", "to": "B",
        "bridge": "Bridge_Hawking", "confidence": 1.0,
        "formula": "T = hbar*c**3 / (8*pi*G*M*kB)",
    }]
    records = [
        _region_record(0x10, 0x10000, 0x10001),
        _bridge_record(0x10001, 0x11000, "Bridge_Hawking", 1.0,
                       "T = hbar*c**3 / (8*pi*G*M*kB)"),
        _region_record(0x20, 0x11000, 0x11001),
    ]
    result = reg.compile_pipeline_icm(_pipeline(records, connections, regions))

    assert result["bridge_count"] == 1
    assert result["warnings"]     == []

    bridge_record = result["records"][1]
    assert bridge_record["gs"]  == GS_PASS
    assert bridge_record["in"]  == 0x10001
    assert bridge_record["out"] == 0x11000
    assert bridge_record["meta"]["bridge"]     == "Bridge_Hawking"
    assert bridge_record["meta"]["confidence"] == 1.0
    assert bridge_record["meta"]["auto_placed"] is True
    assert bridge_record["meta"]["type"]       == "bridge_tile"


def test_auto_place_preserves_surrounding_records(reg):
    """Region records before and after the bridge are passed through correctly."""
    records = [
        _region_record(0xAA, 0x10000, 0x10001),
        _bridge_record(0x10001, 0x11000, "Bridge_Hawking", 1.0),
        _region_record(0xBB, 0x11000, 0x11001),
    ]
    result = reg.compile_pipeline_icm(_pipeline(records))
    assert result["records"][0]["gs"] == 0xAA
    assert result["records"][2]["gs"] == 0xBB


# ── Warn-and-place (conf >= 0.80) ─────────────────────────────────────────

def test_warn_and_place_succeeds_with_warning(reg):
    """A custom bridge at 0.85 should be placed and generate a warning."""
    records = [_bridge_record(0x10001, 0x11000, "CustomBridge_0_85", 0.85)]
    result = reg.compile_pipeline_icm(_pipeline(records))
    assert result["bridge_count"] == 1
    assert len(result["warnings"]) == 1
    assert "CustomBridge_0_85" in result["warnings"][0]
    assert result["records"][0]["gs"] == GS_PASS


def test_warn_and_place_meta_auto_placed_false(reg):
    """Warn-and-place bridge should have auto_placed=False in meta."""
    records = [_bridge_record(0x10001, 0x11000, "WarnBridge", 0.82)]
    result = reg.compile_pipeline_icm(_pipeline(records))
    assert result["records"][0]["meta"]["auto_placed"] is False


# ── Require verification / reject → error ─────────────────────────────────

def test_require_verification_raises(reg):
    """conf=0.70 → require_verification → CompilePipelineError."""
    records = [_bridge_record(0x10001, 0x11000, "WeakBridge", 0.70)]
    with pytest.raises(CompilePipelineError) as exc_info:
        reg.compile_pipeline_icm(_pipeline(records))
    assert "WeakBridge" in str(exc_info.value) or "error" in str(exc_info.value).lower()


def test_reject_policy_raises(reg):
    """conf=0.40 → reject → CompilePipelineError."""
    records = [_bridge_record(0x10001, 0x11000, "BadBridge", 0.40)]
    with pytest.raises(CompilePipelineError):
        reg.compile_pipeline_icm(_pipeline(records))


def test_zero_confidence_raises(reg):
    """conf=0.0 → reject → CompilePipelineError."""
    records = [_bridge_record(0x10001, 0x11000, "NoBridge", 0.0)]
    with pytest.raises(CompilePipelineError):
        reg.compile_pipeline_icm(_pipeline(records))


# ── Strict mode ───────────────────────────────────────────────────────────

def test_strict_mode_blocks_warn_and_place(reg):
    """In strict mode, a warn_and_place bridge raises CompilePipelineError."""
    records = [_bridge_record(0x10001, 0x11000, "EstablishedBridge", 0.85)]
    with pytest.raises(CompilePipelineError):
        reg.compile_pipeline_icm(_pipeline(records), strict=True)


def test_strict_mode_allows_auto_place(reg):
    """In strict mode, auto_place (conf>=0.95) bridges still succeed."""
    records = [_bridge_record(0x10001, 0x11000, "Bridge_Hawking", 1.0)]
    result = reg.compile_pipeline_icm(_pipeline(records), strict=True)
    assert result["bridge_count"] == 1
    assert result["warnings"]     == []


# ── Error message quality ─────────────────────────────────────────────────

def test_error_message_contains_bridge_name(reg):
    """CompilePipelineError message should identify the problematic bridge."""
    records = [_bridge_record(0x10001, 0x11000, "IdentifiableBridge", 0.55)]
    with pytest.raises(CompilePipelineError) as exc_info:
        reg.compile_pipeline_icm(_pipeline(records))
    msg = str(exc_info.value)
    assert "IdentifiableBridge" in msg


def test_error_message_mentions_fix(reg):
    """Error message should tell the user how to fix the issue."""
    records = [_bridge_record(0x10001, 0x11000, "FixMe", 0.65)]
    with pytest.raises(CompilePipelineError) as exc_info:
        reg.compile_pipeline_icm(_pipeline(records))
    msg = str(exc_info.value).lower()
    assert "error" in msg or "fix" in msg or "confidence" in msg


# ── Mixed pipeline ────────────────────────────────────────────────────────

def test_mixed_pipeline_auto_plus_region(reg):
    """
    Region records and auto-placed bridge records coexist correctly.
    Correct ordering: region A → bridge → region B.
    """
    records = [
        _region_record(0x100, 0x10000, 0x10001),
        _bridge_record(0x10001, 0x11000, "Bridge_Hawking", 1.0, "T=..."),
        _region_record(0x200, 0x11000, 0x11001),
        _bridge_record(0x11001, 0x12000, "Bridge_Hawking", 1.0, "T=..."),
        _region_record(0x300, 0x12000, 0x12001),
    ]
    result = reg.compile_pipeline_icm(_pipeline(records))
    assert result["bridge_count"] == 2
    assert len(result["records"]) == 5
    # Region records preserved
    assert result["records"][0]["gs"] == 0x100
    assert result["records"][2]["gs"] == 0x200
    assert result["records"][4]["gs"] == 0x300
    # Bridge records expanded
    assert result["records"][1]["gs"] == GS_PASS
    assert result["records"][3]["gs"] == GS_PASS


def test_mixed_pipeline_with_warn_and_error(reg):
    """
    Pipeline with one bad bridge (conf=0.5) blocks the whole compile,
    even if another bridge would be valid.
    """
    records = [
        _bridge_record(0x10001, 0x11000, "GoodBridge",   1.0),
        _bridge_record(0x11001, 0x12000, "BadBridge",    0.50),
    ]
    with pytest.raises(CompilePipelineError):
        reg.compile_pipeline_icm(_pipeline(records))


# ── Result fields ─────────────────────────────────────────────────────────

def test_result_has_all_fields(reg):
    """Result dict always contains all required keys."""
    result = reg.compile_pipeline_icm(_pipeline([]))
    for key in ("records", "warnings", "auto", "bridge_count", "summary"):
        assert key in result, f"Missing key: {key}"


def test_summary_is_non_empty(reg):
    records = [_bridge_record(0x10001, 0x11000, "Bridge_Hawking", 1.0)]
    result = reg.compile_pipeline_icm(_pipeline(records))
    assert result["summary"]
    assert "bridge" in result["summary"].lower()


# ── Meta provenance ───────────────────────────────────────────────────────

def test_meta_carries_formula(reg):
    """Bridge meta should preserve the formula from the placeholder."""
    formula = "T = hbar*c**3 / (8*pi*G*M*kB)"
    records = [_bridge_record(0x10001, 0x11000, "Bridge_Hawking", 1.0, formula)]
    result = reg.compile_pipeline_icm(_pipeline(records))
    assert result["records"][0]["meta"]["formula"] == formula


def test_meta_carries_policy(reg):
    """Registered bridges should have their compiler_policy in meta."""
    records = [_bridge_record(0x10001, 0x11000, "Bridge_Hawking", 1.0)]
    result = reg.compile_pipeline_icm(_pipeline(records))
    policy = result["records"][0]["meta"]["policy"]
    assert policy in ("auto_place", "warn_and_place", "require_verification", "reject", "custom")


def test_unregistered_bridge_meta_policy_custom(reg):
    """Custom (unregistered) bridges get policy='custom' in meta."""
    records = [_bridge_record(0x10001, 0x11000, "Unregistered_xyz", 0.90)]
    result = reg.compile_pipeline_icm(_pipeline(records))
    assert result["records"][0]["meta"]["policy"] == "custom"


# ── Confidence threshold override ─────────────────────────────────────────

def test_custom_threshold_blocks_normally_ok_bridge(reg):
    """Raising threshold to 0.99 blocks even an 0.85 bridge."""
    records = [_bridge_record(0x10001, 0x11000, "AlmostGood", 0.85)]
    with pytest.raises(CompilePipelineError):
        reg.compile_pipeline_icm(_pipeline(records), confidence_threshold=0.99)


def test_custom_threshold_0_allows_all(reg):
    """
    Lowering threshold to 0.0 passes the threshold gate, but policy still
    applies — a 0.55 bridge is still require_verification → error.
    """
    records = [_bridge_record(0x10001, 0x11000, "WeakBridge", 0.55)]
    with pytest.raises(CompilePipelineError):
        reg.compile_pipeline_icm(_pipeline(records), confidence_threshold=0.0)
