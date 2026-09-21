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
