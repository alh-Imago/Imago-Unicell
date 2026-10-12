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
    assert "result: 13" in text and "agree" in text and "compiled design, run in the VM" in text and out.exists() and out.stat().st_size > 0
    assert C.main([r"\sqrt{a}"]) == 1
    assert "square roots" in capsys.readouterr().err
    assert C.main(["a*b", "--set", "a=1"]) == 2
    assert C.main(["a*b", "--set", "a=x", "--set", "b=1"]) == 2


# ================================================================================================================================
# Division and remainder (ledger #1067): unsigned whole numbers, rounded down; x div 0 = all ones; x mod 0 = x.
# The substrate has no divider; the front end spreads 32 restoring-division steps out in space (a loop unrolled in cells). The design is huge (about 27,000 cells), so the three layers
# of evidence are: (1) the generated operations against the oracle at FULL width (fast, thousands of vectors, every boundary), (2) the SAME generator at 3 and 4 steps through
# the VM, the flex step simulator and generated flex RTL (plumbing: the compiler, the placer and the cells execute exactly this operation mix), (3) power-of-two divisors, which are
# a shift or a mask, at full width through every layer.
# ================================================================================================================================

DIV_FORMS = [r"x / y", r"x \div y", r"\frac{x}{y}"]


@pytest.mark.parametrize("src", DIV_FORMS)
def test_all_three_division_spellings_are_the_same_formula(src):
    _, tree = L.parse_latex(src)
    assert tree == L.Div(L.Var("x"), L.Var("y"))


def test_division_binds_like_multiplication_and_leans_left():
    assert L.parse_latex("a / b / c")[1] == L.Div(L.Div(L.Var("a"), L.Var("b")), L.Var("c"))
    assert L.parse_latex("a * b / c")[1] == L.Div(L.Bin("*", L.Var("a"), L.Var("b")), L.Var("c"))
    assert L.parse_latex(r"a + b \bmod c")[1] == L.Bin("+", L.Var("a"), L.Mod(L.Var("b"), L.Var("c")))
    assert L.parse_latex(r"2 \frac{a}{b}")[1] == L.Bin("*", L.Num(2), L.Div(L.Var("a"), L.Var("b")))


@pytest.mark.parametrize("src,word", [
    ("a / b c", "ambiguous"),
    (r"a \bmod b c", "ambiguous"),
    (r"\frac{a}", "missing"),
    (r"\frac a b", "braced"),
    (r"\frac{a}{b", "not closed"),
    (r"a \pmod{b}", "bmod"),
    ("a % b", "comment"),
])
def test_division_syntax_that_is_ambiguous_or_malformed_is_refused(src, word):
    with pytest.raises(L.LatexError) as ei:
        L.compile_latex(src, check=False)
    assert word in ei.value.format()


def test_division_meaning_is_unsigned_rounded_down_with_the_zero_convention():
    assert (L.udiv(17, 5), L.umod(17, 5)) == (3, 2)
    assert (L.udiv(0xFFFFFFFF, 2), L.umod(0xFFFFFFFF, 2)) == (0x7FFFFFFF, 1)
    assert L.udiv(9, 0) == 0xFFFFFFFF and L.umod(9, 0) == 9
    _, t = L.parse_latex(r"x / 5 + x \bmod 5")
    assert L.evaluate(t, {"x": 17}) == 5
    _, t = L.parse_latex("-x / 2")                                   # a negative is the big unsigned word: documented, not hidden
    assert L.evaluate(t, {"x": 4}) == (0xFFFFFFFC) // 2


def test_the_quotient_and_remainder_fit_together():
    """q*b + r == a for every divisor that is not zero (an identity of the oracle itself, so the two functions cannot drift apart)."""
    rng = random.Random(7)
    for _ in range(2000):
        a, b = rng.getrandbits(32), rng.getrandbits(rng.choice([1, 8, 16, 32])) or 1
        assert (L.udiv(a, b) * b + L.umod(a, b)) & M == a and L.umod(a, b) < b


BOUNDARY = [0, 1, 2, 3, 0x7FFFFFFF, 0x80000000, 0x80000001, 0xFFFFFFFE, 0xFFFFFFFF]


@pytest.mark.parametrize("src,fn", [("x / y", L.udiv), (r"x \bmod y", L.umod)])
def test_generated_operations_are_exact_at_full_width(src, fn):
    r = L.compile_latex(src, check=False)
    rng = random.Random(1067)
    cases = [(a, b) for a in BOUNDARY for b in BOUNDARY]
    cases += [(rng.getrandbits(rng.choice([8, 16, 24, 32])), rng.getrandbits(rng.choice([1, 4, 8, 16, 31, 32]))) for _ in range(1500)]
    for a, b in cases:
        assert L.eval_ir(r.ir, {"x": a, "y": b}) == fn(a, b), (a, b)


@pytest.mark.parametrize("src,vals", [
    ("100 / x", [{"x": k} for k in (0, 1, 3, 7, 100, 101, 0xFFFFFFFF)]),
    ("x / 7", [{"x": k} for k in (0, 6, 7, 8, 700, 0xFFFFFFFF)]),
    (r"1000 \bmod x", [{"x": k} for k in (0, 1, 3, 999, 1000, 1001, 0x80000000)]),
    (r"\frac{a + b}{c} + a", [{"a": a, "b": b, "c": c} for a, b, c in ((10, 5, 4), (0xFFFFFFFF, 1, 3), (7, 7, 0), (1 << 31, 1 << 31, (1 << 31) + 1))]),
    (r"(x / y) * y + x \bmod y", [{"x": a, "y": b} for a, b in ((100, 7), (0xFFFFFFFF, 0x80000000), (5, 0))]),
])
def test_other_division_shapes_are_exact_at_full_width(src, vals):
    r = L.compile_latex(src)                              # IR check on corner/random values happens inside
    for v in vals:
        assert L.eval_ir(r.ir, v) == r.reference(v), (src, v)
    assert r.ir_checked > 5 and (r.hw_skipped or r.checked)


def test_a_big_design_says_out_loud_that_the_vm_comparison_was_skipped():
    r = L.compile_latex("x / y")
    assert r.cells > L.HW_CHECK_MAX_CELLS and r.checked == 0 and r.ir_checked > 10
    assert "skipped" in r.hw_skipped and str(r.cells) in r.hw_skipped


def test_division_by_a_literal_zero_or_one_is_resolved_before_any_hardware():
    assert L.compile_latex(r"x / 1 + y", check=True).cells < 30
    with pytest.raises(L.LatexError) as ei:
        L.compile_latex("x / 0")
    assert "always gives" in str(ei.value)                           # x div 0 is all ones whatever x is
    assert L.compile_latex(r"x \bmod 0 + y").cells < 30                # x mod 0 is x


def test_power_of_two_divisors_are_a_shift_or_a_mask_through_every_layer():
    assert "lshr" in L.compile_latex("x / 8").ir and "and" in L.compile_latex(r"x \bmod 16").ir
    for src in ("x / 8", r"x \bmod 16", r"\frac{a + b}{2}", r"x / 2147483648"):
        r = L.compile_latex(src)
        assert r.cells < 40 and r.checked > 5
        vecs = L.check_vectors(r.args, n_random=2)[:4]
        assert r.stream_step(vecs) == [r.reference(v) for v in vecs]


# ---- the same generator, a few steps wide, through the VM / step simulator / RTL --------------------------------------------------

@pytest.fixture(params=[3, 4])
def narrow(request, monkeypatch):
    monkeypatch.setattr(L, "DIV_STEPS", request.param)
    return request.param


@pytest.mark.parametrize("src,fn", [("x / y", lambda a, b: a // b), (r"x \bmod y", lambda a, b: a % b)])
def test_narrow_division_runs_correctly_in_the_vm(narrow, src, fn):
    r = L.compile_latex(src, check=False)
    n = narrow
    for A, B in ((0, 1), ((1 << n) - 1, 1), ((1 << n) - 1, (1 << n) - 1), (5 % (1 << n), 2)):
        assert r.run({"x": A << (32 - n), "y": B}) == fn(A, B), (n, A, B)


def test_narrow_division_streams_through_the_flex_step_simulator(monkeypatch):
    monkeypatch.setattr(L, "DIV_STEPS", 3)
    r = L.compile_latex("x / y", check=False)
    cases = [(7, 2), (6, 3), (5, 7)]
    got = r.stream_step([{"x": A << 29, "y": B} for A, B in cases])
    assert got == [A // B for A, B in cases]


def test_narrow_division_matches_in_generated_flex_rtl(monkeypatch):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    from fp_block_runner_v1 import run_rtl
    monkeypatch.setattr(L, "DIV_STEPS", 3)
    r = L.compile_latex(r"x \bmod y", check=False)
    cases = [(7, 2), (6, 4), (5, 7), (1, 1)]
    cmap = L._input_cells(r)
    entries = {c: [((A << 29) if a == "x" else B) & M for A, B in cases] for c, a in cmap.items()}
    tmp = tempfile.mkdtemp(prefix="latex_div_rtl_")
    try:
        got = run_rtl(tmp, "latexdiv", r.result.records, entries, {"r": "main.r"}, "plain", settle=20000, cycles=12000)["r"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    assert [g & M for g in got] == [A % B for A, B in cases]


def test_a_second_distinct_long_division_is_refused_but_a_quotient_and_remainder_of_the_same_pair_share_one():
    with pytest.raises(L.LatexError) as ei:
        L.compile_latex(r"\frac{a + b}{c} + a \bmod c")
    assert "2 separate long divisions" in str(ei.value)
    with pytest.raises(L.LatexError):
        L.compile_latex("a / b + c / d")
    r = L.compile_latex(r"(x / y) * y + x \bmod y")                      # same pair: one divider
    assert r.ir_checked > 5
    r2 = L.compile_latex("x / y + x / y")                                 # the same division twice is built once
    assert r2.ir_checked > 5
    assert L.compile_latex("a / b + c / 4").ir_checked > 5               # a power of two is not a long division
