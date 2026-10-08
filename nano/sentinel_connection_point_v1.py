"""
sentinel_connection_point_v1.py -- points.md #872: the existing `Sentinel`
(`sentinel_counter_v1.v`'s faithful port, #279/#410) attached to a
`VixCarrierGrid` as a CONNECTION POINT, so a drain-complete signal that does
not depend on the data's VALUE can prompt a reconfigure.

Why this exists (Alan, 2026-09-28): any data passing through a chain is
modified by it, so a trigger cannot live in the data -- and a value match on
data is just a comparator, which only works for one known value. #871's loop
used the item itself as its marker; that was a placeholder. The sentinel counts
FEED pulses at a chain's head and COLLECT pulses at its tail and never reads a
value: `diff == 0` with the feed side frozen is the exact "run finished" signal.

What is modelled, and where each piece comes from:
  * `Sentinel` -- the real, RTL-ported counter (diff, out_frozen, sticky
    underflow/overflow, safe_to_intervene). Unchanged.
  * FEED / COLLECT taps -- counted from ACCEPTED DELIVERIES into two named
    cells (instrumenting `deliver`, not polling state: polling would miss two
    back-to-back captures where the valid flag never drops). Value is never read.
  * Pass boundary -- a counter of feeds; every `pass_len`-th feed raises
    `out_wrap_pulse` (the role `addr_counter_v1.v`'s wrap plays in the RTL).
  * Feed side -- `freeze_out` level drives the SOURCE head's `freeze_in`;
    `freeze_in` (overflow) drives the section head's.
  * START PROMPT -- the rising edge of `safe_to_intervene` emits a start word
    into a gate cell. At power-on the sentinel is frozen and drained, i.e.
    already safe, so that same edge prompts the INITIAL programming.
  * COMPLETION -- the falling edge of the reprogrammer's `command_active_r`
    (its `status_active` output in the RTL) issues `host_unfreeze_pulse`,
    resuming the feed side. The word stream's own final word still halts the
    word chain through the trigger-mode cell, exactly as in #870.

REAL, HONEST SCOPE:
  * The pass counter, edge detectors, start-word emission and completion
    detection are HARNESS-LEVEL models of fixed connection logic (#263 policy:
    a bounded, deliberately non-portable unit at the chain boundary, NOT a
    uniform cell). No RTL for this glue exists; the sentinel itself does.
  * The start word is delivered with `grid.inject`, modelling the connection
    unit emitting a word onto a fabric cell's face.
  * The reconfigured unit is still a separate target, not a cell of the
    drained section -- the actual fold is still to do.
  * Sentinel error paths (underflow/overflow) are wired but not exercised.
  * VM only; the composition has not been run in RTL.
  * A program that stops short (no COMPLETE word) can never signal completion,
    so the feed side is never released: a total, SAFE stall -- the reprogrammed
    unit stays frozen and no data is touched -- but a stall (see tests).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from sentinel_bram_automaton_v1 import Sentinel  # noqa: E402


class SentinelConnectionPoint:
    def __init__(self, grid, *, feed_pos, collect_pos, source_pos, head_pos,
                 gate_pos, gate_word, program_active_pos, pass_len, chain_length):
        self.grid = grid
        self.sentinel = Sentinel(chain_length=chain_length)
        self.pass_len = pass_len
        self.gate_pos = gate_pos
        self.gate_word = gate_word
        self._source = grid.cells[source_pos]
        self._head = grid.cells[head_pos]
        self._reprogrammer = grid.cells[program_active_pos]

        self._feeds = 0
        self._collects = 0
        self._tap(feed_pos, "_feeds")
        self._tap(collect_pos, "_collects")

        self.tick_no = -1
        self.total_feeds = 0
        self.total_collects = 0
        self.events = []                 # (tick, kind, diff)
        self._prev_safe = False          # so power-on 'safe' is a rising edge
        self._prog_running = False
        self._prog_seen_active = False

        self._drive()
        self._maybe_prompt()             # power-on: frozen + drained == safe -> prompts the first programming

    # -- instrumentation ----------------------------------------------------
    def _tap(self, pos, counter):
        cell = self.grid.cells[pos]
        original = cell.deliver

        def tapped(arrivals, injected=None, **kw):
            result = original(arrivals, injected=injected, **kw)
            if result[0]:                # an ACCEPTED delivery; the value is never inspected
                setattr(self, counter, getattr(self, counter) + 1)
            return result
        cell.deliver = tapped

    # -- connection logic ---------------------------------------------------
    def _log(self, kind):
        self.events.append((self.tick_no, kind, self.sentinel.diff))

    def _drive(self):
        self._source.freeze_in = self.sentinel.freeze_out
        self._head.freeze_in = self.sentinel.freeze_in

    def _maybe_prompt(self):
        safe = self.sentinel.safe_to_intervene
        if safe and not self._prev_safe and not self._prog_running:
            self.grid.inject(self.gate_pos[0], self.gate_pos[1], self.gate_word)
            self._prog_running = True
            self._prog_seen_active = False
            self._log("prompt")
        self._prev_safe = safe

    def tick(self):
        self.tick_no += 1
        self._feeds = self._collects = 0
        self.grid.tick()

        feed, collect = self._feeds > 0, self._collects > 0
        if feed:
            self.total_feeds += 1
            self._log("feed")
        if collect:
            self.total_collects += 1
            self._log("collect")
        wrap = feed and self.total_feeds % self.pass_len == 0
        if wrap:
            self._log("wrap")

        unfreeze = False
        if self._prog_running:
            if self._reprogrammer.command_active_r:
                self._prog_seen_active = True
            elif self._prog_seen_active:
                unfreeze = True          # falling edge of the reprogrammer's active level
                self._prog_running = False
                self._log("complete")

        self.sentinel.step(feed, collect, wrap, unfreeze)
        self._drive()
        self._maybe_prompt()

    def run(self, ticks):
        for _ in range(ticks):
            self.tick()
