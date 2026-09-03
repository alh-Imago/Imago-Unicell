"""tests/vm/test_llvm_ir_frontend_v1.py — points.md #611: real tests
for the first LLVM IR frontend. Every "does it compute the right
answer" test actually runs the real VM (injects, ticks, reads the real
cell state) rather than just checking the ICM compiled -- matching
this project's own "don't just check the format, run it" discipline,
doubly important here given how much of this module's own real
correctness came from tracing actual tick-by-tick VM behavior rather
than reasoning about it in the abstract.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

from llvm_ir_frontend_v1 import compile_llvm_ir  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from vm_ai_port_v1 import VMSession  # noqa: E402


def _run(source, argument_values, ticks=60):
    """Real, end-to-end helper: compile, load into a real grid, inject
    the real starting values, tick, and return the real computed value
    at the chain's own result cell (masked exactly like real 32-bit
    hardware -- the ICM/VM's own real representation)."""
    icm, diagnostics, info = compile_llvm_ir(source, argument_values)
    assert icm is not None, diagnostics
    grid = SuperGrid(icm.records)
    session = VMSession(grid)
    for row, col, value in info.injections:
        session.inject(row, col, value)
    for _ in range(ticks):
        grid.tick()
    cell = grid.cells[info.result_cell]
    return cell.adder_out_buffer, cell.adder_data_valid, info


# ── real, end-to-end correctness -- actually running the VM ─────────

def test_single_add_instruction():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = add i32 %x, 5
      ret i32 %t1
    }
    """
    out, valid, info = _run(ir, {"x": 3})
    assert valid is True
    assert out == 8
    assert info.expected_result == 8


def test_two_instruction_add_chain():
    """The real, original motivating test -- confirmed wrong (20
    instead of 18) through two earlier, real design mistakes before
    the injection-based fix made it correct."""
    ir = """
    define i32 @simple_chain(i32 %x) {
    entry:
      %t1 = add i32 %x, 5
      %t2 = add i32 %t1, 10
      ret i32 %t2
    }
    """
    out, valid, info = _run(ir, {"x": 3})
    assert valid is True
    assert out == 18


def test_sub_instruction():
    """Real, direct confirmation of the sub-as-negated-add fix -- this
    is the case that caught the real north/west arrival-order bug in
    the first place (subtract_mode alone gave the wrong operand
    order)."""
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = sub i32 %x, 3
      ret i32 %t1
    }
    """
    out, valid, info = _run(ir, {"x": 20})
    assert valid is True
    assert out == 17


def test_sub_result_wraps_correctly_when_negative():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = sub i32 %x, 100
      ret i32 %t1
    }
    """
    out, valid, info = _run(ir, {"x": 5})
    assert valid is True
    assert out == (5 - 100) & 0xFFFFFFFF
    signed = out - (1 << 32) if out >= (1 << 31) else out
    assert signed == -95


def test_longer_mixed_add_sub_chain():
    ir = """
    define i32 @f(i32 %x, i32 %y) {
    entry:
      %t1 = add i32 %x, %y
      %t2 = sub i32 %t1, 2
      %t3 = add i32 %t2, 100
      %t4 = sub i32 %t3, 7
      ret i32 %t4
    }
    """
    out, valid, info = _run(ir, {"x": 5, "y": 3})
    assert valid is True
    assert out == 99  # (5+3)-2+100-7


def test_negative_argument_value():
    ir = """
    define i32 @f(i32 %x, i32 %y) {
    entry:
      %t1 = add i32 %x, %y
      %t2 = sub i32 %t1, 2
      %t3 = add i32 %t2, 100
      %t4 = sub i32 %t3, 7
      ret i32 %t4
    }
    """
    out, valid, info = _run(ir, {"x": -10, "y": 50})
    assert valid is True
    assert out == 131  # (-10+50)-2+100-7


def test_injections_are_exactly_what_was_used():
    """Real, direct confirmation the returned injection plan is
    complete and correct -- not just that the end result happens to be
    right."""
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = add i32 %x, 5
      ret i32 %t1
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 3})
    assert diagnostics == []
    values = {v for (_, _, v) in info.injections}
    assert 3 in values
    assert 5 in values
    assert len(info.injections) == 2  # west feeder (x) + north feeder (5)


# ── real diagnostics -- clear, honest rejections, never silent wrongness ──

def test_multiple_functions_rejected():
    ir = """
    define i32 @f(i32 %x) { entry: ret i32 %x }
    define i32 @g(i32 %x) { entry: ret i32 %x }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 1})
    assert icm is None
    assert any("one function" in d.problem for d in diagnostics)


def test_multiple_basic_blocks_rejected():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      br label %next
    next:
      ret i32 %x
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 1})
    assert icm is None
    assert any("basic block" in d.problem for d in diagnostics)


def test_missing_argument_value_rejected():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = add i32 %x, 5
      ret i32 %t1
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {})
    assert icm is None
    assert any("compile-time value" in d.problem for d in diagnostics)


def test_unsupported_opcode_rejected():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = mul i32 %x, 5
      ret i32 %t1
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 3})
    assert icm is None
    assert any("mul" in d.problem for d in diagnostics)


def test_non_chain_dag_rejected():
    """The real, explicitly-deferred general-DAG case -- t3 references
    BOTH t1 and t2 directly, not a genuine linear chain. Must be
    rejected with a clear, real diagnostic, never silently miscompiled."""
    ir = """
    define i32 @f(i32 %x, i32 %y) {
    entry:
      %t1 = add i32 %x, 1
      %t2 = add i32 %y, 2
      %t3 = add i32 %t1, %t2
      ret i32 %t3
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 1, "y": 2})
    assert icm is None
    assert any("LINEAR ACCUMULATION CHAIN" in d.why for d in diagnostics)


def test_ret_of_non_final_value_rejected():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = add i32 %x, 5
      %t2 = add i32 %t1, 10
      ret i32 %t1
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 3})
    assert icm is None
    assert any("chain's own final result" in d.problem for d in diagnostics)


def test_invalid_llvm_ir_rejected_cleanly():
    icm, diagnostics, info = compile_llvm_ir("this is not real LLVM IR", {})
    assert icm is None
    assert diagnostics  # a real parse error, not a crash


def test_empty_function_body_rejected():
    ir = """
    define i32 @f() {
    entry:
      ret i32 0
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {})
    assert icm is None
    assert any("no real instructions" in d.problem for d in diagnostics)
