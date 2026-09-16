"""
rats_nest_timing_v1.py — points.md #764: the real, symbolic timing
model this session's own rat's-nest work named as necessary but did
not build for the priority-based case (`#761`/`#763`, where `priority`
absorbs any real timing mismatch by design, so no timing check was
needed there). This module is for the genuinely different, HARDER
case: a plain, relay-padded convergence (`#750`'s own original
technique -- no `priority`, two paths must keep genuinely different
real lengths to stay correct).

Per Alan's own direct proposal: the timing check runs AFTER the
structural/collision check, using a lightweight, no-VM model -- "using
the lighter model, maybe easier on large models."

REAL, GROUNDED FACTS, confirmed directly against the actual VM before
writing a single line of this model, not assumed or derived from
theory (see points.md #764 for the full, real ground-truth trace):
- A preloaded (`ram_preload`, flowing-mode) source is already `data_
  valid=True` from construction -- it offers on the real VM's very
  first real tick.
- A real adder captures its first real arrival on the tick AFTER that
  offer -- confirmed directly: a source with ZERO relay hops between
  it and the adder has its value captured at real tick 2, not tick 1.
- Each real relay hop adds exactly one real tick of delay -- confirmed
  directly: 1 hop -> captured/completed one tick later; 3 hops -> three
  ticks later, in both cases exactly matching the real hop count, not
  approximately.
- Real, sharpened consequence, matching `#750`'s own real finding
  exactly: two real paths into the SAME two-arrival consumer collide
  if and only if they have the SAME real relay-hop count -- confirmed
  directly, not assumed: equal hop counts (0 and 0) produced the real,
  wrong result (`0`, and the consumer's own `adder_data_valid` never
  even became `True`); every unequal pair tested produced the correct
  result.

REAL, HONEST SCOPE: this model covers exactly the shape this session's
own ground-truth testing confirmed -- two preloaded sources converging
on one plain, two-arrival core (`adder`/`subtractor`/`mul`) via
straight relay chains. It does not yet model a source that is itself
the OUTPUT of an upstream computation (a real, additional real delay
term this module does not compute) -- real, separate, not-yet-tested
work.
"""
from __future__ import annotations

from typing import Optional


# Confirmed directly against the real VM (points.md #764): a preloaded
# source's own value is captured by a directly-adjacent, two-arrival
# consumer on real tick 2 -- not tick 1, matching the VM's own real
# offer-then-deliver cycle (offer happens at the end of one tick;
# capture is processed on the next).
_BASE_ARRIVAL_TICK = 2


def symbolic_arrival_tick(relay_hop_count: int) -> int:
    """The real, predicted tick at which a preloaded source's own value
    is captured by a two-arrival consumer at the far end of a real,
    straight relay chain of `relay_hop_count` cells. Confirmed directly
    against the real VM for hop counts 0, 1, and 3 -- exact match in
    every case, not an approximation."""
    return _BASE_ARRIVAL_TICK + relay_hop_count


def would_collide(hop_count_a: int, hop_count_b: int) -> bool:
    """Real, symbolic prediction of `#750`'s own real hazard: two
    preloaded sources converging on the SAME real, two-arrival consumer
    collide if and only if their own real relay-hop counts are equal --
    confirmed directly against the real VM, not derived from theory
    alone. This is the real, lightweight check meant to run AFTER a
    real structural/collision check passes, per Alan's own direct
    proposal -- a candidate tightening step is only accepted if BOTH
    checks pass."""
    return symbolic_arrival_tick(hop_count_a) == symbolic_arrival_tick(hop_count_b)


def min_safe_hop_count(fixed_hop_count: int, other_hop_count: int) -> Optional[int]:
    """Given one real path's own hop count already fixed, the real,
    minimum hop count the OTHER path could use while still avoiding a
    real collision -- either one hop shorter or one hop longer than
    `fixed_hop_count`, whichever is closer to `other_hop_count`'s own
    real, current value (so tightening prefers shrinking toward the
    real minimum total length, not growing it). Returns `None` only if
    `fixed_hop_count` is already 0 and `other_hop_count` would need to
    go negative to differ downward -- in that real case, the only safe
    move is lengthening, not shortening."""
    if other_hop_count < fixed_hop_count:
        return fixed_hop_count - 1 if fixed_hop_count > 0 else None
    if other_hop_count > fixed_hop_count:
        return fixed_hop_count + 1
    return fixed_hop_count + 1  # equal today -- the real, minimal fix is one hop longer
