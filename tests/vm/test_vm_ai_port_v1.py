"""
test_vm_ai_port_v1.py — verifies the AI-interaction port
(`nano/vm_ai_port_v1.py`, `points.md #216` item 6/`#359`): compile ->
real ICM v3 -> real running VM -> real JSON introspection, all through
one clean object. Building and testing this end to end is what
surfaced a real, previously-undiscovered bug in `run_to_quiescence()`
(`#359`, its own regression tests live in `test_composed_tile_
library_v1.py` and `test_unicell_super_automaton_v1.py`) -- this file
covers the port's own surface specifically.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from vm_ai_port_v1 import VMSession, CompileFailure  # noqa: E402
from dsl_compiler_v1 import compile_source  # noqa: E402
from unicell_automaton_v1 import N, S  # noqa: E402


SENTINEL_DSL = """
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


def test_from_dsl_compiles_and_loads_a_real_running_grid():
    session = VMSession.from_dsl(SENTINEL_DSL)
    assert session.diagnostics == []
    assert len(session.grid.cells) == 3


def test_from_dsl_raises_compile_failure_with_real_diagnostics():
    broken = """
    program broken {
        place r1 as ram_constant at (0, 0) {
            init_data: 1
        }
    }
    """
    try:
        VMSession.from_dsl(broken)
    except CompileFailure as e:
        assert len(e.diagnostics) >= 1
        assert e.diagnostics[0].stage == "place"
        text = e.format(broken.splitlines())
        assert "missing" in text
    else:
        raise AssertionError("expected CompileFailure")


def test_from_python_compiles_and_loads():
    py_src = """
def prog():
    place("r1", "ram_constant", (0, 0), out="e", init_data=0xCAFEBEEF)
"""
    session = VMSession.from_python(py_src)
    d = session.describe_cell(0, 0)
    assert d["ram"]["data_reg"] == 0xCAFEBEEF


def test_from_icm_file_round_trips():
    icm, diags = compile_source("program p { place r1 as ram_constant at (0,0) { out: e init_data: 42 } }")
    assert diags == []
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "test.icm")
        icm.save(path)
        session = VMSession.from_icm_file(path)
        d = session.describe_cell(0, 0)
        assert d["ram"]["data_reg"] == 42


def test_deliver_drives_a_specific_cell_directly():
    session = VMSession.from_dsl(SENTINEL_DSL)
    accepted, forward = session.deliver(0, 0, {N: 1}, None)
    assert accepted is True
    d = session.describe_cell(0, 0)
    assert d["accumulator"]["total"] == 1


def test_deliver_raises_clear_error_for_an_empty_position():
    session = VMSession.from_dsl(SENTINEL_DSL)
    try:
        session.deliver(9, 9, {N: 1}, None)
    except KeyError as e:
        assert "(9,9)" in str(e)
    else:
        raise AssertionError("expected KeyError")


def test_tick_advances_and_describe_reflects_real_state():
    # the real end-to-end proof: compile, drive, run, inspect -- the
    # exact sentinel behavior sequence #340 already proved, now driven
    # entirely through the port's own clean surface.
    session = VMSession.from_dsl(SENTINEL_DSL)
    for _ in range(9):
        session.deliver(0, 0, {N: 1}, None)
    session.tick(15)

    d = session.describe()
    assert d["tick_count"] == 15
    assert d["cells"]["0,0"]["accumulator"]["total"] == 9
    assert d["cells"]["0,1"]["comparator"]["out_buffer"] == 1
    assert d["cells"]["0,2"]["latch"]["state"] is True

    # sticky behavior, same as #340's own acceptance test, now via the port
    for _ in range(5):
        session.deliver(0, 0, {S: 1}, None)
    session.tick(15)
    d2 = session.describe()
    assert d2["cells"]["0,0"]["accumulator"]["total"] == 4
    assert d2["cells"]["0,1"]["comparator"]["out_buffer"] == 0
    assert d2["cells"]["0,2"]["latch"]["state"] is True   # still sticky-set


def test_describe_output_is_genuinely_json_serializable():
    session = VMSession.from_dsl(SENTINEL_DSL)
    session.tick(3)
    text = json.dumps(session.describe())
    reloaded = json.loads(text)
    assert reloaded["tick_count"] == 3


def test_run_to_quiescence_propagates_the_real_fixed_behavior():
    # points.md #359: confirms the port's own wrapper genuinely gets
    # the fix, not a stale copy -- a continuously-live core times out
    # even with zero prior stimulus through this port specifically.
    session = VMSession.from_dsl(SENTINEL_DSL)
    try:
        session.run_to_quiescence(max_ticks=10)
    except TimeoutError:
        pass
    else:
        raise AssertionError("expected TimeoutError")


def test_diagnostics_text_renders_warnings_even_on_success():
    dupe_name_dsl = """
    program p {
        place r1 as ram_constant at (0, 0) { out: e init_data: 1 }
        place r1 as ram_constant at (0, 1) { out: e init_data: 2 }
    }
    """
    session = VMSession.from_dsl(dupe_name_dsl)
    assert len(session.diagnostics) == 1
    assert session.diagnostics[0].severity == "warning"
    text = session.diagnostics_text(dupe_name_dsl)
    assert "r1" in text


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
