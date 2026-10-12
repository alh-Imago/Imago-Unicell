"""Ledger #1084: the numbers and refusal messages quoted in docs/teaching/latex_writing_guide.md are real.
If a compiler change moves one of them, this fails and the guide must be corrected (not the test quietly)."""
import os
import re
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, "..", "..", "nano")):
    sys.path.insert(0, _p)

import latex_frontend_v1 as L  # noqa: E402

GUIDE = os.path.join(_HERE, "..", "..", "docs", "teaching", "latex_writing_guide.md")


def _cells(src, **kw):
    return L.compile_latex(src, check=False, **kw).cells


def test_reduction_pairs_quoted_in_the_guide():
    assert _cells(r"y = \sum_{i=1}^{8} i x") == 284 and _cells("y = 36 x") == 8
    assert _cells("y = a b + a c + a d + a e") == 89 and _cells("y = a (b + c + d + e)") == 26
    assert _cells("y = x^2 (x+1)^2") == 32 == _cells("y = x^4 + 2x^3 + x^2")


def test_polynomial_and_division_counts_quoted_in_the_guide():
    assert _cells("y = 3x^2 + 2x + 1") == 26 and _cells("y = 3x^2 + 2x + 1", polynomial="direct") == 44
    assert _cells("y = x^7") == 38 and _cells("y = x^7", polynomial="direct") == 61
    assert _cells("y = (x+1)^3") == 23 and _cells("y = (x+1)^3", polynomial="horner") == 32
    assert _cells("y = a / 7") == 8 and _cells(r"y = a \bmod 7") == 8
    assert _cells(r"y = \sum_{i=1}^{3} a_i b_i") == 20 == 7 * 3 - 1


def test_matrix_counts_quoted_in_the_guide():
    assert L.compile_matrix_latex("A_{ij} = i j", 3, 3, check=False).cells == 68
    assert L.compile_matrix_latex("A_{ij}", 2, 3, check=False).cells == 44
    r = L.compile_matrix_latex("A_{ij} = i + j", 2, 3, check=False, then=[("B_{ij} = i j", 2, 2)])
    assert r.cells == 73


@pytest.mark.parametrize("src,words", [
    ("y = x^23", "write x^{23} with braces"),
    (r"y = \sqrt{x}", "square roots are not supported"),
    ("y = a / b c", "ambiguous"),
    (r"y = \sum_{i=1}^{n} i", "whole number written out"),
    ("y = x^{-1}", "negative powers mean division"),
])
def test_refusals_quoted_in_the_guide(src, words):
    with pytest.raises(L.LatexError) as e:
        L.compile_latex(src, check=False)
    assert words in str(e.value)
    assert words in open(GUIDE, encoding="utf-8").read()


def test_guide_is_a_tab_of_the_teaching_manual():
    b = open(os.path.join(_HERE, "..", "..", "docs", "build_teaching_manual.py"), encoding="utf-8").read()
    assert "docs/teaching/latex_writing_guide.md" in b and 'id":"formula"' in b
    assert re.search(r"sec-formula", open(os.path.join(_HERE, "..", "..", "docs", "teaching_manual.html"), encoding="utf-8").read())
