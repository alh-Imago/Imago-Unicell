"""
unicell_array_v3.py — UniCell VM, Phase 6 (FINAL) of the v3.1 rebuild
(2026-07-31).

Ground truth: fpga/verilog/unicell_array64_v3.v, verified line-by-line
against the logic (not memory of the earlier session's own RTL work).

This is the phase where everything built in Phases 1-5 (unicell_v3.py)
comes together into a multi-cell array. Two genuinely array-level
mechanisms are modeled here, both verified precisely because they turned
out to be subtly different from each other -- easy to get wrong by
assuming they work the same way:

1. WIRED-OR DATA BUS (deliver()) -- unicell_array64_v3.v lines 312-335.
   When multiple cells fire in the same event, their DATA values OR
   together regardless of whether their addresses match, but the WINNING
   address/routing/transit come from whichever cell fired with the
   HIGHEST array index (the loop runs low-to-high, last write wins). This
   is the real, slightly-naive hardware behavior, not "fixed" to be
   smarter: firing several cells to the SAME address is the deliberate
   composition pattern (points.md #32's wired-OR fan-in, #60's masked
   distributed command assembly); firing to DIFFERENT addresses
   simultaneously is a genuine, documented collision hazard, reproduced
   faithfully here.

2. COMMAND-EMIT ARBITER (emit_arbiter()) -- lines 181-199. Genuinely
   DIFFERENT from the data bus: pure LOWEST-INDEX PRIORITY, no OR-
   combining at all. The RTL's own comment is explicit: "any simultaneous
   emitters are dropped (no queue/fairness yet)". Verified by reading the
   loop direction (high index to low, so the LOWEST index's assignment is
   the one left standing) rather than assumed to mirror the data bus.

3. TARGETED EMISSION DELIVERY (deliver_emitted_command()) -- lines
   201-260 (points.md #66). An emitted command only reaches the cell(s)
   whose input_address matches the emission's target -- every OTHER cell
   never even sees it (cell_cmd_valid is gated FALSE for them at the array
   level, before any cell's own opcode decode runs). This is what closes
   the #65 hole: a command-emit cell's payload accidentally matching a
   real, dangerous opcode can no longer disarm the whole array.

Emitted commands are structurally limited to ONE word (cmd_emit_buf_data
carries only output_address, not a second config payload -- verified,
line 1435) -- topology presets are the only opcodes self-contained enough
to be meaningfully emitted this way, which is exactly what #65/#66
exercised and is reflected in UniCellV3.apply_raw_command()'s scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from unicell_v3 import UniCellV3

_MASK32 = 0xFFFFFFFF


@dataclass
class FireResult:
    """Result of one deliver() call -- mirrors the array's own or_valid/
    or_addr/or_data/or_routing/or_transit registers."""
    valid:   bool
    addr:    Optional[int]
    data:    int
    routing: int
    transit: bool


class UniCellArrayV3:
    """A flat array of UniCellV3 cells sharing one data bus and one command
    bus, matching unicell_array64_v3.v's actual wiring."""

    def __init__(self, num_cells: int, cell_base: int = 0):
        self.cell_base = cell_base
        self.cells: List[UniCellV3] = [
            UniCellV3(CELL_ID=cell_base + i) for i in range(num_cells)
        ]

    def get_cell(self, cell_id: int) -> UniCellV3:
        return self.cells[cell_id - self.cell_base]

    # ── Data bus: wired-OR combine ──────────────────────────────────────────

    def deliver(self, bus_addr: int, bus_data: int) -> FireResult:
        """Deliver ONE data-bus event to every cell simultaneously (matches
        cmd_bus/bus_addr/bus_data being wired to every cell instance
        identically in the generate block). Combines results via the EXACT
        wired-OR loop the RTL uses (lines 319-335): data ORs across every
        firing cell regardless of address; addr/routing/transit come from
        whichever cell fired with the HIGHEST index (last write in the
        low-to-high loop wins) -- NOT grouped by matching address. Firing
        cells to the SAME address (the deliberate composition pattern) and
        firing cells to DIFFERENT addresses (a genuine collision) are both
        reproduced exactly as the real hardware would produce them."""
        or_addr: Optional[int] = None
        or_data = 0
        or_routing = 0
        or_transit = False
        or_valid = False
        for cell in self.cells:
            r = cell.receive(bus_addr, bus_data)
            if r is not None:
                or_addr = cell.output_address
                or_data |= r
                or_routing = cell.last_fire_routing & 0xF  # low 4 bits -- physical
                                                            # N/S/E/W bridges today
                or_transit = cell.last_fire_transit
                or_valid = True
        return FireResult(valid=or_valid, addr=or_addr, data=or_data & _MASK32,
                           routing=or_routing, transit=or_transit)

    # ── Command-emit arbiter ────────────────────────────────────────────────

    def emit_arbiter(self) -> Optional[Tuple[int, int]]:
        """Select the emission from the LOWEST-index cell whose
        last_emit_valid is set (matches lines 190-198's high-to-low loop,
        which leaves the LOWEST index's assignment standing). Genuinely
        different from deliver()'s wired-OR: no combining, pure priority --
        any other cell that ALSO emitted this same event is silently
        dropped, exactly as the RTL's own comment states. Returns
        (bus_word, target_addr), or None if no cell emitted."""
        for cell in self.cells:  # low to high; first match is the lowest index
            if cell.last_emit_valid:
                return (cell.last_emit_bus, cell.last_emit_target)
        return None

    def deliver_emitted_command(self, emission: Optional[Tuple[int, int]]) -> List[int]:
        """Deliver an emitted command ONLY to the cell(s) whose
        input_address matches the emission's target -- points.md #66's
        fix, verified against lines 201-260: cmd_is_runtime_targeted=
        sel_emit_valid gates cell_cmd_valid FALSE for every non-matching
        cell at the array level, before any cell's own opcode decode even
        runs. Every other cell doesn't ignore the command -- it never sees
        it at all. Returns the CELL_IDs that actually applied it (a cell
        can match the address and still reject via its own auth_ok, same
        as any host-issued command would)."""
        if emission is None:
            return []
        bus_word, target_addr = emission
        applied = []
        for cell in self.cells:
            if cell.input_address == target_addr:
                if cell.apply_raw_command(bus_word):
                    applied.append(cell.CELL_ID)
        return applied

    def __repr__(self) -> str:
        return f"UniCellArrayV3(cells={len(self.cells)}, base={self.cell_base})"
