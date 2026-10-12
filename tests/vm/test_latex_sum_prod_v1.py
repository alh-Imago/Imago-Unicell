"""Ledger #1079: fixed-range \\sum and \\prod in the LaTeX front end (the range is written out as a chain; plans `sum_chain` / `product_chain`), dot products by subscript."""
import os
import random
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, "..", "..", "nano")):
    sys.path.insert(0, _p)

import arith_plan_library_v1 as AP  # noqa: E402
import latex_frontend_v1 as L  # noqa: E402

M = 0xFFFFFFFF


def _run(src, vals):
    r = L.compile_latex(src)
    return r, r.run(vals), r.reference(vals)


def test_sums_and_products_evaluate_like_python():
    r, got, want = _run(r"y = \sum_{i=1}^{3} a_i b_i", {"a_1": 2, "a_2": 3, "a_3": 4, "b_1": 5, "b_2": 6, "b_3": 7})
    assert got == want == 56 and r.checked > 0
    assert _run(r"y = \sum_{i=0}^{4} x^i", {"x": 3})[1:] == (121, 121)
    assert _run(r"y = \prod_{i=1}^{3} (x+i)", {"x": 2})[1:] == (60, 60)
    assert _run(r"y = 2\sum_{i=1}^{3} i x + 1", {"x": 5})[1:] == (61, 61)
    assert _run(r"y = \sum_{i=1}^{3} \sum_{j=1}^{2} i j x", {"x": 7})[1:] == (126, 126)           # nested: (1+2+3)(1+2) x
    assert _run(r"y = x + \sum_{i=2}^{2} i x", {"x": 4})[1:] == (12, 12)                            # a one-term range


def test_the_body_is_the_next_term_and_brackets_group_a_sum_of_terms():
    assert _run(r"y = \sum_{i=1}^{3} i x + 1", {"x": 2})[1:] == (13, 13)                            # (1+2+3)*2 + 1: the +1 is outside
    assert _run(r"y = \sum_{i=1}^{3} (i x + 1)", {"x": 2})[1:] == (15, 15)                          # brackets pull it inside


def test_wraparound_and_random_values_agree_with_python():
    rng = random.Random(1079)
    for src, names in [(r"y = \sum_{i=1}^{4} a_i b_i", [f"{p}_{k}" for k in range(1, 5) for p in "ab"]), (r"y = \prod_{i=1}^{5} a_i", [f"a_{k}" for k in range(1, 6)])]:
        r = L.compile_latex(src)
        for _ in range(3):
            v = {n: rng.choice([0, 1, M, rng.randint(0, M)]) for n in names}
            assert r.run(v) == r.reference(v)


@pytest.mark.parametrize("src,why", [
    (r"y = \sum_{i=1}^{n} i x", "whole number"),
    (r"y = \sum_{i=1}^{0} x", "empty"),
    (r"y = \sum_{i=1}^{65} x", "limit"),
    (r"y = \sum_{i=1}^10 x", "braces"),
    (r"y = \sum x", "range"),
    (r"y = \sum_{1=1}^{3} x", "letter"),
    (r"y = \sum_{i}^{3} x", "equals"),
    (r"y = \sum_{i=1} x", "last value"),
])
def test_malformed_ranges_are_refused_with_a_reason(src, why):
    with pytest.raises(L.LatexError) as e:
        L.parse_latex(src)
    assert why in str(e.value).lower(), str(e.value)


def test_the_index_is_local_to_the_sum_and_exponent_must_be_the_index():
    r = L.compile_latex(r"y = i + \sum_{i=1}^{2} i x")                       # the i outside is an ordinary variable
    assert r.args[0] == "i" and "x" in r.args
    with pytest.raises(L.LatexError):
        L.parse_latex(r"y = \sum_{i=1}^{3} x^n")


def test_chain_plans_are_the_shape_the_front_end_writes():
    for name, src, opc in [("sum_chain", r"y = \sum_{i=1}^{5} a_i", "add"), ("product_chain", r"y = \prod_{i=1}^{5} a_i", "mul")]:
        em = L._Emit(core_division=True)
        AP.lookup(name).emit(em, [f"%v_a_{k}" for k in range(1, 6)])
        assert em.n == AP.lookup(name).ops([0] * 5) == 4
        ir, _ = L.to_llvm(L.parse_latex(src)[1])
        body = [ln.strip() for ln in ir.splitlines() if " = " in ln]
        assert [ln.split(" = ")[1].replace("%r", "%_t4") for ln in body] == [ln.split(" = ")[1] for ln in em.lines]


def test_sum_chain_is_exactly_linear_and_a_tree_is_worse():
    cells = [L.compile_latex(r"y = \sum_{i=1}^{%d} a_i" % n).cells for n in range(2, 10)]
    assert cells == [6 * n - 4 for n in range(2, 10)], cells
    tree = L.compile_latex("y = ((a+b)+(c+d))+((e+f)+(g+h))").cells
    assert tree > L.compile_latex(r"y = \sum_{i=1}^{8} a_i").cells
