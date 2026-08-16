"""
test_dsl_compiler_v1.py — verifies the Unicell-S DSL compiler
(`dsl_lexer_v1.py`/`dsl_parser_v1.py`/`dsl_compiler_v1.py`) both by
compiling real programs end to end (lex -> parse -> resolve -> place ->
emit -> reload) and by confirming deliberately-broken variants produce
real `CompileDiagnostic`s with correct source spans and genuinely
helpful reasoning -- the design note's own "suggested first, low-risk
step," and Alan's own explicit requirement that failures explain
themselves rather than surfacing as bare exceptions.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from dsl_compiler_v1 import compile_source  # noqa: E402
from dsl_lexer_v1 import tokenize  # noqa: E402
from dsl_parser_v1 import parse_source  # noqa: E402
import icm_v3 as v3  # noqa: E402


# ── Lexer ────────────────────────────────────────────────────────────

def test_lexer_tokenizes_a_simple_program_with_no_diagnostics():
    tokens, diags = tokenize("program x { place r as ram_constant at (0, 0) { out: e } }")
    assert diags == []
    kinds = [t.kind for t in tokens]
    assert kinds[0] == "KEYWORD" and kinds[-1] == "EOF"


def test_lexer_supports_dotted_identifiers_for_namespaced_params():
    tokens, diags = tokenize("cmp.threshold: 8")
    assert diags == []
    assert tokens[0].kind == "IDENT" and tokens[0].value == "cmp.threshold"


def test_lexer_supports_hex_numbers():
    tokens, diags = tokenize("0xCAFEBEEF")
    assert diags == []
    assert tokens[0].kind == "NUMBER" and tokens[0].value == "0xCAFEBEEF"


def test_lexer_reports_illegal_character_with_real_span():
    tokens, diags = tokenize("place r as ram_constant at (0, 0) { out: e; }")
    assert len(diags) == 1
    d = diags[0]
    assert d.stage == "lex"
    assert d.span is not None


def test_lexer_comments_are_ignored():
    tokens, diags = tokenize("# a comment\nplace r  # trailing comment\n")
    assert diags == []
    assert [t.kind for t in tokens if t.kind != "EOF"] == ["KEYWORD", "IDENT"]


# ── End-to-end: real programs compile correctly ────────────────────────

def test_single_tier0_placement_compiles_end_to_end_and_reloads():
    src = """
    program simple_ram {
        place r1 as ram_constant at (0, 0) {
            out: e
            init_data: 0xCAFEBEEF
        }
    }
    """
    icm, diags = compile_source(src)
    assert diags == []
    assert icm is not None
    assert len(icm.records) == 1
    rec = icm.records[0]
    assert (rec.row, rec.col, rec.core) == (0, 0, "ram")
    assert rec.core_config["init_data"] == 0xCAFEBEEF

    # the real end-to-end proof: save, reload, confirm record_hash holds
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "simple_ram.icm")
        icm.save(path)
        loaded = v3.IcmV3File.load(path)
        assert loaded.records[0].core_config["init_data"] == 0xCAFEBEEF


def test_multiple_tier0_placements_in_one_program():
    src = """
    program two_cells {
        place r1 as ram_constant at (0, 0) {
            out: e
            init_data: 111
        }
        place r2 as ram_flowing at (0, 1) {
            in: w
            out: n
        }
    }
    """
    icm, diags = compile_source(src)
    assert diags == []
    assert len(icm.records) == 2
    positions = {(r.row, r.col) for r in icm.records}
    assert positions == {(0, 0), (0, 1)}


def test_fanout_list_value_compiles_correctly():
    src = """
    program fanout {
        place a as accumulator at (0, 0) {
            inc: n
            dec: w
            out: [e, s]
        }
    }
    """
    icm, diags = compile_source(src)
    assert diags == []
    assert icm.records[0].core_config["downstream_mask"] == ["e", "s"]


def test_sentinel_tier1_tile_compiles_with_namespaced_param():
    src = """
    program my_sentinel {
        place s1 as sentinel at (0, 0) {
            inc: n
            dec: s
            clear: s
            out: e
            cmp.threshold: 8
        }
    }
    """
    icm, diags = compile_source(src)
    assert diags == []
    assert len(icm.records) == 3
    by_pos = {(r.row, r.col): r for r in icm.records}
    assert by_pos[(0, 1)].core_config["threshold"] == 8


def test_dual_threshold_monitor_fanout_tile_compiles():
    src = """
    program dual {
        place m as dual_threshold_monitor at (0, 0) {
            inc: n
            dec: s
            clear_low: s
            out_low: w
            clear_high: n
            out_high: e
            cmp_low.threshold: 3
            cmp_high.threshold: 10
        }
    }
    """
    icm, diags = compile_source(src)
    assert diags == []
    assert len(icm.records) == 5


def test_twin_sentinel_nested_composition_compiles_with_double_namespaced_params():
    src = """
    program twins {
        place t as twin_sentinel at (0, 0) {
            s1_inc: n
            s1_dec: s
            s1_clear: s
            s1_out: e
            s2_inc: n
            s2_dec: s
            s2_clear: s
            s2_out: e
            s1.cmp.threshold: 8
            s2.cmp.threshold: 4
        }
    }
    """
    icm, diags = compile_source(src)
    assert diags == []
    assert len(icm.records) == 6
    by_pos = {(r.row, r.col): r for r in icm.records}
    assert by_pos[(0, 1)].core_config["threshold"] == 8
    assert by_pos[(2, 1)].core_config["threshold"] == 4


# ── Deliberately-broken variants: real diagnostics, correct spans ──────

def test_missing_required_port_produces_helpful_diagnostic():
    src = """
    program broken {
        place r1 as ram_constant at (0, 0) {
            init_data: 0xCAFEBEEF
        }
    }
    """
    icm, diags = compile_source(src)
    assert icm is None
    assert len(diags) == 1
    d = diags[0]
    assert d.severity == "error" and d.stage == "place"
    assert "missing" in d.problem and "out" in d.problem
    assert d.span is not None
    # the span should point at the place statement's own line, not line 1
    assert d.span[0] == 3


def test_unknown_tile_name_lists_known_tiles_as_suggestion():
    src = """
    program broken2 {
        place r1 as totally_bogus_tile at (0, 0) {
            out: e
        }
    }
    """
    icm, diags = compile_source(src)
    assert icm is None
    d = diags[0]
    assert d.stage == "resolve"
    assert "totally_bogus_tile" in d.problem
    assert d.suggestion is not None and "ram_constant" in d.suggestion


def test_unknown_field_reports_the_tiles_real_contract():
    src = """
    program broken3 {
        place r1 as ram_constant at (0, 0) {
            out: e
            init_data: 5
            bogus_field: 1
        }
    }
    """
    icm, diags = compile_source(src)
    assert icm is None
    d = diags[0]
    assert d.stage == "resolve"
    assert "bogus_field" in d.problem
    assert "init_data" in d.why   # the real contract is explained, not just "unknown"


def test_syntax_error_has_correct_line_and_column():
    src = "program broken4 {\n    place r1 as ram_constant at (0, 0) {\n        out e\n    }\n}\n"
    icm, diags = compile_source(src)
    assert icm is None
    d = diags[0]
    assert d.stage == "parse"
    assert d.span[0] == 3   # the 'out e' line


def test_placement_collision_across_two_statements():
    src = """
    program broken5 {
        place r1 as ram_constant at (0, 0) {
            out: e
            init_data: 1
        }
        place r2 as ram_constant at (0, 0) {
            out: s
            init_data: 2
        }
    }
    """
    icm, diags = compile_source(src)
    assert icm is None
    assert any(d.stage == "place" and "occupied" in d.problem for d in diags)


def test_illegal_character_never_reaches_the_parser():
    src = "program broken6 { place r1 as ram_constant at (0, 0) { out: e; } }"
    icm, diags = compile_source(src)
    assert icm is None
    assert all(d.stage == "lex" for d in diags)


def test_multiple_errors_across_statements_are_all_collected():
    # "collect every problem, don't stop at the first" -- confirmed
    # directly: TWO independently-broken placements in one program
    # should produce diagnostics for BOTH, not just the first.
    src = """
    program broken7 {
        place r1 as ram_constant at (0, 0) {
            init_data: 1
        }
        place r2 as ram_constant at (1, 1) {
            init_data: 2
        }
    }
    """
    icm, diags = compile_source(src)
    assert icm is None
    assert len(diags) == 2
    assert all("missing" in d.problem for d in diags)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
