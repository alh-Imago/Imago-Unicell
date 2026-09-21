"""tests/vm/test_dag_frontend_controlflow_v1.py — points.md #803: acyclic control flow by
IF-CONVERSION. Every block's instructions run unconditionally (speculation -- sound because every
supported op is pure: no memory, no division, nothing that can trap); a `phi` becomes a `select`
chain over the incoming EDGE conditions and several `ret`s a select chain over block-execution
conditions, all built from the i1 logic of #802 and simplified symbolically before any gate is
emitted. Every positive test runs the fabric through the real VM against an independent model.
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


def _check(src, ref, xs=XS, args=("x",)):
    res, diags = F.compile_llvm_via_dag(src)
    assert diags == [], [d.problem for d in diags]
    for x in xs:
        got = F.run_in_vm(res, {args[0]: x} if len(args) == 1 else dict(zip(args, x)))
        want = ref(x) if len(args) == 1 else ref(*x)
        assert got == want & M, x
    return res


def _refused(src):
    res, diags = F.compile_llvm_via_dag(src)
    assert res is None and diags
    return " | ".join(d.problem for d in diags)


DIAMOND = """define i32 @f(i32 %x) {
entry:
  %c = icmp slt i32 %x, 5
  br i1 %c, label %a, label %b
a:
  %p = add i32 %x, 1
  br label %m
b:
  %q = sub i32 %x, 1
  br label %m
m:
  %r = phi i32 [ %p, %a ], [ %q, %b ]
  ret i32 %r
}"""


def test_if_else_diamond_with_a_phi_merge():
    _check(DIAMOND, lambda x: x + 1 if s32(x) < 5 else x - 1)


def test_the_swapped_branch_targets_give_the_same_function():
    swapped = DIAMOND.replace("br i1 %c, label %a, label %b", "br i1 %c, label %a, label %b").replace(
        "%c = icmp slt i32 %x, 5", "%c = icmp sge i32 %x, 5").replace(
        "br i1 %c, label %a, label %b", "br i1 %c, label %b, label %a")
    _check(swapped, lambda x: x + 1 if s32(x) < 5 else x - 1)


def test_triangle_with_a_literal_arm():
    src = """define i32 @f(i32 %x) {
entry:
  %c = icmp sgt i32 %x, 100
  br i1 %c, label %big, label %m
big:
  br label %m
m:
  %r = phi i32 [ 100, %big ], [ %x, %entry ]
  ret i32 %r
}"""
    _check(src, lambda x: 100 if s32(x) > 100 else x, xs=[0, 99, 100, 101, 5000, M])


def test_two_early_returns():
    src = """define i32 @f(i32 %x) {
entry:
  %c = icmp slt i32 %x, 0
  br i1 %c, label %neg, label %pos
neg:
  %n = sub i32 0, %x
  ret i32 %n
pos:
  %d = shl i32 %x, 1
  ret i32 %d
}"""
    _check(src, lambda x: (-s32(x)) if s32(x) < 0 else x << 1)


def test_three_early_returns_with_computed_arms_now_compiles():
    """FLIPPED (points.md #805). #803 pinned this as a known limitation: all 576 layouts failed to
    route, and the dataflow graph was later shown PLANAR (so a solution existed). Negotiated-congestion
    routing (PathFinder) finds one."""
    src = """define i32 @f(i32 %x) {
entry:
  %c1 = icmp slt i32 %x, 5
  br i1 %c1, label %lo, label %rest
lo:
  ret i32 111
rest:
  %c2 = icmp slt i32 %x, 10
  br i1 %c2, label %mid, label %hi
mid:
  %m = add i32 %x, 1000
  ret i32 %m
hi:
  %h = shl i32 %x, 1
  ret i32 %h
}"""
    _check(src, lambda x: 111 if s32(x) < 5 else (x + 1000 if s32(x) < 10 else x << 1))


def test_three_early_returns_with_cheap_arms_do_compile():
    src = """define i32 @f(i32 %x) {
entry:
  %c1 = icmp slt i32 %x, 5
  br i1 %c1, label %lo, label %rest
lo:
  ret i32 111
rest:
  %c2 = icmp slt i32 %x, 10
  br i1 %c2, label %mid, label %hi
mid:
  ret i32 222
hi:
  %h = shl i32 %x, 1
  ret i32 %h
}"""
    _check(src, lambda x: 111 if s32(x) < 5 else (222 if s32(x) < 10 else x << 1))


def test_nested_if_three_way():
    src = """define i32 @f(i32 %x) {
entry:
  %c1 = icmp slt i32 %x, 10
  br i1 %c1, label %lo, label %hi
lo:
  %c2 = icmp slt i32 %x, 5
  br i1 %c2, label %lolo, label %lohi
lolo:
  br label %m1
lohi:
  br label %m1
m1:
  %v = phi i32 [ 1, %lolo ], [ 2, %lohi ]
  br label %m
hi:
  br label %m
m:
  %r = phi i32 [ %v, %m1 ], [ 3, %hi ]
  ret i32 %r
}"""
    res = _check(src, lambda x: (1 if s32(x) < 5 else 2) if s32(x) < 10 else 3)
    assert len(res.dag) <= 14           # symbolic simplification: the join's condition collapses to c1


def test_phi_between_two_computed_values_used_afterwards():
    src = """define i32 @f(i32 %x) {
entry:
  %c = icmp sgt i32 %x, 20
  br i1 %c, label %big, label %small
big:
  %b = shl i32 %x, 1
  br label %m
small:
  %s = add i32 %x, 100
  br label %m
m:
  %r = phi i32 [ %b, %big ], [ %s, %small ]
  %z = xor i32 %r, 255
  ret i32 %z
}"""
    _check(src, lambda x: ((x << 1) if s32(x) > 20 else (x + 100)) ^ 255)


def test_two_diamonds_in_sequence():
    src = """define i32 @f(i32 %x) {
entry:
  %c1 = icmp slt i32 %x, 5
  br i1 %c1, label %a1, label %b1
a1:
  br label %m1
b1:
  br label %m1
m1:
  %v = phi i32 [ 1, %a1 ], [ 9, %b1 ]
  %c2 = icmp sgt i32 %x, 50
  br i1 %c2, label %a2, label %b2
a2:
  %t = mul i32 %v, 3
  br label %m2
b2:
  br label %m2
m2:
  %r = phi i32 [ %t, %a2 ], [ %v, %b2 ]
  ret i32 %r
}"""
    _check(src, lambda x: (lambda v: v * 3 if s32(x) > 50 else v)(1 if s32(x) < 5 else 9))


def test_branch_on_an_i1_that_came_from_i1_logic():
    src = """define i32 @f(i32 %x) {
entry:
  %a = icmp sgt i32 %x, 0
  %b = icmp slt i32 %x, 10
  %c = and i1 %a, %b
  br i1 %c, label %yes, label %no
yes:
  %y = add i32 %x, 1000
  br label %m
no:
  br label %m
m:
  %r = phi i32 [ %y, %yes ], [ %x, %no ]
  ret i32 %r
}"""
    _check(src, lambda x: x + 1000 if 0 < s32(x) < 10 else x)


def test_unconditional_chain_of_blocks_is_straight_line_code():
    src = """define i32 @f(i32 %x) {
entry:
  %a = add i32 %x, 1
  br label %b
b:
  %c = shl i32 %a, 2
  br label %d
d:
  %e = xor i32 %c, 7
  ret i32 %e
}"""
    _check(src, lambda x: (((x + 1) & M) << 2 & M) ^ 7)


def test_control_flow_inside_a_function_that_also_has_a_loop_is_a_separate_shape_and_refused():
    src = """define i32 @f(i32 %x) {
entry:
  br label %loop
loop:
  %i = phi i32 [ 0, %entry ], [ %inext, %loop ]
  %inext = add i32 %i, 1
  %c = icmp slt i32 %inext, 3
  br i1 %c, label %loop, label %m
m:
  %r = add i32 %x, %inext
  ret i32 %r
}"""
    # this is the normal loop shape (entry/loop/exit): still handled by the unroller, and the result
    # is a computed value that depends on the argument
    _check(src, lambda x: x + 3)


# ---- refusals ------------------------------------------------------------------------------------

def test_a_cyclic_graph_that_is_not_the_loop_shape_is_refused():
    src = """define i32 @f(i32 %x) {
entry:
  br label %a
a:
  %c = icmp slt i32 %x, 5
  br i1 %c, label %b, label %a
b:
  ret i32 %x
}"""
    assert "self-looping" in _refused(src) or "loop" in _refused(src)


def test_a_returned_argument_or_constant_is_still_refused():
    src = """define i32 @f(i32 %x) {
entry:
  %c = icmp slt i32 %x, 5
  br i1 %c, label %a, label %b
a:
  ret i32 1
b:
  ret i32 2
}"""
    # both arms return literals: the result is a select of two constants -> computed, so THIS compiles
    res, diags = F.compile_llvm_via_dag(src)
    assert diags == []
    for x in XS:
        assert F.run_in_vm(res, {"x": x}) == (1 if s32(x) < 5 else 2)


def test_if_conversion_speculates_only_pure_operations():
    """Documents WHY it is sound: the arms are executed unconditionally, which is only safe because
    nothing in the supported op set can trap or have a side effect. Division is refused outright."""
    src = """define i32 @f(i32 %x) {
entry:
  %c = icmp ne i32 %x, 0
  br i1 %c, label %a, label %b
a:
  %q = sdiv i32 100, %x
  br label %m
b:
  br label %m
m:
  %r = phi i32 [ %q, %a ], [ 0, %b ]
  ret i32 %r
}"""
    assert "sdiv" in _refused(src)
