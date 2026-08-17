"""
tests/vm/test_pipeline_bridge_check.py

Tests for FormatRegistry.check_pipeline_bridges() — the compile-time
confidence-threshold enforcement that mirrors what the Region Connector
already does in the UI.

Coverage:
  - auto_place (conf >= 0.95): silent, appears in auto list
  - warn_and_place (conf >= 0.80): warning, not error
  - require_verification (conf < 0.80 or context mismatch): error
  - reject (conf < 0.60): error
  - below explicit threshold: error regardless of policy
  - strict mode: warnings become errors
  - direct connections (no bridge): always ok, not counted
  - custom (unregistered) bridges: policy derived from confidence alone
  - empty pipeline: ok
  - mixed pipeline: correct triage of auto/warn/error
"""

import pytest
from cell_format import FormatRegistry


# ── Helpers ────────────────────────────────────────────────────────────────

def _pipeline(connections, regions=None):
    """
    Build a minimal pipeline .icm dict for testing.
    regions defaults to one region per unique from/to id.
    """
    if regions is None:
        ids = set()
        for c in connections:
            ids.add(c.get("from", "A"))
            ids.add(c.get("to", "B"))
        # Assign a plausible format to each region id.
        fmt_map = {rid: _FMT_FOR_ID.get(rid, "SI_Physics") for rid in ids}
        regions = [
            {"id": rid, "format": fmt_map[rid],
             "model": rid, "context": _CTX_FOR_ID.get(rid, ""),
             "domain": "Test"}
            for rid in sorted(ids)
        ]
    return {"regions": regions, "connections": connections}


# Region id → format (for helpers above)
_FMT_FOR_ID = {
    "A": "SI_Physics",
    "B": "SI_Physics",
    "C": "Chemistry_Element",
    "D": "DNA_4Base",
    "E": "Amino20",
}
_CTX_FOR_ID = {
    "A": "gravitational",
    "B": "thermal_quantum",
    "C": "",
    "D": "",
    "E": "",
}


@pytest.fixture
def reg():
    return FormatRegistry.get_default()


# ── Direct connection (no bridge) ──────────────────────────────────────────

def test_direct_connection_always_ok(reg):
    """Direct connections (bridge=None) are never flagged."""
    pipeline = _pipeline([{"from": "A", "to": "B", "bridge": None}])
    result = reg.check_pipeline_bridges(pipeline)
    assert result["ok"]
    assert result["errors"]   == []
    assert result["warnings"] == []
    assert result["auto"]     == []


def test_empty_pipeline_ok(reg):
    """No connections at all — trivially ok."""
    result = reg.check_pipeline_bridges({"regions": [], "connections": []})
    assert result["ok"]


# ── Auto-place (discovered physics, conf >= 0.95) ──────────────────────────

def test_auto_place_hawking(reg):
    """
    Bridge_Hawking has confidence=1.0 and context gravitational→thermal_quantum.
    Should be auto-placed with no warnings or errors.
    """
    pipeline = _pipeline([{
        "from": "A", "to": "B",
        "bridge": "Bridge_Hawking",
        "confidence": 1.0,
        "formula": "T = hbar*c**3 / (8*pi*G*M*kB)",
    }])
    result = reg.check_pipeline_bridges(pipeline)
    assert result["ok"]
    assert result["errors"]   == []
    assert result["warnings"] == []
    assert len(result["auto"]) == 1
    assert "Bridge_Hawking" in result["auto"][0]


def test_auto_place_arrhenius(reg):
    """Bridge_Arrhenius SI→Chemistry, conf=1.0 — auto."""
    regions = [
        {"id": "A", "format": "SI_Physics",        "model": "A", "context": "", "domain": "Test"},
        {"id": "C", "format": "Chemistry_Element",  "model": "C", "context": "", "domain": "Test"},
    ]
    pipeline = _pipeline([{
        "from": "A", "to": "C",
        "bridge": "Bridge_Arrhenius",
        "confidence": 1.0,
        "formula": "k = A * exp(-Ea / (R*T))",
    }], regions=regions)
    result = reg.check_pipeline_bridges(pipeline)
    assert result["ok"]
    assert len(result["auto"]) == 1


# ── Warn-and-place (established, conf >= 0.80 < 0.95) ─────────────────────

def test_warn_and_place_navier_stokes(reg):
    """
    Bridge_Navier_Stokes_Temp has confidence=0.95 which is actually auto_place.
    Use a custom bridge at 0.85 to exercise warn_and_place.
    """
    pipeline = _pipeline([{
        "from": "A", "to": "B",
        "bridge": "MyCustom_0_85",
        "confidence": 0.85,
        "formula": "y = f(x)",
    }])
    result = reg.check_pipeline_bridges(pipeline)
    assert result["ok"]
    assert result["errors"]   == []
    assert len(result["warnings"]) == 1
    assert "MyCustom_0_85" in result["warnings"][0]


def test_warn_and_place_strict_becomes_error(reg):
    """In strict mode, warn_and_place is treated as an error."""
    pipeline = _pipeline([{
        "from": "A", "to": "B",
        "bridge": "SomeEstablishedBridge",
        "confidence": 0.82,
        "formula": "some formula",
    }])
    result = reg.check_pipeline_bridges(pipeline, strict=True)
    assert not result["ok"]
    assert len(result["errors"]) == 1
    assert result["warnings"] == []


# ── Require verification (conf < 0.80 but >= 0.60) ────────────────────────

def test_require_verification_is_error(reg):
    """conf=0.70 → require_verification → error."""
    pipeline = _pipeline([{
        "from": "A", "to": "B",
        "bridge": "SpculativeBridge",
        "confidence": 0.70,
        "formula": "vague model",
    }])
    result = reg.check_pipeline_bridges(pipeline)
    assert not result["ok"]
    assert len(result["errors"]) == 1
    assert "SpculativeBridge" in result["errors"][0]


def test_require_verification_at_exactly_060(reg):
    """conf=0.60 is the boundary — still require_verification → error."""
    pipeline = _pipeline([{
        "from": "A", "to": "B",
        "bridge": "BorderlineBridge",
        "confidence": 0.60,
        "formula": "borderline",
    }])
    result = reg.check_pipeline_bridges(pipeline)
    assert not result["ok"]


# ── Reject (conf < 0.60) ───────────────────────────────────────────────────

def test_reject_below_060(reg):
    """conf=0.50 → reject → error."""
    pipeline = _pipeline([{
        "from": "A", "to": "B",
        "bridge": "BadBridge",
        "confidence": 0.50,
        "formula": "",
    }])
    result = reg.check_pipeline_bridges(pipeline)
    assert not result["ok"]
    assert any("REJECT" in e or "reject" in e.lower() or "0.50" in e
               for e in result["errors"])


def test_reject_zero_confidence(reg):
    """conf=0.0 (explicitly no connection) → reject."""
    pipeline = _pipeline([{
        "from": "A", "to": "B",
        "bridge": "NoBridge",
        "confidence": 0.0,
    }])
    result = reg.check_pipeline_bridges(pipeline)
    assert not result["ok"]


# ── Explicit threshold override ────────────────────────────────────────────

def test_custom_threshold_higher(reg):
    """
    Default threshold is 0.80. Raising it to 0.95 should flag
    a bridge that would normally be warn_and_place at 0.85.
    """
    pipeline = _pipeline([{
        "from": "A", "to": "B",
        "bridge": "GoodBridge",
        "confidence": 0.85,
        "formula": "y = x",
    }])
    result = reg.check_pipeline_bridges(pipeline, confidence_threshold=0.95)
    assert not result["ok"]
    assert any("threshold" in e for e in result["errors"])


def test_custom_threshold_lower(reg):
    """
    Lowering threshold to 0.60 should let a 0.65 bridge through as a warning
    (require_verification policy, but above the explicit threshold).
    """
    pipeline = _pipeline([{
        "from": "A", "to": "B",
        "bridge": "SpeculativeBridge",
        "confidence": 0.65,
        "formula": "approx model",
    }])
    # At threshold=0.60 the confidence-threshold gate passes;
    # but require_verification policy still makes it an error.
    result = reg.check_pipeline_bridges(pipeline, confidence_threshold=0.60)
    assert not result["ok"]   # require_verification is still an error


def test_threshold_exactly_at_confidence(reg):
    """Bridge confidence exactly at threshold should NOT trigger threshold error."""
    pipeline = _pipeline([{
        "from": "A", "to": "B",
        "bridge": "ExactBridge",
        "confidence": 0.80,
        "formula": "f(x)",
    }])
    result = reg.check_pipeline_bridges(pipeline, confidence_threshold=0.80)
    # warn_and_place (0.80 >= threshold), not a threshold error
    assert "below threshold" not in " ".join(result["errors"])


# ── Mixed pipeline ─────────────────────────────────────────────────────────

def test_mixed_pipeline_triage(reg):
    """
    Three connections:
      1. Auto (Hawking, conf=1.0)
      2. Warn (custom, conf=0.85)
      3. Error (custom, conf=0.55)
    """
    regions = [
        {"id": "X", "format": "SI_Physics",  "model": "X", "context": "gravitational", "domain": "T"},
        {"id": "Y", "format": "SI_Physics",  "model": "Y", "context": "thermal_quantum","domain": "T"},
        {"id": "Z", "format": "SI_Physics",  "model": "Z", "context": "",              "domain": "T"},
        {"id": "W", "format": "SI_Physics",  "model": "W", "context": "",              "domain": "T"},
    ]
    connections = [
        {"from": "X", "to": "Y", "bridge": "Bridge_Hawking",   "confidence": 1.0,  "formula": "T = ..."},
        {"from": "Z", "to": "W", "bridge": "EstablishedCustom","confidence": 0.85, "formula": "y=f(x)"},
        {"from": "Z", "to": "W", "bridge": "BadCustom",         "confidence": 0.55, "formula": "?"},
    ]
    result = reg.check_pipeline_bridges({"regions": regions, "connections": connections})
    assert not result["ok"]
    assert len(result["auto"])     == 1
    assert len(result["warnings"]) == 1
    assert len(result["errors"])   == 1


# ── Summary string ─────────────────────────────────────────────────────────

def test_summary_is_populated(reg):
    """summary field is always present and non-empty."""
    pipeline = _pipeline([{"from": "A", "to": "B", "bridge": None}])
    result = reg.check_pipeline_bridges(pipeline)
    assert result["summary"]
    assert "connection" in result["summary"]


# ── Registered bridge with context mismatch ───────────────────────────────

def test_registered_bridge_context_mismatch_warns(reg):
    """
    Bridge_Hawking declares source_context='gravitational'.
    Connecting two regions with no context — match is still valid
    (empty context ≠ mismatch for our test, since the bridge has
    source_context set but the region context is empty).
    This tests that the checker doesn't crash on context differences.
    """
    regions = [
        {"id": "P", "format": "SI_Physics", "model": "P", "context": "wrong_ctx", "domain": "T"},
        {"id": "Q", "format": "SI_Physics", "model": "Q", "context": "other_ctx", "domain": "T"},
    ]
    pipeline = _pipeline([{
        "from": "P", "to": "Q",
        "bridge": "Bridge_Hawking",
        "confidence": 1.0,
        "formula": "T = hbar*c**3 / (8*pi*G*M*kB)",
    }], regions=regions)
    # Should not raise — result may be auto or warn depending on context logic
    result = reg.check_pipeline_bridges(pipeline)
    assert isinstance(result["ok"], bool)
    assert isinstance(result["errors"], list)


# ── SI_CHECK dimensional analysis ─────────────────────────────────────────

def test_si_check_matching_dimension_passes(reg):
    """
    Bridge_Hawking output_dimension=[0,0,0,0,1,0,0] (K = temperature).
    SI_Physics.dimension_map["temperature"] = [0,0,0,0,1,0,0].
    Should pass — dimension matches.
    """
    pipeline = _pipeline([{
        "from": "A", "to": "B",
        "bridge": "Bridge_Hawking",
        "confidence": 1.0,
        "formula": "T = hbar*c**3 / (8*pi*G*M*kB)",
    }])
    result = reg.check_pipeline_bridges(pipeline)
    assert result["ok"], result["errors"]
    assert result["errors"] == []


def test_si_check_stefan_boltzmann_power_matches(reg):
    """
    Bridge_Stefan_Boltzmann output_dimension=[2,1,-3,0,0,0,0] (W = power).
    SI_Physics.dimension_map["power"] = [2,1,-3,0,0,0,0].
    Should pass.
    """
    regions = [
        {"id": "A", "format": "SI_Physics", "model": "A", "context": "thermal", "domain": "T"},
        {"id": "B", "format": "SI_Physics", "model": "B", "context": "radiation", "domain": "T"},
    ]
    pipeline = _pipeline([{
        "from": "A", "to": "B",
        "bridge": "Bridge_Stefan_Boltzmann",
        "confidence": 1.0,
        "formula": "P = sigma * A * T**4",
    }], regions=regions)
    result = reg.check_pipeline_bridges(pipeline)
    # Bridge_Stefan_Boltzmann delivers power; SI_Physics consumes power.
    # Dimension match expected.
    assert isinstance(result["ok"], bool)   # should not crash
    assert result["errors"] == [] or all("SI_CHECK" not in e for e in result["errors"])


def test_si_check_arrhenius_rate_matches(reg):
    """
    Bridge_Arrhenius output_dimension=[0,0,-1,0,0,0,0] (s⁻¹ = rate).
    SI_Physics dimension_map has no 'rate' consuming concept in its consumes dict.
    So no relevant_concepts → no dimension check fired → passes.
    """
    regions = [
        {"id": "A", "format": "SI_Physics",        "model": "A", "context": "", "domain": "T"},
        {"id": "C", "format": "Chemistry_Element",  "model": "C", "context": "", "domain": "T"},
    ]
    pipeline = _pipeline([{
        "from": "A", "to": "C",
        "bridge": "Bridge_Arrhenius",
        "confidence": 1.0,
        "formula": "k = A * exp(-Ea / (R*T))",
    }], regions=regions)
    result = reg.check_pipeline_bridges(pipeline)
    # Chemistry_Element has no dimension_map → SI_CHECK skipped → no dim error
    assert result["ok"], result["errors"]


def test_si_check_no_dimension_map_skipped(reg):
    """
    If the target format has no dimension_map (e.g. DNA_4Base),
    the SI_CHECK step is silently skipped — no false errors.
    """
    regions = [
        {"id": "A", "format": "SI_Physics", "model": "A", "context": "", "domain": "T"},
        {"id": "D", "format": "DNA_4Base",  "model": "D", "context": "", "domain": "T"},
    ]
    pipeline = _pipeline([{
        "from": "A", "to": "D",
        "bridge": "Bridge_SI_to_DNA",
        "confidence": 0.85,
        "formula": "Tm = 81.5 + 16.6*log10([Na+]) + 0.41*GC - 675/n",
    }], regions=regions)
    result = reg.check_pipeline_bridges(pipeline)
    # No dim error — DNA_4Base has no dimension_map
    assert all("SI_CHECK" not in e for e in result["errors"])


def test_si_check_custom_bridge_no_output_dimension_skipped(reg):
    """
    Custom bridges typically have no output_dimension declared (empty list).
    SI_CHECK should be silently skipped — only fires on registered bridges
    with a declared output_dimension.
    """
    pipeline = _pipeline([{
        "from": "A", "to": "B",
        "bridge": "MyCustomBridge",
        "confidence": 0.90,
        "formula": "y = f(x)",
    }])
    result = reg.check_pipeline_bridges(pipeline)
    # No SI_CHECK error — custom bridge, no registered output_dimension
    assert all("SI_CHECK" not in e for e in result["errors"])
