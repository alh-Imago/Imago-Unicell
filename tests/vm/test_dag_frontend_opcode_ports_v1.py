"""tests/vm/test_dag_frontend_opcode_ports_v1.py — points.md #797+: the
remaining LLVM opcodes ported ONE AT A TIME into the new library-driven
path (`vix_opcode_library_v1` + `vix_dag_dispatcher_v1` +
`llvm_dag_frontend_v1`), each tested as it is created -- the same process
`mul` (#790/#791) and `and`/`or`/`xor` (#792) went through.

Every positive test runs the compiled fabric through the real VM and
checks against an INDEPENDENT Python model, never against the dispatcher's
own output; where the OLD frontend accepts the same program its own
independent expected-result model is checked too.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import llvm_dag_frontend_v1 as F  # noqa: E402
import llvm_ir_frontend_v1 as OLD  # noqa: E402
import vix_opcode_library_v1 as LIB  # noqa: E402

M = 0xFFFFFFFF
VALUES = [0, 1, 0x12345678, 0x80000001, 2 ** 31, M]


def _ir(body, args="i32 %x"):
    return f"define i32 @f({args}) {{\nentry:\n{body}\n}}\n"


def _compile(src):
    res, diags = F.compile_llvm_via_dag(src)
    assert diags == [], [d.problem for d in diags]
    return res


def _refused(src):
    res, diags = F.compile_llvm_via_dag(src)
    assert res is None and diags
    return " | ".join(d.problem for d in diags)


# ===========================================================================
# shl / lshr  (#797)
# ===========================================================================

def test_shift_entries_are_one_operand_library_entries():
    for op in ("shl", "lshr"):
        e = LIB.lookup(op)
        assert e is not None and e.arity == 1 and e.port_style == "unary_addon"


def test_decompose_shift_matches_the_old_frontends_rule_for_every_amount():
    for k in range(32):
        assert LIB.decompose_shift(k) == OLD._decompose_shift(k)
    with pytest.raises(ValueError):
        LIB.decompose_shift(32)


@pytest.mark.parametrize("op,ref", [("shl", lambda x, k: (x << k) & M), ("lshr", lambda x, k: x >> k)])
def test_every_shift_amount_0_to_31_is_exact(op, ref):
    for k in range(32):
        res = _compile(_ir(f"  %r = {op} i32 %x, {k}\n  ret i32 %r"))
        for x in VALUES:
            assert F.run_in_vm(res, {"x": x}, ticks=200) == ref(x, k), (op, k, hex(x))


@pytest.mark.parametrize("op", ["shl", "lshr"])
def test_shift_agrees_with_the_old_frontends_own_model(op):
    for k in (0, 1, 3, 4, 13, 28, 31):
        src = _ir(f"  %r = {op} i32 %x, {k}\n  ret i32 %r")
        res = _compile(src)
        for x in (5, 0x7FFF0001, 123456):
            _, _, info = OLD.compile_llvm_ir(src, {"x": x})
            assert F.run_in_vm(res, {"x": x}, ticks=200) == info.expected_result, (op, k, x)


def test_shift_amount_is_configuration_not_a_data_operand():
    res = _compile(_ir("  %r = shl i32 %x, 5\n  ret i32 %r"))
    assert [d.operands[0].kind for d in res.dag] == ["dynamic"]
    assert len(res.dag[0].operands) == 1 and res.dag[0].params == {"amount": 5}
    assert res.arg_injections == {"x": [res.arg_injections["x"][0]]}


def test_shift_in_a_chain_with_arithmetic():
    res = _compile(_ir("  %a = add i32 %x, 1\n  %b = shl i32 %a, 4\n  %c = lshr i32 %b, 2\n"
                       "  %d = sub i32 %c, 7\n  ret i32 %d"))
    for x in VALUES:
        assert F.run_in_vm(res, {"x": x}) == ((((x + 1) & M) << 4 & M) >> 2) - 7 & M, hex(x)


def test_shifted_result_fans_out_to_two_consumers():
    res = _compile(_ir("  %s = shl i32 %x, 3\n  %t = add i32 %s, 1\n  %u = add i32 %s, %t\n  ret i32 %u"))
    for x in VALUES:
        s = (x << 3) & M
        assert F.run_in_vm(res, {"x": x}) == (s + (s + 1)) & M, hex(x)


def test_two_shifts_of_two_arguments_converge_into_a_sub():
    res = _compile(_ir("  %s = shl i32 %x, 2\n  %t = lshr i32 %y, 1\n  %r = sub i32 %s, %t\n  ret i32 %r",
                       args="i32 %x, i32 %y"))
    for x, y in [(5, 8), (8, 5), (M, 1), (0, M)]:
        assert F.run_in_vm(res, {"x": x, "y": y}) == (((x << 2) & M) - (y >> 1)) & M, (x, y)


def test_shift_of_a_value_used_by_a_literal_minuend_sub():
    res = _compile(_ir("  %s = lshr i32 %x, 4\n  %r = sub i32 1000, %s\n  ret i32 %r"))
    for x in VALUES:
        assert F.run_in_vm(res, {"x": x}) == (1000 - (x >> 4)) & M, hex(x)


def test_scan_reports_a_shift_as_order_free_single_operand():
    res = _compile(_ir("  %r = shl i32 %x, 5\n  ret i32 %r"))
    n = res.ordering[0]
    assert (n.order_sensitive, n.guarantee, n.ingestion) == (False, "not needed", "plain_chain")
    assert "one data operand" in n.reason


def test_variable_shift_amount_is_refused():
    assert "not a compile-time literal" in _refused(_ir("  %r = shl i32 %x, %y\n  ret i32 %r", args="i32 %x, i32 %y"))


def test_out_of_range_shift_amount_is_refused():
    assert "outside 0-31" in _refused(_ir("  %r = lshr i32 %x, 32\n  ret i32 %r"))


def test_shift_of_a_literal_is_refused():
    assert "both operands are literals" in _refused(_ir("  %r = shl i32 4, 2\n  ret i32 %r"))


# ===========================================================================
# icmp  (#798) -- expands to `sub` + comparator (+ `xor` for eq/ne)
# ===========================================================================

def s32(v):
    v &= M
    return v - (1 << 32) if v >> 31 else v


_PRED = {
    "slt": lambda a, b: s32(a) < s32(b), "sle": lambda a, b: s32(a) <= s32(b),
    "sgt": lambda a, b: s32(a) > s32(b), "sge": lambda a, b: s32(a) >= s32(b),
    "eq": lambda a, b: a == b, "ne": lambda a, b: a != b,
}
_SMALL = [0, 1, 2, 5, 100, M, M - 1, M - 99]           # small values incl. small negatives
_PAIRS = [(a, b) for a in _SMALL for b in _SMALL]
_EXTREME = [0x80000000, 0x80000001, 0xC0000000, M, 0, 1, 0x40000000, 0x7FFFFFFF]
_EXT_PAIRS = [(a, b) for a in _EXTREME for b in _EXTREME]


def _icmp_ir(pred, ret_i1=False):
    if ret_i1:
        return ("define i1 @f(i32 %x, i32 %y) {\nentry:\n"
                f"  %c = icmp {pred} i32 %x, %y\n  ret i1 %c\n}}\n")
    return _ir(f"  %c = icmp {pred} i32 %x, %y\n  %r = select i1 %c, i32 1, i32 0\n  ret i32 %r",
               args="i32 %x, i32 %y")


@pytest.mark.parametrize("pred", list(_PRED))
def test_icmp_every_predicate_result_is_exact_on_the_non_overflowing_domain(pred):
    res = _compile(_icmp_ir(pred, ret_i1=True))
    for a, b in _PAIRS:
        assert F.run_in_vm(res, {"x": a, "y": b}, ticks=350) == int(_PRED[pred](a, b)), (pred, a, b)


@pytest.mark.parametrize("pred", list(_PRED))
def test_icmp_through_select_gives_the_same_answer(pred):
    res = _compile(_icmp_ir(pred))
    for a, b in _PAIRS[::3]:
        assert F.run_in_vm(res, {"x": a, "y": b}, ticks=350) == int(_PRED[pred](a, b)), (pred, a, b)


@pytest.mark.parametrize("pred", ["eq", "ne"])
def test_eq_ne_are_exact_for_every_pair_including_extremes(pred):
    """diff==0 is sign-agnostic, so overflow cannot affect eq/ne."""
    res = _compile(_icmp_ir(pred, ret_i1=True))
    for a, b in _EXT_PAIRS:
        assert F.run_in_vm(res, {"x": a, "y": b}, ticks=350) == int(_PRED[pred](a, b)), (pred, a, b)


@pytest.mark.parametrize("pred", ["slt", "sle", "sgt", "sge"])
def test_ordered_predicates_fail_exactly_on_signed_difference_overflow_known_limitation(pred):
    """points.md #798 -- a documented, PRECISELY BOUNDED negative result,
    inherited from the old frontend (#711). The ordered predicates compute a
    32-bit difference and compare it signed, so they are wrong EXACTLY when
    that difference overflows (opposite-sign operands whose magnitudes sum
    past 2^31-1). Asserts both directions: every overflow pair is wrong AND
    every wrong pair is an overflow. If a sign-aware compare is ever built,
    FLIP this to require exactness everywhere."""
    swap = pred in ("slt", "sle")
    res = _compile(_icmp_ir(pred, ret_i1=True))

    def overflows(a, b):
        A, B = s32(a), s32(b)
        d = (B - A) if swap else (A - B)
        return not -(1 << 31) <= d <= (1 << 31) - 1

    wrong = {(a, b) for a, b in _EXT_PAIRS
             if F.run_in_vm(res, {"x": a, "y": b}, ticks=350) != int(_PRED[pred](a, b))}
    assert wrong == {(a, b) for a, b in _EXT_PAIRS if overflows(a, b)}
    assert wrong, "the extreme set must actually contain overflow cases"


def test_ordered_predicates_carry_a_caveat_eq_ne_do_not():
    assert "overflow" in " ".join(_compile(_icmp_ir("slt")).caveats)
    assert _compile(_icmp_ir("eq")).caveats == []


def test_icmp_with_a_literal_operand_either_side():
    for src, ref in [
        (_ir("  %c = icmp slt i32 %x, 100\n  %r = select i1 %c, i32 1, i32 0\n  ret i32 %r"), lambda x: s32(x) < 100),
        (_ir("  %c = icmp sgt i32 100, %x\n  %r = select i1 %c, i32 1, i32 0\n  ret i32 %r"), lambda x: 100 > s32(x)),
        (_ir("  %c = icmp eq i32 %x, 7\n  %r = select i1 %c, i32 1, i32 0\n  ret i32 %r"), lambda x: x == 7),
        (_ir("  %c = icmp ne i32 7, %x\n  %r = select i1 %c, i32 1, i32 0\n  ret i32 %r"), lambda x: x != 7),
    ]:
        res = _compile(src)
        for x in (0, 6, 7, 8, 99, 100, 101, M, M - 5):
            assert F.run_in_vm(res, {"x": x}, ticks=350) == int(ref(x)), (src, x)


def test_icmp_expansion_keeps_the_source_name_and_traces_the_pieces():
    res = _compile(_icmp_ir("eq"))
    names = [d.name for d in res.dag]
    assert "c" in names and any(n.startswith("c__") for n in names)
    by = {n.name: n for n in res.ordering}
    assert by["c"].origin is None                                   # the source %name itself
    assert all(n.origin == "c" for n in res.ordering if n.name.startswith("c__"))
    assert any("expanded into" in r for r in res.rewrites)


def test_icmp_agrees_with_the_old_frontends_own_model_where_it_accepts_the_program():
    """The old frontend only accepts an ORDERED icmp feeding a select (it refuses
    eq/ne there -- its own restriction, #668); the new path is more general.
    Cross-check every predicate the old one accepts, and require that be all four."""
    agreed = 0
    for pred in ("slt", "sle", "sgt", "sge", "eq", "ne"):
        src = _ir(f"  %c = icmp {pred} i32 %x, 7\n  %r = select i1 %c, i32 1, i32 0\n  ret i32 %r")
        res = _compile(src)
        for x in (3, 7, 12):
            _, _, info = OLD.compile_llvm_ir(src, {"x": x})
            if info is None:
                break
            assert F.run_in_vm(res, {"x": x}, ticks=350) == info.expected_result, (pred, x)
        else:
            agreed += 1
    assert agreed == 4


def test_unsigned_predicate_is_refused():
    assert "not supported" in _refused(_ir("  %c = icmp ult i32 %x, 5\n  %r = select i1 %c, i32 1, i32 0\n  ret i32 %r"))


def test_icmp_of_two_literals_is_refused():
    assert "both operands are literals" in _refused(
        _ir("  %c = icmp slt i32 3, 5\n  %r = select i1 %c, i32 1, i32 0\n  ret i32 %r"))


# ===========================================================================
# select  (#798) -- mask-and-merge from library ops: m = 0-c, (t&m)|(f&~m)
# ===========================================================================

def _sel_cases(src, cases, ref, ticks=350):
    res = _compile(src)
    for a in cases:
        assert F.run_in_vm(res, a, ticks=ticks) == ref(**a) & M, (a,)
    return res


def test_select_with_two_literal_arms():
    _sel_cases(_icmp_ir("slt"), [{"x": 3, "y": 5}, {"x": 5, "y": 3}], lambda x, y: int(s32(x) < s32(y)))


def test_select_arm_is_the_argument_itself():
    _sel_cases(_ir("  %c = icmp slt i32 %x, 10\n  %r = select i1 %c, i32 %x, i32 10\n  ret i32 %r"),
               [{"x": x} for x in (0, 9, 10, 11, M)], lambda x: x if s32(x) < 10 else 10)


def test_select_min_and_max_with_a_literal():
    _sel_cases(_ir("  %c = icmp sgt i32 %x, 50\n  %r = select i1 %c, i32 50, i32 %x\n  ret i32 %r"),
               [{"x": x} for x in (0, 10, 50, 51, 200, M)], lambda x: 50 if s32(x) > 50 else x)


def test_select_with_two_dynamic_arms():
    _sel_cases(_ir("  %c = icmp slt i32 %x, 10\n  %r = select i1 %c, i32 %y, i32 %z\n  ret i32 %r",
                   args="i32 %x, i32 %y, i32 %z"),
               [{"x": x, "y": y, "z": z} for x in (3, 10, 50) for y in (7, M) for z in (0, 99)],
               lambda x, y, z: y if s32(x) < 10 else z)


def test_select_max_of_two_arguments():
    _sel_cases(_ir("  %c = icmp sgt i32 %x, %y\n  %r = select i1 %c, i32 %x, i32 %y\n  ret i32 %r",
                   args="i32 %x, i32 %y"),
               [{"x": a, "y": b} for a in (0, 3, M, 100) for b in (0, 7, M, 99)],
               lambda x, y: max(s32(x), s32(y)))


def test_select_absolute_value_uses_a_computed_arm():
    _sel_cases(_ir("  %c = icmp slt i32 %x, 0\n  %n = sub i32 0, %x\n  %r = select i1 %c, i32 %n, i32 %x\n  ret i32 %r"),
               [{"x": x} for x in (0, 1, 5, M, M - 4, 0x7FFFFFFF)], lambda x: abs(s32(x)))


def test_select_agrees_with_the_old_frontends_own_model():
    src = _ir("  %c = icmp sgt i32 %x, 50\n  %r = select i1 %c, i32 50, i32 %x\n  ret i32 %r")
    res = _compile(src)
    for x in (10, 50, 51, 200):
        _, _, info = OLD.compile_llvm_ir(src, {"x": x})
        assert F.run_in_vm(res, {"x": x}, ticks=350) == info.expected_result, x


def test_select_with_a_literal_condition_is_refused():
    assert _refused(_ir("  %r = select i1 true, i32 1, i32 2\n  ret i32 %r"))


_UNPLACEABLE_BY_GROWTH = [
    # two independently COMPUTED arms
    _ir("  %a = add i32 %x, 1\n  %b = shl i32 %x, 2\n  %c = icmp eq i32 %x, 5\n  %r = select i1 %c, i32 %a, i32 %b\n  ret i32 %r"),
    # a chain of selects
    _ir("  %c1 = icmp slt i32 %x, 10\n  %a = select i1 %c1, i32 10, i32 %x\n  %c2 = icmp sgt i32 %a, 20\n"
        "  %r = select i1 %c2, i32 20, i32 %a\n  ret i32 %r"),
]


@pytest.mark.parametrize("src", _UNPLACEABLE_BY_GROWTH)
def test_growth_placer_limit_is_still_a_loud_precise_refusal_known_limitation(src):
    """points.md #798, kept on purpose. The GROWTH placer (`vix_dag_dispatcher_v1`) has no
    global occupancy planning: when two independently-computed values must merge, its routes
    can cross other structure and `flatten()` rejects the collision. Forced onto that placer
    the frontend must still give a `place`-stage diagnostic -- never a raw exception, never a
    wrong answer. (The ROUTED placer, #800, does place these -- see test_virtual_layout_v1.py.)"""
    res, diags = F.compile_llvm_via_dag(src, placer="growth")
    assert res is None
    assert diags and diags[0].stage == "place" and "collision" in diags[0].problem


@pytest.mark.parametrize("src", _UNPLACEABLE_BY_GROWTH)
def test_shapes_growth_cannot_place_compile_and_verify_under_the_default_placer(src):
    """#800: FLIPPED from #798's negative result, as its own docstring instructed. The default
    ('auto') tries growth first and falls back to the virtual-space router."""
    res = _compile(src)
    assert res.placer == "routed"
    for x in (0, 5, 6, 9, 10, 11, 15, 20, 21, 99, M):
        expect = ((x + 1) if x == 5 else (x << 2)) & M if "shl" in src else min(max(s32(x), 10), 20) & M
        assert F.run_in_vm(res, {"x": x}) == expect, hex(x)


# ===========================================================================
# ashr  (#798) -- logical shift OR a sign-fill: lshr(x,k) | shl(0 - lshr(x,31), 32-k)
# ===========================================================================

def test_ashr_every_amount_0_to_31_is_exact_for_negative_and_positive_values():
    edge = [0x80000000, 0x80000001, 0xFFFFFFF0, 0x7FFFFFFF, 0x12345678]   # full 32x10 sweep: see #798
    for k in range(32):
        res = _compile(_ir(f"  %r = ashr i32 %x, {k}\n  ret i32 %r"))
        for x in edge:
            assert F.run_in_vm(res, {"x": x}, ticks=350) == (s32(x) >> k) & M, (k, hex(x))


def test_ashr_agrees_with_the_old_frontends_own_model():
    for k in (0, 1, 4, 7, 16, 31):
        src = _ir(f"  %r = ashr i32 %x, {k}\n  ret i32 %r")
        res = _compile(src)
        for x in (5, M - 20, 0x7FFF0001, 0x80000000):
            _, _, info = OLD.compile_llvm_ir(src, {"x": x})
            assert F.run_in_vm(res, {"x": x}, ticks=350) == info.expected_result, (k, hex(x))


def test_ashr_needs_no_sign_magnitude_machinery_only_library_ops():
    res = _compile(_ir("  %r = ashr i32 %x, 5\n  ret i32 %r"))
    assert {d.opcode for d in res.dag} <= {"lshr", "shl", "sub", "or", "add"}
    assert len(res.dag) == 5


def test_ashr_of_a_computed_value_and_in_a_chain():
    res = _compile(_ir("  %a = add i32 %x, 100\n  %b = ashr i32 %a, 3\n  %c = shl i32 %b, 1\n  ret i32 %c"))
    for x in (0, 1, M - 200, 0x7FFFFF00, 0x80000000, M):
        assert F.run_in_vm(res, {"x": x}, ticks=350) == (((s32((x + 100) & M) >> 3) & M) << 1) & M, hex(x)


def test_ashr_variable_or_out_of_range_amount_is_refused():
    assert "not a compile-time literal" in _refused(
        _ir("  %r = ashr i32 %x, %y\n  ret i32 %r", args="i32 %x, i32 %y"))
    assert "outside 0-31" in _refused(_ir("  %r = ashr i32 %x, 32\n  ret i32 %r"))


# ===========================================================================
# numbered / unnamed SSA values  (#799) -- real clang output is full of `%0`
# ===========================================================================

def _numbered(body, args="i32"):
    """`define i32 @f(i32) { ... }` -- an UNNAMED argument is %0, the unnamed
    entry block takes the next number, so instruction results start at %2."""
    return f"define i32 @f({args}) {{\n{body}\n}}\n"


def test_unnamed_argument_and_results_compile_and_run():
    res = _compile(_numbered("  %2 = add i32 %0, 5\n  %3 = shl i32 %2, 2\n  ret i32 %3"))
    assert list(res.arg_injections) == ["v0"]
    assert [d.name for d in res.dag] == ["v2", "v3"]
    for x in VALUES:
        assert F.run_in_vm(res, {"v0": x}) == (((x + 5) & M) << 2) & M, hex(x)


def test_mixed_named_and_numbered_values_and_arguments():
    res = _compile(_numbered("  %2 = add i32 %0, 5\n  %3 = sub i32 %2, %named\n  %x = shl i32 %3, 2\n"
                             "  %4 = add i32 %x, %0\n  ret i32 %4", args="i32, i32 %named"))
    assert set(res.arg_injections) == {"v0", "named"}
    for a, b in [(10, 3), (0, 0), (M, 1), (100, 200), (7, M)]:
        assert F.run_in_vm(res, {"v0": a, "named": b}) == ((((((a + 5) - b) & M) << 2) & M) + a) & M, (a, b)


def test_numbered_values_through_expansions_icmp_select_ashr():
    res = _compile(_numbered("  %2 = icmp slt i32 %0, 10\n  %3 = select i1 %2, i32 %0, i32 10\n"
                             "  %4 = ashr i32 %3, 2\n  ret i32 %4"))
    for x in (0, 9, 10, 11, M, M - 20):
        assert F.run_in_vm(res, {"v0": x}, ticks=350) == ((s32(x) if s32(x) < 10 else 10) >> 2) & M, x


def test_a_real_name_that_looks_like_a_generated_one_cannot_collide():
    """`%0` becomes `v0`; a REAL value named `%v0` must not be confused with it."""
    res = _compile("define i32 @f(i32 %v0) {\nentry:\n  %0 = add i32 %v0, 1\n  %r = add i32 %0, 10\n  ret i32 %r\n}\n")
    assert len(set(d.name for d in res.dag)) == len(res.dag)
    assert set(res.arg_injections) == {"v0"}
    assert set(d.name for d in res.dag) == {"v0_", "r"}
    for x in VALUES:
        assert F.run_in_vm(res, {"v0": x}) == (x + 11) & M, hex(x)


def test_returning_a_numbered_value_and_an_unrecognised_operand_shape():
    res = _compile(_numbered("  %2 = mul i32 %0, 3\n  ret i32 %2"))
    assert res.result_name == "v2"
    assert F.run_in_vm(res, {"v0": 7}) == 21


def test_fanout_from_a_nano_gate_result_uses_the_gates_own_output_field():
    """points.md #799 regression: the tap logic used to write `downstream_mask`
    onto ANY producer, but a nano gate's output field is `routing_mask` -- so
    fanning a gate result (and/or/xor, or a `select`'s `or`) out to two consumers
    made the VM reject the cell. No earlier test fanned out from a gate."""
    for op, fn in (("and", lambda x: x & 12), ("or", lambda x: x | 12), ("xor", lambda x: x ^ 12)):
        res = _compile(_ir(f"  %a = {op} i32 %x, 12\n  %b = add i32 %a, 1\n  %c = add i32 %a, %b\n  ret i32 %c"))
        for x in VALUES:
            a = fn(x) & M
            assert F.run_in_vm(res, {"x": x}) == (a + a + 1) & M, (op, hex(x))


def test_out_field_comes_from_the_tile_registry():
    import vix_dag_dispatcher_v1 as D
    assert D._out_field("nano") == "routing_mask"
    assert D._out_field("adder") == "downstream_mask"
    with pytest.raises(ValueError):
        D._out_field("branch")            # no single output field -- refuse to guess
