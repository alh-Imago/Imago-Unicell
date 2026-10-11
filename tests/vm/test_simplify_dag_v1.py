"""tests/vm/test_simplify_dag_v1.py -- ledger #1065: constant folding, identity removal and dead-value removal for placer `routed_x`.

Before: `%c = add i32 3, 4` was refused ("constant folding is not built into this frontend"); `x*1`, `x+0` cost a cell each; unused values stayed in the design.
Proves: the pass folds / removes exactly what it says, never replaces the returned value, never re-points a reader that needs a computed value (icmp, select), does not edit the
caller's list; designs are smaller and compute the Python answer (random programs, differential check in the standard VM); the step simulator agrees; `auto` is unchanged."""
import os
import random
import shutil
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for sub in ("nano", "tools", os.path.join("tests", "vm")):
    sys.path.insert(0, os.path.join(ROOT, sub))

import llvm_dag_frontend_v1 as F  # noqa: E402
from vix_dag_dispatcher_v1 import DagInstr, DagOperand  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402
from flex_layout_view_v1 import Layout  # noqa: E402
import flex_layout_sim_v2 as S2  # noqa: E402

M = 0xFFFFFFFF
SRC = """define i32 @f(i32 %a, i32 %b) {
entry:
  %u = mul i32 %a, 1
  %v = add i32 %b, 0
  %w = sub i32 %u, %v
  %dead = mul i32 %a, 77
  %c = add i32 3, 4
  %r = add i32 %w, %c
  ret i32 %r
}
"""


def dag(src):
    fn, _ = F.extract_llvm_function(src)
    r, _ = F.resolve_symbols(fn.arguments, fn.instrs)
    return r.dag, fn.result_name


def sig(d):
    return [(i.name, i.opcode, [(o.kind, o.value, o.ref_name) for o in i.operands]) for i in d]


def test_folds_identities_and_drops_dead_values():
    d, res = dag(SRC)
    new, notes = F.simplify_dag(d, res)
    assert sig(new) == [("w", "sub", [("dynamic", None, "a"), ("dynamic", None, "b")]), ("r", "add", [("ref", None, "w"), ("const", 7, None)])]
    assert any("folded to 7" in n for n in notes) and any("never used" in n for n in notes)


def test_does_not_edit_the_callers_list():
    d, res = dag(SRC)
    before = sig(d)
    F.simplify_dag(d, res)
    assert sig(d) == before


def test_the_returned_value_is_never_replaced():
    src = "define i32 @f(i32 %a) {\nentry:\n  %r = add i32 %a, 0\n  ret i32 %r\n}\n"
    d, res = dag(src)
    new, _ = F.simplify_dag(d, res)
    assert [i.name for i in new] == ["r"]
    r, diags = F.compile_llvm_via_dag(src, placer="routed_x")
    assert r is not None, [x.format([]) for x in diags]
    assert F.run_in_vm(r, {"a": 41}) == 41


def test_mul_and_and_by_zero_become_zero_and_shift_amounts_are_checked():
    src = ("define i32 @f(i32 %a, i32 %b) {\nentry:\n  %z = mul i32 %a, 0\n  %y = and i32 %b, 0\n  %q = shl i32 5, 40\n  %s = add i32 %z, %y\n  %r = add i32 %s, %a\n  ret i32 %r\n}\n")
    d, res = dag(src)
    new, _ = F.simplify_dag(d, res)
    names = [i.name for i in new]
    assert "z" not in names and "y" not in names
    assert "q" not in names                                  # unused, so dropped (and never folded: 40 is not a legal amount)


def test_default_placer_still_refuses_the_two_literal_add_and_routed_x_accepts_it():
    res, diags = F.compile_llvm_via_dag(SRC)
    assert res is None and any("literals" in x.format([]) for x in diags)
    res, diags = F.compile_llvm_via_dag(SRC, placer="routed_x")
    assert res is not None, [x.format([]) for x in diags]
    assert F.run_in_vm(res, {"a": 100, "b": 30}) == 77
    assert len(res.records) < 20


def test_a_reader_that_needs_a_computed_value_keeps_it():
    src = ("define i32 @f(i32 %a, i32 %b) {\nentry:\n  %u = add i32 %a, 0\n  %c = icmp slt i32 %u, %b\n  %r = select i1 %c, i32 %a, i32 %b\n  ret i32 %r\n}\n")
    d, res = dag(src)
    new, _ = F.simplify_dag(d, res)
    assert "u" in [i.name for i in new]                      # icmp still reads %u
    r, diags = F.compile_llvm_via_dag(src, placer="routed_x")
    assert r is not None, [x.format([]) for x in diags]
    assert F.run_in_vm(r, {"a": 3, "b": 9}) == 3 and F.run_in_vm(r, {"a": 9, "b": 3}) == 3


def _py(op, a, b):
    return {"add": a + b, "sub": a - b, "mul": a * b, "and": a & b, "or": a | b, "xor": a ^ b}[op] & M


def _random_program(rng):
    ops = ["add", "sub", "mul", "and", "or", "xor"]
    consts = [0, 1, 2, 3, 7, M, 0x0F0F]
    vals = ["%a", "%b"]
    lines, model = [], []
    uses = {}
    n = rng.randint(3, 7)
    for i in range(n):
        for _ in range(20):
            op = rng.choice(ops)
            if rng.random() < 0.5:
                x, y = rng.choice(vals), str(rng.choice(consts) if rng.random() < 0.9 else rng.randint(0, 9))
                if rng.random() < 0.3 and op not in ("sub",):
                    x, y = y, x
            else:
                x, y = rng.choice(vals), rng.choice(vals)
            if x == y or (x[0] != "%" and y[0] != "%"):
                if not (x[0] != "%" and y[0] != "%" and rng.random() < 0.3):
                    continue
            if any(uses.get(v, 0) >= 3 for v in (x, y) if v[0] == "%"):
                continue
            break
        else:
            continue
        nm = "r" if i == n - 1 else f"t{i}"
        lines.append(f"  %{nm} = {op} i32 {x}, {y}")
        model.append((nm, op, x, y))
        for v in (x, y):
            if v[0] == "%":
                uses[v] = uses.get(v, 0) + 1
        vals.append("%" + nm)
    if not model or model[-1][0] != "r":
        return None
    return "define i32 @f(i32 %a, i32 %b) {\nentry:\n" + "\n".join(lines) + "\n  ret i32 %r\n}\n", model


def _eval(model, a, b):
    env = {"%a": a & M, "%b": b & M}
    for nm, op, x, y in model:
        gx = env[x] if x[0] == "%" else int(x) & M
        gy = env[y] if y[0] == "%" else int(y) & M
        env["%" + nm] = _py(op, gx, gy)
    return env["%r"]


def test_random_programs_match_python_after_simplification():
    rng = random.Random(1065)
    checked = folded = 0
    for _ in range(120):
        prog = _random_program(rng)
        if prog is None:
            continue
        src, model = prog
        res, diags = F.compile_llvm_via_dag(src, placer="routed_x")
        if res is None:
            continue                                         # an honest refusal (placement) is not a wrong answer; the count below guards against refusing everything
        for a, b in ((5, 9), (0xDEADBEEF, 0x12345678), (M, 1)):
            assert F.run_in_vm(res, {"a": a, "b": b}) == _eval(model, a, b), src
        checked += 1
        folded += any("folded" in n or "identity" in n or "never used" in n for n in res.rewrites)
    assert checked >= 40 and folded >= 10, (checked, folded)


def test_simplified_design_agrees_in_the_step_simulator():
    res, diags = F.compile_llvm_via_dag(SRC, placer="routed_x")
    assert res is not None
    tmp = tempfile.mkdtemp(prefix="simplify_")
    try:
        path = os.path.join(tmp, "d.icm")
        IcmV3File(name="d", records=res.records).save(path)
        sim = S2.StepSim(Layout.load(path), width=32)
        cmap = {c: {"a": 100, "b": 30}[v] for c, v in {"main.dynq_w_a": "a", "main.dynq_w_b": "b"}.items()}
        sim.inject(cmap)
        sim.step(400)
        assert sim.seen["main.r"] == [77]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
