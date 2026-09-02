"""
test_root_definition_extractor_v1.py — verifies mechanical extraction
of field-map bit positions directly from RTL comments (`points.md
#216` item 1, `#355`). Includes real regression tests for the two
parser bugs actually found and fixed while building this (wrapped
headers losing every field), not hypothetical edge cases invented
after the fact -- confirmed broken, then fixed, then locked in here.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from root_definition_extractor_v1 import (  # noqa: E402
    extract_field_map, extract_all, extract_nano_subset_within_super, FieldDef,
)
import icm_v3 as v3  # noqa: E402
from validate_icm_v3_against_rtl_v1 import validate  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _write(tmp_path, name, content):
    path = os.path.join(tmp_path, name)
    with open(path, "w") as f:
        f.write(content)
    return path


def test_extracts_a_simple_field_map():
    src = """
// cfg_data[63:0] field map:
//   [3:0]   downstream_mask  -- one-hot, N/S/E/W
//   [7:4]   upstream_mask    -- one-hot, N/S/E/W
"""
    with tempfile.TemporaryDirectory() as d:
        path = _write(d, "test.v", src)
        rd = extract_field_map(path)
        assert rd is not None
        names = [f.name for f in rd.fields]
        assert names == ["downstream_mask", "upstream_mask"]
        assert rd.fields[0].hi == 3 and rd.fields[0].lo == 0
        assert rd.fields[1].hi == 7 and rd.fields[1].lo == 4


def test_single_bit_field():
    src = """
// cfg_data[63:0] field map:
//   [8]     fixed_mode  -- 1=permanent, 0=flowing
"""
    with tempfile.TemporaryDirectory() as d:
        path = _write(d, "test.v", src)
        rd = extract_field_map(path)
        assert rd.fields[0].hi == 8 and rd.fields[0].lo == 8
        assert rd.fields[0].width == 1


def test_wrapped_header_does_not_lose_fields_real_bug_found_and_fixed():
    # The real bug: a header wrapping onto a second comment line before
    # the first real [hi:lo] entry appears used to lose EVERY field in
    # the block. Confirmed broken by actually running an earlier version
    # of this extractor against real RTL before fixing it -- this is a
    # locked-in regression test, not a hypothetical.
    src = """
// cfg_data[63:0] field map (first proposal, NOT frozen -- flag any
// change needed after Alan reviews):
//   [3:0]   downstream_mask  -- one-hot, N/S/E/W
"""
    with tempfile.TemporaryDirectory() as d:
        path = _write(d, "test.v", src)
        rd = extract_field_map(path)
        assert len(rd.fields) == 1
        assert rd.fields[0].name == "downstream_mask"


def test_wrapped_description_does_not_truncate_later_fields():
    # The other real bug: a wrapped DESCRIPTION (not just a wrapped
    # header) between two real fields used to lose everything after it.
    src = """
// cfg_data[63:0] field map:
//   [13]    ready  -- NEW. Broadcast UNCONDITIONALLY on all 4 ports --
//                     cannot be gated by routing_mask.
//   [69:64] routing_mask  -- output side
"""
    with tempfile.TemporaryDirectory() as d:
        path = _write(d, "test.v", src)
        rd = extract_field_map(path)
        names = [f.name for f in rd.fields]
        assert names == ["ready", "routing_mask"], names


def test_block_ends_at_a_blank_line():
    src = """
// cfg_data[63:0] field map:
//   [3:0]   downstream_mask  -- one-hot

module foo;
// [7:4] this_should_not_be_captured -- outside the block
endmodule
"""
    with tempfile.TemporaryDirectory() as d:
        path = _write(d, "test.v", src)
        rd = extract_field_map(path)
        assert len(rd.fields) == 1


def test_field_name_width_suffix_present_in_raw_extraction():
    # RTL sometimes writes "init_data[31:0]" as the field NAME itself --
    # extraction should preserve it raw (normalization is the caller's
    # job, tested separately via the real validator).
    src = """
// cfg_data[63:0] field map:
//   [41:10] init_data[31:0]  -- preset value
"""
    with tempfile.TemporaryDirectory() as d:
        path = _write(d, "test.v", src)
        rd = extract_field_map(path)
        assert rd.fields[0].name == "init_data[31:0]"


def test_no_field_map_found_returns_none():
    with tempfile.TemporaryDirectory() as d:
        path = _write(d, "test.v", "module foo;\nendmodule\n")
        rd = extract_field_map(path)
        assert rd is None


# ── Real extraction against the ACTUAL repo RTL, not synthetic fixtures ──

def test_extract_all_against_real_rtl_finds_every_core():
    result = extract_all(REPO_ROOT)
    expected_cores = {"nano", "ram", "adder", "accumulator", "comparator", "latch", "sequencer", "branch",
                       "_super_latch", "nano_within_super"}
    assert set(result.keys()) == expected_cores
    for core in expected_cores:
        assert len(result[core].fields) > 0, f"{core} extracted zero fields"


def test_nano_within_super_matches_hand_derived_fields():
    result = extract_all(REPO_ROOT)
    names_and_positions = {f.name: (f.lo, f.hi) for f in result["nano_within_super"].fields}
    assert names_and_positions == {
        "topology": (0, 9), "ready": (10, 10),
        "routing_mask": (11, 16), "cardinal_edge": (17, 22),
    }


def test_ram_extraction_matches_icm_v3_field_table():
    result = extract_all(REPO_ROOT)
    extracted = {f.name.split("[")[0]: (f.lo, f.hi) for f in result["ram"].fields
                 if f.name != "reserved"}
    assert extracted == v3.CORE_FIELD_TABLES[v3.SEL_RAM]


# ── The real cross-check: icm_v3.py's hand-typed tables against the
# RTL's own comments, mechanically, not eyeballed ──────────────────────

def test_full_validation_passes_with_zero_mismatches():
    mismatches = validate(REPO_ROOT)
    assert mismatches == 0


def test_validation_catches_a_real_injected_mismatch():
    # Proves the validator actually WORKS as a check, not just that it
    # currently passes -- deliberately corrupt a copy of icm_v3's own
    # table and confirm the validator catches it.
    import copy
    original = v3.CORE_FIELD_TABLES[v3.SEL_RAM]
    corrupted = copy.deepcopy(v3.CORE_FIELD_TABLES)
    corrupted[v3.SEL_RAM] = dict(original)
    corrupted[v3.SEL_RAM]["downstream_mask"] = (99, 99)  # deliberately wrong

    real_table = v3.CORE_FIELD_TABLES
    try:
        v3.CORE_FIELD_TABLES = corrupted
        mismatches = validate(REPO_ROOT)
        assert mismatches > 0
    finally:
        v3.CORE_FIELD_TABLES = real_table


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
