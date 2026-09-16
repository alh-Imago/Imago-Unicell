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

REAL, HONEST SCOPE, updated (`#765`): originally covered only two
preloaded leaves converging on one plain, two-arrival core. Now
generalized to cover a source that is itself a composed piece's own
output too, via `composed_output_ready_tick()` -- confirmed directly
against real VM ground truth (see `points.md` #765) that a downstream
consumer's own real capture delay past a composed piece's own output
follows the EXACT SAME formula as past a preloaded leaf, once that
piece's own real "ready tick" is known.
"""
from __future__ import annotations

from typing import Optional


# Confirmed directly against the real VM (points.md #764): a preloaded
# leaf source is modeled as "ready" at a real, fixed tick of 1 -- a
# modeling convention chosen so the general formula below reproduces
# the real, measured base case (a leaf with zero relay hops is
# captured at real tick 2) exactly, not by coincidence.
_LEAF_READY_TICK = 1


def symbolic_arrival_tick(relay_hop_count: int, source_ready_tick: int = _LEAF_READY_TICK) -> int:
    """The real, predicted tick at which a value becomes available to a
    two-arrival consumer at the far end of a real, straight relay chain
    of `relay_hop_count` cells, given the value's own real source
    becomes ready at `source_ready_tick`. Defaults to a preloaded leaf
    (`source_ready_tick=1`), reproducing this module's own original,
    leaf-only formula exactly for backward compatibility.

    Points.md #765: generalized directly from real, ground-truth VM
    traces, not derived from theory alone -- confirmed for a composed
    piece's own output (a real, upstream two-arrival adder) feeding a
    downstream consumer through 0, 1, 2, and 3 real relay hops: the
    real, measured delay is EXACTLY `source_ready_tick + hop_count + 1`
    in every case, the same real formula the original, leaf-only
    version already used with `source_ready_tick` fixed at 1."""
    return source_ready_tick + relay_hop_count + 1


def composed_output_ready_tick(input_a_arrival_tick: int, input_b_arrival_tick: int) -> int:
    """Points.md #765: the real tick at which a two-arrival core's own
    output becomes ready (offering downstream), given the real arrival
    ticks of its own two real inputs. Confirmed directly against the
    real VM, not assumed: a two-arrival core's own `data_valid` becomes
    True on the EXACT SAME real tick its own second, later-arriving
    input is captured -- no additional real delay beyond that. This is
    the real, recursive piece that lets `symbolic_arrival_tick()` be
    applied to a SOURCE that is itself a composed piece's own output,
    not just a preloaded leaf -- pass this function's own real result
    as the next level's own `source_ready_tick`."""
    return max(input_a_arrival_tick, input_b_arrival_tick)


def would_collide(hop_count_a: int, hop_count_b: int,
                   source_ready_a: int = _LEAF_READY_TICK,
                   source_ready_b: int = _LEAF_READY_TICK) -> bool:
    """Real, symbolic prediction of `#750`'s own real hazard: two
    values converging on the SAME real, two-arrival consumer collide if
    and only if their own real, predicted arrival ticks are equal --
    confirmed directly against the real VM, not derived from theory
    alone. Defaults to two preloaded leaves (matching this module's own
    original real scope); `source_ready_a`/`source_ready_b` generalize
    this to real, composed sources (`#765`) by passing each one's own
    real `composed_output_ready_tick()` result instead of the default."""
    return (symbolic_arrival_tick(hop_count_a, source_ready_a)
            == symbolic_arrival_tick(hop_count_b, source_ready_b))


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


def choose_tightening_strategy(convergence_kinds: "list[str]") -> str:
    """Points.md #766: the real, stated dispatch rule Alan gave
    directly for a design where convergence points might use EITHER
    real style -- `priority`-arbitrated (`#761`/`#763`, no timing check
    needed, `priority` absorbs any real mismatch by design) or plain,
    relay-padded (`#750`/`#764`, where real timing genuinely decides
    correctness). Each item in `convergence_kinds` is the real style
    used at one real convergence point in the design: `"priority"` or
    `"relay_padded"`.

    Returns `"fast"` if every real convergence point in the design uses
    `priority` (safe to use the fast, structural-only tightening
    throughout, `#762`); `"timing"` otherwise. Real, honest reasoning
    for the mixed case, stated precisely rather than overclaimed: a
    `priority` nexus's own two real inputs arrive on genuinely
    different physical directions (its own N/S faces), never sharing
    one direction the way `adder`'s `in_a`/`in_b` do -- so `#750`'s own
    real hazard (`would_collide()`'s own real subject) doesn't apply to
    it at all, not merely "harmlessly." Alan's own real point stands
    regardless: for a MIXED design, using the relay-padded-style,
    timing-aware tightening path (`#764`) UNIFORMLY -- rather than
    dispatching per convergence point -- is a real, simpler, single
    code path that correctly covers the relay-padded points (where it's
    required) at the real cost of not using `priority`'s own faster
    path where it would have been available. Slower, but one real,
    uniform mechanism handling both real cases at once, exactly as
    Alan proposed."""
    if not convergence_kinds:
        raise ValueError("choose_tightening_strategy: no convergence points given")
    if all(k == "priority" for k in convergence_kinds):
        return "fast"
    return "timing"
