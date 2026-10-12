"""arith_plan_library_v1.py -- ledger #1078: the arithmetic PLAN library. A plan is a base pattern plus a rule for repeating it, so the compiler places a known shape
at the size asked for instead of rebuilding the arithmetic from single operations each time.

A plan here is a small description (name, base stage, ports that join one copy to the next, how many copies, the operation count it costs) and an `emit` that writes the
repeated stages through the front end's own emitter (`em.op`). So the stages go through the same compiler, placer and cells as everything else: the plan fixes the SHAPE, the
compiler still does the placing. Timing is data-driven, so a longer chain only takes longer.

First plan: `horner`. Base stage: acc' = acc * x + c. Ports: in = acc (previous stage), x (the variable, read by every stage), c (this stage's coefficient); out = acc'.
A degree-N polynomial is N stages chained, out of one stage into the acc port of the next. Also here: `sum_chain` and `product_chain` (ledger #1079), the chains that a fixed-range \\sum / \\prod write out. Measured (compiled cells, routed_x): a chain of adds over plain
variables is exactly 6 cells per term; a balanced TREE of adds was much larger (8 terms: 101 cells against 44 for the chain), so the chain is the shape. A dot product (sum of products of
two vectors) grows faster than linearly (n = 2..9 terms: 29, 53, 89, 137, 188, 260, 326, 413 cells), almost all of it relay cells the general placer adds to route the 2n inputs.
Operation count: N multiplies and N adds (a zero coefficient drops its add, because
acc + 0 = acc; a leading coefficient of 1 drops the first multiply, because 1 * x = x). Arithmetic is mod 2^32 like the cells, so the result equals the expanded polynomial exactly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

MASK = 0xFFFFFFFF
MAX_DEGREE = 64


@dataclass(frozen=True)
class Plan:
    name: str
    summary: str
    base: str                                   # the base pattern, in words
    ports: str                                  # how one copy joins the next
    ops: Callable[[List[int]], int]             # operation count for the given coefficients (the cost formula; tests check it against what is emitted)
    emit: Callable                              # emit(em, x_operand, coeffs_low_to_high) -> result operand


def _lit(v: int) -> str:
    v &= MASK
    return str(v if v < (1 << 31) else v - (1 << 32))


def horner_ops(coeffs: List[int]) -> int:
    """Operations of the Horner chain for coeffs (low degree first, trailing zeros ignored): one multiply and one add per stage, minus the identities."""
    c = _trim(coeffs)
    n = len(c) - 1
    if n < 1:
        return 0
    ops = 0
    lead_one = (c[n] == 1)
    for i in range(n - 1, -1, -1):
        stage_first = (i == n - 1)
        if not (stage_first and lead_one):
            ops += 1                                     # the multiply
        if c[i] != 0:
            ops += 1                                     # the add
    return ops


def _trim(coeffs: List[int]) -> List[int]:
    c = [v & MASK for v in coeffs]
    while len(c) > 1 and c[-1] == 0:
        c.pop()
    return c


def horner_emit(em, x: str, coeffs: List[int]) -> str:
    """Write the stages. Returns the result operand (a %name, or a literal if the polynomial is constant)."""
    c = _trim(coeffs)
    n = len(c) - 1
    if n < 1:
        return _lit(c[0])
    if n > MAX_DEGREE:
        raise ValueError(f"degree {n}: the horner plan is limited to degree {MAX_DEGREE}")
    acc = _lit(c[n])                                      # the leading coefficient starts the chain
    for i in range(n - 1, -1, -1):
        if acc == "1":
            prod = x                                      # 1 * x
        else:
            prod = em.op("mul", x, acc) if acc.lstrip("-").isdigit() else em.op("mul", acc, x)       # literal second where the operation allows it
        acc = prod if c[i] == 0 else em.op("add", prod, _lit(c[i]))
    return acc


def chain_ops(terms: List) -> int:
    """Operations of a chain over the given terms: one join fewer than the number of terms."""
    return max(0, len(terms) - 1)


def _chain_emit(opcode: str):
    def emit(em, terms: List[str]) -> str:
        """Join the already-built term operands into a chain, acc' = acc <op> term, left to right (the first term starts it)."""
        if not terms:
            raise ValueError("a chain needs at least one term")
        acc = terms[0]
        for t in terms[1:]:
            acc = em.op(opcode, acc, t)
        return acc
    return emit


PLANS: Dict[str, Plan] = {
    "horner": Plan(
        name="horner",
        summary="a polynomial in one variable as a chain of multiply-add stages",
        base="acc' = acc * x + c",
        ports="in: acc (from the previous stage), x (read by every stage), c (this stage's coefficient); out: acc' (to the next stage's acc)",
        ops=horner_ops,
        emit=horner_emit),
    "sum_chain": Plan(
        name="sum_chain",
        summary="a sum over a fixed range as a chain of adds (what \\sum_{i=a}^{b} writes out)",
        base="acc' = acc + term",
        ports="in: acc (from the previous stage), term (this stage's value); out: acc' (to the next stage)",
        ops=chain_ops,
        emit=_chain_emit("add")),
    "product_chain": Plan(
        name="product_chain",
        summary="a product over a fixed range as a chain of multiplies (what \\prod_{i=a}^{b} writes out)",
        base="acc' = acc * term",
        ports="in: acc (from the previous stage), term (this stage's value); out: acc' (to the next stage)",
        ops=chain_ops,
        emit=_chain_emit("mul")),
}


def lookup(name: str) -> Plan:
    if name not in PLANS:
        raise KeyError(f"no plan named {name!r}; the library has {sorted(PLANS)}")
    return PLANS[name]
