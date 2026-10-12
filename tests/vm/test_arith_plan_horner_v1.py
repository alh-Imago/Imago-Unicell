"""Ledger #1078: the arithmetic plan library and its first plan, Horner (a base stage 'acc' = acc * x + c' repeated once per degree).

Checks: the plan writes the stages it says it does (operation-count formula == what is emitted); the polynomial recogniser expands correctly mod 2^32; a Horner design equals
the formula on random polynomials and values (incl. wrap-around and negative coefficients); the dense polynomial's CELL COUNT grows exactly linearly with the degree (12 per
stage + 2, measured, degrees 1..8); 'auto' keeps the smaller design; real flex and sub RTL agree with the formula."""
import json
import os
import random
import re
import shutil
import sys
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, "..", "..", "nano"), os.path.join(_HERE, "..", "..", "tools")):
    sys.path.insert(0, _p)

import arith_plan_library_v1 as AP  # noqa: E402
import latex_frontend_v1 as L  # noqa: E402
import flex_rtl_harness_v1 as _h  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402

M = 0xFFFFFFFF


def _src(coeffs):
    terms = []
    for k, c in enumerate(coeffs):
        if c:
            terms.append(f"{c}" if k == 0 else (f"{c}x" if k == 1 else f"{c}x^{{{k}}}"))
    return "y = " + " + ".join(terms)


def test_library_lists_horner_and_refuses_unknown():
    assert "horner" in AP.PLANS and AP.lookup("horner").base == "acc' = acc * x + c"
    with pytest.raises(KeyError):
        AP.lookup("nope")


@pytest.mark.parametrize("coeffs", [[1, 2, 3], [0, 0, 1], [5, 0, 0, 7], [0, 1, 0, 1], [4294967295, 3, 1], [9, 0, 0, 0, 0, 2], [1, 1, 1, 1, 1]])
def test_operation_formula_equals_what_is_emitted(coeffs):
    em = L._Emit(core_division=True)
    AP.horner_emit(em, "%v_x", coeffs)
    assert em.n == AP.horner_ops(coeffs), (coeffs, em.lines)


def test_recogniser_expands_mod_2_32():
    p = lambda s: L._poly_of(L.parse_latex(s)[1])
    assert p("y = (x+1)^3") == ("x", {0: 1, 1: 3, 2: 3, 3: 1})
    assert p("y = 3x^2 - 3x^2 + 4")[1] == {0: 4}
    assert p("y = -x^2") == ("x", {2: M})
    assert p("y = (x-1)(x+1)") == ("x", {0: M, 2: 1})
    assert p("y = a x") is None                                   # two variables
    assert p("y = x / 3") is None and p("y = x \\bmod 3") is None


def test_random_polynomials_equal_the_formula_on_random_words():
    rng = random.Random(1078)
    for _ in range(25):
        deg = rng.randint(2, 12)
        coeffs = [rng.choice([0, 1, rng.randint(0, M), rng.randint(0, 9)]) for _ in range(deg)] + [rng.randint(2, M)]
        label, tree = L.parse_latex(_src(coeffs))
        ir, args = L.to_llvm(tree, polynomial="horner")
        for _v in range(6):
            x = rng.choice([0, 1, M, 1 << 31, rng.randint(0, M)])
            want = sum(c * pow(x, k, 1 << 32) for k, c in enumerate(coeffs)) & M
            assert L.eval_ir(ir, {args[0]: x}) == want, (coeffs, x)


def test_dense_cell_count_is_exactly_linear_in_the_degree():
    counts = []
    for n in range(1, 9):
        r = L.compile_latex(_src([k + 2 for k in range(n + 1)]), polynomial="horner")
        counts.append(r.cells)
    assert counts == [12 * n + 2 for n in range(1, 9)], counts


def test_horner_is_checked_on_the_vm_and_matches_direct():
    for src in ["y = 3x^2 + 2x + 1", "y = x^{7}", "y = 2x^5 - 3x^3 + x + 9"]:
        h, d = L.compile_latex(src, polynomial="horner"), L.compile_latex(src, polynomial="direct")
        assert h.checked > 0 and d.checked > 0
        for v in ({"x": 0}, {"x": 1}, {"x": 12345}, {"x": M}):
            assert h.run(v) == d.run(v) == h.reference(v)


def test_auto_keeps_the_smaller_design():
    for src in ["y = 3x^2 + 2x + 1", "y = x^{7}", "y = (x+1)^3", "y = x^4 + x^3 + x^2 + x + 1", "y = a^2 + b", "y = x^2"]:
        a, h, d = (L.compile_latex(src, polynomial=m).cells for m in ("auto", "horner", "direct"))
        assert a == min(h, d), (src, a, h, d)
    assert L.compile_latex("y = 3x^2 + 2x + 1").cells < L.compile_latex("y = 3x^2 + 2x + 1", polynomial="direct").cells     # measured: 26 against 44
    assert L.compile_latex("y = (x+1)^3").cells == L.compile_latex("y = (x+1)^3", polynomial="direct").cells                  # direct wins here (23 against 32)


def test_polynomial_option_validated():
    with pytest.raises(L.LatexError):
        L.compile_latex("y = x^2", polynomial="newton")
    with pytest.raises(L.LatexError):
        L.to_llvm(L.parse_latex("y = x^2")[1], polynomial="auto")


def test_a_polynomial_inside_a_bigger_formula_is_placed_as_the_plan():
    r = L.compile_latex("y = (3x^2 + 2x + 1) / z", polynomial="horner")
    assert r.checked > 0 and "udiv" in r.ir and r.ir.count(" = mul ") == 2


_VECS = [{"x": 0}, {"x": 1}, {"x": 7}, {"x": 12345}, {"x": M}, {"x": 1 << 31}, {"x": 65537}, {"x": 99}]


def test_horner_design_as_generated_flex_rtl():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    r = L.compile_latex("y = 3x^2 + 2x + 1", polynomial="horner")
    tmp = tempfile.mkdtemp(prefix="horner_")
    try:
        d, res = _h.build(tmp, "lx", r.result.records, 32)
        assert res.returncode == 0, (res.stderr or res.stdout)[:500]
        top = json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"]
        text = open(os.path.join(d, top + ".v")).read()
        cmap = L._input_cells(r)
        streams = {}
        for name in sorted(set(re.findall(r"\bin_(\w+)_data", text))):
            cid = [c for c in cmap if c.replace(".", "_") == name]
            assert len(cid) == 1
            streams[name] = [v[cmap[cid[0]]] & M for v in _VECS]
        _, got = _h.run_level(d, streams, "plain", 3, settle=600, cycles=60000, width=32)
        (out,) = got.values()
        assert out == [r.reference(v) for v in _VECS], out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_horner_design_as_generated_sub_rtl():
    import test_sub_div_v1 as _sub   # the sub simulator lives with the sub divider tests
    assert shutil.which("iverilog") and shutil.which("vvp")
    r = L.compile_latex("y = 3x^2 + 2x + 1", polynomial="horner")
    tmp = tempfile.mkdtemp(prefix="hornersub_")
    try:
        icm = os.path.join(tmp, "x.icm")
        IcmV3File(name="x", records=r.result.records).save(icm)
        out = os.path.join(tmp, "g")
        p = _h.cli("-s", "sub", "--icm", icm, "--output", out)
        assert p.returncode == 0, (p.stderr or p.stdout)[:500]
        top = json.load(open(os.path.join(out, "ASSEMBLY.json")))["top"]
        text = open(os.path.join(out, top + ".v")).read()
        cmap = L._input_cells(r)
        ins = re.findall(r"input\s+wire\s+\[31:0\]\s+in_(\w+)_data", text)
        items = []
        for v in _VECS:
            it = {}
            for n in ins:
                cid = [c for c in cmap if c.replace(".", "_") == n]
                assert len(cid) == 1
                it[n] = v[cmap[cid[0]]] & M
            items.append(it)
        got, _ = _sub.simulate(out, items)
        assert [g[1] for g in got] == [r.reference(v) for v in _VECS], got
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
