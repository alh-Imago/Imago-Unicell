"""
test_c_frontend_v1.py — verifies the real C-AST frontend (`points.md
#374`), both standalone and cross-checked against the DSL frontend for
the same program (same discipline `test_python_frontend_v1.py`/
`test_python_ast_frontend_v1.py` already established for `#344`/`#348`).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from c_frontend_v1 import compile_c_source, parse_c_source  # noqa: E402
from dsl_compiler_v1 import compile_source  # noqa: E402


def test_single_tier0_placement_compiles():
    src = """
void simple_ram(void) {
    place("r1", "ram_constant", 0, 0);
    field("r1", "out", "e");
    field("r1", "init_data", 0xCAFEBEEF);
}
"""
    icm, diags = compile_c_source(src)
    assert diags == []
    assert icm is not None
    assert icm.name == "simple_ram"
    rec = icm.records[0]
    assert (rec.row, rec.col, rec.core) == (0, 0, "ram")
    assert rec.core_config["init_data"] == 0xCAFEBEEF


def test_two_cell_program_matches_dsl_equivalent_exactly():
    # the real cross-check: the SAME program, authored two different
    # ways, must reach the exact same ICM v3 records.
    c_src = """
void two_cells(void) {
    place("r1", "ram_constant", 0, 0);
    field("r1", "out", "e");
    field("r1", "init_data", 5);
    place("acc1", "accumulator", 0, 1);
    field("acc1", "inc", "w");
    field("acc1", "dec", "n");
    field("acc1", "out", "e");
}
"""
    dsl_src = """
    program two_cells {
        place r1 as ram_constant at (0, 0) {
            out: e
            init_data: 5
        }
        place acc1 as accumulator at (0, 1) {
            inc: w
            dec: n
            out: e
        }
    }
    """
    c_icm, c_diags = compile_c_source(c_src)
    dsl_icm, dsl_diags = compile_source(dsl_src)
    assert c_diags == [] and dsl_diags == []
    assert c_icm is not None and dsl_icm is not None
    c_records = [(r.row, r.col, r.core, r.core_config) for r in c_icm.records]
    dsl_records = [(r.row, r.col, r.core, r.core_config) for r in dsl_icm.records]
    assert c_records == dsl_records


def test_hex_integer_field_value():
    src = """
void p(void) {
    place("r1", "ram_constant", 0, 0);
    field("r1", "out", "e");
    field("r1", "init_data", 0xCAFE);
}
"""
    icm, diags = compile_c_source(src)
    assert diags == []
    assert icm.records[0].core_config["init_data"] == 0xCAFE


def test_field_before_place_is_a_real_error():
    icm, diags = compile_c_source(
        'void p(void) { field("r1", "out", "e"); place("r1", "ram_constant", 0, 0); }'
    )
    assert icm is None
    assert "no place(" in diags[0].problem


def test_duplicate_place_name_is_a_real_error():
    icm, diags = compile_c_source(
        'void p(void) { place("r1", "ram_constant", 0, 0); place("r1", "ram_constant", 1, 1); }'
    )
    assert icm is None
    assert "already placed" in diags[0].problem


def test_wrong_place_arg_count_is_a_real_error():
    icm, diags = compile_c_source('void p(void) { place("r1", "ram_constant", 0); }')
    assert icm is None
    assert "got 3 argument" in diags[0].problem


def test_non_literal_argument_is_a_real_error_with_a_real_span():
    icm, diags = compile_c_source('void p(void) { place(some_name, "ram_constant", 0, 0); }')
    assert icm is None
    assert "literal" in diags[0].problem
    assert diags[0].span is not None


def test_unrecognized_function_call_is_a_real_error():
    icm, diags = compile_c_source('void p(void) { bogus("r1"); }')
    assert icm is None
    assert "unrecognized call" in diags[0].problem


def test_zero_top_level_functions_is_a_real_error():
    icm, diags = compile_c_source("int x;")
    assert icm is None
    assert "found 0" in diags[0].problem


def test_two_top_level_functions_is_a_real_error():
    icm, diags = compile_c_source("void a(void) {} void b(void) {}")
    assert icm is None
    assert "found 2" in diags[0].problem


def test_real_c_syntax_error_gives_a_real_span():
    icm, diags = compile_c_source('void p(void) { place("r1" "ram_constant", 0, 0) }')
    assert icm is None
    assert diags[0].span is not None and diags[0].span[0] >= 1


def test_backend_level_error_still_carries_a_real_span_from_the_c_source():
    # missing a required port (accumulator needs both inc AND dec) --
    # this is a BACKEND diagnostic (place.py's own validation), not a
    # parse-level one, proving diagnostics flow through end to end with
    # real spans, not just parser-level errors.
    icm, diags = compile_c_source(
        'void p(void) { place("acc1", "accumulator", 0, 0); field("acc1", "inc", "w"); '
        'field("acc1", "out", "e"); }'
    )
    assert icm is None
    assert any("missing" in d.problem for d in diags)


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
