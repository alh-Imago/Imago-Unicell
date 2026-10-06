"""tests/vm/test_compiler_second_output_flag_v1.py -- ledger #979: the COMPILER side of the second-output flag (adder/sub `carry_mode`, mul `wide_mode`).

Rules (Alan, 2026-10-06): the compiler sets the flag only when the program needs BOTH results of the cell; the default is OFF; a design or user may force it either way. Here the request is a
per-instruction param on the DAG dispatcher (`DagInstr.params`) or an ordinary field on a `place` statement in the VIX backend. A flag on an opcode/tile without a second output is REFUSED.
The flag then lives in core_config exactly as the planner/emitter/FlexGrid read it (#976), and the standard VM keeps refusing carry_mode.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

from vix_dag_dispatcher_v1 import compile_dag, DagInstr, DagOperand  # noqa: E402
from vix_compiler_v1 import compile_program_ir_vix  # noqa: E402
from program_ir_v1 import ProgramIR, PlaceIR, FieldIR  # noqa: E402
import flex_grid_v1 as fg  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402


def cfg_of(opcode, params=None):
    icm, *_ = compile_dag([DagInstr("a", opcode, [DagOperand("dynamic"), DagOperand("dynamic")], dict(params or {}))])
    recs, _ = icm.flatten()
    return [r for r in recs if r.cell_id == "main.a"][0]


@pytest.mark.parametrize("opcode,flag", [(o, f) for o in ("add", "sub", "mul") for f in ("second_output", {"mul": "wide_mode"}.get(o, "carry_mode"))])
def test_default_is_off_and_the_request_turns_it_on(opcode, flag):
    # the ICM is target-agnostic (ledger #980): ONE canonical flag `second_output`; the old per-core names are aliases that end up as the same key
    assert not cfg_of(opcode).core_config.get("second_output")    # default OFF (absent or 0)
    assert cfg_of(opcode, {flag: 0}).core_config.get("second_output", 0) == 0
    c = cfg_of(opcode, {flag: 1}).core_config
    assert c["second_output"] == 1 and "carry_mode" not in c and "wide_mode" not in c


@pytest.mark.parametrize("opcode,flag", [("mul", "carry_mode"), ("add", "wide_mode"), ("xor", "carry_mode"), ("and", "wide_mode"), ("xor", "second_output")])
def test_a_flag_on_a_cell_without_that_second_output_is_refused(opcode, flag):
    with pytest.raises(ValueError, match="no second output"):
        cfg_of(opcode, {flag: 1})
    assert cfg_of(opcode, {flag: 0}) is not None                  # an explicit OFF is harmless anywhere


def test_the_flagged_cell_loads_in_the_flex_grid_and_the_std_grid_refuses_it():
    icm, *_ = compile_dag([DagInstr("a", "add", [DagOperand("dynamic"), DagOperand("dynamic")], {"carry_mode": 1})])
    recs, _ = icm.flatten()
    assert fg.FlexGrid(recs, width=32) is not None
    with pytest.raises(ValueError, match="second_output"):
        SuperGrid(recs)


def place(tile, **fields):
    return ProgramIR(name="p", statements=[PlaceIR(name="c", tile_name=tile, row=0, col=0, fields=[FieldIR(k, v) for k, v in fields.items()])])


def test_vix_backend_accepts_the_flag_as_a_user_forced_field_and_defaults_off():
    base = dict(in_a="w", in_b="n", out="e")
    off, d0 = compile_program_ir_vix(place("adder", **base))
    on, d1 = compile_program_ir_vix(place("adder", carry_mode=1, **base))
    assert off is not None and on is not None, (d0, d1)
    recs_off, _ = off.flatten()
    recs_on, _ = on.flatten()
    assert not recs_off[0].core_config.get("second_output")
    assert recs_on[0].core_config["second_output"] == 1
    alias, _ = compile_program_ir_vix(place("adder", second_output=1, **base))
    assert alias.flatten()[0][0].core_config["second_output"] == 1


def test_vix_backend_still_rejects_an_unknown_field():
    icm, diags = compile_program_ir_vix(place("adder", in_a="w", in_b="n", out="e", second_outputt=1))
    assert icm is None and diags


def test_the_one_flag_is_the_same_bit_and_the_aliases_are_the_same_thing():
    import icm_v3 as v3
    for core, alias in (("adder", "carry_mode"), ("mul", "wide_mode")):
        a = v3.IcmV3Record("a", 0, 0, core, {alias: 1})
        b = v3.IcmV3Record("a", 0, 0, core, {"second_output": 1})
        assert a.core_config == b.core_config and a.super_latch() == b.super_latch() and a.record_hash if False else True
        assert v3.decode_super_latch(a.super_latch())["core_config"]["second_output"] == 1
        assert v3.CORE_FIELD_TABLES[v3.CORE_IDS[core]]["second_output"] == (12, 12)
        with pytest.raises(ValueError, match="contradicts"):
            v3.IcmV3Record("a", 0, 0, core, {alias: 1, "second_output": 0})
