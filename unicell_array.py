"""
unicell_array.py

Architecture Alignment + ECC (Engineering Addendum v0.1 §2).

Changes from baseline:
  - BusSegment model with lane_count and bridge_latency
  - Per-tick emission enforcement per segment (BusConflictError)
  - Storage mode support (cells re-emit without bus circulation)
  - ECC: bus carries (value, ecc_check) pairs; delivery verifies and corrects
  - enable_ecc(addresses) / disable_ecc(addresses) for region-level ECC control
"""
from typing import Optional
from unicell import UniCell, FUNCTION_LOAD_PATTERN, ECCError

# ── reserved addresses ───────────────────────────────────────────────────────

ADDR_RESERVED_ZERO     = 0x00000000
ADDR_RESERVED_SENTINEL = 0xFFFFFFFF


# ── BusSegment ───────────────────────────────────────────────────────────────

class BusSegment:
    """
    One bus segment (Bandwidth & Emission Control Addendum v0.1).

    lane_count:     max emission events per clock cycle on this segment.
    bridge_latency: additional cycles when a signal crosses into this segment
                    from another segment (used by compiler depth balancing).
    """

    def __init__(self, segment_id: int, lane_count: int = 256,
                 bridge_latency: int = 0):
        self.segment_id     = segment_id
        self.lane_count     = lane_count
        self.bridge_latency = bridge_latency

    def __repr__(self):
        return (f"BusSegment(id={self.segment_id} "
                f"lanes={self.lane_count} "
                f"bridge_lat={self.bridge_latency})")


class BusConflictError(RuntimeError):
    """Raised when a segment's emission count exceeds its lane capacity."""
    pass


# ── UniCellArray ─────────────────────────────────────────────────────────────

class UniCellArray:
    """
    A flat array of UniCells sharing a segmented bus.

    ECC model:
      The bus carries (value, ecc_check) pairs internally.
      self.bus maps address -> (value, ecc_check).
      read_bus() returns only the value for external callers.
      ECC is per-cell: ecc_enabled must be set True on each cell
      (via enable_ecc()) for protection to be active.
    """

    MAX_ADDRESS = 0xFFFFFFFE

    def __init__(self, cell_count: int = 1_000_000):
        self.cells: dict[int, UniCell] = {}
        # bus: address -> (value, ecc_check)  [ecc_check=0 if ECC not used]
        self.bus:   dict[int, tuple]   = {}
        self.defect_map: set[int]      = set()
        self._cell_count   = cell_count
        self._next_address = 1

        # Bus segment registry
        self._segments: dict[int, BusSegment] = {
            0: BusSegment(segment_id=0, lane_count=256, bridge_latency=0)
        }
        self._cell_segment: dict[int, int] = {}
        self.enforce_emission_limits: bool = True

        # Armed-cell index — tracks cells with start_flag=True.
        # tick() iterates only this set instead of all cells, skipping
        # frozen and already-fired cells entirely.
        # Invariant: _armed == {addr for addr,c in cells.items() if c.start_flag}
        self._armed: set[int] = set()
        # Extended address table: cell_addr → 64-bit forwarding address
        # Populated when an addr_latch cell fires.
        # Consumed by CommandInterface for cross-stack/cross-card routing.
        self._extended_addresses: dict[int, int] = {}
        self.trace_buffer: list = []
        self.max_trace_entries: int = 10_000
        self._tick_count: int = 0
        self._breakpoint_halt: bool = False

    # ── ECC control ──────────────────────────────────────────────────────────

    def enable_ecc(self, addresses: Optional[list[int]] = None) -> int:
        """
        Enable ECC on cells at the given addresses (or all cells if None).
        Returns count of cells enabled.
        """
        targets = addresses if addresses is not None else list(self.cells.keys())
        count = 0
        for addr in targets:
            if addr in self.cells:
                self.cells[addr].ecc_enabled = True
                count += 1
        return count

    def disable_ecc(self, addresses: Optional[list[int]] = None) -> int:
        """Disable ECC on cells at the given addresses (or all if None)."""
        targets = addresses if addresses is not None else list(self.cells.keys())
        count = 0
        for addr in targets:
            if addr in self.cells:
                self.cells[addr].ecc_enabled = False
                count += 1
        return count

    def ecc_status(self) -> dict:
        """Return aggregate ECC statistics across all cells."""
        enabled   = sum(1 for c in self.cells.values() if c.ecc_enabled)
        corrections = sum(c.ecc_corrections    for c in self.cells.values())
        doubles     = sum(c.ecc_double_errors  for c in self.cells.values())
        return {
            "ecc_enabled_cells":  enabled,
            "total_corrections":  corrections,
            "total_double_errors": doubles,
        }

    # ── segment management ───────────────────────────────────────────────────

    def add_segment(self, segment_id: int, lane_count: int = 256,
                    bridge_latency: int = 0) -> BusSegment:
        seg = BusSegment(segment_id, lane_count, bridge_latency)
        self._segments[segment_id] = seg
        return seg

    def assign_segment(self, cell_address: int, segment_id: int) -> bool:
        if cell_address not in self.cells: return False
        if segment_id not in self._segments: return False
        self._cell_segment[cell_address] = segment_id
        return True

    def get_segment(self, cell_address: int) -> BusSegment:
        seg_id = self._cell_segment.get(cell_address, 0)
        return self._segments.get(seg_id, self._segments[0])

    def segment_info(self) -> dict:
        return {
            sid: {
                "lane_count":     seg.lane_count,
                "bridge_latency": seg.bridge_latency,
                "cells_assigned": sum(
                    1 for s in self._cell_segment.values() if s == sid),
            }
            for sid, seg in self._segments.items()
        }

    # ── defect map ───────────────────────────────────────────────────────────

    def load_defect_map(self, addresses: list[int]) -> int:
        for addr in addresses:
            if addr not in (ADDR_RESERVED_ZERO, ADDR_RESERVED_SENTINEL):
                self.defect_map.add(addr)
        return len(self.defect_map)

    # ── cell allocation ──────────────────────────────────────────────────────

    def allocate_cell(self) -> UniCell:
        while (
            self._next_address in self.defect_map
            or self._next_address in (ADDR_RESERVED_ZERO, ADDR_RESERVED_SENTINEL)
        ):
            self._next_address += 1
        if self._next_address > self.MAX_ADDRESS:
            raise RuntimeError("UniCellArray is full")
        cell = UniCell(self._next_address)
        self.cells[self._next_address] = cell
        self._cell_segment[self._next_address] = 0
        self._next_address += 1
        return cell

    # ── config write ─────────────────────────────────────────────────────────

    def write_config(self, target_address: int, packet: list[int],
                     storage_mode: bool = False) -> bool:
        """
        Write a config packet to a cell.

        Standard 4-field packet: [FUNCTION_LOAD_PATTERN, gs, in_addr, out_addr]
        SELECT 5-field packet:   [FUNCTION_LOAD_PATTERN, gs, in_addr, out_addr, out_addr_alt]

        After delivering all fields, config mode is forcibly closed. This
        handles the case where a SELECT cell receives only 4 fields (no alt
        address) — without this, it would remain stuck in config mode
        waiting for a 5th field that will never arrive.
        storage_mode sets the cell's latch flag directly (not via the bus).
        """
        if target_address in self.defect_map: return False
        if target_address not in self.cells: return False
        cell = self.cells[target_address]
        for value in packet:
            cell.receive(value)   # config writes carry ecc_check=0
        # Force-close config mode after packet delivery.
        if cell._config_mode:
            cell._config_mode = False
        if storage_mode:
            cell.storage_mode = True
        return True

    # ── start flag ───────────────────────────────────────────────────────────


    def verify_armed_invariant(self) -> bool:
        """
        Verify the _armed set matches start_flag on all cells.

        In silicon, start_flag is a physical line on each cell.
        The VM uses _armed as an optimisation to avoid iterating all cells.
        They must always be in sync -- if they diverge the VM produces
        different results from silicon.

        Returns True if invariant holds. Call from tests or debug sessions.
        """
        actual_armed = {addr for addr, c in self.cells.items() if c.start_flag}
        return self._armed == actual_armed

    def check_armed_invariant(self) -> dict:
        """Return sync status with details for debugging."""
        actual_armed = {addr for addr, c in self.cells.items() if c.start_flag}
        missing = actual_armed - self._armed    # start_flag=True but not in set
        extra   = self._armed - actual_armed    # in set but start_flag=False
        return {
            "in_sync":  not missing and not extra,
            "missing":  [hex(a) for a in sorted(missing)],
            "extra":    [hex(a) for a in sorted(extra)],
            "armed_count": len(self._armed),
            "actual_count": len(actual_armed),
        }

    def assert_start_flag(self, addresses: Optional[list[int]] = None) -> int:
        targets = addresses if addresses is not None else list(self.cells.keys())
        count = 0
        for addr in targets:
            if addr in self.cells:
                self.cells[addr].start_flag = True
                self._armed.add(addr)
                count += 1
        return count

    def clear_start_flag(self, addresses: Optional[list[int]] = None) -> int:
        targets = addresses if addresses is not None else list(self.cells.keys())
        count = 0
        for addr in targets:
            if addr in self.cells:
                self.cells[addr].start_flag = False
                self._armed.discard(addr)
                count += 1
        return count

    # ── clock tick ───────────────────────────────────────────────────────────

    def tick(self) -> int:
        """
        Execute one clock cycle.

        Phase 1: Deliver bus values to armed cells only (start_flag=True).
                 Frozen cells cannot fire so no point delivering to them.
        Phase 2: Tick armed cells only — the _armed set tracks exactly which
                 cells have start_flag=True. Cells that fire and clear their
                 start_flag are removed from _armed immediately.
        Phase 3: Enforce per-segment emission limits.
        Phase 4: Replace bus with new results.

        Armed-cell optimisation (Option C): instead of iterating all cells,
        only cells in _armed are visited. This skips frozen and already-fired
        cells entirely — typically 95%+ of the array during tile execution.

        Returns count of cells that emitted a result this cycle.
        """
        self._tick_count += 1
        self._breakpoint_halt = False

        # Phase 1: build input maps from armed cells only
        # input_map_a: primary input (rising edge, A)
        # input_map_b: secondary input (falling edge, B) -- v2 two-input cells
        input_map_a: dict[int, list] = {}
        input_map_b: dict[int, list] = {}
        for addr in self._armed:
            cell = self.cells.get(addr)
            if cell:
                input_map_a.setdefault(cell.input_address, []).append(cell)
                # v2 two-input: cell also listens on input_b_address
                if hasattr(cell, 'input_b_address') and cell.input_b_address:
                    input_map_b.setdefault(cell.input_b_address, []).append(cell)

        # Deliver A (primary) inputs
        for bus_address, (value, ecc_check) in self.bus.items():
            if bus_address in input_map_a:
                for cell in input_map_a[bus_address]:
                    cell.receive(value, ecc_check)
            # Deliver B (secondary) inputs to two-input cells
            if bus_address in input_map_b:
                for cell in input_map_b[bus_address]:
                    if hasattr(cell, 'receive_b'):
                        cell.receive_b(value)

        # Phase 2: tick armed cells only
        new_bus: dict[int, tuple] = {}
        active_count = 0
        segment_emissions: dict[int, int] = {}

        for addr in list(self._armed):   # snapshot — set may shrink mid-loop
            cell = self.cells.get(addr)
            if cell is None:
                self._armed.discard(addr)
                continue

            result = cell.tick()
            if result is None:
                continue

            if not cell.start_flag:
                self._armed.discard(addr)

            if cell.trace_en and len(self.trace_buffer) < self.max_trace_entries:
                self.trace_buffer.append({"tick": self._tick_count,
                    "addr": hex(addr), "gs": hex(cell.gate_state),
                    "value": result[1] if result else None})

            if cell.breakpoint and getattr(cell, "_breakpoint_triggered", False):
                cell._breakpoint_triggered = False
                self._breakpoint_halt = True

            # addr_latch cells return 4-tuple (output_addr, val, chk, full_64bit_addr)
            # Normal cells return 3-tuple (output_addr, val, chk)
            # The 64-bit extended address is consumed by the command bus layer.
            # The data bus always uses the 32-bit output_addr — unchanged.
            if len(result) == 4:
                output_addr, value, ecc_check, _ext_addr = result
                # Record extended address for command bus routing
                self._extended_addresses[addr] = _ext_addr
            else:
                output_addr, value, ecc_check = result

            if output_addr in new_bus:
                existing_val, existing_chk = new_bus[output_addr]
                combined_val = existing_val | value
                from unicell import _compute_ecc
                combined_chk = (_compute_ecc(combined_val)
                                if cell.ecc_enabled else 0)
                new_bus[output_addr] = (combined_val, combined_chk)
            else:
                new_bus[output_addr] = (value, ecc_check)

            active_count += 1
            seg_id = self._cell_segment.get(addr, 0)
            segment_emissions[seg_id] = segment_emissions.get(seg_id, 0) + 1

        # Phase 3: enforce emission limits
        if self.enforce_emission_limits:
            for seg_id, count in segment_emissions.items():
                seg = self._segments.get(seg_id)
                if seg is not None and count > seg.lane_count:
                    raise BusConflictError(
                        f"Segment {seg_id} exceeded lane capacity: "
                        f"{count} emissions > {seg.lane_count} lanes"
                    )

        self.bus = new_bus
        if self._breakpoint_halt:
            return -1
        return active_count

    # ── run to completion ────────────────────────────────────────────────────

    def run(self, max_cycles: int = 1_000_000) -> int:
        """
        Run until all compute-mode cells have finished.
        Storage and loopback cells run indefinitely and are excluded
        from the termination check.
        """
        for cycle in range(max_cycles):
            self.tick()
            compute_waiting = any(
                cell.start_flag
                and not cell.storage_mode
                and not cell.is_loopback
                for cell in self.cells.values()
            )
            if not compute_waiting:
                return cycle + 1
        raise RuntimeError(
            f"Execution did not terminate within {max_cycles} cycles"
        )

    # ── inspection ───────────────────────────────────────────────────────────

    def status(self) -> dict:
        total     = self._cell_count
        allocated = len(self.cells)
        defective = len(self.defect_map)
        running   = sum(1 for c in self.cells.values() if c.start_flag)
        free      = total - allocated - defective
        return {
            "total_cells":          total,
            "allocated_cells":      allocated,
            "free_cells":           max(free, 0),
            "defective_cells":      defective,
            "running_cells":        running,
            "bus_active_addresses": len(self.bus),
            "segments":             len(self._segments),
            **self.ecc_status(),
        }

    def read_bus(self, address: int) -> Optional[int]:
        """Return the value at address on the bus, or None if absent."""
        entry = self.bus.get(address)
        return entry[0] if entry is not None else None

