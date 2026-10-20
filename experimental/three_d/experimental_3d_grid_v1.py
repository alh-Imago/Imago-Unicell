"""
experimental_3d_grid_v1.py — a deliberately SEPARATE, VM-only thought
experiment: what does the topology-as-computation idea look like with
SIX cardinal neighbors (N/S/E/W/U/D) instead of four?

REAL, HONEST SCOPE, stated up front and not to be forgotten later: this
is NOT an extension of `unicell_super_automaton_v1.py`, NOT grounded in
any real RTL, and makes NO claim about `unicell_super_v1/v2.v` ever
growing a 5th/6th physical port. Checked directly before writing a line
of this file: `unicell_super_v1.v`'s own real port list is strictly
N/S/E/W (`data_in_n/s/e/w`, `fire_n/s/e/w`, `ack_in/out_n/s/e/w`,
`ready_in_n/s/e/w`) -- no up/down anywhere. Nano's own `routing_mask`/
`cardinal_edge` fields ARE 6 bits wide in the real RTL, but that's
reserved bit-width headroom, not an implemented 6th direction -- only
the low 4 bits mean anything in real silicon today.

WHY THIS EXISTS: Alan's own real architectural question -- does a
6-cardinal fabric unlock genuinely NEW composable shapes, or just
faster/bigger versions of what 4-cardinal already does? -- and a real,
concrete motivating case already on the roadmap (FlowTrix's own D2Q9
lattice Boltzmann demo; a true D3Q19 would be the first genuine reason
to want vertical neighbors, not novelty for its own sake). Building
real 3D RTL first would be a large, uncharacterized undertaking (every
core's own field budget grows, branch_cell_v1.v is already at 41 of 42
bits at 4-way routing alone) -- so this explores the SHAPE question
cheaply in software first, exactly the same "sim before silicon"
discipline this project already applies to every real core.

THE TOY CELL MODEL, deliberately generic (NOT a stand-in for any real
core): two modes only.
  - "relay": stateless, whatever arrives on ANY listened direction is
    immediately re-offered on `downstream_mask` next tick. No capture
    logic, no config beyond which directions to listen on and which to
    offer to -- the simplest possible thing that can prove a SHAPE
    works, deliberately not entangled with any real core's own
    semantics.
  - "accumulate": a loose, 6-directional cousin of `accumulator_cell_v1
    .v`'s own real static-mode behavior (inc_mask/dec_mask/step_amount/
    running total), reused here ONLY because it's a familiar, already-
    understood shape for the "chaos" stress run below -- not a claim
    that the real accumulator core has 6 real directions.

Direction convention: N/S move along the row axis, E/W along the
column axis, U/D along a THIRD axis this project's real hardware has
never had -- called `layer` here throughout, deliberately not "z", to
avoid any accidental suggestion of a real spatial/physical meaning
beyond "a second stacked plane of cells."
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

N, S, E, W, U, D = range(6)
_DIRS = (N, S, E, W, U, D)
_OPPOSITE = {N: S, S: N, E: W, W: E, U: D, D: U}
_DELTA = {N: (-1, 0, 0), S: (1, 0, 0), E: (0, 1, 0), W: (0, -1, 0),
          U: (0, 0, 1), D: (0, 0, -1)}
_MASK6 = 0b111111
_MASK32 = 0xFFFFFFFF


def pack_dirmask(dirs) -> int:
    m = 0
    for d in dirs:
        m |= 1 << d
    return m


def _wrap_signed32(v: int) -> int:
    v &= _MASK32
    return v - (1 << 32) if v & 0x80000000 else v


@dataclass
class ToyCell3D:
    """One cell. `mode='relay'` or `mode='accumulate'` -- see this
    file's own header for what each really means (and doesn't)."""
    row: int
    col: int
    layer: int
    mode: str = "relay"

    # ── relay ──
    listen_mask: int = 0
    relay_value: int = 0
    relay_valid: bool = False

    # ── accumulate ──
    inc_mask: int = 0
    dec_mask: int = 0
    step_amount: int = 1
    total: int = 0
    out_buffer: int = 0

    downstream_mask: int = 0
    pending_ack: int = 0

    def deliver(self, arrivals: Dict[int, int]) -> bool:
        """Returns accepted (True/False, retried next tick if False)."""
        if not arrivals:
            return True
        if self.mode == "relay":
            matched = [d for d in arrivals if (self.listen_mask >> d) & 1]
            if not matched:
                return True
            if self.relay_valid:
                return False   # a prior relayed value hasn't drained yet
            self.relay_value = arrivals[matched[0]] & _MASK32
            self.relay_valid = True
            return True
        # accumulate
        capture_inc = any((self.inc_mask >> d) & 1 for d in arrivals)
        capture_dec = any((self.dec_mask >> d) & 1 for d in arrivals)
        step = self.step_amount
        delta = step if (capture_inc and not capture_dec) else -step if (capture_dec and not capture_inc) else 0
        if capture_inc or capture_dec:
            self.total = _wrap_signed32(self.total + delta)
        return True

    def offer_state(self) -> Tuple[int, bool, int]:
        if self.mode == "relay":
            return (self.relay_value, self.relay_valid, self.downstream_mask)
        self.out_buffer = self.total & _MASK32
        return (self.out_buffer, True, self.downstream_mask)

    def is_continuously_live(self) -> bool:
        return self.mode == "accumulate"

    def clear_valid_on_drain(self) -> None:
        if self.mode == "relay":
            self.relay_valid = False


class Grid3D:
    """A grid of `ToyCell3D`s wired to fixed physical neighbors across
    THREE axes -- same "no addressing, no shared bus" model as
    `CAGrid`/`SuperGrid`, generalized here to six neighbor directions
    instead of four. Same multi-pass tick shape as `SuperGrid.tick()`
    (event-driven delivery, drain detection, a generic offer pass for
    continuously-live cells) -- deliberately mirrored, not reinvented,
    even though this is a toy.
    """

    def __init__(self):
        self.cells: Dict[Tuple[int, int, int], ToyCell3D] = {}
        self._pending: Dict[Tuple[int, int, int], List[Tuple[Optional[Tuple], Optional[int], int]]] = {}
        self.tick_count = 0

    def place(self, cell: ToyCell3D) -> None:
        self.cells[(cell.row, cell.col, cell.layer)] = cell

    def neighbor_pos(self, pos: Tuple[int, int, int], direction: int) -> Optional[Tuple[int, int, int]]:
        dr, dc, dl = _DELTA[direction]
        nb = (pos[0] + dr, pos[1] + dc, pos[2] + dl)
        return nb if nb in self.cells else None

    def inject(self, pos: Tuple[int, int, int], value: int) -> None:
        self._pending.setdefault(pos, []).append((None, None, value))

    def tick(self) -> Dict[Tuple[int, int, int], bool]:
        active: Dict[Tuple[int, int, int], bool] = {}
        outgoing: List[Tuple[Tuple, Tuple, int, int]] = []
        retry: Dict[Tuple, List] = {}

        pre_tick_pending = {pos: c.pending_ack for pos, c in self.cells.items()}

        current = self._pending
        self._pending = {}

        for pos, events in current.items():
            cell = self.cells[pos]
            active[pos] = True
            by_dir: Dict[int, Tuple[Optional[Tuple], int]] = {}
            injected_val = None
            for origin, from_dir, value in events:
                if from_dir is None:
                    injected_val = (injected_val or 0) | (value & _MASK32)
                else:
                    by_dir[from_dir] = (origin, value & _MASK32)
            real_dirs = {d: v for d, (_o, v) in by_dir.items()}
            if injected_val is not None:
                # a toy injected value listens on whatever's configured,
                # matching direction N by convention for simplicity
                real_dirs.setdefault(N, injected_val)
            accepted = cell.deliver(real_dirs)
            if not accepted:
                for d, (origin, value) in by_dir.items():
                    retry.setdefault(pos, []).append((origin, d, value))
                continue
            for d, (origin, _v) in by_dir.items():
                if origin is not None:
                    self.cells[origin].pending_ack &= ~(1 << _OPPOSITE[d]) & _MASK6

        for pos, events in retry.items():
            self._pending.setdefault(pos, []).extend(events)

        for pos, cell in self.cells.items():
            if cell.is_continuously_live():
                continue
            was = pre_tick_pending.get(pos, 0)
            if was != 0 and cell.pending_ack == 0:
                cell.clear_valid_on_drain()
                active[pos] = True

        for pos, cell in self.cells.items():
            if cell.pending_ack != 0:
                continue
            value, valid, downstream = cell.offer_state()
            if not valid or downstream == 0:
                continue
            cell.pending_ack = downstream & _MASK6
            active[pos] = True
            for direction in _DIRS:
                if (downstream >> direction) & 1:
                    nb = self.neighbor_pos(pos, direction)
                    if nb is not None:
                        outgoing.append((nb, pos, direction, value))

        for nb, origin, out_dir, value in outgoing:
            self._pending.setdefault(nb, []).append((origin, _OPPOSITE[out_dir], value))

        self.tick_count += 1
        return active

    def run(self, max_ticks: int = 500) -> int:
        ticks = 0
        while ticks < max_ticks:
            self.tick()
            ticks += 1
            if not self._pending:
                return ticks
        return ticks
