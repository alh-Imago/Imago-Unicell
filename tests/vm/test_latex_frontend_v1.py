"""tests/vm/test_latex_frontend_v1.py -- ledger #1066: the LaTeX front end (integer maths in, a checked UniCell design out).

Correctness first. Three independent oracles:
  * hand-worked answers (known numbers);
  * Python's own big integers: a random formula is written both as LaTeX and as a Python expression, the Python one is evaluated with exact integers and reduced mod 2^32 (a ring
    homomorphism, so it must equal the cells' wrap-around), and the compiled design in the standard VM must agree;
  * the same designs in the flex step simulator and in generated flex RTL (iverilog), streamed at the module's safe spacing.
Also: everything outside the subset is REFUSED with a message (never guessed), and the oracle comparison cannot be bypassed (a corrupted design raises LatexCheckError)."""
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

import latex_frontend_v1 as L  # noqa: E402

M = 0xFFFFFFFF


# ---- known answers ------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("src,vals,want", [
    (r"y = (a + b)^2 - 3c", {"a": 2, "b": 3, "c": 4}, 13),
    (r"2xy + x^3", {"x": 3, "y": 5}, 57),
    (r"5 - x", {"x": 2}, 3),
    (r"-x - -y", {"x": 10, "y": 4}, (-6) & M),
    (r"(a+b)(a+b) + (a+b)", {"a": 1, "b": 2}, 12),
    (r"\left(a-b\right)\cdot c^{10}", {"a": 7, "b": 5, "c": 2}, 2048),
    (r"x^0 + x", {"x": 9}, 10),
    (r"x^{12}", {"x": 2}, 4096),
    (r"3 \times x_1 + x_{12}", {"x_1": 4, "x_12": 5}, 17),
    (r"\alpha\beta + 1", {"alpha": 6, "beta": 7}, 43),
    (r"\mathrm{rate}\,t", {"rate": 5, "t": 8}, 40),
    (r"x", {"x": 77}, 77),
    (r"$x + 1$", {"x": 1}, 2),
])
def test_known_answers(src, vals, want):
    r = L.compile_latex(src)
    assert r.reference(vals) == want
    assert r.run(vals) == want
    assert r.checked > 5


def test_it_wraps_at_32_bits_like_the_cells():
    r = L.compile_latex("x + x")
    assert r.run({"x": 0x80000000}) == 0
    assert L.as_signed(r.run({"x": 0xFFFFFFFF})) == -2
    assert L.compile_latex("x^2").run({"x": 0x10000}) == 0


def test_argument_order_is_first_appearance_and_label_is_kept():
    r = L.compile_latex(r"\mathrm{total} = c + a*b")
    assert r.args == ["c", "a", "b"] and r.label == "total"


# ---- refusals -----------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("src,word", [
    (r"\frac{a}{b}", "division"),
    ("a / b", "division"),
    (r"\sqrt{x}", "square roots"),
    (r"\sin x", "not supported"),
    ("2.5 x", "decimal"),
    ("1,000 x", "comma"),
    ("x^n", "whole number"),
    ("x^{-1}", "negative powers"),
    ("x^{65}", "limit"),
    ("x^23", "braces"),
    ("x^2^3", "ambiguous"),
    ("x_12", "braces"),
    ("(a + b", "not closed"),
    ("a + b)", "closing bracket"),
    ("a +", "ends"),
    ("* a", "needs"),
    ("", "empty"),
    ("x = x + 1", "both sides"),
    ("a = b = c", "single name"),
    ("total = a + b", "mathrm"),
    ("4294967296 x", "32 bits"),
    ("|x|", "absolute"),
    (r"\sum_{i} x", "\\sum"),
    (r"\pi x", "pi"),
    ("a < b", "comparison"),
    (r"\unknown x", "not supported"),
    ("3 + 4", "no variable"),
])
def test_everything_outside_the_subset_is_refused_with_a_reason(src, word):
    with pytest.raises(L.LatexError) as ei:
        L.compile_latex(src)
    assert word in ei.value.format()


def test_error_shows_where():
    with pytest.raises(L.LatexError) as ei:
        L.compile_latex("a + 2.5 b")
    text = ei.value.format()
    assert "a + 2.5 b" in text and text.rstrip().endswith("^")
    assert ei.value.pos == 5


# ---- differential check against Python's own integers --------------------------------------------------------------------------

def _random_formula(rng, names, depth=3):
    """(latex, python) for the same random formula."""
    if depth == 0 or rng.random() < 0.25:
        if rng.random() < 0.6:
            n = rng.choice(names)
            return n, n
        k = rng.randint(0, 40)
        return str(k), str(k)
    kind = rng.choice(["+", "-", "*", "*", "pow", "neg", "group"])
    a = _random_formula(rng, names, depth - 1)
    if kind == "pow":
        e = rng.randint(0, 5)
        return f"({a[0]})^{{{e}}}", f"({a[1]})**{e}"
    if kind == "neg":
        return f"-({a[0]})", f"(-({a[1]}))"
    if kind == "group":
        return f"\\left({a[0]}\\right)", f"({a[1]})"
    b = _random_formula(rng, names, depth - 1)
    if kind == "*":
        sep = rng.choice([" * ", r" \cdot ", r" \times ", " "])
        return f"({a[0]}){sep}({b[0]})", f"(({a[1]})*({b[1]}))"
    return f"({a[0]}) {kind} ({b[0]})", f"(({a[1]}){kind}({b[1]}))"


def test_random_formulas_match_python_integers_in_the_standard_vm():
    rng = random.Random(20261011)
    names = ["a", "b", "c"]
    compiled = refused = 0
    for _ in range(80):
        latex, py = _random_formula(rng, names)
        try:
            r = L.compile_latex(latex, check=False)
        except L.LatexError as e:
            if "no variable" in str(e):
                continue
            refused += 1                       # an honest compiler refusal is not a wrong answer; the count below stops it hiding everything
            continue
        for vals in L.check_vectors(r.args, n_random=3, seed=len(latex)):
            want = eval(py, {"__builtins__": {}}, dict(vals)) & M
            assert r.run(vals) == want, (latex, vals)
        compiled += 1
    assert compiled >= 45, (compiled, refused)


def test_corrupting_the_design_is_caught_by_the_built_in_check(monkeypatch):
    real = L.LatexResult.run

    def wrong(self, values):
        return (real(self, values) + 1) & M
    monkeypatch.setattr(L.LatexResult, "run", wrong)
    with pytest.raises(L.LatexCheckError):
        L.compile_latex("a*b + 1")


# ---- the flex step simulator and generated RTL ----------------------------------------------------------------------------------

FORMULAS = [r"(a + b)^2 - 3c", r"2xy + x^3", r"5 - x"]


@pytest.mark.parametrize("src", FORMULAS)
def test_streamed_through_the_flex_step_simulator_at_safe_spacing(src):
    r = L.compile_latex(src)
    vecs = L.check_vectors(r.args, n_random=2)[:5]
    got = r.stream_step(vecs)
    assert got == [r.reference(v) for v in vecs]


@pytest.mark.parametrize("src", FORMULAS)
def test_generated_flex_rtl_matches_the_oracle(src):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    from fp_block_runner_v1 import run_rtl
    r = L.compile_latex(src)
    vecs = L.check_vectors(r.args, n_random=2)[:6]
    cmap = L._input_cells(r)
    entries = {c: [v[a] & M for v in vecs] for c, a in cmap.items()}
    tmp = tempfile.mkdtemp(prefix="latex_rtl_")
    try:
        got = run_rtl(tmp, "latexf", r.result.records, entries, {"r": "main.r"}, "plain", settle=9000, cycles=6000)["r"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert [g & M for g in got] == [r.reference(v) for v in vecs]


# ---- the command line -------------------------------------------------------------------------------------------------------------

def test_cli_exit_codes_and_output(tmp_path, capsys):
    import latex_cli_v1 as C
    out = tmp_path / "f.icm"
    assert C.main(["(a+b)^2 - 3c", "--set", "a=2", "--set", "b=3", "--set", "c=4", "-o", str(out)]) == 0
    text = capsys.readouterr().out
    assert "result: 13" in text and "all agree" in text and out.exists() and out.stat().st_size > 0
    assert C.main([r"\frac{a}{b}"]) == 1
    assert "division" in capsys.readouterr().err
    assert C.main(["a*b", "--set", "a=1"]) == 2
    assert C.main(["a*b", "--set", "a=x", "--set", "b=1"]) == 2
