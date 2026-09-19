"""
vix_convergence_shapes_v1.py — points.md #777: the real, formalized
shape catalog Alan's own direct synthesis describes, unifying every
rule proven across `#750`-`#776` into one concrete decision function --
"you chain these together and shrink."

Alan's own real synthesis, quoted directly: "if there is an adder, or
other 2 sequence arrival needed, and it has an order, like the
subtract, it needs a sequencer, that's its front end, if not it can
use priority or just 1 chain in if all the data is in order, so that's
the shape in the library, if it needs a set stagger, that's the shape
in the library, you chain these together and shrink."

REAL, DELIBERATE SHARPENING of one nuance, confirmed by re-checking
`#773`/`#774` directly rather than assumed: "set stagger" (relay-
padding, `#750`/`#771`/`#773`) and "sequencer" (`#772`) are not
interchangeable choices for the same real case -- they are two
DIFFERENT real shapes, chosen by whether the real arrival timing is
KNOWABLE at compile time, not simply "order-sensitive vs not":
- Order doesn't matter (commutative) + genuine convergence -> PRIORITY
  (rank-based, `#751`/`#765`) -- simplest real shape once no operand-
  identity concern exists at all.
- No genuine convergence at all (a single, already-ordered dependency)
  -> PLAIN CHAIN -- no arbitration cell needed whatsoever (`#756`).
- Order matters (non-commutative) + real arrival ticks are KNOWABLE
  (both operands are leaves and/or composed results with a real,
  computable ready tick) -> STAGGER (relay-padding equalized to the
  correct real arrival tick, `#773`'s own sharpened formula -- equal
  TICK, not merely equal hop count).
- Order matters + at least one real operand's own arrival tick is
  genuinely UNKNOWABLE at compile time (a dynamic, runtime value) ->
  SEQUENCER (`#772`'s own sequenced-channel mode) -- the only real
  shape that needs no advance timing knowledge at all, confirmed
  directly in `#774`.

Real, honest scope: this module formalizes the real DECISION RULE and
a real, minimal shape catalog -- it does not yet wire this into the
LLVM IR frontend or `vix_compiler_v1.py` (`#776`'s own real, next,
separate step). Every 2-way shape here builds on tiles/functions
already proven this session; N-way composition (chaining 2-way shapes
together, then tightening) is `#765`'s own already-proven recursive
structure, reused directly, not reinvented.
"""
from __future__ import annotations

from enum import Enum


class ConvergenceShape(Enum):
    """The real, minimal catalog of known convergence shapes this
    session's own work has proven, each with its own real, distinct
    real-world justification -- not an arbitrary taxonomy."""

    PLAIN_CHAIN = "plain_chain"
    """No genuine convergence at all -- a single, already-ordered
    dependency (`#756`'s own already-proven linear-chain compilation).
    No arbitration cell of any kind is needed."""

    PRIORITY = "priority"
    """Genuine convergence, but the operation is commutative --
    operand identity doesn't matter, so simple, rank-based `priority`
    arbitration (`#751`) is sufficient and simplest. No timing
    equalization needed at all."""

    STAGGER = "stagger"
    """Genuine convergence, the operation is non-commutative (operand
    identity matters), AND both real operands have a knowable real
    arrival tick at compile time (leaves and/or composed results).
    Uses relay-padding to equalize the real arrival TICK (`#773`'s own
    sharpened rule -- not merely equal hop count) so rank correctly
    decides which operand becomes which. Zero head-of-line-blocking
    cost once built correctly, but requires the compiler to compute
    real, exact timing -- a real, genuine risk if that computation is
    ever wrong (`#770`'s own original finding)."""

    SEQUENCER = "sequencer"
    """Genuine convergence, the operation is non-commutative, AND at
    least one real operand's own arrival tick is genuinely unknowable
    at compile time (a dynamic, runtime value, `#774`). The only real
    shape that needs no advance timing knowledge at all -- structurally
    immune to `#770`'s own hazard, at the real cost of potential
    head-of-line blocking (`#772`'s own named trade-off)."""


def choose_convergence_shape(has_real_convergence: bool, is_commutative: bool,
                              all_arrival_ticks_knowable: bool) -> ConvergenceShape:
    """The real, formalized decision function synthesizing `#750`-
    `#776` into Alan's own stated rule. Real, deliberate parameters,
    each one a real, compile-time-answerable fact about a specific
    real convergence point, not a guess:

    `has_real_convergence`: does this real consumer genuinely have TWO
    OR MORE separate, real producers meeting at it, or is it fed by a
    single, already-ordered dependency? (`#756` vs `#750`'s own
    distinction.)

    `is_commutative`: does swapping the two real operands change the
    real result? (`add`/`mul` -> True; `subtract` and everything else
    where operand identity matters -> False.)

    `all_arrival_ticks_knowable`: can the compiler compute a real,
    exact arrival tick for every real operand feeding this point at
    compile time? True for leaves and composed results (`#773`'s own
    generalized `symbolic_arrival_tick()`/`composed_output_ready_tick()`
    formulas); False the moment any real operand is a genuinely
    dynamic, runtime value (`#774`)."""
    if not has_real_convergence:
        return ConvergenceShape.PLAIN_CHAIN
    if is_commutative:
        return ConvergenceShape.PRIORITY
    if all_arrival_ticks_knowable:
        return ConvergenceShape.STAGGER
    return ConvergenceShape.SEQUENCER
