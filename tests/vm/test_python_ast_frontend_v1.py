"""
test_python_ast_frontend_v1.py — verifies the real Python-AST frontend
(`points.md #348`), both standalone and cross-checked against the DSL
frontend for the same program (same discipline `test_python_frontend_v1
.py`'s dict-based cross-check already established for `#344`).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from python_ast_frontend_v1 import compile_python_source, parse_python_source  # noqa: E402
from dsl_compiler_v1 import compile_source  # noqa: E402


def test_single_tier0_placement_compiles():
    src = """
def simple_ram():
    place("r1", "ram_constant", (0, 0), out="e", init_data=0xCAFEBEEF)
"""
    icm, diags = compile_python_source(src)
    assert diags == []
    assert icm is not None
    assert icm.name == "simple_ram"
    rec = icm.records[0]
    assert (rec.row, rec.col, rec.core) == (0, 0, "ram")
    assert rec.core_config["init_data"] == 0xCAFEBEEF


def test_fanout_list_value():
    src = """
def fanout():
    place("a", "accumulator", (0, 0), inc="n", dec="w", out=["e", "s"])
"""
    icm, diags = compile_python_source(src)
    assert diags == []
    assert icm.records[0].core_config["downstream_mask"] == ["e", "s"]


def test_reserved_keyword_port_via_double_star_unpacking():
    # 'in' is a Python reserved keyword -- can't be a plain kwarg,
    # must go through **{"in": ...} unpacking.
    src = """
def uses_in():
    place("r", "ram_flowing", (0, 0), **{"in": "w", "out": "e"})
"""
    icm, diags = compile_python_source(src)
    assert diags == []
    assert icm.records[0].core_config["upstream_mask"] == ["w"]


def test_define_with_block_and_expose():
    src = """
def my_sentinel_program():
    with define("my_sentinel"):
        place("acc", "accumulator", (0, 0), out="e")
        place("cmp", "comparator", (0, 1), **{"in": "w", "out": "e"})
        place("lat", "latch", (0, 2), set="w")
        expose("inc", "acc.inc")
        expose("dec", "acc.dec")
        expose("clear", "lat.clear")
        expose("out", "lat.out")

    place("s1", "my_sentinel", (0, 0), inc="n", dec="s", clear="s", out="e",
          **{"cmp.threshold": 8})
"""
    icm, diags = compile_python_source(src)
    assert diags == []
    assert len(icm.records) == 3
    by_pos = {(r.row, r.col): r for r in icm.records}
    assert by_pos[(0, 1)].core_config["threshold"] == 8


def test_fixed_param_inside_define_works_via_python_frontend_too():
    # #347's fixed-params feature should just work here -- ProgramIR is
    # ProgramIR regardless of which frontend built it.
    src = """
def prog():
    with define("fixed_threshold_tile"):
        place("acc", "accumulator", (0, 0), out="e")
        place("cmp", "comparator", (0, 1), **{"in": "w", "out": "e", "threshold": 42})
        expose("inc", "acc.inc")
        expose("dec", "acc.dec")
        expose("out", "cmp.out")

    place("s", "fixed_threshold_tile", (0, 0), inc="n", dec="s", out="e")
"""
    icm, diags = compile_python_source(src)
    assert diags == []
    by_pos = {(r.row, r.col): r for r in icm.records}
    assert by_pos[(0, 1)].core_config["threshold"] == 42


# ── The real proof: same program, same output as the DSL ──────────────

def test_python_and_dsl_frontends_agree_on_the_same_program():
    py_src = """
def cross_check():
    place("r1", "ram_constant", (0, 0), out="e", init_data=0xCAFEBEEF)
    place("r2", "ram_flowing", (0, 1), **{"in": "w", "out": "n"})
"""
    dsl_src = """
    program cross_check {
        place r1 as ram_constant at (0, 0) {
            out: e
            init_data: 0xCAFEBEEF
        }
        place r2 as ram_flowing at (0, 1) {
            in: w
            out: n
        }
    }
    """
    py_icm, py_diags = compile_python_source(py_src)
    dsl_icm, dsl_diags = compile_source(dsl_src)

    assert py_diags == [] and dsl_diags == []
    py_by_pos = {(r.row, r.col): (r.core, r.core_config) for r in py_icm.records}
    dsl_by_pos = {(r.row, r.col): (r.core, r.core_config) for r in dsl_icm.records}
    assert py_by_pos == dsl_by_pos


# ── Deliberately-broken variants: real diagnostics, not raw Python tracebacks ──

def test_python_syntax_error_produces_real_diagnostic():
    src = "def prog(:\n    pass\n"
    icm, diags = compile_python_source(src)
    assert icm is None
    assert diags[0].stage == "parse"
    assert diags[0].span is not None


def test_non_literal_argument_rejected():
    src = """
def prog():
    x = 5
    place("r1", "ram_constant", (0, 0), out="e", init_data=x)
"""
    icm, diags = compile_python_source(src)
    assert icm is None
    assert diags[0].stage == "parse"


def test_for_loop_rejected_with_clear_reason():
    src = """
def prog():
    for i in range(3):
        place("r1", "ram_constant", (0, i), out="e", init_data=1)
"""
    icm, diags = compile_python_source(src)
    assert icm is None
    assert "loops" in diags[0].why


def test_wrong_arg_count_on_place_call():
    src = """
def prog():
    place("r1", "ram_constant")
"""
    icm, diags = compile_python_source(src)
    assert icm is None
    assert "positional argument" in diags[0].problem


def test_missing_required_port_gives_the_real_backend_diagnostic():
    # confirms this frontend's errors aren't just parse-stage -- backend
    # (resolve/place) diagnostics flow through identically to the DSL's.
    src = """
def prog():
    place("r1", "ram_constant", (0, 0), init_data=1)
"""
    icm, diags = compile_python_source(src)
    assert icm is None
    assert diags[0].stage == "place"
    assert "out" in diags[0].problem


def test_requires_exactly_one_top_level_function():
    src = """
def a():
    place("r1", "ram_constant", (0, 0), out="e", init_data=1)

def b():
    place("r2", "ram_constant", (0, 0), out="e", init_data=2)
"""
    icm, diags = compile_python_source(src)
    assert icm is None
    assert "exactly one" in diags[0].problem


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
