"""arith_plan_library_v1.py -- ledger #1078: the arithmetic PLAN library. A plan is a base pattern plus a rule for repeating it, so the compiler places a known shape
at the size asked for instead of rebuilding the arithmetic from single operations each time.

A plan here is a small description (name, base stage, ports that join one copy to the next, how many copies, the operation count it costs) and an `emit` that writes the
repeated stages through the front end's own emitter (`em.op`). So the stages go through the same compiler, placer and cells as everything else: the plan fixes the SHAPE, the
compiler still does the placing. Timing is data-driven, so a longer chain only takes longer.

First plan: `horner`. Base stage: acc' = acc * x + c. Ports: in = acc (previous stage), x (the variable, read by every stage), c (this stage's coefficient); out = acc'.
A degree-N polynomial is N stages chained, out of one stage into the acc port of the next. Operation count: N multiplies and N adds (a zero coefficient drops its add, because
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


PLANS: Dict[str, Plan] = {
    "horner": Plan(
        name="horner",
        summary="a polynomial in one variable as a chain of multiply-add stages",
        base="acc' = acc * x + c",
        ports="in: acc (from the previous stage), x (read by every stage), c (this stage's coefficient); out: acc' (to the next stage's acc)",
        ops=horner_ops,
        emit=horner_emit),
}


def lookup(name: str) -> Plan:
    if name not in PLANS:
        raise KeyError(f"no plan named {name!r}; the library has {sorted(PLANS)}")
    return PLANS[name]
