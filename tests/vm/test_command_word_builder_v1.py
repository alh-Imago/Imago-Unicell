"""
test_command_word_builder_v1.py -- points.md #859: proves Alan's own
real design (multiple narrow sources, combined via nano's own OR and
shift capability, assembling a wide command word to feed a command
cell's own programmer-mode relay) -- corrected via the ALREADY-PROVEN
#382/#390-#397 collector mechanism, after a first, naive attempt
(parallel OR-tree, two independent free-running sources racing to fill
one nano's A/B slots) genuinely failed.

Real design history, kept honest rather than presenting only the final
answer:

  Attempt 1 (two independent sequencers feeding one nano's A/B slots in
  parallel, then a 3-nano OR tree): produced a genuinely garbled result
  (0xfa11 instead of the correct 0xf001aa11). Root cause, confirmed
  directly against `unicell_automaton_v1.py`'s own real capture logic:
  nano's A/B capture is source-AGNOSTIC and first-come-first-served --
  whichever real arrival shows up first becomes A, whichever shows up
  second (from ANY other open direction) becomes B. With two
  independent, free-running sources, a faster one can supply BOTH
  slots for a round, silently skipping the slower source's own
  contribution entirely. A real, genuine finding: nano's OR is
  commutative (order doesn't itself cause wrong VALUES), but the
  TEMPORAL pairing across independent sources is genuinely unsafe
  without an explicit synchronizing mechanism.

  Attempt 2 (this file): Alan's own real recollection -- "we have
  tried this before" -- pointed directly at real, already-proven prior
  work: `#301`/`#302`/`#381`/`#390-#397`
  (`docs/stripped-cell/design-notes/ram_interface_collector_mechanism.md`),
  the RAM-interface collector mechanism, and its own real VM-level
  proof (`test_hierarchical_27leaf_collector_v1.py`, the 27=3x3x3
  hierarchical collector). The real fix: never let more than one
  source be live at a time. Each source is a nano configured
  `hold_in=True, a_reemit_in=True` (holds its own pre-shifted value,
  silent until explicitly triggered, the trigger's own content
  irrelevant -- #382's own Finding 3), triggered ONE AT A TIME by the
  host (standing in for a real command cell's own lockstep
  reprogram+trigger, per #302's own Finding 4). No two sources are
  ever live simultaneously, so nano's own source-agnostic A/B capture
  never gets a chance to race.

  Real, new extension beyond #382's own original proof: that test only
  ever did pure single-value RELAY (pass-through, unmodified). This
  file adds real OR-ACCUMULATION on top, using nano's own `loop_back`
  field (confirmed directly in `unicell_automaton_v1.py`: `if
  self.loop_back: self.a_data = computed` -- the gate's own computed
  result becomes the new held A for the next round) with
  `hold_in=True` (so `a_arrived` stays sticky across multiple real
  B-arrivals, instead of resetting after one fire) -- each new,
  already-shifted source value gets folded into a running OR total,
  correctly assembling a full 32-bit word from four independent 8-bit
  contributions, one real, explicit collection step at a time.

Real, honest scope, named directly rather than smoothed over, matching
the SAME boundary `test_hierarchical_27leaf_collector_v1.py` already
states for itself: this drives real `CACell` objects directly
(host-orchestrated, matching #382's own proven methodology) -- it does
NOT attempt real 2D grid embedding of these cells, and it does NOT
attempt the real, separate, still-open question Alan named directly:
in a genuine grid-wired deployment (not host-orchestrated), the target
command cell "is set in motion when it gets its first set of data...
it doesn't hold" -- meaning the accumulator's own intermediate (rounds
1-3) offered outputs must be genuinely SUPPRESSED from ever reaching
the real target, with only the round-4 (complete) value released, in
one clean step. This test's own host simply chooses which round's
output to forward (an honest simplification for proving the core
mechanism); the real, grid-wired gate for this -- the natural
candidate being a `#850`-style pulse-mode counter that only fires once
after the 4th real collection -- remains a real, separate, unbuilt
piece of work.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from unicell_automaton_v1 import CACell, N  # noqa: E402
from unicell_gate_core import TOPO_OR  # noqa: E402


def _make_source(value: int) -> CACell:
    """A held, pre-loaded source -- identical real shape to #382's own
    `_make_header`, reused directly, not reinvented."""
    return CACell(row=0, col=0, start_flag=True, hold_in=True, a_reemit_in=True,
                  a_data=value, a_arrived=True, routing_mask=0)


def _fire_source(src: CACell) -> int:
    """Trigger a source to reemit its held value -- the trigger's own
    content is irrelevant (#382 Finding 3), N with a dummy 0 used
    uniformly, same convention as the proven collector test."""
    accepted, forward = src.deliver({N: 0})
    assert accepted, "source rejected its own reemit trigger"
    _route, value = forward
    src.pending_ack = 0
    src._needs_confirm = False
    return value


def _make_accumulator() -> CACell:
    """Real, new extension of #382's own collector shape: hold_in+
    loop_back+TOPO_OR, so each new arrival gets OR'd into a running
    total that persists as the cell's own held A for the next round,
    rather than pure single-value relay."""
    return CACell(row=0, col=0, start_flag=True, hold_in=True, loop_back=True,
                  topology=TOPO_OR, routing_mask=0)


def _feed_accumulator(acc: CACell, value: int):
    """Deliver one already-shifted contribution into the accumulator.
    Returns the round's own offered (route, value) tuple if this round
    produced a real fire, else None (the very first round only
    captures A, computing nothing yet -- matches nano's own real,
    confirmed capture-then-fire two-stage shape)."""
    accepted, forward = acc.deliver({N: value})
    assert accepted, "accumulator rejected delivery"
    acc.pending_ack = 0
    acc._needs_confirm = False
    return forward


def _build_word(byte0: int, byte1: int, byte2: int, byte3: int) -> int:
    """The real, complete mechanism: four sources, pre-shifted into
    their own correct byte position, collected ONE AT A TIME (never
    two live simultaneously), OR-accumulated into one 32-bit word."""
    src0 = _make_source(byte0)
    src1 = _make_source(byte1 << 8)
    src2 = _make_source(byte2 << 16)
    src3 = _make_source(byte3 << 24)
    acc = _make_accumulator()

    _feed_accumulator(acc, _fire_source(src0))   # round 1: capture only
    _feed_accumulator(acc, _fire_source(src1))   # round 2: real OR
    _feed_accumulator(acc, _fire_source(src2))   # round 3: real OR
    final = _feed_accumulator(acc, _fire_source(src3))   # round 4: the complete word
    return final[1]


def test_single_word_assembles_correctly():
    result = _build_word(0x11, 0xAA, 0x01, 0xF0)
    assert result == 0xF001AA11


def test_four_distinct_words_all_assemble_correctly():
    """The real, motivating case: up to 4 distinct full command words,
    one per real 'slot' across four independently-cycling sources --
    matching Alan's own original framing ('allowing up to 4 sets of
    commands to be sent')."""
    seq_a = [0x11, 0x22, 0x33, 0x44]
    seq_b = [0xAA, 0xBB, 0xCC, 0xDD]
    seq_c = [0x01, 0x02, 0x03, 0x04]
    seq_d = [0xF0, 0xF1, 0xF2, 0xF3]
    expected = [0xF001AA11, 0xF102BB22, 0xF203CC33, 0xF304DD44]

    for slot in range(4):
        result = _build_word(seq_a[slot], seq_b[slot], seq_c[slot], seq_d[slot])
        assert result == expected[slot], f"slot {slot}: got {result:08x}, expected {expected[slot]:08x}"


def test_intermediate_rounds_are_real_partial_values_not_the_final_word():
    """Confirms directly (not assumed) the exact real hazard Alan named:
    an intermediate round's own offered value is genuinely a PARTIAL,
    wrong-if-forwarded-prematurely result -- concrete evidence for why a
    real grid-wired deployment needs an explicit release gate, not just
    documentation of the concern."""
    src0 = _make_source(0x11)
    src1 = _make_source(0xAA << 8)
    src2 = _make_source(0x01 << 16)
    acc = _make_accumulator()

    _feed_accumulator(acc, _fire_source(src0))
    round2 = _feed_accumulator(acc, _fire_source(src1))
    round3 = _feed_accumulator(acc, _fire_source(src2))

    assert round2[1] == 0xAA11, "round 2's own real offer -- correct so far, but NOT the final word"
    assert round3[1] == 0x1AA11, "round 3's own real offer -- still partial"
    assert round3[1] != 0xF001AA11, "genuinely wrong if a real command cell fired on this early"
