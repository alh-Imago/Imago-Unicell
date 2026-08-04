"""
unicell_card_v3.py — UniCell VM, Phase 7 (card-level scheduling model),
2026-08-02.

Ground truth: fpga/verilog/unicell_zone64_v3.v's inbound arbitration
(lines 195-222) and fpga/verilog/unicell_array64_v3.v's cpu_valid-vs-
or_valid priority (lines 360-389), both re-verified line-by-line while
building this, plus fpga/verilog/top_card_2zone_v3.v's confirmed shared-
host-bus wiring -- not reconstructed from the Phase 1-6 rebuild's own
assumptions.

This is NOT a new phase of the six-phase cell/array rebuild (that's
complete, see points.md #67). It's the next concrete step after it: a
card-level container proving out points.md #70's corrected scheduling
model empirically, rather than continuing to reason about it. Existing,
proven pieces (UniCellV3, UniCellArrayV3) are reused entirely unchanged
-- this file adds only the layer above them: multiple zones, real
cardinal arbitration between them, and one shared card-wide host/loader
channel.

TWO VERIFIED, MUTUALLY-EXCLUSIVE FACTS THIS MODEL ENCODES PRECISELY
(points.md #70's "dynamically-coupled zone pairs" framing, now made
concrete):

1. A zone's INBOUND side arbitrates priority-style, NOT wired-OR, between
   host injection and its four cardinal bridges (unicell_zone64_v3.v
   195-222): host injection wins outright if present that cycle; among
   the four bridges, whichever is checked LAST in declaration order wins
   if more than one is simultaneously valid (non-blocking-assignment
   last-write-wins) -- the others are SILENTLY DROPPED that cycle, not
   corrupted-via-OR. Genuinely different from the array's own internal
   wired-OR combine (points.md #32), which IS an OR.

2. A zone's inbound reception and its OWN internal cell-to-cell chaining
   are MUTUALLY EXCLUSIVE within one cycle (unicell_array64_v3.v 360-389):
   `if (cpu_valid) [external wins] else if (or_valid) [internal chaining
   proceeds]`. A zone that's receiving from outside this cycle cannot
   ALSO advance its own internal computation that same cycle -- and,
   since the array's own outbound path (out_*, which the zone wrapper
   reads to route across bridges) only ever fires from the SAME or_valid
   branch, a receiving zone cannot originate a NEW outbound event that
   cycle either. This is the precise mechanism behind "receiving blocks
   that zone's own computing," not an assumption.

Zone-to-zone delivery is modeled with one tick of latency (matches real
hardware's registered bridge stage) via per-zone pending-event queues,
resolved each tick in the order: external arbitration (if anything is
pending) always wins over that zone's own queued internal continuation,
exactly matching fact 2 above.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from unicell_array_v3 import UniCellArrayV3, FireResult

# Cardinal directions and their opposite, for neighbor lookups and
# multicast fan-out. Bit positions match routing_mask's low 4 bits
# (verified, unicell64_v3.v: bit0=N, bit1=S, bit2=E, bit3=W).
N, S, E, W = 0, 1, 2, 3
_DIR_BIT = {N: 0, S: 1, E: 2, W: 3}
_OPPOSITE = {N: S, S: N, E: W, W: E}


@dataclass
class ZoneState:
    """Per-zone bookkeeping for one card-level tick."""
    row: int
    col: int
    array: UniCellArrayV3
    # Queued for delivery -- either from a neighbor's cardinal-routed fire
    # (arrives one tick after the sender fired) or a host injection
    # scheduled for a specific tick. List because multiple sources could
    # target the same zone in the same tick; only one wins per fact 1.
    pending_external: List[Tuple[str, int, int]] = field(default_factory=list)
    # This zone's own queued continuation from a non-transit fire last
    # tick -- what would drive its own bus next, absent external traffic.
    pending_internal: Optional[Tuple[int, int]] = None
    # Per-tick outcome, recorded by Card.tick() for the measurement layer.
    last_tick_state: str = "idle"  # "receiving" | "computing" | "idle"


@dataclass
class TickStats:
    tick: int
    receiving: int
    computing: int
    idle: int
    total_zones: int

    @property
    def busy(self) -> int:
        return self.receiving + self.computing

    @property
    def achieved_fraction(self) -> float:
        return self.busy / self.total_zones if self.total_zones else 0.0


class UniCellCardV3:
    """
    A grid of zones (rows x cols), each a UniCellArrayV3, wired with real
    cardinal bridges between physically adjacent zones and one shared,
    card-wide host/loader channel (points.md #70's dynamically-coupled-
    zone-pairs model, made concrete and measurable).
    """

    def __init__(self, rows: int, cols: int, cells_per_zone: int = 25):
        self.rows = rows
        self.cols = cols
        self.zones: Dict[Tuple[int, int], ZoneState] = {}
        zone_id = 0
        for r in range(rows):
            for c in range(cols):
                arr = UniCellArrayV3(num_cells=cells_per_zone, cell_base=zone_id * cells_per_zone)
                self.zones[(r, c)] = ZoneState(row=r, col=c, array=arr)
                zone_id += 1
        self._host_queue: List[Tuple[int, Tuple[int, int], int, int]] = []
        # (tick_number, (row,col), addr, data) -- host injections scheduled
        # for a specific future tick, matching the one shared card-wide
        # channel (top_card_2zone_v3.v's confirmed wiring): only ONE host
        # injection can be scheduled per tick, card-wide, enforced in
        # schedule_host_injection().
        self.tick_count = 0
        self.history: List[TickStats] = []

    def neighbor(self, row: int, col: int, direction: int) -> Optional[Tuple[int, int]]:
        dr, dc = {N: (-1, 0), S: (1, 0), E: (0, 1), W: (0, -1)}[direction]
        pos = (row + dr, col + dc)
        return pos if pos in self.zones else None

    def schedule_host_injection(self, tick: int, row: int, col: int, addr: int, data: int) -> None:
        """Schedule a host-driven injection for a specific future tick.
        Only one is allowed per tick, card-wide -- matches the confirmed
        single shared cmd_bus/cpu_addr wiring (top_card_2zone_v3.v): the
        host channel is one resource for the whole card, not per-zone."""
        if any(t == tick for t, *_ in self._host_queue):
            raise ValueError(f"tick {tick} already has a scheduled host injection -- "
                              f"the host channel is ONE shared resource, card-wide "
                              f"(points.md #70), only one injection per tick is possible")
        self._host_queue.append((tick, (row, col), addr, data))

    def tick(self) -> TickStats:
        """Advance the whole card by exactly one cycle."""
        t = self.tick_count
        receiving = computing = idle = 0

        host_this_tick = next(((pos, addr, data) for tt, pos, addr, data in self._host_queue if tt == t), None)

        # Resolve, per zone, the winning event for THIS tick (fact 1:
        # host beats every bridge; among bridges, declaration-order N/S/E/W
        # last-valid-wins, others silently dropped).
        winners: Dict[Tuple[int, int], Optional[Tuple[str, int, int]]] = {}
        for pos, zone in self.zones.items():
            if host_this_tick is not None and host_this_tick[0] == pos:
                winners[pos] = ("host", host_this_tick[1], host_this_tick[2])
                continue
            winner = None
            for label, addr, data in zone.pending_external:
                winner = (label, addr, data)  # last-in-list wins, matches
                                               # last-write-wins semantics
            winners[pos] = winner
            zone.pending_external = []  # consumed this tick regardless of outcome

        # Apply each zone's outcome: external wins outright over internal
        # (fact 2) -- a receiving zone cannot also advance its own
        # computation, or originate a new outbound event, this same tick.
        next_pending_internal: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {}
        cross_zone_deliveries: List[Tuple[Tuple[int, int], int, int]] = []

        for pos, zone in self.zones.items():
            winner = winners[pos]
            if winner is not None:
                _, addr, data = winner
                result = zone.array.deliver(addr, data)
                zone.last_tick_state = "receiving"
                receiving += 1
            elif zone.pending_internal is not None:
                addr, data = zone.pending_internal
                result = zone.array.deliver(addr, data)
                zone.last_tick_state = "computing"
                computing += 1
            else:
                result = None
                zone.last_tick_state = "idle"
                idle += 1

            zone.pending_internal = None  # consumed regardless

            if result is not None and result.valid:
                if result.transit:
                    # Cardinal-routed: fan out to every neighbor whose
                    # direction bit is set (routing_mask multicast,
                    # verified points.md #17 rule 2 -- one fire, several
                    # directions at once). One tick of latency, matching
                    # the real registered bridge stage.
                    for direction, bit in _DIR_BIT.items():
                        if (result.routing >> bit) & 1:
                            nb = self.neighbor(pos[0], pos[1], direction)
                            if nb is not None:
                                cross_zone_deliveries.append((nb, result.addr, result.data))
                            # else: routes off the physical edge of the
                            # card -- nowhere to go, silently has no effect,
                            # matching real hardware (an unwired bridge
                            # port simply has nothing on the other end).
                else:
                    # Non-transit: stays local, continues chaining within
                    # THIS zone next tick (matches or_valid's own
                    # bus_addr<=or_addr feedback).
                    next_pending_internal[pos] = (result.addr, result.data)

        for pos, zone in self.zones.items():
            zone.pending_internal = next_pending_internal.get(pos)

        for pos, addr, data in cross_zone_deliveries:
            self.zones[pos].pending_external.append(("bridge", addr, data))

        stats = TickStats(tick=t, receiving=receiving, computing=computing,
                           idle=idle, total_zones=len(self.zones))
        self.history.append(stats)
        self.tick_count += 1
        return stats

    def run(self, num_ticks: int) -> List[TickStats]:
        return [self.tick() for _ in range(num_ticks)]

    def achieved_vs_ceiling(self) -> float:
        """Average fraction of zones busy (receiving or computing) per
        tick across the whole run so far -- the actual measured
        parallelism, out of a ceiling of 1.0 (every zone busy every tick)."""
        if not self.history:
            return 0.0
        return sum(s.achieved_fraction for s in self.history) / len(self.history)

    def __repr__(self) -> str:
        return f"UniCellCardV3({self.rows}x{self.cols} zones, tick={self.tick_count})"
