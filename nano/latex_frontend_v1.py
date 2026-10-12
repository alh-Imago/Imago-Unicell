"""nano/latex_frontend_v1.py -- ledger #1066: write a formula in LaTeX, get a UniCell design that computes it, checked against a plain Python evaluation of the SAME formula.

    from latex_frontend_v1 import compile_latex
    r = compile_latex(r"y = (a + b)^2 - 3c")
    r.args                      # ['a', 'b', 'c']   (order of first appearance)
    r.run({"a": 2, "b": 3, "c": 4})          # 13
    r.reference({"a": 2, "b": 3, "c": 4})    # 13  (the pure-Python answer, the oracle)

WHAT IT IS: a small, strict parser for integer maths. It turns the formula into LLVM IR (add, sub, mul only) and hands it to the existing compiler with `placer="routed_x"`
(crossing tiles, a relay tree for values read more than three times, constant folding, plain refusals). It adds no new hardware and no new cell kinds.

WHAT IT COMPUTES: 32-bit whole numbers that wrap around (two's complement), exactly like the cells. `2^31 + 2^31` is 0, not 4294967296. Results come back as unsigned 0..2^32-1;
`as_signed()` gives the signed reading. There are NO fractions: a decimal point, roots and functions (sin, log, ...) are refused with a message, never approximated; division gives the whole-number quotient.

SUPPORTED (and nothing else):
  numbers      whole numbers: 12, 0x1F is NOT supported (LaTeX has no hex)
  names        one letter is one variable: `x`; two letters side by side are a PRODUCT (`xy` means x times y, as in maths). A longer name: `\\mathrm{rate}` or `\\text{rate}`.
               Subscripts: `x_1`, `x_{12}`, `a_i`. Greek letters: `\\alpha` ... `\\omega` (no `\\pi`, `\\e`: those are not whole numbers).
  operators    +  -  (also unary minus)   *   \\cdot   \\times   and plain side-by-side multiplication (`2x`, `3(a+b)`, `(a)(b)`)
  division     `a / b`, `a \\div b`, `\\frac{a}{b}` (quotient, rounded down) and `a \\bmod b` (remainder). UNSIGNED whole numbers: a negative value is its big two's-complement word,
               so `-x / 2` is NOT minus half of x. Dividing by zero gives all ones (0xFFFFFFFF) and the remainder by zero is the dividend (the restoring-division convention, also RISC-V's).
               Same level as `*`, left to right; a number or name straight after a division (`a / b c`) is refused as ambiguous.
               A power-of-two divisor is a shift or a mask (tiny). Any other divisor is one cell of the division core (below); with division="unrolled" it is instead a 32-step long-division loop unrolled in cells: about 23,000 cells for one division.
               By default (division="core"; ledger #1074, made the default in #1076) a general division or remainder is ONE cell of the division core
               (`udiv` / `urem`): 8 cells for `a / b`, 38 for a formula with two divisions, any number of divisions, and the design is small enough for the VM check. It needs a
               target that has the division core. Checked so far: the VM, and the flex and sub families (the compiled design built as real RTL by the assembler and run in iverilog,
               ledger #1074 and #1075; on sub one result per clock). NOT yet run: a LaTeX-compiled design on the cardinal (v4/v4c) cells, though those cells exist. "core" is the default (Alan, ledger #1076); division="unrolled" keeps the old form for a target without the core.
  grouping     ( )   \\left( \\right)   { }   (square brackets [ ] too)
  powers       x^2, x^{3}, (a+b)^2: the exponent must be a whole number written out (0..64). Not x^n, not x^{-1}, not x^{1/2}.
  naming       an optional `name =` in front is just a label; it must not appear on the right-hand side.
  spacing      \\, \\; \\: \\! \\quad \\qquad and spaces are ignored.

Anything else raises `LatexError` with the position and a plain reason. The first version refuses rather than guesses.

HOW IT IS CHECKED (correctness first): `compile_latex(..., check=True)` (the default) does two comparisons with the plain-Python `reference()`, on a fixed set of corner values plus random ones.
  1. The generated operations are run by a tiny interpreter (`eval_ir`): this catches a wrong translation of the formula, is fast, and runs on every compile at full width.
  2. The compiled design is run in the standard VM, unless it is too large for the VM (more than HW_CHECK_MAX_CELLS cells, as every general division is): then `hw_skipped` says so and
     the command line prints a NOTE. `check="full"` forces it (minutes to hours for a division).
A mismatch raises `LatexCheckError`; the design is not returned. `LatexResult.stream_step()` feeds items through the flex step simulator at `safe_spacing()`, a CONSERVATIVE rule of
thumb (not a measured limit): feeding items closer than the design can take gives silently wrong answers, so the default is generous.
"""
from __future__ import annotations

import os
import random
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MASK = 0xFFFFFFFF
MAX_POWER = 64
GREEK = {"alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "zeta", "eta", "theta", "vartheta", "iota", "kappa", "lambda", "mu", "nu", "xi", "rho", "varrho",
         "sigma", "varsigma", "tau", "upsilon", "phi", "varphi", "chi", "psi", "omega", "Gamma", "Delta", "Theta", "Lambda", "Xi", "Sigma", "Upsilon", "Phi", "Psi", "Omega"}
SPACING_CMDS = {",", ";", ":", "!", " ", "quad", "qquad"}
TIMES_CMDS = {"cdot", "times", "ast"}
NOT_YET = {
    "pmod": "\\pmod is not supported; write the remainder as a \\bmod b",
    "pod": "\\pod is not supported; write the remainder as a \\bmod b",
    "sqrt": "square roots are not supported (no fractions or irrational results; only whole numbers)",
    "sum": "sums over a range (\\sum) are not supported yet; write the terms out",
    "prod": "products over a range (\\prod) are not supported yet; write the factors out",
    "int": "integrals are not supported",
    "pi": "pi is not a whole number; only whole-number maths is supported",
    "infty": "infinity is not a number the cells can hold",
    "pm": "plus-or-minus gives two answers; write the two formulas separately",
    "mp": "minus-or-plus gives two answers; write the two formulas separately",
}
FUNCTIONS = {"sin", "cos", "tan", "cot", "sec", "csc", "log", "ln", "exp", "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh", "min", "max", "gcd", "lcm", "det", "lim"}


class LatexError(ValueError):
    """The formula is not in the supported subset (or is malformed). `pos` is the 0-based character position in the source."""

    def __init__(self, message: str, source: str = "", pos: Optional[int] = None):
        super().__init__(message)
        self.message, self.source, self.pos = message, source, pos

    def format(self) -> str:
        if self.pos is None or not self.source:
            return f"error: {self.message}"
        line = self.source.replace("\n", " ")
        return f"error: {self.message}\n  {line}\n  {' ' * min(self.pos, len(line))}^"

    def __str__(self):
        return self.format()


class LatexCheckError(AssertionError):
    """The compiled design disagreed with the plain Python evaluation of the same formula. It is never returned; this is raised instead."""


# ---------------------------------------------------------------------------------------------------------------------------------
# 1. Tokens
# ---------------------------------------------------------------------------------------------------------------------------------

@dataclass
class Tok:
    kind: str            # num, name, op, lparen, rparen, caret, sub, end
    text: str
    pos: int


def _tokenise(src: str) -> List[Tok]:
    toks: List[Tok] = []
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c.isspace() or c == "~":
            i += 1
        elif c.isdigit():
            j = i
            while j < n and src[j].isdigit():
                j += 1
            if j < n and src[j] == ".":
                raise LatexError("decimal numbers are not supported: only whole numbers (write the scaled whole number, e.g. 25 for 2.5 tenths)", src, j)
            if j < n and src[j] == "," and j + 1 < n and src[j + 1].isdigit():
                raise LatexError("a comma inside a number is not supported (write 1000, not 1,000)", src, j)
            toks.append(Tok("num", src[i:j], i))
            i = j
        elif c.isalpha():
            toks.append(Tok("name", c, i))
            i += 1
        elif c in "+-":
            toks.append(Tok("op", c, i))
            i += 1
        elif c == "%":
            raise LatexError("% starts a comment in LaTeX; write the remainder as a \\bmod b", src, i)
        elif c == "*":
            toks.append(Tok("op", "*", i))
            i += 1
        elif c in "([{":
            toks.append(Tok("lparen", c, i))
            i += 1
        elif c in ")]}":
            toks.append(Tok("rparen", c, i))
            i += 1
        elif c == "^":
            toks.append(Tok("caret", c, i))
            i += 1
        elif c == "_":
            toks.append(Tok("sub", c, i))
            i += 1
        elif c == "=":
            toks.append(Tok("eq", c, i))
            i += 1
        elif c == "/":
            toks.append(Tok("op", "/", i))
            i += 1
        elif c == "\\":
            m = re.match(r"\\([A-Za-z]+|.)", src[i:])
            if not m:
                raise LatexError("a backslash at the end of the formula", src, i)
            cmd = m.group(1)
            pos = i
            i += len(m.group(0))
            if cmd in SPACING_CMDS:
                continue
            if cmd in TIMES_CMDS:
                toks.append(Tok("op", "*", pos))
            elif cmd == "div":
                toks.append(Tok("op", "/", pos))
            elif cmd in ("bmod", "mod"):
                toks.append(Tok("op", "%", pos))
            elif cmd in ("frac", "dfrac", "tfrac"):
                toks.append(Tok("frac", cmd, pos))
            elif cmd in ("left", "right"):
                if i < n and src[i] in "([{)]}.|":
                    ch = src[i]
                    if ch == "|":
                        raise LatexError("absolute value |...| is not supported", src, i)
                    i += 1
                    if ch != ".":
                        toks.append(Tok("lparen" if ch in "([{" else "rparen", ch, pos))
                else:
                    raise LatexError(f"\\{cmd} must be followed by a bracket", src, i)
            elif cmd in ("mathrm", "text", "mathit", "operatorname", "mathsf", "textit"):
                m2 = re.match(r"\{([A-Za-z][A-Za-z0-9]*)\}", src[i:])
                if not m2:
                    raise LatexError(f"\\{cmd} must be followed by {{name}} (letters and digits, starting with a letter)", src, i)
                toks.append(Tok("name", m2.group(1), pos))
                i += len(m2.group(0))
            elif cmd in GREEK:
                toks.append(Tok("name", cmd, pos))
            elif cmd in NOT_YET:
                raise LatexError(NOT_YET[cmd], src, pos)
            elif cmd in FUNCTIONS:
                raise LatexError(f"the function \\{cmd} is not supported: only + - * and whole-number powers", src, pos)
            elif cmd in ("{", "}"):
                toks.append(Tok("lparen" if cmd == "{" else "rparen", cmd, pos))
            else:
                raise LatexError(f"\\{cmd} is not supported", src, pos)
        elif c == "|":
            raise LatexError("absolute value |...| is not supported", src, i)
        elif c in "<>!":
            raise LatexError(f"{c!r} (a comparison or factorial) is not supported", src, i)
        elif c in ".,;:":
            raise LatexError(f"{c!r} is not supported here", src, i)
        else:
            raise LatexError(f"the character {c!r} is not supported", src, i)
    toks.append(Tok("end", "", n))
    return toks


# ---------------------------------------------------------------------------------------------------------------------------------
# 2. Syntax tree and parser
# ---------------------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Num:
    value: int


@dataclass(frozen=True)
class Var:
    name: str


@dataclass(frozen=True)
class Neg:
    arg: "Expr"


@dataclass(frozen=True)
class Bin:
    op: str             # + - *
    left: "Expr"
    right: "Expr"


@dataclass(frozen=True)
class Div:
    left: "Expr"
    right: "Expr"


@dataclass(frozen=True)
class Mod:
    left: "Expr"
    right: "Expr"


@dataclass(frozen=True)
class Pow:
    base: "Expr"
    exp: int


Expr = object


class _Parser:
    def __init__(self, src: str):
        self.src = src
        self.toks = _tokenise(src)
        self.i = 0

    def peek(self) -> Tok:
        return self.toks[self.i]

    def take(self) -> Tok:
        t = self.toks[self.i]
        self.i += 1
        return t

    def err(self, msg: str, tok: Optional[Tok] = None) -> LatexError:
        return LatexError(msg, self.src, (tok or self.peek()).pos)

    # label =  (optional)
    def parse(self) -> Tuple[Optional[str], Expr]:
        label = None
        save = self.i
        if self.peek().kind == "name":
            nm = self._name_with_subscript()
            if self.peek().kind == "eq":
                self.take()
                label = nm
            else:
                self.i = save
        e = self.expr()
        if self.peek().kind == "eq":
            raise self.err("an = may only follow a single name, as in `y = formula`; letters side by side mean a product, so write a longer name as \\mathrm{total} = ...")
        if self.peek().kind == "rparen":
            raise self.err(f"the closing bracket {self.peek().text!r} has no matching opening bracket")
        if self.peek().kind != "end":
            raise self.err(f"unexpected {self.peek().text!r}")
        return label, e

    def expr(self) -> Expr:
        left = self.term()
        while self.peek().kind == "op" and self.peek().text in "+-":
            op = self.take().text
            right = self.term()
            left = Bin(op, left, right)
        return left

    def term(self) -> Expr:
        left = self.unary()
        divided = False                                         # the last operator was a division or remainder
        while True:
            t = self.peek()
            if t.kind == "op" and t.text == "*":
                self.take()
                right = self.unary()
                left = Bin("*", left, right)
                divided = False
            elif t.kind == "op" and t.text in ("/", "%"):
                self.take()
                right = self.unary()
                left = Div(left, right) if t.text == "/" else Mod(left, right)
                divided = True
            elif t.kind in ("num", "name", "lparen", "frac") and not (t.kind == "lparen" and t.text in ")]}"):
                if divided:
                    raise self.err("a number or name straight after a division or remainder is ambiguous (is it multiplied before or after?): add brackets")
                right = self.unary_implicit()
                left = Bin("*", left, right)
            else:
                return left

    def unary_implicit(self) -> Expr:
        # side-by-side multiplication: the right factor may not start with a sign (2 -x is a subtraction, handled by expr)
        return self.power()

    def unary(self) -> Expr:
        t = self.peek()
        if t.kind == "op" and t.text in "+-":
            self.take()
            inner = self.unary()
            return Neg(inner) if t.text == "-" else inner
        return self.power()

    def power(self) -> Expr:
        base = self.atom()
        if self.peek().kind == "caret":
            ct = self.take()
            ex = self._exponent(ct)
            if self.peek().kind == "caret":
                raise self.err("a power of a power (x^2^3) is ambiguous: write (x^2)^3 or x^{6}")
            return Pow(base, ex)
        return base

    def _exponent(self, caret: Tok) -> int:
        t = self.peek()
        braced = False
        if t.kind == "lparen" and t.text == "{":
            self.take()
            braced = True
            t = self.peek()
        sign = 1
        if t.kind == "op" and t.text == "-":
            raise self.err("negative powers mean division, which is not supported", t)
        if t.kind != "num":
            if t.kind == "name":
                raise self.err("the exponent must be a whole number written out (x^n with a variable n is not supported)", t)
            raise self.err("the exponent must be a whole number (0 to %d)" % MAX_POWER, t)
        self.take()
        digits = t.text
        if not braced and len(digits) > 1:
            # LaTeX takes only ONE digit after ^ without braces: x^23 is x^2 times 3
            raise self.err(f"write x^{{{digits}}} with braces: in LaTeX x^{digits} means x^{digits[0]} followed by {digits[1:]}", t)
        v = int(digits) * sign
        if braced:
            if self.peek().kind == "rparen" and self.peek().text == "}":
                self.take()
            else:
                raise self.err("the exponent must be a single whole number inside the braces")
        if v > MAX_POWER:
            raise self.err(f"the power {v} is larger than the limit of {MAX_POWER}", t)
        return v

    def _name_with_subscript(self) -> str:
        t = self.take()
        nm = t.text
        if self.peek().kind == "sub":
            st = self.take()
            nxt = self.peek()
            if nxt.kind == "lparen" and nxt.text == "{":
                self.take()
                parts = []
                while not (self.peek().kind == "rparen" and self.peek().text == "}"):
                    p = self.take()
                    if p.kind not in ("num", "name"):
                        raise self.err("a subscript may contain only letters and digits", p)
                    parts.append(p.text)
                    if p.kind == "end":
                        raise self.err("the subscript is not closed", st)
                self.take()
                sub = "".join(parts)
            elif nxt.kind in ("num", "name"):
                self.take()
                sub = nxt.text[0] if nxt.kind == "num" else nxt.text
                if nxt.kind == "num" and len(nxt.text) > 1:
                    # x_12 in LaTeX is x_1 followed by 2
                    raise self.err(f"write x_{{{nxt.text}}} with braces: in LaTeX x_{nxt.text} means x_{nxt.text[0]} followed by {nxt.text[1:]}", nxt)
            else:
                raise self.err("a subscript must be a letter, a digit or {...}", nxt)
            if not sub:
                raise self.err("an empty subscript", st)
            nm = f"{nm}_{sub}"
        return nm

    def _group(self, what: str) -> Expr:
        t = self.peek()
        if not (t.kind == "lparen" and t.text == "{"):
            raise self.err(f"\\frac needs two braced parts, \\frac{{top}}{{bottom}}; the {what} is missing its {{ }}", t)
        self.take()
        e = self.expr()
        r = self.peek()
        if not (r.kind == "rparen" and r.text == "}"):
            raise self.err(f"the {what} of the fraction is not closed with }}", r)
        self.take()
        return e

    def atom(self) -> Expr:
        t = self.peek()
        if t.kind == "frac":
            self.take()
            top = self._group("top")
            bottom = self._group("bottom")
            return Div(top, bottom)
        if t.kind == "num":
            self.take()
            v = int(t.text)
            if v > MASK:
                raise self.err(f"{v} does not fit in 32 bits (the largest whole number is {MASK})", t)
            return Num(v)
        if t.kind == "name":
            nm = self._name_with_subscript()
            return Var(nm)
        if t.kind == "lparen" and t.text in "([{":
            self.take()
            e = self.expr()
            r = self.peek()
            if r.kind != "rparen":
                raise self.err(f"the bracket opened at position {t.pos} is not closed", r)
            self.take()
            return e
        if t.kind == "rparen":
            raise self.err(f"unexpected closing bracket {t.text!r}")
        if t.kind == "end":
            raise self.err("the formula ends where a number, name or bracket was expected")
        if t.kind == "op":
            raise self.err(f"{t.text!r} needs a number or name on both sides")
        raise self.err(f"unexpected {t.text!r}")


def parse_latex(src: str) -> Tuple[Optional[str], Expr]:
    """(label or None, syntax tree). Raises LatexError."""
    if not src or not src.strip():
        raise LatexError("the formula is empty", src or "", 0)
    s = src.strip()
    if s.startswith("$$") and s.endswith("$$") and len(s) >= 4:
        s = s[2:-2]
    elif s.startswith("$") and s.endswith("$") and len(s) >= 2:
        s = s[1:-1]
    elif s.startswith("\\(") and s.endswith("\\)"):
        s = s[2:-2]
    elif s.startswith("\\[") and s.endswith("\\]"):
        s = s[2:-2]
    p = _Parser(s)
    label, e = p.parse()
    if label is not None and label in variables(e):
        raise LatexError(f"{label} is on both sides of the =; a formula cannot refer to its own result", s, 0)
    return label, e


# ---------------------------------------------------------------------------------------------------------------------------------
# 3. Tree utilities, the Python oracle, constant folding
# ---------------------------------------------------------------------------------------------------------------------------------

def variables(e: Expr) -> List[str]:
    """Variable names in order of first appearance."""
    seen: List[str] = []

    def walk(x):
        if isinstance(x, Var):
            if x.name not in seen:
                seen.append(x.name)
        elif isinstance(x, Neg):
            walk(x.arg)
        elif isinstance(x, (Bin, Div, Mod)):
            walk(x.left)
            walk(x.right)
        elif isinstance(x, Pow):
            walk(x.base)
    walk(e)
    return seen


def udiv(a: int, b: int) -> int:
    """UNSIGNED whole-number quotient (rounded down). Dividing by zero gives all ones (0xFFFFFFFF), the convention of the restoring-division hardware and of RISC-V."""
    a, b = a & MASK, b & MASK
    return MASK if b == 0 else a // b


def umod(a: int, b: int) -> int:
    """UNSIGNED remainder, the partner of udiv: a - (a div b) * b. Taking the remainder by zero gives the dividend back (the same convention)."""
    a, b = a & MASK, b & MASK
    return a if b == 0 else a % b


def evaluate(e: Expr, values: Dict[str, int]) -> int:
    """The oracle: plain Python integers, then reduced modulo 2^32 at every step (exactly the wrap-around of the cells). No hardware, no compiler involved."""
    if isinstance(e, Num):
        return e.value & MASK
    if isinstance(e, Var):
        if e.name not in values:
            raise KeyError(f"no value given for {e.name}")
        return values[e.name] & MASK
    if isinstance(e, Neg):
        return (-evaluate(e.arg, values)) & MASK
    if isinstance(e, Bin):
        a, b = evaluate(e.left, values), evaluate(e.right, values)
        return ((a + b) if e.op == "+" else (a - b) if e.op == "-" else (a * b)) & MASK
    if isinstance(e, Div):
        return udiv(evaluate(e.left, values), evaluate(e.right, values))
    if isinstance(e, Mod):
        return umod(evaluate(e.left, values), evaluate(e.right, values))
    if isinstance(e, Pow):
        b = evaluate(e.base, values)
        r = 1
        for _ in range(e.exp):
            r = (r * b) & MASK
        return r
    raise TypeError(e)


def fold(e: Expr) -> Expr:
    """Fold sub-trees that contain no variable into one number (wrapping at 32 bits). Mirrors evaluate()."""
    if isinstance(e, (Num, Var)):
        return e
    if isinstance(e, Neg):
        a = fold(e.arg)
        return Num((-a.value) & MASK) if isinstance(a, Num) else Neg(a)
    if isinstance(e, Bin):
        a, b = fold(e.left), fold(e.right)
        if isinstance(a, Num) and isinstance(b, Num):
            return Num(evaluate(Bin(e.op, a, b), {}))
        return Bin(e.op, a, b)
    if isinstance(e, (Div, Mod)):
        a, b = fold(e.left), fold(e.right)
        if isinstance(a, Num) and isinstance(b, Num):
            return Num(evaluate(type(e)(a, b), {}))
        if isinstance(b, Num):
            if b.value == 0:                                      # x div 0 = all ones; x mod 0 = x
                return Num(MASK) if isinstance(e, Div) else a
            if b.value == 1:
                return a if isinstance(e, Div) else Num(0)
        return type(e)(a, b)
    if isinstance(e, Pow):
        b = fold(e.base)
        return Num(evaluate(Pow(b, e.exp), {})) if isinstance(b, Num) else Pow(b, e.exp)
    raise TypeError(e)


# ---------------------------------------------------------------------------------------------------------------------------------
# 4. LLVM IR
# ---------------------------------------------------------------------------------------------------------------------------------

def _argname(v: str) -> str:
    return "v_" + v


class _Emit:
    def __init__(self, core_division: bool = False, polynomial: str = "direct"):
        self.polynomial = polynomial                      # ledger #1078: "direct" | "auto" | "horner" (see to_llvm)
        self.core_division = core_division                # ledger #1074: True = division and remainder are the `udiv` / `urem` operations of the division core (one cell each)
        self.lines: List[str] = []
        self.n = 0
        self.memo: Dict[Tuple, str] = {}
        self.divisions: set = set()                       # distinct (dividend, divisor) pairs that need a full long division

    def op(self, opcode: str, a: str, b: str) -> str:
        key = (opcode, a, b) if opcode in ("sub", "shl", "lshr", "udiv", "urem") else (opcode,) + tuple(sorted((a, b)))     # the same sum or product is built once
        if key in self.memo:
            return self.memo[key]
        self.n += 1
        nm = f"%_t{self.n}"
        self.lines.append(f"  {nm} = {opcode} i32 {a}, {b}")
        self.memo[key] = nm
        return nm


def _is_lit(x: str) -> bool:
    return re.fullmatch(r"-?\d+", x) is not None


def _udivmod(em: _Emit, a: str, b: str, want: str, steps: int = 32) -> str:
    """Unsigned long division, `steps` (32) steps unrolled in space (restoring division, one quotient bit per step), from add/sub/mul/and/or/xor/shifts only. `want` is "q" or "r".
    Each step shifts the next dividend bit into the remainder R, and subtracts the divisor when R >= b, setting that quotient bit. No 33rd bit is ever needed: before the shift R is at
    most the top (k-1) bits of the dividend, below 2^31 for every k <= 32, so 2R+bit fits in 32 bits (a mutation test that removed an extra carry guard I had first written found
    it could never fire). R >= b is decided WITHOUT a signed comparison, by the borrow identity ((~r & b) | (~(r ^ b) & (r - b))) >> 31, which is exact over the whole 32-bit range
    (a signed difference is not: mutation-tested). b = 0 falls out as q = all ones, r = the dividend (the convention of udiv/umod). A literal dividend is first made a computed value
    (zero from `b xor b`, plus the literal) because the cells need a run-time operand. A divisor that is a plain variable is read directly: each read is its own input cell (the
    compiler's rule for arguments), about 130 of them; copying it first so a relay tree carried it made the placer take over a minute without finishing, so that was not used."""
    bb = b
    A = a if not _is_lit(a) else em.op("add", em.op("xor", bb, bb), a)
    R, Q = None, None
    for _ in range(steps):
        topa = em.op("lshr", A, "31")
        A = em.op("shl", A, "1")
        R2 = topa if R is None else em.op("or", em.op("shl", R, "1"), topa)
        d = em.op("sub", R2, bb)
        x = em.op("xor", R2, bb)
        u1 = em.op("and", em.op("xor", R2, "-1"), bb)
        u2 = em.op("and", em.op("xor", x, "-1"), d)
        ult = em.op("lshr", em.op("or", u1, u2), "31")
        take = em.op("xor", ult, "1")
        m = em.op("mul", take, "-1")
        R = em.op("sub", R2, em.op("and", m, bb))
        Q = take if Q is None else em.op("or", em.op("shl", Q, "1"), take)
    return Q if want == "q" else R


def _poly_of(e: Expr, limit: int = 64):
    """ledger #1078: (variable, {degree: coefficient mod 2^32}) if `e` is a polynomial in ONE variable (sums, differences, products, whole powers, negation, numbers), else None.
    The variable is None for a constant. Degrees above `limit` give None. Arithmetic is mod 2^32, exactly like the cells, so the expanded polynomial equals the formula on every word."""
    if isinstance(e, Num):
        return (None, {0: e.value & MASK} if e.value & MASK else {})
    if isinstance(e, Var):
        return (e.name, {1: 1})
    if isinstance(e, Neg):
        r = _poly_of(e.arg, limit)
        return None if r is None else (r[0], {d: (-c) & MASK for d, c in r[1].items() if (-c) & MASK})
    if isinstance(e, Pow):
        r = _poly_of(e.base, limit)
        if r is None:
            return None
        out = (None, {0: 1})
        for _ in range(e.exp):
            out = _poly_mul(out, r, limit)
            if out is None:
                return None
        return out
    if isinstance(e, Bin):
        a, b = _poly_of(e.left, limit), _poly_of(e.right, limit)
        if a is None or b is None:
            return None
        if a[0] and b[0] and a[0] != b[0]:
            return None
        if e.op == "*":
            return _poly_mul(a, b, limit)
        sign = 1 if e.op == "+" else -1
        out = dict(a[1])
        for d, c in b[1].items():
            out[d] = (out.get(d, 0) + sign * c) & MASK
        return (a[0] or b[0], {d: c for d, c in out.items() if c})
    return None


def _poly_mul(a, b, limit):
    if a[0] and b[0] and a[0] != b[0]:
        return None
    out: Dict[int, int] = {}
    for d1, c1 in a[1].items():
        for d2, c2 in b[1].items():
            if d1 + d2 > limit:
                return None
            out[d1 + d2] = (out.get(d1 + d2, 0) + c1 * c2) & MASK
    return (a[0] or b[0], {d: c for d, c in out.items() if c})


def _try_plan(e: Expr, em: "_Emit"):
    """ledger #1078: place the Horner plan for `e` if it is a one-variable polynomial of degree >= 2 and the mode is "horner"; else None. (Which mode wins is decided by
    compile_latex, by compiling both ways and counting cells: operation counts mislead, see its docstring.)"""
    if em.polynomial == "direct" or not isinstance(e, (Bin, Pow, Neg)):
        return None
    r = _poly_of(e)
    if r is None or r[0] is None or not r[1] or max(r[1]) < 2:
        return None
    import arith_plan_library_v1 as AP
    coeffs = [r[1].get(d, 0) for d in range(max(r[1]) + 1)]
    return AP.lookup("horner").emit(em, "%" + _argname(r[0]), coeffs)


def _gen(e: Expr, em: _Emit) -> str:
    """Operand string (a %name or a literal). Literals go second wherever the operation allows it."""
    planned = _try_plan(e, em)
    if planned is not None:
        return planned
    if isinstance(e, Num):
        return str(e.value if e.value < (1 << 31) else e.value - (1 << 32))
    if isinstance(e, Var):
        return "%" + _argname(e.name)
    if isinstance(e, Neg):
        a = _gen(e.arg, em)
        return em.op("mul", a, "-1")
    if isinstance(e, (Div, Mod)):
        a, b = _gen(e.left, em), _gen(e.right, em)
        isdiv = isinstance(e, Div)
        if _is_lit(b):
            bv = int(b) & MASK
            if bv & (bv - 1) == 0 and bv > 0:                    # a power of two: a shift, or a mask, exactly
                k = bv.bit_length() - 1
                if isdiv:
                    return a if k == 0 else em.op("lshr", a, str(k))
                return em.op("and", a, str(bv - 1))
        if em.core_division:                                     # the division core: ONE cell, dividend first (the compiler orders the arrivals, as for sub)
            return em.op("udiv" if isdiv else "urem", a, b)
        em.divisions.add((a, b))
        return _udivmod(em, a, b, "q" if isdiv else "r", DIV_STEPS)
    if isinstance(e, Pow):
        b = _gen(e.base, em)
        if e.exp == 0:
            return "1"
        # square-and-multiply: fewer cells than a chain of multiplications
        result: Optional[str] = None
        sq = b
        k = e.exp
        while k:
            if k & 1:
                result = sq if result is None else em.op("mul", result, sq)
            k >>= 1
            if k:
                sq = em.op("mul", sq, sq)
        return result
    if isinstance(e, Bin):
        a, b = _gen(e.left, em), _gen(e.right, em)
        if e.op in "+*":
            opc = "add" if e.op == "+" else "mul"
            if _is_lit(a) and not _is_lit(b):
                a, b = b, a
            return em.op(opc, a, b)
        # subtraction: the minuend must be a computed value or an argument; 5 - x is x * -1 + 5
        if _is_lit(a):
            return em.op("add", em.op("mul", b, "-1"), a)
        return em.op("sub", a, b)
    raise TypeError(e)


MAX_GENERAL_DIVISIONS = 1                           # distinct long divisions per formula (a quotient and a remainder of the SAME two values share one). Two had not finished placing after 10 minutes
DIV_STEPS = 32                                      # quotient bits produced; only tests lower it (a smaller instance divides the TOP `steps` bits of the dividend)


def to_llvm(e: Expr, args: Optional[List[str]] = None, division: str = "core", polynomial: str = "direct") -> Tuple[str, List[str]]:
    """(LLVM IR text, argument names). The returned value is always named %r. Raises LatexError if the formula has no variable or reduces to one.
    division="core" (the DEFAULT since ledger #1076, Alan's decision): a general division is the `udiv` / `urem` operation, ONE cell of the division core (any number per formula).
    Needs a target that has the division core.
    division="unrolled": a general division is built from add/sub/mul/shifts, about 23,000 cells, at most one per formula. Needs nothing but the basic cells (for a target without the core).
    polynomial="direct" (default here): the formula is built as written. "horner" (ledger #1078): every one-variable polynomial of degree 2 or more in the formula is placed as the
    Horner PLAN (`arith_plan_library_v1`). compile_latex's own default, "auto", tries both and keeps the one that compiles to fewer cells."""
    if polynomial not in ("horner", "direct"):
        raise LatexError(f"polynomial must be \"horner\" or \"direct\" here, not {polynomial!r}")
    if division not in ("unrolled", "core"):
        raise LatexError(f"division must be \"unrolled\" or \"core\", not {division!r}")
    seen = variables(e)
    e = fold(e)
    args = args if args is not None else seen
    if isinstance(e, Num):
        if seen:
            raise LatexError("whatever the inputs are, this formula always gives %d, so there is nothing to compute at run time" % e.value)
        raise LatexError("the formula contains no variable, so there is nothing to compute at run time (it is just the number %d)" % e.value)
    em = _Emit(core_division=(division == "core"), polynomial=polynomial)
    top = _gen(e, em)
    if len(em.divisions) > MAX_GENERAL_DIVISIONS:
        raise LatexError(f"this formula needs {len(em.divisions)} separate long divisions. Each is about 23,000 cells, and the placer takes impractically long for more than one "
                         f"(two had not finished after 10 minutes). For now: one general division per formula (a quotient and a remainder of the same two values share one), "
                         f"divide by a power of two or a plain number you can avoid, or split the formula into two designs")
    if not em.lines or top != f"%_t{em.n}":
        # a bare variable (or something that reduced to one): give the design one computed cell to read
        em.n += 1
        em.lines.append(f"  %_t{em.n} = add i32 {top}, 0")
        top = f"%_t{em.n}"
    body = "\n".join(em.lines).replace(top, "%r")
    sig = ", ".join(f"i32 %{_argname(a)}" for a in args)
    return f"define i32 @formula({sig}) {{\nentry:\n{body}\n  ret i32 %r\n}}\n", args


def eval_ir(ir: str, values: Dict[str, int]) -> int:
    """A tiny interpreter for the IR this module writes (add sub mul and or xor shl lshr ashr udiv urem on 32-bit words). It checks the GENERATOR (the formula became the right operations)
    without the hardware model, so it is fast enough to run on every compile, including designs too large for the VM. `values` maps formula variable -> word."""
    head = ir.splitlines()[0]
    env: Dict[str, int] = {}
    for name in re.findall(r"i32 %(\w+)", head):
        env[name] = values[name[2:]] & MASK if name.startswith("v_") else 0

    def val(t: str) -> int:
        t = t.strip()
        return env[t[1:]] if t.startswith("%") else int(t) & MASK
    for line in ir.splitlines()[2:]:
        m = re.match(r"\s*%(\w+) = (\w+) i32 ([^,]+), (.+)$", line)
        if not m:
            continue
        nm, op, a, b = m.groups()
        x, y = val(a), val(b)
        if op == "add":
            r = x + y
        elif op == "sub":
            r = x - y
        elif op == "mul":
            r = x * y
        elif op == "and":
            r = x & y
        elif op == "or":
            r = x | y
        elif op == "xor":
            r = x ^ y
        elif op == "shl":
            r = x << y
        elif op == "lshr":
            r = x >> y
        elif op == "ashr":
            r = as_signed(x) >> y
        elif op == "udiv":
            r = udiv(x, y)
        elif op == "urem":
            r = umod(x, y)
        else:
            raise ValueError(f"eval_ir: unknown operation {op!r}")
        env[nm] = r & MASK
    return env["r"]


# ---------------------------------------------------------------------------------------------------------------------------------
# 5. Compile, check, run
# ---------------------------------------------------------------------------------------------------------------------------------

CORNERS = [0, 1, 2, 3, 7, 255, 0x7FFF, 0x8000, 0xFFFF, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0xFFFFFFFE]


def check_vectors(args: List[str], n_random: int = 6, seed: int = 1066) -> List[Dict[str, int]]:
    """Corner values (0, 1, small, the sign boundary, all ones) one variable at a time, a few all-the-same, and random words. Deterministic."""
    rng = random.Random(seed)
    vecs: List[Dict[str, int]] = []
    for k in (0, 1, 3, 0x80000000, 0xFFFFFFFF):
        vecs.append({a: k for a in args})
    for i, a in enumerate(args):
        for k in (0, 1, 0xFFFFFFFF, 0x80000000):
            v = {b: (5 + j) for j, b in enumerate(args)}
            v[a] = k
            vecs.append(v)
    for _ in range(n_random):
        vecs.append({a: rng.getrandbits(32) for a in args})
    seen, out = set(), []
    for v in vecs:
        key = tuple(sorted(v.items()))
        if key not in seen:
            seen.add(key)
            out.append(v)
    return out


def as_signed(x: int) -> int:
    x &= MASK
    return x - (1 << 32) if x >> 31 else x


@dataclass
class LatexResult:
    source: str
    label: Optional[str]
    tree: Expr
    ir: str
    args: List[str]
    result: object                     # DagFrontendResult
    checked: int = 0                   # how many test vectors the compiled design was compared on in the VM (the hardware model)
    ir_checked: int = 0                # how many test vectors the generated IR was compared on (the plain interpreter)
    hw_skipped: str = ""               # why the VM comparison was skipped (a design too large for the VM), empty if it ran
    notes: List[str] = field(default_factory=list)

    def reference(self, values: Dict[str, int]) -> int:
        """The plain-Python answer for this formula (unsigned 0..2^32-1)."""
        return evaluate(self.tree, values)

    def run(self, values: Dict[str, int]) -> int:
        """Run the compiled design in the standard VM (unsigned 0..2^32-1)."""
        import llvm_dag_frontend_v1 as F
        return F.run_in_vm(self.result, {_argname(a): values[a] & MASK for a in self.args}) & MASK

    @property
    def cells(self) -> int:
        return len(self.result.records)

    def safe_spacing(self) -> int:
        """Ticks between items for streaming through the flex step simulator. A CONSERVATIVE RULE OF THUMB, not a measured limit: too little gives silently wrong answers."""
        return max(500, 3 * self.cells)

    def stream_step(self, vectors: List[Dict[str, int]], spacing: Optional[int] = None) -> List[int]:
        """Feed the vectors one after another through the flex step simulator (tools/flex_layout_sim_v2) at `spacing` (default safe_spacing()). Returns the answers."""
        import tempfile, shutil
        tools = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools")
        sys.path.insert(0, tools)
        from icm_v3 import IcmV3File
        from flex_layout_view_v1 import Layout
        import flex_layout_sim_v2 as S2
        spacing = spacing or self.safe_spacing()
        cmap = _input_cells(self)                                  # input cell -> argument name
        tmp = tempfile.mkdtemp(prefix="latex_step_")
        try:
            path = os.path.join(tmp, "f.icm")
            IcmV3File(name="formula", records=self.result.records).save(path)
            sim = S2.StepSim(Layout.load(path), width=32)
            nxt, t = 0, 0
            limit = spacing * len(vectors) + 3 * spacing + 5000
            while t < limit and len(sim.seen["main.r"]) < len(vectors):
                if nxt < len(vectors) and t % spacing == 0:
                    sim.inject({c: vectors[nxt][a] & MASK for c, a in cmap.items()})
                    nxt += 1
                sim.step(1)
                t += 1
            return [v & MASK for v in sim.seen["main.r"]]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def _input_cells(res: LatexResult) -> Dict[str, str]:
    """Compiled input cell name -> argument name, read from the IR. One input cell per USE of an argument. An argument next to a literal feeds a single-operand cell (`_x`);
    next to anything else the cells are `_a` / `_b` by operand slot (the compiler's own naming rule)."""
    m: Dict[str, str] = {}
    argset = {_argname(a): a for a in res.args}
    present = {r.cell_id for r in res.result.records}               # operations nothing reads (the unused half of a division) are dropped by the compiler
    for line in res.ir.splitlines():
        mm = re.match(r"\s*%(\w+) = (\w+) i32 ([^,]+), (.+)$", line)
        if not mm:
            continue
        nm, op, a, b = mm.groups()
        a, b = a.strip(), b.strip()
        isarg = lambda t: t.startswith("%") and t[1:] in argset
        if (isarg(a) and _is_lit(b)) or (isarg(b) and _is_lit(a)):
            m[f"main.dynq_{nm}_x"] = argset[(a if isarg(a) else b)[1:]]
        else:
            if isarg(a):
                m[f"main.dynq_{nm}_a"] = argset[a[1:]]
            if isarg(b):
                m[f"main.dynq_{nm}_b"] = argset[b[1:]]
    return {k: v for k, v in m.items() if k in present}


HW_CHECK_MAX_CELLS = 1500          # the standard VM ticks about 3 x cells times, each tick over every cell: beyond this a vector takes minutes


def compile_latex(source: str, check=True, n_random: int = 6, placer: str = "routed_x", hw_max_cells: int = HW_CHECK_MAX_CELLS, division: str = "core", div_steps: int = 0, polynomial: str = "auto") -> LatexResult:
    """Parse, compile and CHECK a formula. Raises LatexError for text outside the subset (or a compiler refusal) and LatexCheckError if anything disagrees with the Python oracle.
    check=True   the generated IR is compared with the oracle on corner and random vectors (always, fast); the compiled design is ALSO run in the VM and compared, unless it has
                 more than `hw_max_cells` cells (then `hw_skipped` says so and the CLI prints it: the VM would take minutes per vector).
    check="full" the VM comparison is run whatever the size (slow for big designs).
    check=False  no comparison (not recommended).
    div_steps    0 (default: each family's own) or K = 1..32 quotient bits per clock for every division cell: a speed-versus-size choice (latency ceil(32/K) clocks; more bits per clock = more logic). Written into the design's div records as `steps`; flex builds it, sub accepts only 32, the VM ignores it (ledger #1077).
    polynomial   "auto" (default, ledger #1078): a one-variable polynomial of degree 2 or more is built both as written and as the Horner plan (arith_plan_library_v1), and the design
                 with fewer cells is kept; "horner" always uses the plan; "direct" never does. The design is checked against the formula either way.
    division     "core" (default) or "unrolled": see to_llvm. With "core" a formula may contain any number of divisions and the design is small enough for the VM check."""
    import llvm_dag_frontend_v1 as F
    label, tree = parse_latex(source)
    if polynomial not in ("auto", "horner", "direct"):
        raise LatexError(f"polynomial must be \"auto\", \"horner\" or \"direct\", not {polynomial!r}")
    ir, args = to_llvm(tree, division=division, polynomial="direct" if polynomial == "auto" else polynomial)
    res, diags = F.compile_llvm_via_dag(ir, placer=placer)
    if polynomial == "auto" and res is not None:
        ir_h, _ = to_llvm(tree, division=division, polynomial="horner")
        if ir_h != ir:                                                  # the formula holds a polynomial the plan can place: keep whichever compiles to fewer cells (a tie keeps the direct form)
            res_h, _d = F.compile_llvm_via_dag(ir_h, placer=placer)
            if res_h is not None and len(res_h.records) < len(res.records):
                ir, res = ir_h, res_h
    if res is None:
        text = "; ".join(f"{d.problem} -- {d.why}. Try: {d.suggestion}" if d.suggestion else f"{d.problem} -- {d.why}" for d in diags)
        raise LatexError("the compiler could not build this formula: " + text)
    if not isinstance(div_steps, int) or isinstance(div_steps, bool) or not 0 <= div_steps <= 32:
        raise LatexError(f"div_steps must be 0 (unset) or 1 to 32, not {div_steps!r}")
    if div_steps:
        for r in res.records:
            if r.core == "div":
                r.core_config = dict(r.core_config or {}, steps=div_steps)
    out = LatexResult(source=source, label=label, tree=tree, ir=ir, args=args, result=res, notes=list(res.rewrites))
    if check:
        vecs = check_vectors(args, n_random=n_random)
        for v in vecs:
            got, want = eval_ir(ir, v), out.reference(v)
            if got != want:
                raise LatexCheckError(f"the generated operations gave {got} but the formula gives {want} for {v}; formula: {source!r}")
            out.ir_checked += 1
        if check == "full" or out.cells <= hw_max_cells:
            for v in vecs:
                got, want = out.run(v), out.reference(v)
                if got != want:
                    raise LatexCheckError(f"the compiled design gave {got} but the formula gives {want} for {v}; formula: {source!r}")
                out.checked += 1
        else:
            out.hw_skipped = (f"the design has {out.cells} cells, more than {hw_max_cells}: the VM comparison was skipped (it would take minutes per value). "
                              f"The generated operations WERE compared with the formula on {out.ir_checked} values; use check=\"full\" to run the VM anyway")
    return out
