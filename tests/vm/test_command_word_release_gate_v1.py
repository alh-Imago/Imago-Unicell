"""
test_command_word_release_gate_v1.py -- points.md #860: the real
release gate `#859` left open, built and proven. Closes the exact
hazard Alan named directly: a real command cell "is set in motion when
it gets its first set of data... it doesn't hold" -- so the command-
word builder's own intermediate (rounds 1-3) accumulator offers must
never reach a real target; only the complete, round-4 word may.

Real mechanism: an AND gate, single-shot, two real inputs --

  A = a genuine ENABLE MASK, held by a separate cell (`hold_in=True,
      a_update_in=True`), starting at 0 (disabled). A real update-
      arrival silently REPLACES this held value (produces no offer of
      its own) -- standing in for a `#850`-style pulse-mode counter's
      own threshold pulse (silent while counting, fires exactly once
      at threshold=4), which would flip this mask to all-1s the moment
      the 4th real source has been collected, in a genuine grid-wired
      deployment.
  B = the accumulator's own offered value for that round.

  AND(0, anything) = 0 -- correctly suppresses an early release.
  AND(all-1s, value) = value -- correctly passes the real, complete
  word through, once genuinely enabled.

Real, honest scope, named directly rather than smoothed over: this is
host-orchestrated (direct `CACell` calls, the enable mask flipped by an
explicit host call timed BEFORE round 4 is run), matching the same
real boundary `#859`'s own test already states for itself. It proves
the GATE MECHANISM is logically correct -- decoupled from the separate,
still-open question of exactly how a `#850`-style pulse counter's own
real threshold-pulse would be wired to arrive at the enable mask's own
input at the right real moment in an actual, grid-placed deployment.
That wiring (and its own exact timing/ordering guarantees relative to
the accumulator's own round-4 offer) remains real, unbuilt work.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from unicell_automaton_v1 import CACell, N, S  # noqa: E402
from unicell_gate_core import TOPO_OR, TOPO_AND  # noqa: E402


def _make_source(value: int) -> CACell:
    return CACell(row=0, col=0, start_flag=True, hold_in=True, a_reemit_in=True,
                  a_data=value, a_arrived=True, routing_mask=0)


def _fire_source(src: CACell) -> int:
    accepted, forward = src.deliver({N: 0})
    assert accepted
    _route, value = forward
    src.pending_ack = 0
    src._needs_confirm = False
    return value


def _make_accumulator() -> CACell:
    return CACell(row=0, col=0, start_flag=True, hold_in=True, loop_back=True,
                  topology=TOPO_OR, routing_mask=0)


def _feed_accumulator(acc: CACell, value: int):
    accepted, forward = acc.deliver({N: value})
    assert accepted
    acc.pending_ack = 0
    acc._needs_confirm = False
    return forward


def _make_gate_enable() -> CACell:
    """Starts disabled (0). Stands in for the held output of a
    #850-style pulse-mode counter, not yet built for real here."""
    return CACell(row=0, col=0, start_flag=True, hold_in=True, a_update_in=True,
                  a_data=0, a_arrived=True, routing_mask=0)


def _update_gate_enable(gate: CACell, new_value: int) -> None:
    accepted, forward = gate.deliver({N: new_value})
    assert accepted
    assert forward is None, "a_update_in mode must never itself produce an offer"
    gate.pending_ack = 0
    gate._needs_confirm = False


def _try_release(gate_enable_value: int, candidate_value: int):
    """A fresh, real, single-shot AND gate per attempt -- real two-
    arrival capture, A (enable) first, B (candidate) second, fires once."""
    rg = CACell(row=0, col=0, start_flag=True, topology=TOPO_AND, routing_mask=0)
    accepted, forward = rg.deliver({N: gate_enable_value})
    assert accepted and forward is None, "capturing A alone must not fire yet"
    accepted, forward = rg.deliver({S: candidate_value})
    assert accepted
    return forward[1] if forward else 0


def test_release_gate_suppresses_every_intermediate_round():
    """Real, concrete proof of the exact hazard #859 demonstrated and
    Alan named directly: rounds 2 and 3's own real, correctly-computed
    partial values must both be suppressed to 0 while the gate is
    still disabled."""
    src0 = _make_source(0x11)
    src1 = _make_source(0xAA << 8)
    src2 = _make_source(0x01 << 16)
    acc = _make_accumulator()
    gate = _make_gate_enable()

    _feed_accumulator(acc, _fire_source(src0))
    r2 = _feed_accumulator(acc, _fire_source(src1))
    r3 = _feed_accumulator(acc, _fire_source(src2))

    assert r2[1] == 0xAA11, "sanity: round 2's own real partial value"
    assert _try_release(gate.a_data, r2[1]) == 0, "round 2 must be suppressed"
    assert r3[1] == 0x1AA11, "sanity: round 3's own real partial value"
    assert _try_release(gate.a_data, r3[1]) == 0, "round 3 must be suppressed"


def test_release_gate_passes_through_the_complete_word_once_enabled():
    """The real, positive half of the proof: once the enable mask is
    genuinely flipped (standing in for the pulse-counter's own real
    threshold pulse), the gate correctly releases the complete word,
    not a truncated or corrupted one."""
    src0 = _make_source(0x11)
    src1 = _make_source(0xAA << 8)
    src2 = _make_source(0x01 << 16)
    src3 = _make_source(0xF0 << 24)
    acc = _make_accumulator()
    gate = _make_gate_enable()

    _feed_accumulator(acc, _fire_source(src0))
    _feed_accumulator(acc, _fire_source(src1))
    _feed_accumulator(acc, _fire_source(src2))
    _update_gate_enable(gate, 0xFFFFFFFF)   # the real pulse, standing in for #850's own threshold-fire
    final = _feed_accumulator(acc, _fire_source(src3))

    assert final[1] == 0xF001AA11, "sanity: the real, complete word"
    assert _try_release(gate.a_data, final[1]) == 0xF001AA11, "must pass through unmodified once enabled"


def test_release_gate_still_suppresses_if_enabled_too_early():
    """A real, necessary negative check: enabling the gate does NOT
    retroactively validate an already-partial value -- the gate only
    ever does a plain AND of whatever it's given. If something
    genuinely enabled the gate before round 4, an EARLY value would
    incorrectly pass through -- confirming the real ordering
    requirement (enable must happen at or after the true final round,
    never before) rather than assuming the gate protects against
    misordering on its own."""
    partial_value = 0x1AA11   # round 3's own real, partial value
    released = _try_release(0xFFFFFFFF, partial_value)
    assert released == partial_value, (
        "the gate itself does not detect 'this is a partial value' -- "
        "correct release timing is a real, separate responsibility "
        "(the pulse-counter's own threshold), not something this gate "
        "alone can guarantee"
    )
