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


def _run_shift(source, argument_values, ticks=30):
    """Same real end-to-end discipline as `_run()`, but for shl/lshr
    (#690): their own result cell is a real `ram` core (the sink cell
    that captures the shift addon's OWN offered value, not the shift
    cell itself -- the addon chain applies at offer time, not by
    mutating a cell's stored register, #690's own real finding)."""
    icm, diagnostics, info = compile_llvm_ir(source, argument_values)
    assert icm is not None, diagnostics
    grid = SuperGrid(icm.records)
    session = VMSession(grid)
    for row, col, value in info.injections:
        session.inject(row, col, value)
    for _ in range(ticks):
        grid.tick()
    cell = grid.cells[info.result_cell]
    return cell.ram_data_reg, cell.ram_data_valid, info


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


# ── real icmp support (points.md #613) ──────────────────────────────

def _run_icmp(source, argument_values, ticks=40):
    """Real, end-to-end helper for icmp -- the result cell is a
    comparator, not an adder, so it reads a different real field."""
    icm, diagnostics, info = compile_llvm_ir(source, argument_values)
    assert icm is not None, diagnostics
    grid = SuperGrid(icm.records)
    session = VMSession(grid)
    for row, col, value in info.injections:
        session.inject(row, col, value)
    for _ in range(ticks):
        grid.tick()
    cell = grid.cells[info.result_cell]
    return cell.cmp_out_buffer, cell.cmp_data_valid, info


def _icmp_ir(pred):
    return f"""
    define i1 @f(i32 %x) {{
    entry:
      %c = icmp {pred} i32 %x, 5
      ret i1 %c
    }}
    """


def test_icmp_sge_all_boundary_cases():
    ir = _icmp_ir("sge")
    assert _run_icmp(ir, {"x": 10})[0] == 1
    assert _run_icmp(ir, {"x": 5})[0] == 1   # boundary: equal counts as >=
    assert _run_icmp(ir, {"x": 3})[0] == 0


def test_icmp_sgt_all_boundary_cases():
    ir = _icmp_ir("sgt")
    assert _run_icmp(ir, {"x": 10})[0] == 1
    assert _run_icmp(ir, {"x": 5})[0] == 0   # boundary: equal is NOT >
    assert _run_icmp(ir, {"x": 3})[0] == 0


def test_icmp_slt_all_boundary_cases():
    ir = _icmp_ir("slt")
    assert _run_icmp(ir, {"x": 10})[0] == 0
    assert _run_icmp(ir, {"x": 5})[0] == 0   # boundary: equal is NOT <
    assert _run_icmp(ir, {"x": 3})[0] == 1


def test_icmp_sle_all_boundary_cases():
    ir = _icmp_ir("sle")
    assert _run_icmp(ir, {"x": 10})[0] == 0
    assert _run_icmp(ir, {"x": 5})[0] == 1   # boundary: equal counts as <=
    assert _run_icmp(ir, {"x": 3})[0] == 1


def test_icmp_mid_chain_reads_running_value():
    """Real, direct confirmation icmp correctly reads the chain's own
    running value through multiple prior instructions, not just a
    bare argument."""
    ir = """
    define i1 @f(i32 %x, i32 %y) {
    entry:
      %t1 = add i32 %x, %y
      %t2 = sub i32 %t1, 3
      %c = icmp sgt i32 %t2, 10
      ret i1 %c
    }
    """
    out, valid, info = _run_icmp(ir, {"x": 5, "y": 8})   # (5+8)-3=10, 10>10=False
    assert out == 0
    out2, valid2, info2 = _run_icmp(ir, {"x": 5, "y": 10})  # (5+10)-3=12, 12>10=True
    assert out2 == 1


# ═══════════════════════════════════════════════════════════════════════
# points.md #668: icmp eq/ne, promoted from #613's own honestly-
# rejected placeholder to a real, working 6/8-cell composition --
# diff -> two comparators (threshold 0 and 1) -> XOR gives eq exactly
# (true only when diff==0); ne reuses the same eq composition, then
# XORs its own clean 0/1 result against a real, one-time-injected
# constant 1 for an exact boolean NOT. A real, hard-won finding along
# the way: nano's own two-arrival gate OR-combines two same-tick
# arrivals from different sources into ONE event rather than treating
# them as separate sequential operands, so the two comparator outputs
# need deliberately unequal hop counts to land on genuinely different
# ticks -- the same real fact #611's own west/north injection stagger
# already had to work around, now confirmed to generalize to this
# shape too.
# ═══════════════════════════════════════════════════════════════════════

def _run_eq_ne(pred, x, y, ticks=40):
    ir = f"""
    define i1 @f(i32 %x) {{
    entry:
      %c = icmp {pred} i32 %x, {y}
      ret i1 %c
    }}
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": x})
    assert icm is not None, diagnostics
    grid = SuperGrid(icm.records)
    for row, col, value in info.injections:
        grid.inject(row, col, value)
    for _ in range(ticks):
        grid.tick()
    return grid.cells[info.result_cell]._nano.out_buffer, info


def test_icmp_eq_all_real_cases():
    for x, y, expected in [(5, 5, 1), (5, 8, 0), (8, 5, 0), (0, 0, 1), (100, 100, 1), (3, 4, 0)]:
        result, info = _run_eq_ne("eq", x, y)
        assert result == expected, f"eq({x},{y}) = {result}, expected {expected}"


def test_icmp_ne_all_real_cases():
    for x, y, expected in [(5, 5, 0), (5, 8, 1), (8, 5, 1), (0, 0, 0), (100, 100, 0), (3, 4, 1)]:
        result, info = _run_eq_ne("ne", x, y)
        assert result == expected, f"ne({x},{y}) = {result}, expected {expected}"


def test_icmp_ne_gives_a_clean_boolean_not_a_bitwise_one():
    """Points.md #668: the real bug found and fixed -- TOPO_XNOR alone
    gives 0xFFFFFFFE/0xFFFFFFFF (a genuine bitwise not-XOR over all 32
    bits), not a clean 0/1. This is the regression test for that fix."""
    result, _ = _run_eq_ne("ne", 5, 8)
    assert result == 1, f"expected a clean boolean 1, got {result!r} (0xFFFFFFFF would indicate the bitwise-NOT regression)"
    result0, _ = _run_eq_ne("ne", 5, 5)
    assert result0 == 0, f"expected a clean boolean 0, got {result0!r} (0xFFFFFFFE would indicate the bitwise-NOT regression)"


def test_icmp_eq_ne_rejected_mid_chain():
    """Points.md #668: eq/ne's own real result lands on a different
    physical row than the ordinary chain convention -- using it mid-
    chain (not as the final, returned instruction) must be rejected
    with a clear diagnostic, not silently wired to the wrong cell."""
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %c = icmp eq i32 %x, 5
      %r = add i32 %x, 1
      ret i32 %r
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 5})
    assert icm is None
    assert any("mid-chain" in d.problem for d in diagnostics)


def test_icmp_unsupported_predicate_still_honestly_rejected():
    """Real, necessary regression -- #668 must not have accidentally
    widened the honest-rejection net to swallow a genuinely
    unsupported predicate along with eq/ne."""
    ir = """
    define i1 @f(i32 %x) {
    entry:
      %c = icmp ugt i32 %x, 5
      ret i1 %c
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 5})
    assert icm is None
    assert any("ugt" in d.problem for d in diagnostics)


def test_icmp_negative_values():
    ir = _icmp_ir("slt")
    out, valid, info = _run_icmp(ir, {"x": -100})
    assert out == 1  # -100 < 5


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


# ═══════════════════════════════════════════════════════════════════════
# points.md #652/#653: the real, narrow single counting-loop shape,
# lowered to #638/#649/#652's own real, proven 4-cell bounded-loop-ring
# tiles. Every test actually runs the real VM (the SAME per-round
# protocol #649/#652's own tests already established), not just
# checking the ICM compiled.
# ═══════════════════════════════════════════════════════════════════════

_COUNT_LOOP_IR = """
define i32 @count(i32 %n) {{
entry:
  br label %loop
loop:
  %i = phi i32 [ {seed}, %entry ], [ %i.next, %loop ]
  %i.next = add i32 %i, {step}
  %cond = icmp slt i32 %i, %n
  br i1 %cond, label %loop, label %exit
exit:
  ret i32 %i
}}
"""


def _run_loop(source, argument_values):
    """Real, end-to-end helper, the SAME per-round protocol #649/#652's
    own tests already established: entry-seed (two real arrivals),
    then repeatedly inject the real bound into LOOP_CTRL, and if it
    routes CONTINUE, inject the real increment into ADDER and consume
    the real result into LOOPVAR (a_update_in, asserted BEFORE the
    value lands -- #636's own real sequencing lesson) before reemitting
    for the next round."""
    icm, diagnostics, info = compile_llvm_ir(source, argument_values)
    assert icm is not None, diagnostics
    grid = SuperGrid(icm.records)
    loopvar_ca = grid.cells[info.loopvar_pos]._nano
    loop_ctrl_ca = grid.cells[info.loop_ctrl_pos]._nano
    adder = grid.cells[info.adder_pos]
    lv_r, lv_c = info.loopvar_pos
    lc_r, lc_c = info.loop_ctrl_pos
    ad_r, ad_c = info.adder_pos

    grid.inject(lv_r, lv_c, info.entry_seed_value)
    grid.run_to_quiescence()
    grid.inject(lv_r, lv_c, 0xDEADBEEF)
    grid.run_to_quiescence()

    rounds = 0
    while True:
        grid.inject(lc_r, lc_c, info.bound_value)
        grid.run_to_quiescence()
        if not (adder.adder_a_arrived and not loop_ctrl_ca.a_arrived):
            break
        loopvar_ca.a_update_in = True
        grid.inject(ad_r, ad_c, info.increment_value)
        grid.run_to_quiescence()
        loopvar_ca.a_update_in = False
        loopvar_ca.a_reemit_in = True
        grid.inject(lv_r, lv_c, 0xFFFFFFFF)
        grid.run_to_quiescence()
        loopvar_ca.a_reemit_in = False
        rounds += 1
        assert rounds <= 1000, "real bug: exceeded 1000 rounds, likely an infinite loop"

    return loopvar_ca.a_data, rounds, info


def test_loop_basic_count_to_three():
    out, rounds, info = _run_loop(_COUNT_LOOP_IR.format(seed=0, step=1), {"n": 3})
    assert out == 3 == info.expected_final_value
    assert rounds == 3 == info.expected_continue_rounds


def test_loop_different_bound():
    out, rounds, info = _run_loop(_COUNT_LOOP_IR.format(seed=0, step=1), {"n": 5})
    assert out == 5 == info.expected_final_value
    assert rounds == 5


def test_loop_zero_iterations_edge_case():
    out, rounds, info = _run_loop(_COUNT_LOOP_IR.format(seed=0, step=1), {"n": 0})
    assert out == 0 == info.expected_final_value
    assert rounds == 0


def test_loop_single_iteration_edge_case():
    out, rounds, info = _run_loop(_COUNT_LOOP_IR.format(seed=0, step=1), {"n": 1})
    assert out == 1 == info.expected_final_value
    assert rounds == 1


def test_loop_literal_bound_instead_of_argument():
    ir = """
    define i32 @count_lit() {
    entry:
      br label %loop
    loop:
      %i = phi i32 [ 0, %entry ], [ %i.next, %loop ]
      %i.next = add i32 %i, 1
      %cond = icmp slt i32 %i, 4
      br i1 %cond, label %loop, label %exit
    exit:
      ret i32 %i
    }
    """
    out, rounds, info = _run_loop(ir, {})
    assert out == 4 == info.expected_final_value


def test_loop_nonzero_entry_seed():
    out, rounds, info = _run_loop(_COUNT_LOOP_IR.format(seed=5, step=1), {"n": 8})
    assert out == 8 == info.expected_final_value
    assert rounds == 3


def test_loop_step_by_two():
    out, rounds, info = _run_loop(_COUNT_LOOP_IR.format(seed=0, step=2), {"n": 10})
    assert out == 10 == info.expected_final_value
    assert rounds == 5


def test_loop_wrong_block_count_rejected():
    ir = """
    define i32 @f(i32 %n) {
    a:
      br label %b
    b:
      br label %c
    c:
      br label %d
    d:
      ret i32 %n
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"n": 3})
    assert icm is None
    assert any("expected exactly 1" in d.problem and "exactly 3" in d.problem for d in diagnostics)


def test_loop_wrong_predicate_rejected():
    ir = """
    define i32 @bad(i32 %n) {
    entry:
      br label %loop
    loop:
      %i = phi i32 [ 0, %entry ], [ %i.next, %loop ]
      %i.next = add i32 %i, 1
      %cond = icmp sgt i32 %n, %i
      br i1 %cond, label %loop, label %exit
    exit:
      ret i32 %i
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"n": 3})
    assert icm is None
    assert any("predicate" in d.problem for d in diagnostics)


def test_loop_nonliteral_entry_seed_rejected():
    ir = """
    define i32 @bad(i32 %start, i32 %n) {
    entry:
      br label %loop
    loop:
      %i = phi i32 [ %start, %entry ], [ %i.next, %loop ]
      %i.next = add i32 %i, 1
      %cond = icmp slt i32 %i, %n
      br i1 %cond, label %loop, label %exit
    exit:
      ret i32 %i
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"start": 0, "n": 3})
    assert icm is None
    assert any("literal compile-time constant" in d.problem for d in diagnostics)


def test_loop_postincrement_check_rejected_with_clear_diagnostic():
    """Real, deliberate negative test: checking %i.next (post-increment)
    instead of %i (the phi's own pre-increment value) does NOT match
    #638/#649/#652's own real, proven hardware -- must be rejected with
    a clear diagnostic, not silently mis-lowered."""
    ir = """
    define i32 @bad(i32 %n) {
    entry:
      br label %loop
    loop:
      %i = phi i32 [ 0, %entry ], [ %i.next, %loop ]
      %i.next = add i32 %i, 1
      %cond = icmp slt i32 %i.next, %n
      br i1 %cond, label %loop, label %exit
    exit:
      ret i32 %i.next
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"n": 3})
    assert icm is None
    assert any("pre-increment" in d.problem for d in diagnostics)


# ═══════════════════════════════════════════════════════════════════════
# points.md #661: the real descending-loop counterpart -- sub paired
# with icmp sgt, lowered to nano_loop_ctrl_desc + subtractor. Every
# test actually runs the real VM, same discipline as the ascending
# suite above.
# ═══════════════════════════════════════════════════════════════════════

_COUNTDOWN_LOOP_IR = """
define i32 @countdown(i32 %n) {{
entry:
  br label %loop
loop:
  %i = phi i32 [ {seed}, %entry ], [ %i.next, %loop ]
  %i.next = sub i32 %i, {step}
  %cond = icmp sgt i32 %i, %n
  br i1 %cond, label %loop, label %exit
exit:
  ret i32 %i
}}
"""


def test_descending_loop_basic_countdown():
    out, rounds, info = _run_loop(_COUNTDOWN_LOOP_IR.format(seed=10, step=1), {"n": 7})
    assert out == 7 == info.expected_final_value
    assert rounds == 3 == info.expected_continue_rounds


def test_descending_loop_zero_iterations_edge_case():
    out, rounds, info = _run_loop(_COUNTDOWN_LOOP_IR.format(seed=5, step=1), {"n": 5})
    assert out == 5 == info.expected_final_value
    assert rounds == 0


def test_descending_loop_step_by_two():
    out, rounds, info = _run_loop(_COUNTDOWN_LOOP_IR.format(seed=20, step=2), {"n": 10})
    assert out == 10 == info.expected_final_value
    assert rounds == 5


def test_descending_loop_mismatched_add_with_sgt_rejected():
    """A real, deliberate mismatch: `add` (ascending shape) paired with
    `icmp sgt` (descending predicate) matches neither real supported
    combination -- must be rejected with a clear diagnostic."""
    ir = """
    define i32 @bad(i32 %n) {
    entry:
      br label %loop
    loop:
      %i = phi i32 [ 0, %entry ], [ %i.next, %loop ]
      %i.next = add i32 %i, 1
      %cond = icmp sgt i32 %i, %n
      br i1 %cond, label %loop, label %exit
    exit:
      ret i32 %i
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"n": 3})
    assert icm is None
    assert any("expected" in d.problem and "sgt" in d.problem for d in diagnostics)


def test_descending_loop_mismatched_sub_with_slt_rejected():
    ir = """
    define i32 @bad(i32 %n) {
    entry:
      br label %loop
    loop:
      %i = phi i32 [ 10, %entry ], [ %i.next, %loop ]
      %i.next = sub i32 %i, 1
      %cond = icmp slt i32 %i, %n
      br i1 %cond, label %loop, label %exit
    exit:
      ret i32 %i
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"n": 3})
    assert icm is None
    assert any("expected" in d.problem and "sgt" in d.problem for d in diagnostics)


# ═══════════════════════════════════════════════════════════════════════
# points.md #674: select (LLVM's own ternary), the remaining half of
# the standing "promote select + icmp eq to Tier-1" task (#668 covered
# eq/ne). result = cond ? true_val : false_val, lowered to a real
# 5-cell composition: mask = 0 - cond (broadcasts a bare 0/1 boolean to
# a full 0x0/0xFFFFFFFF word), not_mask = XOR(mask, 0xFFFFFFFF), then
# AND_TRUE/AND_FALSE gate true_val/false_val by mask/not_mask, OR
# combines them.
#
# A real, hard-won lesson from building this, worth keeping in mind for
# anything built after it: an earlier version of this composition
# passed under artificially-sequenced test timing (values injected one
# at a time with pauses between them) and then failed outright once
# tested under REAL injection timing (every value delivered up front,
# matching how the frontend's own `injections` list is actually
# applied) -- an added relay meant to stagger one path had accidentally
# made two naturally-unequal hop counts equal again, silently
# reintroducing the exact same-tick convergence bug #668 already found
# once. The fix was leaving the natural 2-vs-3 hop asymmetry alone, not
# "correcting" it.
# ═══════════════════════════════════════════════════════════════════════

def _run_select(x, y, predicate, ticks=60):
    ir = f"""
    define i32 @f(i32 %x) {{
    entry:
      %c = icmp {predicate} i32 %x, {y}
      %r = select i1 %c, i32 %x, i32 {y}
      ret i32 %r
    }}
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": x})
    assert icm is not None, diagnostics
    grid = SuperGrid(icm.records)
    for row, col, value in info.injections:
        grid.inject(row, col, value)
    for _ in range(ticks):
        grid.tick()
    return grid.cells[info.result_cell]._nano.out_buffer


def test_select_real_cases_across_predicates():
    cases = [
        (10, 5, "sgt", 10), (3, 5, "sgt", 5), (5, 5, "sgt", 5),
        (10, 5, "slt", 5), (3, 5, "slt", 3),
        (100, 100, "sle", 100), (100, 99, "sge", 100),
    ]
    for x, y, pred, expect in cases:
        result = _run_select(x, y, pred)
        assert result == expect, f"select(x={x}, {pred}, y={y}) = {result}, expected {expect}"


def test_select_handles_a_real_negative_two_complement_value():
    result = _run_select(0xFFFFFFFF, 5, "sge")   # x as -1 signed; -1 >= 5 is false
    assert result == 5


# ── points.md #688: select/icmp_eq/icmp_ne promoted to the real,
# registered composed tiles (#686), their own internal constants now
# seeded via the ICM v3 file-format preload mechanism (#687) rather
# than manually, precisely-timed live injection. ──────────────────────

def test_select_no_longer_needs_runtime_injection_for_its_own_constants():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %c = icmp sgt i32 %x, 5
      %r = select i1 %c, i32 100, i32 200
      ret i32 %r
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 10})
    assert icm is not None
    # Only the icmp's own real comparison constant (5) and argument
    # (x=10) remain -- select's own internal 0/0xFFFFFFFF/100/200 are
    # NOT in this list at all anymore; they're preloaded directly.
    injected_values = {v for _, _, v in info.injections}
    assert 100 not in injected_values
    assert 200 not in injected_values
    assert 0xFFFFFFFF not in injected_values


def test_select_constants_are_real_preloads_on_the_compiled_records():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %c = icmp sgt i32 %x, 5
      %r = select i1 %c, i32 100, i32 200
      ret i32 %r
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 10})
    preloaded = {r.preload_value for r in icm.records if r.preload_value is not None}
    assert preloaded == {0, 0xFFFFFFFF, 100, 200}


def test_icmp_ne_no_longer_needs_runtime_injection_for_its_own_constant():
    ir = """
    define i1 @f(i32 %x) {
    entry:
      %c = icmp ne i32 %x, 5
      ret i1 %c
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 7})
    assert icm is not None
    injected_values = {v for _, _, v in info.injections}
    # the real, one-time constant `1` icmp_ne's own final XOR needs is
    # no longer a live injection -- it's a real preload now.
    preloaded = {r.preload_value for r in icm.records if r.preload_value is not None}
    assert 1 in preloaded
    assert icm.records  # sanity: real records still produced


def test_select_rejected_mid_chain():
    """Points.md #674: select's own real result lands on a different
    physical row than the ordinary chain convention -- using it mid-
    chain must be rejected with a clear diagnostic, matching #668's
    own real restriction for eq/ne."""
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %c = icmp sgt i32 %x, 5
      %r = select i1 %c, i32 %x, i32 5
      %r2 = add i32 %r, 1
      ret i32 %r2
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 10})
    assert icm is None
    assert any("mid-chain" in d.problem for d in diagnostics)


def test_select_requires_cond_from_the_immediately_preceding_ordinary_icmp():
    """Points.md #674: a select whose cond doesn't come directly from
    the immediately preceding ordinary icmp must be rejected -- here
    hit indirectly via #668's own 'eq must be final' rule, since any
    chain pairing eq/ne with a following select is already invalid on
    those terms first."""
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %c = icmp eq i32 %x, 5
      %r = select i1 %c, i32 %x, i32 5
      ret i32 %r
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 5})
    assert icm is None
    assert len(diagnostics) > 0


# ═══════════════════════════════════════════════════════════════════════
# points.md #690: shl/lshr, real and buildable now that shift_fine_
# addon_v1/shift_lane_addon_v2 (#683/#684) exist in real hardware.
# Every "does it compute the right answer" test actually runs the real
# VM, same discipline as every other opcode in this file.
# ═══════════════════════════════════════════════════════════════════════

def test_shl_single_instruction():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %r = shl i32 %x, 11
      ret i32 %r
    }
    """
    out, valid, info = _run_shift(ir, {"x": 3})
    assert valid is True
    assert out == (3 << 11) & 0xFFFFFFFF


def test_lshr_single_instruction():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %r = lshr i32 %x, 11
      ret i32 %r
    }
    """
    out, valid, info = _run_shift(ir, {"x": 0x80000000})
    assert valid is True
    assert out == (0x80000000 >> 11) & 0xFFFFFFFF


def test_shl_lshr_real_cases_across_the_full_0_31_range():
    # Real, direct confirmation the coarse+fine decomposition covers
    # every real amount, not just the 9 coarse taps -- 11, 19, 27 are
    # each only reachable via a real fine correction.
    cases = [0, 1, 3, 5, 7, 11, 15, 19, 23, 27, 31]
    for amount in cases:
        ir_shl = f"""
        define i32 @f(i32 %x) {{
        entry:
          %r = shl i32 %x, {amount}
          ret i32 %r
        }}
        """
        out, valid, _ = _run_shift(ir_shl, {"x": 0x12345678})
        expected = (0x12345678 << amount) & 0xFFFFFFFF
        assert out == expected, f"shl by {amount}: got {out:#x}, expected {expected:#x}"

        ir_lshr = f"""
        define i32 @f(i32 %x) {{
        entry:
          %r = lshr i32 %x, {amount}
          ret i32 %r
        }}
        """
        out2, valid2, _ = _run_shift(ir_lshr, {"x": 0xFEDCBA98})
        expected2 = (0xFEDCBA98 >> amount) & 0xFFFFFFFF
        assert out2 == expected2, f"lshr by {amount}: got {out2:#x}, expected {expected2:#x}"


def test_shl_then_add_chained():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %a = shl i32 %x, 4
      %r = add i32 %a, 7
      ret i32 %r
    }
    """
    out, valid, info = _run(ir, {"x": 3})
    assert valid is True
    assert out == ((3 << 4) + 7) & 0xFFFFFFFF


def test_add_then_shl_chained():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %a = add i32 %x, 5
      %r = shl i32 %a, 3
      ret i32 %r
    }
    """
    out, valid, info = _run_shift(ir, {"x": 10})
    assert valid is True
    assert out == ((10 + 5) << 3) & 0xFFFFFFFF


def test_shl_amount_out_of_range_gives_a_real_diagnostic():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %r = shl i32 %x, 32
      ret i32 %r
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 1})
    assert icm is None
    assert any("0-31" in d.problem for d in diagnostics)


def test_ashr_amount_4_no_longer_rejected():
    # points.md #705: this exact scenario used to be the real,
    # confirmed hardware-gap rejection -- now genuinely supported via
    # the sign-magnitude composition (#702/#703). Kept as a real
    # regression marker for that specific change, not just deleted.
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %r = ashr i32 %x, 4
      ret i32 %r
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 1})
    assert icm is not None, diagnostics


# ═══════════════════════════════════════════════════════════════════════
# points.md #700/#701: general DAG data flow -- the "actual hard,
# unsolved part" this frontend's own docstring has named since #610.
# Real, deliberately narrow first pass: an add/sub instruction may
# reference ANY earlier add/sub result, not just the immediately
# preceding one, using #700's own real hold+trigger mechanism
# (promoted to the real `nano_hold_trigger` tile, #701). Every "does it
# compute the right answer" test actually runs the real VM.
# ═══════════════════════════════════════════════════════════════════════

def _run_dag(source, argument_values, ticks=400):
    icm, diagnostics, info = compile_llvm_ir(source, argument_values)
    assert icm is not None, diagnostics
    grid = SuperGrid(icm.records)
    for row, col, value in info.injections:
        grid.inject(row, col, value)
    for _ in range(ticks):
        grid.tick()
    cell = grid.cells[info.result_cell]
    return cell.adder_out_buffer, cell.adder_data_valid, info


def test_dag_reference_to_a_non_adjacent_earlier_add_result():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = add i32 %x, 5
      %t2 = add i32 %t1, 10
      %t3 = add i32 %t1, 3
      ret i32 %t3
    }
    """
    for x, expected in [(10, 18), (0, 8), (100, 108), (7, 15)]:
        out, valid, info = _run_dag(ir, {"x": x})
        assert valid is True
        assert out == expected, f"x={x}: got {out}, expected {expected}"
        assert info.expected_result == expected


def test_dag_reference_holds_and_only_delivers_on_the_real_explicit_trigger():
    """Real, direct confirmation this isn't an accidental instant
    pass-through: inspects the drop cell's own internal nano state
    directly across many ticks, confirming it holds the real relayed
    value the whole time before the program's own real trigger fires."""
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = add i32 %x, 1
      %t2 = add i32 %t1, 2
      %t3 = add i32 %t2, 3
      %t4 = add i32 %t3, 4
      %t5 = add i32 %t1, 100
      ret i32 %t5
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 5})
    assert icm is not None, diagnostics
    grid = SuperGrid(icm.records)
    for row, col, value in info.injections:
        grid.inject(row, col, value)
    drop_pos = next((r.row, r.col) for r in icm.records if "relay_drop" in r.cell_id)
    for t in range(1, 60):
        grid.tick()
        if t == 20:
            drop_state = grid.cells[drop_pos]._nano
            assert drop_state.a_arrived is True
            assert drop_state.a_data == 6   # x+1
    cell = grid.cells[info.result_cell]
    assert cell.adder_out_buffer == 106
    assert cell.adder_data_valid is True


def test_dag_reference_with_sub_on_both_ends():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = sub i32 %x, 3
      %t2 = add i32 %t1, 100
      %t3 = sub i32 %t1, 1
      ret i32 %t3
    }
    """
    out, valid, info = _run_dag(ir, {"x": 20})
    assert valid is True
    assert out == 16


def test_two_non_overlapping_dag_references_in_one_function():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = add i32 %x, 1
      %t2 = add i32 %t1, 2
      %t3 = add i32 %t1, 100
      %t4 = add i32 %t3, 1
      %t5 = add i32 %t4, 1
      %t6 = add i32 %t5, 2
      %t7 = add i32 %t5, 200
      ret i32 %t7
    }
    """
    out, valid, info = _run_dag(ir, {"x": 5})
    assert valid is True
    assert out == 308


def test_dag_reference_to_a_non_add_sub_producer_gives_a_specific_diagnostic():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = shl i32 %x, 2
      %t2 = add i32 %t1, 5
      %t3 = add i32 %t1, 10
      ret i32 %t3
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 3})
    assert icm is None
    assert any("deliberately narrow" in d.why for d in diagnostics)


def test_multiple_consumers_of_the_same_producer_rejected_with_specific_diagnostic():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = add i32 %x, 1
      %t2 = add i32 %t1, 2
      %t3 = add i32 %t1, 100
      %t4 = add i32 %t3, 3
      %t5 = add i32 %t1, 1000
      ret i32 %t5
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 5})
    assert icm is None
    assert any("already tapped by an earlier DAG reference" in d.problem for d in diagnostics)


def test_overlapping_dag_reference_ranges_rejected_with_specific_diagnostic():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = add i32 %x, 1
      %t2 = add i32 %t1, 2
      %t3 = add i32 %t1, 100
      %t4 = add i32 %t2, 200
      %t5 = add i32 %t4, 1
      ret i32 %t5
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": 5})
    assert icm is None
    assert any("overlaps an earlier one" in d.problem for d in diagnostics)


# ═══════════════════════════════════════════════════════════════════════
# points.md #705: ashr wired into the frontend for real -- Alan's own
# sign-magnitude composition (#702/#703) via branch + reconvergence,
# no new RTL. Real, honest scope: nibble-aligned shift amounts only
# (0, 4, 8, ..., 28) -- the lost-bit detection stage's own real
# hardware granularity (nibble_mask, 4 bits) can't precisely extract a
# non-nibble-aligned bit range, confirmed directly by an early attempt
# at amount=1 giving a silently wrong answer.
# ═══════════════════════════════════════════════════════════════════════

def _run_ashr_frontend(x, n, ticks=60):
    ir = f"""
    define i32 @f(i32 %x) {{
    entry:
      %r = ashr i32 %x, {n}
      ret i32 %r
    }}
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": x})
    assert icm is not None, diagnostics
    grid = SuperGrid(icm.records)
    for row, col, value in info.injections:
        grid.inject(row, col, value)
    for _ in range(ticks):
        grid.tick()
    cell = grid.cells[info.result_cell]
    return cell.ram_data_reg, cell.ram_data_valid, info


def _real_ashr(x, n, bits=32):
    x &= (1 << bits) - 1
    if x >= (1 << (bits - 1)):
        x -= (1 << bits)
    return (x >> n) & ((1 << bits) - 1)


def test_ashr_negative_value_nibble_aligned():
    out, valid, info = _run_ashr_frontend(-80, 4)
    assert valid is True
    assert out == _real_ashr(-80, 4) == info.expected_result


def test_ashr_positive_value_nibble_aligned():
    out, valid, info = _run_ashr_frontend(20, 4)
    assert valid is True
    assert out == _real_ashr(20, 4)


def test_ashr_zero():
    out, valid, info = _run_ashr_frontend(0, 4)
    assert valid is True
    assert out == 0


def test_ashr_shift_by_zero_is_identity():
    out, valid, info = _run_ashr_frontend(-12345, 0)
    assert valid is True
    assert out == _real_ashr(-12345, 0) == (-12345) & 0xFFFFFFFF


def test_ashr_real_sweep_nibble_aligned_amounts():
    for x in [-80, 20, 0, -5, -2147483648, -1, -16, -17, -100, 5, 100, 2147483647]:
        for n in (0, 4, 8, 12, 16, 20, 24, 28):
            out, valid, info = _run_ashr_frontend(x, n)
            expected = _real_ashr(x, n)
            assert valid is True, f"x={x} n={n}: not valid"
            assert out == expected, f"x={x} n={n}: got {out:#x}, expected {expected:#x}"


def test_ashr_non_nibble_aligned_amount_gives_a_specific_diagnostic():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %r = ashr i32 %x, 1
      ret i32 %r
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": -5})
    assert icm is None
    assert any("not nibble-aligned" in d.problem for d in diagnostics)


def test_ashr_chained_after_add():
    ir = """
    define i32 @f(i32 %x) {
    entry:
      %t1 = add i32 %x, 100
      %t2 = ashr i32 %t1, 4
      ret i32 %t2
    }
    """
    icm, diagnostics, info = compile_llvm_ir(ir, {"x": -200})
    assert icm is not None, diagnostics
    grid = SuperGrid(icm.records)
    for row, col, value in info.injections:
        grid.inject(row, col, value)
    for _ in range(80):
        grid.tick()
    cell = grid.cells[info.result_cell]
    expected = _real_ashr(-200 + 100, 4)
    assert cell.ram_data_valid is True
    assert cell.ram_data_reg == expected == info.expected_result
