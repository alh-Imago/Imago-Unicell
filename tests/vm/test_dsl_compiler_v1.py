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


# ── Naming hygiene lint (points.md #350) ───────────────────────────────

def test_duplicate_top_level_name_produces_a_warning_not_an_error():
    src = """
    program p {
        place r1 as ram_constant at (0, 0) { out: e init_data: 1 }
        place r1 as ram_constant at (0, 1) { out: e init_data: 2 }
    }
    """
    icm, diags = compile_source(src)
    assert icm is not None   # a warning must NOT block compilation
    lint_diags = [d for d in diags if d.stage == "lint"]
    assert len(lint_diags) == 1
    assert lint_diags[0].severity == "warning"
    assert "r1" in lint_diags[0].problem


def test_no_duplicate_name_warning_when_names_are_distinct():
    src = """
    program p {
        place r1 as ram_constant at (0, 0) { out: e init_data: 1 }
        place r2 as ram_constant at (0, 1) { out: e init_data: 2 }
    }
    """
    icm, diags = compile_source(src)
    assert diags == []


def test_duplicate_subcell_name_inside_define_produces_a_warning():
    src = """
    program p {
        define bad {
            place x as accumulator at (0, 0) { out: e }
            place x as comparator at (0, 1) { in: w out: e }
            expose inc -> x.inc
            expose dec -> x.dec
            expose out -> x.out
        }
    }
    """
    icm, diags = compile_source(src)
    lint_diags = [d for d in diags if d.stage == "lint"]
    assert len(lint_diags) == 1
    assert lint_diags[0].severity == "warning"
    assert "bad" in lint_diags[0].what and "'x'" in lint_diags[0].problem


def test_three_way_duplicate_name_only_flags_the_repeats_not_the_first():
    src = """
    program p {
        place r1 as ram_constant at (0, 0) { out: e init_data: 1 }
        place r1 as ram_constant at (0, 1) { out: e init_data: 2 }
        place r1 as ram_constant at (0, 2) { out: e init_data: 3 }
    }
    """
    icm, diags = compile_source(src)
    lint_diags = [d for d in diags if d.stage == "lint"]
    assert len(lint_diags) == 2   # the 2nd and 3rd 'r1', not the first


# ── define/expose (points.md #346): a program can define its own
# reusable composed tile inline. ────────────────────────────────────

def test_define_recreates_sentinel_from_scratch():
    src = """
    program recreated_sentinel {
        define my_sentinel {
            place acc as accumulator at (0, 0) {
                out: e
            }
            place cmp as comparator at (0, 1) {
                in: w
                out: e
            }
            place lat as latch at (0, 2) {
                set: w
            }

            expose inc -> acc.inc
            expose dec -> acc.dec
            expose clear -> lat.clear
            expose out -> lat.out
        }

        place s1 as my_sentinel at (0, 0) {
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
    assert by_pos[(0, 0)].core == "accumulator"
    assert by_pos[(0, 1)].core_config["threshold"] == 8
    assert by_pos[(0, 2)].core == "latch"


def test_defined_tile_can_be_placed_more_than_once():
    src = """
    program two_instances {
        define pair {
            place add as adder at (0, 0) { out: e }
            place cmp as comparator at (0, 1) { in: w out: e }
            expose in_a -> add.in_a
            expose in_b -> add.in_b
            expose out -> cmp.out
        }
        place p1 as pair at (0, 0) {
            in_a: n
            in_b: w
            out: e
            cmp.threshold: 5
        }
        place p2 as pair at (2, 0) {
            in_a: n
            in_b: w
            out: e
            cmp.threshold: 10
        }
    }
    """
    icm, diags = compile_source(src)
    assert diags == []
    assert len(icm.records) == 4
    by_pos = {(r.row, r.col): r for r in icm.records}
    assert by_pos[(0, 1)].core_config["threshold"] == 5
    assert by_pos[(2, 1)].core_config["threshold"] == 10


def test_define_of_define_nests_correctly_with_double_namespaced_params():
    src = """
    program nested {
        define pair {
            place add as adder at (0, 0) { out: e }
            place cmp as comparator at (0, 1) { in: w out: e }
            expose in_a -> add.in_a
            expose in_b -> add.in_b
            expose out -> cmp.out
        }
        define double_pair {
            place p1 as pair at (0, 0) {
                in_a: n
                in_b: w
            }
            place p2 as pair at (1, 0) {
                in_a: n
                in_b: w
            }
            expose p1_in_a -> p1.in_a
            expose p1_in_b -> p1.in_b
            expose p1_out -> p1.out
            expose p2_in_a -> p2.in_a
            expose p2_in_b -> p2.in_b
            expose p2_out -> p2.out
        }
        place dp as double_pair at (0, 0) {
            p1_in_a: n
            p1_in_b: w
            p1_out: e
            p2_in_a: n
            p2_in_b: w
            p2_out: e
            p1.cmp.threshold: 5
            p2.cmp.threshold: 10
        }
    }
    """
    icm, diags = compile_source(src)
    assert diags == []
    assert len(icm.records) == 4
    by_pos = {(r.row, r.col): r for r in icm.records}
    assert by_pos[(0, 1)].core_config["threshold"] == 5
    assert by_pos[(1, 1)].core_config["threshold"] == 10


def test_define_missing_expose_produces_helpful_diagnostic():
    src = """
    program broken1 {
        define broken_tile {
            place acc as accumulator at (0, 0) {
                out: e
            }
            place cmp as comparator at (0, 1) {
                in: w
                out: e
            }
            expose inc -> acc.inc
        }
        place s as broken_tile at (0, 0) {
            inc: n
            cmp.threshold: 8
        }
    }
    """
    icm, diags = compile_source(src)
    assert icm is None
    define_diags = [d for d in diags if "defining tile" in d.what]
    assert len(define_diags) == 1
    assert "acc" in define_diags[0].problem and "dec" in define_diags[0].problem
    assert define_diags[0].suggestion is not None and "expose" in define_diags[0].suggestion


def test_define_fixed_param_bakes_into_the_tile_no_longer_required_from_caller():
    # points.md #347: a sub-cell's own param can now be FIXED inside
    # define -- it disappears from what the newly-defined tile requires
    # from its own caller entirely.
    src = """
    program p {
        define fixed_threshold_tile {
            place acc as accumulator at (0, 0) { out: e }
            place cmp as comparator at (0, 1) {
                in: w
                out: e
                threshold: 42
            }
            expose inc -> acc.inc
            expose dec -> acc.dec
            expose out -> cmp.out
        }
        place s as fixed_threshold_tile at (0, 0) {
            inc: n
            dec: s
            out: e
        }
    }
    """
    icm, diags = compile_source(src)
    assert diags == []
    assert icm is not None
    by_pos = {(r.row, r.col): r for r in icm.records}
    assert by_pos[(0, 1)].core_config["threshold"] == 42


def test_define_fixed_param_cannot_be_overridden_by_caller():
    # a caller trying to ALSO supply the now-fixed param should get a
    # real 'unknown param' diagnostic -- it's genuinely not part of the
    # defined tile's contract anymore, not silently accepted or ignored.
    src = """
    program p {
        define fixed_threshold_tile {
            place acc as accumulator at (0, 0) { out: e }
            place cmp as comparator at (0, 1) {
                in: w
                out: e
                threshold: 42
            }
            expose inc -> acc.inc
            expose dec -> acc.dec
            expose out -> cmp.out
        }
        place s as fixed_threshold_tile at (0, 0) {
            inc: n
            dec: s
            out: e
            cmp.threshold: 99
        }
    }
    """
    icm, diags = compile_source(src)
    assert icm is None
    assert any("cmp.threshold" in d.problem for d in diags)


def test_define_expose_referencing_unknown_subcell():
    src = """
    program broken3 {
        define broken_tile {
            place acc as accumulator at (0, 0) { out: e }
            expose inc -> acc.inc
            expose dec -> acc.dec
            expose out -> nonexistent.out
        }
    }
    """
    icm, diags = compile_source(src)
    assert icm is None
    d = diags[0]
    assert "nonexistent" in d.problem
    assert "acc" in d.why


def test_place_can_forward_reference_a_define_later_in_the_file():
    # points.md #347: place statements get real forward declarations --
    # this must now WORK, not fail, unlike before.
    src = """
    program forward_ref {
        place s as later_defined at (0, 0) {
            out: e
        }
        define later_defined {
            place a as ram_constant at (0, 0) {
                out: e
                init_data: 7
            }
            expose out -> a.out
        }
    }
    """
    icm, diags = compile_source(src)
    assert diags == []
    assert icm is not None
    assert icm.records[0].core_config["init_data"] == 7


def test_define_still_cannot_forward_reference_a_later_define():
    # the real, narrower, stated limit: a define can only reference an
    # EARLIER define, not a later one -- full mutual forward refs among
    # defines is a genuinely different, harder problem, not attempted.
    src = """
    program p {
        define outer {
            place x as inner at (0, 0) {
                out: e
            }
            expose out -> x.out
        }
        define inner {
            place a as ram_constant at (0, 0) {
                out: e
                init_data: 1
            }
            expose out -> a.out
        }
    }
    """
    icm, diags = compile_source(src)
    assert icm is None
    assert any("inner" in d.problem for d in diags)


def test_defined_tile_does_not_leak_into_a_second_unrelated_compile():
    # per the module docstring's own claim: each compile_program_ir()
    # call gets a fresh, disposable library scope -- a tile defined in
    # one compile must NOT be visible in a completely separate one.
    src1 = """
    program p1 {
        define one_off_tile {
            place a as ram_flowing at (0, 0) {
                in: n
                out: e
            }
            expose in_side -> a.in
            expose out_side -> a.out
        }
    }
    """
    icm1, diags1 = compile_source(src1)
    assert diags1 == []   # defining with no placements of it is fine on its own

    src2 = """
    program p2 {
        place r as one_off_tile at (0, 0) {
            in_side: n
            out_side: e
        }
    }
    """
    icm2, diags2 = compile_source(src2)
    assert icm2 is None
    assert any("one_off_tile" in d.problem for d in diags2)   # NOT visible here


# ── Parser error recovery (points.md #372) ──────────────────────────────
# Real, statement-level panic-mode recovery: on a syntax error inside one
# place/define/expose statement, that statement is abandoned wholesale and
# the parser resyncs to the next plausible statement boundary, rather than
# stopping at the first error. These tests are the real acceptance proof
# for that -- not just "it doesn't crash," but "it finds every independent
# error and correctly recovers position even when the error is buried
# inside an open brace."

def test_recovery_two_independent_errors_both_reported():
    src = """
    program broken {
        place r1 XXXXX ram_constant at (0,0) {
            out: e
            init_data: 1
        }
        place r2 as ram_constant at (1,0) {
            out e
            init_data: 2
        }
        place r3 as ram_constant at (2,0) {
            out: e
            init_data: 3
        }
    }
    """
    icm, diags = compile_source(src)
    assert icm is None
    errors = [d for d in diags if d.severity == "error"]
    assert len(errors) == 2
    assert "expected keyword 'as'" in errors[0].problem
    assert "expected COLON" in errors[1].problem


def test_recovery_three_independent_errors_including_inside_a_define():
    src = """
    program p {
        define broken_tile {
            place a as adder at (0,0) {
                in_a n
                in_b: w
                out: e
            }
            expose out -> a.out
        }
        place r1 GARBAGE ram_constant at (5,0) {
            out: e
            init_data: 1
        }
        place r2 as ram_constant at (6,0) {
            out e
            init_data: 2
        }
        place r3 as ram_constant at (7,0) {
            out: e
            init_data: 3
        }
    }
    """
    icm, diags = compile_source(src)
    assert icm is None
    errors = [d for d in diags if d.severity == "error"]
    assert len(errors) == 3


def test_recovery_error_inside_a_define_still_lets_expose_parse_after_it():
    # the define's own inner recovery (place/expose resync, not place/define)
    src = """
    program p {
        define broken_tile {
            place a as adder at (0,0) {
                in_a n
                in_b: w
                out: e
            }
            expose out -> a.out
        }
        place r1 as ram_constant at (5,0) {
            out: e
            init_data: 1
        }
    }
    """
    icm, diags = compile_source(src)
    errors = [d for d in diags if d.severity == "error"]
    assert len(errors) == 1
    assert "in_a" in errors[0].problem or "COLON" in errors[0].problem


def test_recovery_clean_program_unaffected():
    icm, diags = compile_source(
        "program p { place r1 as ram_constant at (0,0) { out: e init_data: 1 } }"
    )
    assert icm is not None
    assert diags == []


def test_recovery_missing_closing_brace_terminates_cleanly():
    # a real, honest diagnostic instead of hanging or crashing
    icm, diags = compile_source(
        "program p { place r1 as ram_constant at (0,0) { out: e init_data: 1 }"
    )
    assert icm is None
    assert any("closing" in d.problem for d in diags)


def test_recovery_unrecoverable_header_still_gives_exactly_one_diagnostic():
    # the program's own header (program NAME {) has no sane resync point
    icm, diags = compile_source("this is not even close to valid syntax")
    assert icm is None
    assert len(diags) == 1


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
