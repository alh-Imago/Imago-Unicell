"""tests/vm/test_dag_frontend_i1_v1.py — points.md #802: i1 <-> i32 conversions
(zext / sext / trunc) and i1 logic (and / or / xor / select with i1 arms).

An i1 is a canonical 0/1 in a 32-bit cell, so the conversions are built from ops
that already exist: zext = a one-cell copy, sext = `0 - c` (the mask `select`
already uses), trunc = `and x, 1`. Every positive test runs the fabric through
the real VM against an independent Python model.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import llvm_dag_frontend_v1 as F  # noqa: E402

M = 0xFFFFFFFF
XS = [0, 1, 4, 5, 6, 9, 10, 11, 100, M, M - 3]


def s32(v):
    v &= M
    return v - (1 << 32) if v >> 31 else v


def _ir(body, args="i32 %x", ret="i32"):
    return f"define {ret} @f({args}) {{\nentry:\n{body}\n}}\n"


def _compile(src):
    res, diags = F.compile_llvm_via_dag(src)
    assert diags == [], [d.problem for d in diags]
    return res


def _check(src, ref, xs=XS):
    res = _compile(src)
    for x in xs:
        assert F.run_in_vm(res, {"x": x}) == ref(x) & M, hex(x)
    return res


def test_zext_of_a_comparison():
    _check(_ir("  %c = icmp slt i32 %x, 5\n  %z = zext i1 %c to i32\n  ret i32 %z"), lambda x: int(s32(x) < 5))


def test_summing_zexts_counts_how_many_conditions_hold():
    _check(_ir("  %a = icmp sgt i32 %x, 0\n  %b = icmp slt i32 %x, 10\n  %za = zext i1 %a to i32\n"
               "  %zb = zext i1 %b to i32\n  %s = add i32 %za, %zb\n  ret i32 %s"),
           lambda x: int(s32(x) > 0) + int(s32(x) < 10))


def test_sext_makes_an_all_ones_mask():
    _check(_ir("  %c = icmp slt i32 %x, 5\n  %m = sext i1 %c to i32\n  %r = and i32 %x, %m\n  ret i32 %r"),
           lambda x: x if s32(x) < 5 else 0)


def test_sext_itself_is_zero_or_all_ones():
    _check(_ir("  %c = icmp eq i32 %x, 5\n  %m = sext i1 %c to i32\n  ret i32 %m"), lambda x: M if x == 5 else 0)


def test_trunc_takes_the_low_bit():
    _check(_ir("  %b = trunc i32 %x to i1\n  %r = select i1 %b, i32 111, i32 222\n  ret i32 %r"),
           lambda x: 111 if x & 1 else 222)


def test_i1_and_is_a_range_check():
    _check(_ir("  %a = icmp sgt i32 %x, 0\n  %b = icmp slt i32 %x, 10\n  %c = and i1 %a, %b\n"
               "  %r = select i1 %c, i32 1, i32 0\n  ret i32 %r"), lambda x: int(0 < s32(x) < 10))


def test_i1_or():
    _check(_ir("  %a = icmp slt i32 %x, 2\n  %b = icmp sgt i32 %x, 50\n  %c = or i1 %a, %b\n"
               "  %z = zext i1 %c to i32\n  ret i32 %z"), lambda x: int(s32(x) < 2 or s32(x) > 50))


def test_i1_not_is_xor_with_true():
    _check(_ir("  %a = icmp slt i32 %x, 5\n  %n = xor i1 %a, true\n  %z = zext i1 %n to i32\n  ret i32 %z"),
           lambda x: int(not s32(x) < 5))


def test_i1_xor_of_two_comparisons():
    _check(_ir("  %a = icmp slt i32 %x, 5\n  %b = icmp slt i32 %x, 10\n  %c = xor i1 %a, %b\n"
               "  %z = zext i1 %c to i32\n  ret i32 %z"), lambda x: int((s32(x) < 5) != (s32(x) < 10)))


def test_select_with_i1_arms():
    src = _ir("  %a = icmp slt i32 %x, 5\n  %b = icmp sgt i32 %x, 50\n  %s = icmp eq i32 %x, 7\n"
              "  %c = select i1 %s, i1 %a, i1 %b\n  %z = zext i1 %c to i32\n  ret i32 %z")
    _check(src, lambda x: int(s32(x) < 5) if x == 7 else int(s32(x) > 50), xs=[7, 3, 60, 4, M])


def test_a_returned_i1_reads_back_as_zero_or_one():
    res = _compile(_ir("  %a = icmp sgt i32 %x, 3\n  %b = icmp slt i32 %x, 9\n  %c = and i1 %a, %b\n  ret i1 %c", ret="i1"))
    for x in (0, 3, 4, 8, 9, 50):
        assert F.run_in_vm(res, {"x": x}) == int(3 < x < 9)


def test_a_negated_condition_selects_the_other_arm():
    _check(_ir("  %a = icmp slt i32 %x, 5\n  %n = xor i1 %a, true\n  %r = select i1 %n, i32 7, i32 8\n  ret i32 %r"),
           lambda x: 7 if not s32(x) < 5 else 8)


def test_conversions_compose_with_the_rest_of_the_pipeline_and_a_loop():
    """zext inside an unrolled loop: count how many of x, x+1, x+2, x+3 are below 6."""
    src = ("define i32 @f(i32 %x) {\nentry:\n  br label %loop\nloop:\n"
           "  %i = phi i32 [ 0, %entry ], [ %inext, %loop ]\n  %acc = phi i32 [ 0, %entry ], [ %accnext, %loop ]\n"
           "  %v = add i32 %x, %i\n  %c = icmp slt i32 %v, 6\n  %z = zext i1 %c to i32\n"
           "  %accnext = add i32 %acc, %z\n  %inext = add i32 %i, 1\n  %cond = icmp slt i32 %inext, 4\n"
           "  br i1 %cond, label %loop, label %exit\nexit:\n  ret i32 %accnext\n}\n")
    res = _compile(src)
    for x in (0, 2, 3, 5, 6, 100):
        assert F.run_in_vm(res, {"x": x}) == sum(1 for k in range(4) if x + k < 6), x


# ---- refusals ----------------------------------------------------------------------------

def _refused(src):
    res, diags = F.compile_llvm_via_dag(src)
    assert res is None and diags
    return " | ".join(d.problem for d in diags)


def test_narrow_and_wide_integer_types_are_refused_with_the_reason():
    assert "not supported" in _refused(_ir("  %t = trunc i32 %x to i8\n  %z = zext i8 %t to i32\n  ret i32 %z"))
    assert "i8" in _refused(_ir("  %z = zext i8 %x to i32\n  ret i32 %z", args="i8 %x"))
    assert "i64" in _refused(_ir("  %c = icmp slt i32 %x, 5\n  %z = zext i1 %c to i64\n  ret i64 %z", ret="i64"))


def test_zext_of_something_that_is_not_an_i1_producer_is_refused():
    # an i1 ARGUMENT is not accepted: nothing guarantees its value is 0/1
    assert "i1" in _refused(_ir("  %z = zext i1 %b to i32\n  ret i32 %z", args="i1 %b"))


def test_the_narrow_conversion_diagnostic_names_the_missing_type_system():
    res, diags = F.compile_llvm_via_dag(_ir("  %t = trunc i32 %x to i8\n  %z = zext i8 %t to i32\n  ret i32 %z"))
    assert res is None
    assert any("sub-word" in d.why for d in diags)
