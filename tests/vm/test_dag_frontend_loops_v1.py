"""tests/vm/test_dag_frontend_loops_v1.py — points.md #801: loops by
compile-time UNROLLING (Alan's option (b)). The loop block is interpreted
iteration by iteration; compile-time-known values (the induction variable)
fold away, the exit condition must fold to a constant, and everything
data-dependent is emitted as ordinary instructions. Every positive test runs
the compiled fabric through the real VM against an independent Python loop.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import llvm_dag_frontend_v1 as F  # noqa: E402

M = 0xFFFFFFFF
XS = [0, 1, 7, 100, 0x7FFFFFFF, M]


def s32(v):
    v &= M
    return v - (1 << 32) if v >> 31 else v


def _loop(body, args="i32 %x", entry="", exit_="", cond_br="br i1 %cond, label %loop, label %exit",
          phis="  %i = phi i32 [ 0, %entry ], [ %inext, %loop ]\n  %acc = phi i32 [ 0, %entry ], [ %accnext, %loop ]",
          ret="%accnext"):
    return (f"define i32 @f({args}) {{\nentry:\n{entry}  br label %loop\nloop:\n{phis}\n{body}\n  {cond_br}\n"
            f"exit:\n{exit_}  ret i32 {ret}\n}}\n")


def _compile(src):
    res, diags = F.compile_llvm_via_dag(src)
    assert diags == [], [d.problem for d in diags]
    return res


def _refused(src):
    res, diags = F.compile_llvm_via_dag(src)
    assert res is None and diags
    return " | ".join(d.problem for d in diags)


ACC5 = _loop("  %accnext = add i32 %acc, %x\n  %inext = add i32 %i, 1\n  %cond = icmp slt i32 %inext, 5")


def test_accumulator_loop_matches_a_python_loop():
    res = _compile(ACC5)
    for x in XS:
        assert F.run_in_vm(res, {"x": x}) == (5 * x) & M, hex(x)


def test_the_induction_variable_folds_away_and_leaves_only_data_dependent_work():
    """5 iterations of `acc += x` must be 5 adds -- no cell for the counter, no cell
    for the exit test, no constant cells for the loop bookkeeping."""
    res = _compile(ACC5)
    assert [d.opcode for d in res.dag] == ["add"] * 5
    assert [d.name for d in res.dag] == [f"accnext__it{k}" for k in range(5)]


def test_power_loop_with_an_unsigned_exit_predicate():
    res = _compile(_loop("  %accnext = mul i32 %acc, %x\n  %inext = add i32 %i, 1\n  %cond = icmp ult i32 %inext, 6",
                         phis="  %i = phi i32 [ 0, %entry ], [ %inext, %loop ]\n"
                              "  %acc = phi i32 [ 1, %entry ], [ %accnext, %loop ]"))
    for x in (0, 1, 2, 3, 7, M):
        assert F.run_in_vm(res, {"x": x}) == pow(x, 6, 1 << 32), x


def test_two_loop_carried_values_that_swap():
    res = _compile(_loop("  %s = add i32 %a, %b\n  %inext = add i32 %i, 1\n  %cond = icmp slt i32 %inext, 8",
                         args="i32 %x, i32 %y",
                         phis="  %i = phi i32 [ 0, %entry ], [ %inext, %loop ]\n"
                              "  %a = phi i32 [ %x, %entry ], [ %b, %loop ]\n"
                              "  %b = phi i32 [ %y, %entry ], [ %s, %loop ]", ret="%s"))
    def ref(x, y):
        a, b = x, y
        for _ in range(8):
            a, b = b, (a + b) & M
        return b
    for a, b in ((0, 1), (1, 1), (5, 9), (M, 3)):
        assert F.run_in_vm(res, {"x": a, "y": b}) == ref(a, b), (a, b)


def test_descending_loop_with_a_negative_step():
    res = _compile(_loop("  %accnext = add i32 %acc, %x\n  %inext = sub i32 %i, 3\n  %cond = icmp sgt i32 %inext, 0",
                         phis="  %i = phi i32 [ 10, %entry ], [ %inext, %loop ]\n"
                              "  %acc = phi i32 [ 0, %entry ], [ %accnext, %loop ]"))
    assert len(res.dag) == 4                                    # i = 10 -> 7 -> 4 -> 1 -> -2
    for x in XS:
        assert F.run_in_vm(res, {"x": x}) == (4 * x) & M, hex(x)


def test_reversed_branch_targets():
    res = _compile(_loop("  %accnext = add i32 %acc, %x\n  %inext = add i32 %i, 1\n  %cond = icmp sge i32 %inext, 4",
                         cond_br="br i1 %cond, label %exit, label %loop"))
    for x in XS:
        assert F.run_in_vm(res, {"x": x}) == (4 * x) & M, hex(x)


def test_code_before_and_after_the_loop_and_a_post_loop_phi():
    res = _compile(_loop("  %accnext = add i32 %acc, %base\n  %inext = add i32 %i, 1\n  %cond = icmp slt i32 %inext, 3",
                         entry="  %base = shl i32 %x, 1\n",
                         exit_="  %res = phi i32 [ %accnext, %loop ]\n  %r = add i32 %res, 100\n", ret="%r"))
    for x in XS:
        assert F.run_in_vm(res, {"x": x}) == (3 * ((x << 1) & M) + 100) & M, hex(x)


def test_the_induction_variable_can_feed_a_shift_amount():
    """`shl %y, %i` inside the loop: %i is a literal in every iteration, so it becomes a
    literal shift amount -- a variable-looking shift the fabric CAN do once unrolled."""
    res = _compile(_loop("  %sh = shl i32 %y, %i\n  %accnext = add i32 %acc, %sh\n  %inext = add i32 %i, 1\n"
                         "  %cond = icmp slt i32 %inext, 5", args="i32 %y"))
    for y in XS:
        assert F.run_in_vm(res, {"y": y}) == sum((y << k) & M for k in range(5)) & M, hex(y)


def test_a_data_dependent_select_inside_the_loop_running_maximum():
    res = _compile(_loop("  %sh = shl i32 %y, %i\n  %c = icmp sgt i32 %acc, %sh\n"
                         "  %accnext = select i1 %c, i32 %acc, i32 %sh\n  %inext = add i32 %i, 1\n"
                         "  %cond = icmp slt i32 %inext, 4", args="i32 %y"))
    for y in (0, 1, 3, 100, M, M - 5):
        m = 0
        for k in range(4):
            sh = (y << k) & M
            m = m if s32(m) > s32(sh) else sh
        assert F.run_in_vm(res, {"y": y}) == m, y


def test_numbered_values_inside_a_loop():
    res = _compile(_loop("  %0 = add i32 %acc, %x\n  %1 = add i32 %i, 1\n  %2 = icmp slt i32 %1, 4",
                         phis="  %i = phi i32 [ 0, %entry ], [ %1, %loop ]\n"
                              "  %acc = phi i32 [ 0, %entry ], [ %0, %loop ]",
                         cond_br="br i1 %2, label %loop, label %exit", ret="%0"))
    for x in XS:
        assert F.run_in_vm(res, {"x": x}) == (4 * x) & M, hex(x)


def test_a_longer_loop_compiles_and_runs():
    res = _compile(_loop("  %accnext = add i32 %acc, %x\n  %inext = add i32 %i, 1\n  %cond = icmp slt i32 %inext, 32"))
    assert len(res.dag) == 32
    for x in (0, 3, M):
        assert F.run_in_vm(res, {"x": x}) == (32 * x) & M, x


# ---------------------------------------------------------------------------
# Refusals: precise, never a guess.
# ---------------------------------------------------------------------------

def test_a_data_dependent_exit_is_refused():
    text = _refused(_loop("  %accnext = add i32 %acc, %x\n  %inext = add i32 %i, 1\n  %cond = icmp slt i32 %accnext, 100"))
    assert "not a compile-time constant" in text


def test_a_loop_past_the_unroll_limit_is_refused():
    text = _refused(_loop("  %accnext = add i32 %acc, %x\n  %inext = add i32 %i, 1\n  %cond = icmp slt i32 %inext, 100000"))
    assert "unrolled iterations" in text


def test_a_loop_whose_result_is_a_compile_time_constant_is_refused():
    text = _refused(_loop("  %accnext = add i32 %acc, 1\n  %inext = add i32 %i, 1\n  %cond = icmp slt i32 %inext, 5",
                          ret="%inext"))
    assert "compile-time constant or an argument" in text


def test_three_blocks_without_a_loop_are_refused():
    src = ("define i32 @f(i32 %x) {\nentry:\n  %c = icmp slt i32 %x, 5\n  br i1 %c, label %a, label %b\n"
           "a:\n  ret i32 %x\nb:\n  ret i32 %x\n}\n")
    assert "self-looping" in _refused(src)


def test_more_than_three_blocks_are_refused():
    src = ("define i32 @f(i32 %x) {\nentry:\n  br label %a\na:\n  br label %b\nb:\n  br label %c\nc:\n  ret i32 %x\n}\n")
    assert "basic blocks" in _refused(src)


def test_auto_placer_keeps_the_smaller_layout():
    """#801: compile time is milliseconds, simulation time scales with cell count. The growth
    placer spaces independent leaves 100 rows apart (739 cells for this loop); the routed
    placer needs 140. `auto` must take the smaller one."""
    src = _loop("  %sh = shl i32 %y, %i\n  %accnext = add i32 %acc, %sh\n  %inext = add i32 %i, 1\n"
                "  %cond = icmp slt i32 %inext, 5", args="i32 %y")
    growth, routed, auto = (F.compile_llvm_via_dag(src, placer=p)[0] for p in ("growth", "routed", "auto"))
    assert len(routed.records) < len(growth.records)
    assert auto.placer == "routed" and len(auto.records) == len(routed.records)
    for y in (0, 3, M):
        assert F.run_in_vm(auto, {"y": y}) == F.run_in_vm(growth, {"y": y}) == sum((y << k) & M for k in range(5)) & M
