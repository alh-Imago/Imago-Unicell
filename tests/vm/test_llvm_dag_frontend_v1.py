"""tests/vm/test_llvm_dag_frontend_v1.py — points.md #795: real tests for
the first frontend feeding `compile_dag()`. Every positive test runs the
compiled fabric through the real VM and checks the result against an
INDEPENDENT Python model of the same program (never against
`compile_dag()`'s own output), and the shared programs are additionally
cross-checked against the OLD frontend's own independent expected-result
model.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import pytest  # noqa: E402

import llvm_dag_frontend_v1 as F  # noqa: E402
import llvm_ir_frontend_v1 as OLD  # noqa: E402
from vix_dag_dispatcher_v1 import compile_dag, DagInstr, DagOperand  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

M = 0xFFFFFFFF
EDGES = [0, 1, 7, 100, 2 ** 31, M]


def _ir(body: str, args: str = "i32 %x") -> str:
    return f"define i32 @f({args}) {{\nentry:\n{body}\n}}\n"


def _compile(src):
    res, diags = F.compile_llvm_via_dag(src)
    assert diags == [], [d.problem for d in diags]
    assert res is not None
    return res


def _problems(src):
    res, diags = F.compile_llvm_via_dag(src)
    assert res is None
    assert diags, "expected at least one diagnostic"
    return " | ".join(d.problem for d in diags), diags


# ---------------------------------------------------------------------------
# The proof case (scope note item 8).
# ---------------------------------------------------------------------------

PROOF = _ir("  %a = add i32 %x, 5\n  %b = sub i32 %a, 3\n  ret i32 %b")


def test_proof_case_add_then_sub_matches_independent_model_across_edges():
    res = _compile(PROOF)
    for x in EDGES:
        assert F.run_in_vm(res, {"x": x}) == ((x + 5) - 3) & M, x


def test_proof_case_agrees_with_old_frontends_own_model():
    res = _compile(PROOF)
    for x in (10, 0, 7, 12345):
        _, _, info = OLD.compile_llvm_ir(PROOF, {"x": x})
        assert F.run_in_vm(res, {"x": x}) == info.expected_result


def test_arguments_are_determined_not_baked_in():
    """One compile, many inputs: the argument is an injection site, not
    a compile-time constant (scope note item 2's DETERMINED case)."""
    res = _compile(PROOF)
    assert res.arg_injections == {"x": [res.arg_injections["x"][0]]}
    assert len(res.arg_injections["x"]) == 1
    assert F.run_in_vm(res, {"x": 1}) == 3
    assert F.run_in_vm(res, {"x": 2}) == 4


def test_original_names_are_preserved_and_rewrites_recorded():
    """Scope item 7: `%name` is used directly, and the sub->add lowering
    is recorded rather than silent."""
    res = _compile(PROOF)
    assert [d.name for d in res.dag] == ["a", "b"]
    assert set(res.positions) == {"a", "b"}
    assert res.result_name == "b"
    assert len(res.rewrites) == 1 and "%b" in res.rewrites[0] and "0xfffffffd" in res.rewrites[0]


# ---------------------------------------------------------------------------
# Real DAG shapes.
# ---------------------------------------------------------------------------

def test_diamond_fanout_plus_convergence():
    src = _ir("  %t1 = add i32 %x, 5\n  %t2 = add i32 %t1, 10\n  %t3 = add i32 %t1, %t2\n  ret i32 %t3")
    res = _compile(src)
    for x in EDGES:
        assert F.run_in_vm(res, {"x": x}) == ((x + 5) + (x + 5 + 10)) & M, x
    for x in (1, 9):
        _, _, info = OLD.compile_llvm_ir(src, {"x": x})
        assert F.run_in_vm(res, {"x": x}) == info.expected_result


def test_two_arguments_noncommutative_convergence_in_both_argument_orders():
    """Both leaves are genuinely determined, so arrival order is unknowable
    -- the SEQUENCER path (#774) must be selected AND its order applied."""
    src = _ir("  %p = add i32 %x, 5\n  %q = add i32 %y, 10\n  %r = sub i32 %p, %q\n  ret i32 %r",
              args="i32 %x, i32 %y")
    res = _compile(src)
    assert "r" in res.seq_orders
    for x, y in [(20, 3), (3, 20), (0, 0), (M, 1), (1, M)]:
        assert F.run_in_vm(res, {"x": x, "y": y}) == ((x + 5) - (y + 10)) & M, (x, y)


def test_one_argument_feeding_two_instructions_gets_two_injection_sites():
    src = _ir("  %a = add i32 %x, 1\n  %b = add i32 %x, 2\n  %c = add i32 %a, %b\n  ret i32 %c")
    res = _compile(src)
    assert len(res.arg_injections["x"]) == 2
    for x in EDGES:
        assert F.run_in_vm(res, {"x": x}) == ((x + 1) + (x + 2)) & M, x


def test_same_value_as_both_operands():
    src = _ir("  %a = add i32 %x, 4\n  %c = add i32 %a, %a\n  ret i32 %c")
    res = _compile(src)
    for x in EDGES:
        assert F.run_in_vm(res, {"x": x}) == ((x + 4) * 2) & M, x


def test_deeper_sub_chain_lowers_every_constant_subtraction():
    src = _ir("  %a = add i32 %x, 100\n  %b = sub i32 %a, 8\n  %c = sub i32 %b, 1\n  ret i32 %c")
    res = _compile(src)
    assert len(res.rewrites) == 2
    for x in EDGES:
        assert F.run_in_vm(res, {"x": x}) == ((x + 100) - 8 - 1) & M, x


@pytest.mark.parametrize("op,fn,k", [
    ("add", lambda x, k: x + k, 9),
    ("mul", lambda x, k: x * k, 3),
    ("and", lambda x, k: x & k, 12),
    ("or", lambda x, k: x | k, 12),
    ("xor", lambda x, k: x ^ k, 12),
])
def test_every_library_opcode_end_to_end(op, fn, k):
    res = _compile(_ir(f"  %r = {op} i32 %x, {k}\n  ret i32 %r"))
    for x in EDGES:
        assert F.run_in_vm(res, {"x": x}) == fn(x, k) & M, (op, x)


# ---------------------------------------------------------------------------
# Source-agnostic symbol resolution (scope item 2) -- exercised directly,
# because LLVM's own verifier prevents most of these from ever reaching it.
# ---------------------------------------------------------------------------

def _op(n):
    return F.SourceOperand(kind="name", name=n)


def _lit(v):
    return F.SourceOperand(kind="literal", value=v)


def test_resolution_classifies_argument_result_and_literal():
    prog, diags = F.resolve_symbols(["x"], [
        F.SourceInstr("a", "add", [_op("x"), _lit(5)]),
        F.SourceInstr("b", "add", [_op("a"), _lit(1)]),
    ])
    assert diags == []
    assert [o.kind for o in prog.dag[0].operands] == ["dynamic", "const"]
    assert [o.kind for o in prog.dag[1].operands] == ["ref", "const"]
    assert prog.arg_uses == {"x": [("a", 0)]}


def test_resolution_undeclared_name():
    prog, diags = F.resolve_symbols(["x"], [F.SourceInstr("a", "add", [_op("nope"), _lit(1)])])
    assert prog is None and any("not declared" in d.problem for d in diags)


def test_resolution_use_before_definition():
    prog, diags = F.resolve_symbols([], [
        F.SourceInstr("a", "add", [_op("b"), _lit(1)]),
        F.SourceInstr("b", "add", [_lit(1), _lit(1)]),
    ])
    assert prog is None and any("before it is defined" in d.problem for d in diags)


def test_resolution_duplicate_definition_and_argument_shadowing():
    _, diags = F.resolve_symbols(["x"], [
        F.SourceInstr("a", "add", [_op("x"), _lit(1)]),
        F.SourceInstr("a", "add", [_op("x"), _lit(2)]),
        F.SourceInstr("x", "add", [_lit(1), _lit(2)]),
    ])
    text = " | ".join(d.problem for d in diags)
    assert "defined more than once" in text and "also a function argument" in text


def test_resolution_collects_every_problem_not_just_the_first():
    _, diags = F.resolve_symbols(["x"], [
        F.SourceInstr("a", "add", [_op("ghost1"), _lit(1)]),
        F.SourceInstr("b", "add", [_op("ghost2"), _lit(1)]),
        F.SourceInstr("a", "add", [_op("x"), _lit(1)]),
    ])
    assert len(diags) >= 3


# ---------------------------------------------------------------------------
# Extraction and capability diagnostics: a clear refusal, never a silent
# miscompile.
# ---------------------------------------------------------------------------

def test_unnamed_ssa_value_is_refused_and_never_misread_as_a_literal():
    """Regression for a real trap: llvmlite reports name '' for BOTH a
    literal and a reference to an unnamed temporary, and str() of the
    latter is the whole defining instruction whose LAST TOKEN ('5') looks
    like an integer. A naive last-token parse would compile `sub 100, 5`."""
    text, diags = _problems(_ir("  %0 = add i32 %x, 5\n  %b = sub i32 100, %0\n  ret i32 %b"))
    assert "unnamed" in text


def test_control_flow_is_refused():
    src = ("define i32 @f(i32 %x) {\nentry:\n  br label %next\nnext:\n"
           "  %a = add i32 %x, 1\n  ret i32 %a\n}\n")
    text, _ = _problems(src)
    assert "basic blocks" in text


def test_multiple_functions_refused():
    src = ("define i32 @f(i32 %x) {\nentry:\n  %a = add i32 %x, 1\n  ret i32 %a\n}\n"
           "define i32 @g(i32 %x) {\nentry:\n  %a = add i32 %x, 2\n  ret i32 %a\n}\n")
    text, _ = _problems(src)
    assert "exactly one function" in text


def test_invalid_ir_refused():
    text, _ = _problems("this is not llvm ir")
    assert text


def test_non_i32_argument_refused():
    src = "define i32 @f(i64 %x) {\nentry:\n  %a = add i32 1, 2\n  ret i32 %a\n}\n"
    text, _ = _problems(src)
    assert "i64" in text


def test_non_i32_instruction_refused():
    src = "define i64 @f(i32 %x) {\nentry:\n  %a = add i64 5, 6\n  ret i64 %a\n}\n"
    text, _ = _problems(src)
    assert "i64" in text


def test_opcode_without_library_entry_names_the_escalation_ladder():
    text, diags = _problems(_ir("  %a = shl i32 %x, 2\n  ret i32 %a"))
    assert "no library entry for opcode `shl`" in text
    assert any("#752" in (d.why + (d.suggestion or "")) for d in diags)


def test_returning_an_argument_directly_is_refused():
    text, _ = _problems(_ir("  ret i32 %x"))
    assert "not the result of any instruction" in text


def test_two_literal_operands_refused():
    text, _ = _problems(_ir("  %a = add i32 3, 4\n  ret i32 %a"))
    assert "both operands are literals" in text


def test_literal_minuend_is_refused_not_silently_miscompiled():
    text, diags = _problems(_ir("  %b = sub i32 100, %x\n  ret i32 %b"))
    assert "FIRST operand" in text
    assert any("#770" in d.why for d in diags)


# ---------------------------------------------------------------------------
# The backend limitation this frontend found, documented as it actually is.
# ---------------------------------------------------------------------------

def _backend_sub(instrs, target, x):
    icm, pos, dyn, seq = compile_dag(instrs)
    recs, _ = icm.flatten()
    g = SuperGrid(recs)
    for _label, r, c in dyn:
        g.cells[(r, c)].ram_data_reg = x
        g.cells[(r, c)].ram_data_valid = True
    for _ in range(600):
        g.tick()
    return g.cells[pos[target]].adder_out_buffer


def test_backend_plain_chain_sub_ignores_operand_order_known_limitation():
    """points.md #795 -- a documented NEGATIVE result, in the same spirit
    as #764/#775. `compile_dag()`'s plain-chain path gives a real+constant
    pair of a non-commutative op no operand-order guarantee: whichever
    arrives first becomes the minuend (#770's hazard). Observed, x=50,
    c=8, a = x+100:

        sub(dynamic, const) -> x-c   (right, by arrival luck)
        sub(const, dynamic) -> x-c   (WRONG: wanted c-x)
        sub(ref, const)     -> c-a   (WRONG: wanted a-c)
        sub(const, ref)     -> c-a   (right, by arrival luck)

    Asserts the CURRENT behaviour so the limitation cannot be forgotten
    or silently regress differently. If the backend is ever given a real
    ordering guarantee, these assertions should be FLIPPED to the correct
    values, and `_lower_for_backend()` / the literal-minuend diagnostic
    in the frontend can then be reconsidered."""
    x, c = 50, 8
    pre = DagInstr("a", "add", [DagOperand("dynamic"), DagOperand("const", value=100)])
    assert _backend_sub([DagInstr("t", "sub", [DagOperand("dynamic"), DagOperand("const", value=c)])], "t", x) == x - c
    assert _backend_sub([DagInstr("t", "sub", [DagOperand("const", value=c), DagOperand("dynamic")])], "t", x) == x - c
    a = x + 100
    assert _backend_sub([pre, DagInstr("t", "sub", [DagOperand("ref", ref_name="a"), DagOperand("const", value=c)])],
                        "t", x) == (c - a) & M
    assert _backend_sub([pre, DagInstr("t", "sub", [DagOperand("const", value=c), DagOperand("ref", ref_name="a")])],
                        "t", x) == (c - a) & M
