"""
unicell_automaton_v1.py — pure cellular-automaton cell model (2026-08-02).

A genuinely different architecture from unicell_v3.py, not a variant of
it. Alan's proposal, worked through directly in this session: if wiring
only ever connects a cell to its immediate physical neighbor (whether
that's the next cell within what used to be a zone, or across what used
to be a cardinal boundary), arbitrary addressing becomes meaningless --
there's no shared bus left to address INTO. input_address/output_address
latches and every opcode that manipulates them (SET_INPUT_ADDR,
SET_OUTPUT_ADDR, SET_TARGET/config_match's whole targeting apparatus)
become structurally redundant, not just unused -- there's nothing left
for them to select between. The model collapses to what the project
looked like at its earliest roots: pure cell automata, plus everything
learned this week about routing and cardinality layered on top.

THE HYPOTHESIS THIS FILE EXISTS TO TEST: this week's dominant finding
(#69/#70/#71) was that a zone's shared local bus caps it to one burst per
cycle, regardless of cell count or shape -- that's WHY the 32-bit adder
needed rebuilding around a small reused unit rather than 482 dedicated
cells (#72/#73). If there is no shared bus at all -- every cell has its
own dedicated point-to-point link to each neighbor -- there is nothing
left to collide on. Every cell could, in principle, fire every single
cycle, independent of every other cell's activity. This file does not
assume that's true; it's built to measure it.

DESIGN CHOICES MADE HERE, STATED EXPLICITLY (not left as buried
assumptions, since getting this wrong would misrepresent what's being
tested):

- ROUTING_MASK keeps its existing meaning exactly: which of a cell's up
  to 4 neighbor directions (N/S/E/W) this fire's result is sent to.
  Multicast-capable, same as always (points.md #17 rule 2) -- one fire
  can reach multiple neighbors at once.

- CARDINAL_EDGE is reinterpreted, out of necessity: there is no "local
  bus" left for it to distinguish from anymore. The natural, minimal
  extension of its ORIGINAL meaning (#32/#58's transit cells: a fire
  that crosses a boundary without injecting into the receiving cluster's
  own computation) is applied per INCOMING direction instead of per
  outgoing one: for each direction data can arrive FROM, cardinal_edge
  decides whether this cell CONSUMES it (normal two-arrival
  participation) or RELAYS it (pure pass-through, using this cell's OWN
  routing_mask to forward it onward, without ever becoming this cell's
  own a_data/computation input at all). This is the same "conduit vs.
  participant" distinction #58 already established, just applied at
  every hop instead of only at what used to be a zone boundary.

- No input_address/output_address, no auth, no config_match, no
  SET_TARGET. A cell's identity is its fixed grid position. Getting data
  INTO the fabric happens via direct injection at designated boundary
  cells (the natural way real systolic arrays/cellular automata are fed)
  -- there's no addressed "host bus" to inject through generally,
  because there's no addressing at all.

Gate computation itself is UNCHANGED from unicell_v3.py -- same
NOR-decomposition, same 12 topology codes, same two-arrival mechanics
for CONSUMING cells. Reused directly, not reimplemented, since nothing
about how a gate computes changed, only how cells reach each other.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from unicell_v3 import compute_gate, TOPO_PASS_A

_MASK32 = 0xFFFFFFFF
N, S, E, W = 0, 1, 2, 3
_DIR_BIT = {N: 0, S: 1, E: 2, W: 3}
_OPPOSITE = {N: S, S: N, E: W, W: E}


@dataclass
class CACell:
    """One cell in the pure automaton model. No address fields exist at
    all -- position IS identity, fixed at construction, never
    reconfigured.

    READY / OUTPUT-BUFFER (points.md #77): `out_buffer` is genuinely
    separate from `data_reg` -- data_reg stays the cell's own working
    register, overwritten every fire exactly as before; out_buffer holds
    specifically the value being OFFERED to whatever consumes it, only
    updated when `ready` is True (meaning the previous offering was
    already confirmed read). `ready` gates firing itself: a cell whose
    own output hasn't been consumed cannot fire, which means it cannot
    accept a new arrival either (bus_hit-equivalent gating applies to
    both) -- this is what makes the backward stall cascade automatic
    rather than a separately-designed mechanism (points.md #77)."""
    row: int
    col: int
    topology: int = TOPO_PASS_A
    start_flag: bool = False
    routing_mask: int = 0        # which neighbor direction(s) THIS cell's fire goes to
    cardinal_edge: int = 0       # per INCOMING direction: 1=relay (don't consume), 0=consume
    invert_out: bool = False
    latch_in: bool = False
    loop_back: bool = False
    one_shot: bool = False

    a_data: int = 0
    a_arrived: bool = False
    one_shot_fired: bool = False
    data_reg: int = 0

    out_buffer: Optional[int] = None  # the offered output -- separate from data_reg
    ready: bool = True                 # True = out_buffer empty/consumed, may fire again

    def fire_from(self, from_direction: Optional[int], value: int):
        """Deliver one value arriving from a given direction (None for a
        direct external injection at a boundary cell). Returns a tuple
        (accepted, forward) where accepted is False if this cell's own
        ready flag is False (out_buffer still holding an unconfirmed
        value) -- meaning the event was NOT consumed at all and must be
        retried later, not dropped. forward is (routing_mask, value) to
        deliver onward if this cell just fired, or None otherwise.

        RELAY bypasses ready entirely -- a pure conduit holds no state of
        its own, so there is nothing for it to be "not ready" about.
        """
        if from_direction is not None and ((self.cardinal_edge >> _DIR_BIT[from_direction]) & 1):
            return (True, (self.routing_mask, value & _MASK32))  # pure relay, unchanged value

        if not self.ready:
            return (False, None)  # cannot accept anything while my own output is unconsumed

        if not self.start_flag:
            return (True, None)  # accepted (nothing to retry) but not armed -- absorbed silently

        if not self.a_arrived:
            self.a_data = value & _MASK32
            self.a_arrived = True
            return (True, None)

        if self.one_shot and self.one_shot_fired:
            return (True, None)

        a = self.a_data
        b = value & _MASK32
        computed = compute_gate(self.topology, a, b)
        self.data_reg = computed

        if self.latch_in:
            self.a_arrived = True
            self.a_data = b
        else:
            self.a_arrived = False

        if self.loop_back:
            self.a_data = computed

        if self.one_shot:
            self.one_shot_fired = True
            self.start_flag = False

        fired = (~computed) & _MASK32 if self.invert_out else computed
        self.out_buffer = fired  # offered output, separate from data_reg
        self.ready = False       # occupied until confirmed read (by a downstream
                                 # neighbor's successful acceptance, or an explicit
                                 # confirm_read() for a chain-end cell)
        return (True, (self.routing_mask, fired))


class CAGrid:
    """A grid of CACells wired ONLY to their fixed physical neighbors --
    no addressing, no shared bus, no bridges-to-elsewhere. Each cell's
    neighbor set is determined entirely by grid position, fixed at
    construction."""

    def __init__(self, rows: int, cols: int):
        self.rows, self.cols = rows, cols
        self.cells: Dict[Tuple[int, int], CACell] = {
            (r, c): CACell(row=r, col=c) for r in range(rows) for c in range(cols)
        }
        # Each pending entry: (origin_pos_or_None, from_direction, value).
        # origin_pos is who PRODUCED this event -- needed so a successful
        # delivery can confirm THAT cell's ready flag (points.md #77).
        # None origin = a direct external injection, nothing to confirm.
        self._pending: Dict[Tuple[int, int], List[Tuple[Optional[Tuple[int, int]], Optional[int], int]]] = {}
        self.tick_count = 0

    def neighbor_pos(self, row: int, col: int, direction: int) -> Optional[Tuple[int, int]]:
        dr, dc = {N: (-1, 0), S: (1, 0), E: (0, 1), W: (0, -1)}[direction]
        pos = (row + dr, col + dc)
        return pos if pos in self.cells else None

    def inject(self, row: int, col: int, value: int) -> None:
        """External injection at a boundary cell -- the only way data
        enters the fabric at all, since there's no addressed host bus."""
        self._pending.setdefault((row, col), []).append((None, None, value))

    def confirm_read(self, row: int, col: int) -> None:
        """Explicit external confirmation that a cell's offered output has
        been consumed -- the chain-end case (points.md #77): the "memory-
        reading top command layer" reads out_buffer and acknowledges it,
        which is what allows this cell (and, via the cascade, everything
        feeding it) to become ready for new data again."""
        cell = self.cells[(row, col)]
        cell.ready = True

    def tick(self) -> Dict[Tuple[int, int], bool]:
        """Advance every cell that has a pending delivery by one event.
        Rejected deliveries (target not ready) are RE-QUEUED for the next
        tick, not dropped -- this is what makes the backward stall real
        rather than silent data loss. Returns which positions were
        actively processed (accepted or rejected-and-retried) this tick."""
        active: Dict[Tuple[int, int], bool] = {}
        outgoing: List[Tuple[Tuple[int, int], Optional[Tuple[int, int]], Optional[int], int]] = []
        retry: Dict[Tuple[int, int], List[Tuple[Optional[Tuple[int, int]], Optional[int], int]]] = {}

        current = self._pending
        self._pending = {}

        for pos, events in current.items():
            cell = self.cells[pos]
            for origin, from_dir, value in events:
                accepted, result = cell.fire_from(from_dir, value)
                active[pos] = True
                if not accepted:
                    retry.setdefault(pos, []).append((origin, from_dir, value))
                    continue
                if origin is not None:
                    self.cells[origin].ready = True  # confirmed: the sender's offering was consumed
                if result is not None:
                    mask, out_value = result
                    for direction, bit in _DIR_BIT.items():
                        if (mask >> bit) & 1:
                            nb = self.neighbor_pos(pos[0], pos[1], direction)
                            if nb is not None:
                                outgoing.append((nb, pos, _OPPOSITE[direction], out_value))

        for pos, events in retry.items():
            self._pending.setdefault(pos, []).extend(events)

        for nb, origin, arrive_from, value in outgoing:
            self._pending.setdefault(nb, []).append((origin, arrive_from, value))

        self.tick_count += 1
        return active

    def run_to_quiescence(self, max_ticks: int = 10000) -> int:
        """Run until nothing is pending anywhere. Returns ticks used."""
        ticks = 0
        while self._pending and ticks < max_ticks:
            self.tick()
            ticks += 1
        if self._pending:
            raise TimeoutError(f"did not quiesce within {max_ticks} ticks")
        return ticks
