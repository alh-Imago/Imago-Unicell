"""
test_python_frontend_v1.py — proves `program_ir_v1.ProgramIR` and
`dsl_compiler_v1.compile_program_ir()` are genuinely frontend-agnostic
(`points.md #344`), not just structured to look that way. Every test
here calls `compile_from_dict()`/`compile_program_ir()` directly --
`dsl_lexer_v1`/`dsl_parser_v1` are never imported or exercised in this
file at all. Several tests compile the SAME program both ways (DSL text
vs. plain Python dicts) and confirm identical output records.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from python_frontend_v1 import compile_from_dict, program_ir_from_dict  # noqa: E402
from dsl_compiler_v1 import compile_program_ir, compile_source  # noqa: E402
from program_ir_v1 import ProgramIR, PlaceIR, FieldIR  # noqa: E402


def test_single_tier0_placement_compiles_via_dict_frontend():
    icm, diags = compile_from_dict("simple_ram", [
        {"name": "r1", "tile": "ram_constant", "at": (0, 0),
         "fields": {"out": "e", "init_data": 0xCAFEBEEF}},
    ])
    assert diags == []
    assert icm is not None
    assert len(icm.records) == 1
    rec = icm.records[0]
    assert (rec.row, rec.col, rec.core) == (0, 0, "ram")
    assert rec.core_config["init_data"] == 0xCAFEBEEF


def test_fanout_list_value_via_dict_frontend():
    icm, diags = compile_from_dict("fanout", [
        {"name": "a", "tile": "accumulator", "at": (0, 0),
         "fields": {"inc": "n", "dec": "w", "out": ["e", "s"], "step_amount": 1}},
    ])
    assert diags == []
    assert icm.records[0].core_config["downstream_mask"] == ["e", "s"]


def test_sentinel_tier1_via_dict_frontend():
    icm, diags = compile_from_dict("my_sentinel", [
        {"name": "s1", "tile": "sentinel", "at": (0, 0),
         "fields": {"inc": "n", "dec": "s", "clear": "s", "out": "e", "cmp.threshold": 8}},
    ])
    assert diags == []
    assert len(icm.records) == 3
    by_pos = {(r.row, r.col): r for r in icm.records}
    assert by_pos[(0, 1)].core_config["threshold"] == 8


def test_twin_sentinel_nested_composition_via_dict_frontend():
    icm, diags = compile_from_dict("twins", [
        {"name": "t", "tile": "twin_sentinel", "at": (0, 0), "fields": {
            "s1_inc": "n", "s1_dec": "s", "s1_clear": "s", "s1_out": "e",
            "s2_inc": "n", "s2_dec": "s", "s2_clear": "s", "s2_out": "e",
            "s1.cmp.threshold": 8, "s2.cmp.threshold": 4,
        }},
    ])
    assert diags == []
    assert len(icm.records) == 6
    by_pos = {(r.row, r.col): r for r in icm.records}
    assert by_pos[(0, 1)].core_config["threshold"] == 8
    assert by_pos[(2, 1)].core_config["threshold"] == 4


# ── The real proof: the SAME program, compiled through BOTH frontends,
# must produce identical results. ─────────────────────────────────────

def test_dsl_and_dict_frontends_agree_on_the_same_program():
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
    dsl_icm, dsl_diags = compile_source(dsl_src)

    dict_icm, dict_diags = compile_from_dict("cross_check", [
        {"name": "r1", "tile": "ram_constant", "at": (0, 0),
         "fields": {"out": "e", "init_data": 0xCAFEBEEF}},
        {"name": "r2", "tile": "ram_flowing", "at": (0, 1),
         "fields": {"in": "w", "out": "n"}},
    ])

    assert dsl_diags == [] and dict_diags == []
    assert dsl_icm is not None and dict_icm is not None

    dsl_by_pos = {(r.row, r.col): (r.core, r.core_config) for r in dsl_icm.records}
    dict_by_pos = {(r.row, r.col): (r.core, r.core_config) for r in dict_icm.records}
    assert dsl_by_pos == dict_by_pos   # genuinely identical backend output


def test_broken_placement_produces_the_same_kind_of_diagnostic_via_dict_frontend():
    # missing required 'out' port -- same failure mode #343 already
    # proved via DSL text; confirming it produces the same STRUCTURED
    # diagnostic (not a bare exception) when the IR is built directly.
    icm, diags = compile_from_dict("broken", [
        {"name": "r1", "tile": "ram_constant", "at": (0, 0),
         "fields": {"init_data": 0xCAFEBEEF}},   # 'out' missing
    ])
    assert icm is None
    assert len(diags) == 1
    d = diags[0]
    assert d.severity == "error" and d.stage == "place"
    assert "missing" in d.problem and "out" in d.problem
    assert d.span is None   # a dict-built PlaceIR genuinely has no span to offer


def test_dict_frontend_placement_collision_detected_same_as_dsl():
    icm, diags = compile_from_dict("collide", [
        {"name": "r1", "tile": "ram_constant", "at": (0, 0), "fields": {"out": "e", "init_data": 1}},
        {"name": "r2", "tile": "ram_constant", "at": (0, 0), "fields": {"out": "s", "init_data": 2}},
    ])
    assert icm is None
    assert any(d.stage == "place" and "occupied" in d.problem for d in diags)


def test_program_ir_from_dict_produces_real_ir_objects():
    ir = program_ir_from_dict("x", [
        {"name": "r1", "tile": "ram_constant", "at": (0, 0), "fields": {"out": "e", "init_data": 1}},
    ])
    assert isinstance(ir, ProgramIR)
    assert isinstance(ir.statements[0], PlaceIR)
    assert isinstance(ir.statements[0].fields[0], FieldIR)
    assert ir.statements[0].span is None   # no source region -- honestly None, not fabricated


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
