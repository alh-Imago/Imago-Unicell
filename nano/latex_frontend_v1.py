"""nano/latex_frontend_v1.py -- ledger #1066: write a formula in LaTeX, get a UniCell design that computes it, checked against a plain Python evaluation of the SAME formula.

    from latex_frontend_v1 import compile_latex
    r = compile_latex(r"y = (a + b)^2 - 3c")
    r.args                      # ['a', 'b', 'c']   (order of first appearance)
    r.run({"a": 2, "b": 3, "c": 4})          # 13
    r.reference({"a": 2, "b": 3, "c": 4})    # 13  (the pure-Python answer, the oracle)

WHAT IT IS: a small, strict parser for integer maths. It turns the formula into LLVM IR (add, sub, mul only) and hands it to the existing compiler with `placer="routed_x"`
(crossing tiles, a relay tree for values read more than three times, constant folding, plain refusals). It adds no new hardware and no new cell kinds.

WHAT IT COMPUTES: 32-bit whole numbers that wrap around (two's complement), exactly like the cells. `2^31 + 2^31` is 0, not 4294967296. Results come back as unsigned 0..2^32-1;
`as_signed()` gives the signed reading. There are NO fractions: a decimal point, division, roots and functions (sin, log, ...) are refused with a message, never approximated.

SUPPORTED (and nothing else):
  numbers      whole numbers: 12, 0x1F is NOT supported (LaTeX has no hex)
  names        one letter is one variable: `x`; two letters side by side are a PRODUCT (`xy` means x times y, as in maths). A longer name: `\\mathrm{rate}` or `\\text{rate}`.
               Subscripts: `x_1`, `x_{12}`, `a_i`. Greek letters: `\\alpha` ... `\\omega` (no `\\pi`, `\\e`: those are not whole numbers).
  operators    +  -  (also unary minus)   *   \\cdot   \\times   and plain side-by-side multiplication (`2x`, `3(a+b)`, `(a)(b)`)
  grouping     ( )   \\left( \\right)   { }   (square brackets [ ] too)
  powers       x^2, x^{3}, (a+b)^2: the exponent must be a whole number written out (0..64). Not x^n, not x^{-1}, not x^{1/2}.
  naming       an optional `name =` in front is just a label; it must not appear on the right-hand side.
  spacing      \\, \\; \\: \\! \\quad \\qquad and spaces are ignored.

Anything else raises `LatexError` with the position and a plain reason. The first version refuses rather than guesses.

HOW IT IS CHECKED (correctness first): `compile_latex(..., check=True)` (the default) runs the compiled design in the standard VM on a fixed set of corner values plus random ones
and compares every answer with `reference()`. A mismatch raises `LatexCheckError`; it does not return a design. `run_stream_step()` does the same in the flex step simulator, feeding
items at `safe_spacing()`, a CONSERVATIVE rule of thumb (not a measured limit): feeding items closer than the design can take gives silently wrong answers, so the default is generous.
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
    "frac": "division is not supported: the cells add, subtract and multiply whole numbers. Multiply through by the denominator instead, or ask for a divider to be built",
    "dfrac": "division is not supported: the cells add, subtract and multiply whole numbers",
    "tfrac": "division is not supported: the cells add, subtract and multiply whole numbers",
    "div": "division is not supported: the cells add, subtract and multiply whole numbers",
    "sqrt": "square roots are not supported (no fractions or irrational results; only whole numbers)",
    "sum": "sums over a range (\\sum) are not supported yet; write the terms out",
    "prod": "products over a range (\\prod) are not supported yet; write the factors out",
    "int": "integrals are not supported",
    "pi": "pi is not a whole number; only whole-number maths is supported",
    "infty": "infinity is not a number the cells can hold",
    "pm": "plus-or-minus gives two answers; write the two formulas separately",
    "mp": "minus-or-plus gives two answers; write the two formulas separately",
}
FUNCTIONS = {"sin", "cos", "tan", "cot", "sec", "csc", "log", "ln", "exp", "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh", "min", "max", "gcd", "lcm", "det", "lim", "mod", "bmod", "pmod"}


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
            raise LatexError(NOT_YET["div"], src, i)
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
        while True:
            t = self.peek()
            if t.kind == "op" and t.text == "*":
                self.take()
                right = self.unary()
                left = Bin("*", left, right)
            elif t.kind in ("num", "name", "lparen") and not (t.kind == "lparen" and t.text in ")]}"):
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

    def atom(self) -> Expr:
        t = self.peek()
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
        elif isinstance(x, Bin):
            walk(x.left)
            walk(x.right)
        elif isinstance(x, Pow):
            walk(x.base)
    walk(e)
    return seen


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
    def __init__(self):
        self.lines: List[str] = []
        self.n = 0
        self.memo: Dict[Tuple, str] = {}

    def op(self, opcode: str, a: str, b: str) -> str:
        key = (opcode, a, b) if opcode == "sub" else (opcode,) + tuple(sorted((a, b)))     # the same sum or product is built once
        if key in self.memo:
            return self.memo[key]
        self.n += 1
        nm = f"%_t{self.n}"
        self.lines.append(f"  {nm} = {opcode} i32 {a}, {b}")
        self.memo[key] = nm
        return nm


def _is_lit(x: str) -> bool:
    return re.fullmatch(r"-?\d+", x) is not None


def _gen(e: Expr, em: _Emit) -> str:
    """Operand string (a %name or a literal). Literals go second wherever the operation allows it."""
    if isinstance(e, Num):
        return str(e.value if e.value < (1 << 31) else e.value - (1 << 32))
    if isinstance(e, Var):
        return "%" + _argname(e.name)
    if isinstance(e, Neg):
        a = _gen(e.arg, em)
        return em.op("mul", a, "-1")
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


def to_llvm(e: Expr, args: Optional[List[str]] = None) -> Tuple[str, List[str]]:
    """(LLVM IR text, argument names). The returned value is always named %r. Raises LatexError if the formula has no variable or reduces to one."""
    e = fold(e)
    args = args if args is not None else variables(e)
    if isinstance(e, Num):
        raise LatexError("the formula contains no variable, so there is nothing to compute at run time (it is just the number %d)" % e.value)
    em = _Emit()
    top = _gen(e, em)
    if not em.lines or top != f"%_t{em.n}":
        # a bare variable (or something that reduced to one): give the design one computed cell to read
        em.n += 1
        em.lines.append(f"  %_t{em.n} = add i32 {top}, 0")
        top = f"%_t{em.n}"
    body = "\n".join(em.lines).replace(top, "%r")
    sig = ", ".join(f"i32 %{_argname(a)}" for a in args)
    return f"define i32 @formula({sig}) {{\nentry:\n{body}\n  ret i32 %r\n}}\n", args


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
    checked: int = 0                   # how many test vectors the compiled design was compared on
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
    return m


def compile_latex(source: str, check: bool = True, n_random: int = 6, placer: str = "routed_x") -> LatexResult:
    """Parse, compile and (by default) CHECK a formula. Raises LatexError for text outside the subset, LatexCheckError if the compiled design disagrees with the Python oracle,
    and LatexError (with the compiler's own words) if the compiler refuses the design."""
    import llvm_dag_frontend_v1 as F
    label, tree = parse_latex(source)
    ir, args = to_llvm(tree)
    res, diags = F.compile_llvm_via_dag(ir, placer=placer)
    if res is None:
        text = "; ".join(f"{d.problem} -- {d.why}. Try: {d.suggestion}" if d.suggestion else f"{d.problem} -- {d.why}" for d in diags)
        raise LatexError("the compiler could not build this formula: " + text)
    out = LatexResult(source=source, label=label, tree=tree, ir=ir, args=args, result=res, notes=list(res.rewrites))
    if check:
        for v in check_vectors(args, n_random=n_random):
            got, want = out.run(v), out.reference(v)
            if got != want:
                raise LatexCheckError(f"the compiled design gave {got} but the formula gives {want} for {v}; formula: {source!r}")
            out.checked += 1
    return out
