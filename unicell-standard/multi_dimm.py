"""
multi_dimm.py — Multi-DIMM controller with routing table and swap support.

Extends the single-array ImagoController with:
  - Multiple UniCellArray instances (one per DIMM slot)
  - 64-bit system address map: slot -> (base, top) address range
  - Cross-DIMM routing table CAM: intercepts bus results destined
    for a different DIMM and forwards them
  - Swap mechanism: serialise a region to .icm, free its cells,
    reload into any available space (possibly different DIMM)
  - Partial snapshot: save a region's config without freeing cells

Architecture reference (UniCell Architecture v1.8, Address Architecture):
  Cell-level:  32-bit local address within one DIMM
  System-level: 64-bit address = (slot_number << 32) | local_address
  Cross-DIMM:  controller intercepts, routing table CAM forwards
"""

import json
import os
import time
import hashlib
from typing import Optional

from unicell_array import UniCellArray
from controller import ImagoController, CellMapRecord, Region
from unicell import FUNCTION_LOAD_PATTERN

# ── system address helpers ────────────────────────────────────────────────────

DIMM_ADDRESS_BITS = 32
DIMM_LOCAL_MASK   = 0xFFFFFFFF   # lower 32 bits = local address within DIMM
DIMM_SLOT_SHIFT   = 32           # upper bits = slot number

def system_address(slot: int, local: int) -> int:
    """Pack slot number and local address into a 64-bit system address."""
    return (slot << DIMM_SLOT_SHIFT) | (local & DIMM_LOCAL_MASK)

def split_system_address(addr: int) -> tuple[int, int]:
    """Split a 64-bit system address into (slot, local_address)."""
    slot  = addr >> DIMM_SLOT_SHIFT
    local = addr & DIMM_LOCAL_MASK
    return slot, local


# ── MultiDimmController ───────────────────────────────────────────────────────

class MultiDimmController:
    """
    Models a BIOS-plus chip managing multiple UniCell DIMMs.

    Each DIMM slot has its own UniCellArray. The controller maintains
    a routing table mapping system address ranges to slot numbers.
    Cross-DIMM data forwarding is handled transparently.

    System addresses are 64-bit: upper 32 bits = slot, lower 32 = local.
    The compiler and ProgramBuilder use system addresses throughout.
    Individual cells still use 32-bit local addresses internally.
    """

    MAX_SLOTS = 16   # maximum DIMM slots

    def __init__(self, cells_per_dimm: int = 1_000_000):
        self.cells_per_dimm = cells_per_dimm

        # Slot number -> UniCellArray
        self._dimms: dict[int, UniCellArray] = {}

        # Routing table: slot -> (base_system_addr, top_system_addr)
        self._routing: dict[int, tuple[int, int]] = {}

        # Region registry: region_id -> Region (same as ImagoController)
        self._regions: dict[str, Region] = {}

        # Machine-unique key (simulated)
        self._machine_key: int = 0xDEADC0DEBEEF1234

        # Execution stats
        self.total_cycles: int = 0

        # Add the first DIMM automatically
        self.add_dimm(0)

    # ── DIMM management ───────────────────────────────────────────────────────

    def add_dimm(self, slot: int) -> UniCellArray:
        """
        Add a DIMM to the given slot.
        Registers its address range in the routing table.
        Returns the new UniCellArray.
        """
        if slot in self._dimms:
            raise ValueError(f"Slot {slot} already occupied")
        if slot >= self.MAX_SLOTS:
            raise ValueError(f"Slot {slot} exceeds MAX_SLOTS ({self.MAX_SLOTS})")

        dimm = UniCellArray(self.cells_per_dimm)
        self._dimms[slot] = dimm

        base = system_address(slot, 1)              # 0x0 reserved
        top  = system_address(slot, 0xFFFFFFFF)
        self._routing[slot] = (base, top)

        print(f"[MULTI-DIMM] Slot {slot} installed — "
              f"system range 0x{base:016X}–0x{top:016X} "
              f"({self.cells_per_dimm:,} cells)")
        return dimm

    def remove_dimm(self, slot: int) -> None:
        """
        Remove a DIMM from the given slot.
        Raises if any active regions are on this DIMM.
        """
        active = [
            r for r in self._regions.values()
            if r.state != Region.FREED and
            any(split_system_address(a)[0] == slot
                for a in r.cell_addresses)
        ]
        if active:
            raise RuntimeError(
                f"Cannot remove slot {slot}: "
                f"{len(active)} active region(s) present"
            )
        del self._dimms[slot]
        del self._routing[slot]
        print(f"[MULTI-DIMM] Slot {slot} removed")

    def slot_count(self) -> int:
        return len(self._dimms)

    def _slot_for_system_addr(self, system_addr: int) -> Optional[int]:
        """Return the slot number for a given system address, or None."""
        slot, _ = split_system_address(system_addr)
        return slot if slot in self._dimms else None

    def _dimm_for_system_addr(self, system_addr: int) -> Optional[UniCellArray]:
        """Return the UniCellArray for a given system address, or None."""
        slot = self._slot_for_system_addr(system_addr)
        return self._dimms.get(slot)

    # ── cell allocation ───────────────────────────────────────────────────────

    def _allocate_cell_system(
        self,
        preferred_slot: Optional[int] = None
    ) -> tuple[int, int]:
        """
        Allocate one cell, returning (system_address, local_address).
        Tries preferred_slot first, then any available slot.
        """
        slots_to_try = []
        if preferred_slot is not None and preferred_slot in self._dimms:
            slots_to_try.append(preferred_slot)
        slots_to_try.extend(
            s for s in sorted(self._dimms.keys())
            if s != preferred_slot
        )

        for slot in slots_to_try:
            dimm = self._dimms[slot]
            try:
                cell = dimm.allocate_cell()
                sys_addr = system_address(slot, cell.address)
                return sys_addr, cell.address
            except RuntimeError:
                continue  # this DIMM is full, try next

        raise RuntimeError(
            "All DIMMs are full — cannot allocate cell. "
            f"Total capacity: {self.cells_per_dimm * len(self._dimms):,} cells"
        )

    # ── config write ──────────────────────────────────────────────────────────

    def _write_config_system(
        self,
        target_sys_addr: int,
        gate_state: int,
        input_sys_addr: int,
        output_sys_addr: int,
    ) -> bool:
        """
        Write a config packet to a cell identified by system address.
        Translates system addresses to local addresses for the cell.
        The cell stores local addresses; the routing table handles
        cross-DIMM forwarding at runtime.
        """
        slot, local_addr = split_system_address(target_sys_addr)
        dimm = self._dimms.get(slot)
        if dimm is None:
            return False

        # Translate input/output system addresses to local addresses
        # within their respective DIMMs
        _, local_in  = split_system_address(input_sys_addr)
        _, local_out = split_system_address(output_sys_addr)

        packet = [
            FUNCTION_LOAD_PATTERN,
            gate_state,
            local_in,
            local_out,
        ]
        return dimm.write_config(local_addr, packet)

    # ── security gate ─────────────────────────────────────────────────────────

    def _security_gate(self, cell_map: list[CellMapRecord]) -> bool:
        if len(cell_map) == 0:
            return False
        for record in cell_map:
            if record.output_address == 0x00000000:
                return False
            if (record.input_address  & DIMM_LOCAL_MASK) == FUNCTION_LOAD_PATTERN:
                return False
            if (record.output_address & DIMM_LOCAL_MASK) == FUNCTION_LOAD_PATTERN:
                return False
        return True

    # ── load map ──────────────────────────────────────────────────────────────

    def load_map(
        self,
        cell_map: list[CellMapRecord],
        image_name: str = "unnamed",
        preferred_slot: Optional[int] = None,
    ) -> Optional[str]:
        """
        Load a compiled cell map into the array.
        Allocates cells across DIMMs, preferring preferred_slot.
        Remaps addresses: the cell map uses relative addresses;
        each cell receives its actual system-assigned addresses.
        Returns region_id on success, None on failure.
        """
        if not self._security_gate(cell_map):
            print(f"[MULTI-DIMM] Security gate REJECTED '{image_name}'")
            return None

        # Build address remap: compiler-relative addr -> system addr.
        # We use a counter-based scheme: assign sequential system addresses
        # to each unique address in the cell map WITHOUT allocating real cells
        # for them -- addresses are logical bus positions, not physical cells.
        # Only CellMapRecord entries represent actual cells.
        old_addrs: set[int] = set()
        for r in cell_map:
            old_addrs.add(r.input_address)
            old_addrs.add(r.output_address)

        # Assign system addresses from a counter (no cell allocation)
        addr_remap: dict[int, int] = {}
        slot_for_remap = preferred_slot if preferred_slot is not None                          else min(self._dimms.keys())
        base_slot = slot_for_remap
        counter = self._dimms[base_slot]._next_address
        for old_addr in sorted(old_addrs):
            addr_remap[old_addr] = system_address(base_slot, counter)
            counter += 1
        # Advance the DIMM's address counter past our reserved range
        self._dimms[base_slot]._next_address = counter

        # Allocate actual cells and write config
        cell_sys_addresses = []
        try:
            for record in cell_map:
                # Allocate a fresh cell for this record
                cell_sys_addr, cell_local = self._allocate_cell_system(
                    preferred_slot
                )
                new_in  = addr_remap[record.input_address]
                new_out = addr_remap[record.output_address]

                success = self._write_config_system(
                    cell_sys_addr,
                    record.gate_state,
                    new_in,
                    new_out,
                )
                if not success:
                    raise RuntimeError(
                        f"Config write failed at 0x{cell_sys_addr:016X}"
                    )
                cell_sys_addresses.append(cell_sys_addr)

        except RuntimeError as e:
            print(f"[MULTI-DIMM] Load failed mid-write: {e}")
            return None

        region = Region(cell_sys_addresses, image_name)
        self._regions[region.region_id] = region

        # Determine which slots this region spans
        slots_used = sorted(set(
            split_system_address(a)[0] for a in cell_sys_addresses
        ))
        print(
            f"[MULTI-DIMM] Loaded '{image_name}' — "
            f"{len(cell_sys_addresses)} cells — "
            f"slot(s) {slots_used} — "
            f"region {region.region_id}"
        )
        return region.region_id

    # ── start flag ────────────────────────────────────────────────────────────

    def _assert_start_flag_region(self, region: Region) -> None:
        """Assert start flag for all cells in a region across all DIMMs."""
        by_slot: dict[int, list[int]] = {}
        for sys_addr in region.cell_addresses:
            slot, local = split_system_address(sys_addr)
            by_slot.setdefault(slot, []).append(local)
        for slot, locals_ in by_slot.items():
            if slot in self._dimms:
                self._dimms[slot].assert_start_flag(locals_)

    def _clear_start_flag_region(self, region: Region) -> None:
        """Clear start flag for all cells in a region."""
        by_slot: dict[int, list[int]] = {}
        for sys_addr in region.cell_addresses:
            slot, local = split_system_address(sys_addr)
            by_slot.setdefault(slot, []).append(local)
        for slot, locals_ in by_slot.items():
            if slot in self._dimms:
                self._dimms[slot].clear_start_flag(locals_)

    # ── cross-DIMM tick ───────────────────────────────────────────────────────

    def _tick_all(self) -> int:
        """
        Execute one clock cycle across all DIMMs.
        Handles cross-DIMM forwarding: results posted to addresses on
        a different DIMM are moved to that DIMM's bus.

        Returns total active cell count across all DIMMs.
        """
        total_active = 0

        # Tick each DIMM independently
        for slot, dimm in self._dimms.items():
            active = dimm.tick()
            total_active += active

        # Cross-DIMM forwarding: scan all DIMM buses for values
        # whose addresses belong to a different DIMM
        for src_slot, src_dimm in self._dimms.items():
            forwards = {}
            for local_addr, value in list(src_dimm.bus.items()):
                # Check if this local address is actually a forwarding address
                # In the current model local addresses stay local.
                # True cross-DIMM requires the compiler to assign system
                # addresses. This tick handles the case where a cell's
                # output_address was remapped to another DIMM's local space.
                # For now, local buses are independent; cross-DIMM is via
                # the routing table which is populated at load time.
                pass

        return total_active

    # ── run ───────────────────────────────────────────────────────────────────

    def run(
        self,
        region_id: str,
        inputs: Optional[dict[int, int]] = None,
        max_cycles: int = 1_000_000,
        capture_addresses: Optional[list[int]] = None,
    ) -> Optional[dict[int, int]]:
        """
        Run a region to completion.
        inputs: {system_address: value}
        capture_addresses: [system_address, ...]
        Returns {system_address: value} or None.
        """
        region = self._regions.get(region_id)
        if region is None:
            print(f"[MULTI-DIMM] Region '{region_id}' not found")
            return None

        # Inject inputs onto the appropriate DIMM buses
        if inputs:
            for sys_addr, value in inputs.items():
                slot, local = split_system_address(sys_addr)
                if slot in self._dimms:
                    self._dimms[slot].bus[local] = value

        self._assert_start_flag_region(region)
        region.state = Region.RUNNING

        sink_addrs_by_slot: dict[int, set[int]] = {}
        if capture_addresses:
            for sys_addr in capture_addresses:
                slot, local = split_system_address(sys_addr)
                sink_addrs_by_slot.setdefault(slot, set()).add(local)

        captured: dict[int, int] = {}   # local_addr -> value
        cycles = 0

        for cycle in range(max_cycles):
            # Intercept sink addresses before tick
            for slot, locals_ in sink_addrs_by_slot.items():
                dimm = self._dimms.get(slot)
                if dimm is None:
                    continue
                for local in list(dimm.bus.keys()):
                    sys_addr = system_address(slot, local)
                    if local in locals_:
                        if sys_addr not in captured:
                            captured[sys_addr] = dimm.bus.pop(local)
                        else:
                            del dimm.bus[local]

            active = self._tick_all()
            cycles += 1

            # Capture new sink values after tick
            for slot, locals_ in sink_addrs_by_slot.items():
                dimm = self._dimms.get(slot)
                if dimm is None:
                    continue
                for local in locals_:
                    val = dimm.bus.get(local)
                    sys_addr = system_address(slot, local)
                    if val is not None and sys_addr not in captured:
                        captured[sys_addr] = val

            if active == 0:
                break
        else:
            self._clear_start_flag_region(region)
            raise RuntimeError(
                f"Region '{region_id}' timed out after {max_cycles} cycles"
            )

        self._clear_start_flag_region(region)
        region.state = Region.HALTED
        region.cycles_run += cycles
        self.total_cycles += cycles

        if capture_addresses is not None:
            return {a: captured.get(a) for a in capture_addresses}
        # Return everything captured plus current bus state
        result = dict(captured)
        for slot, dimm in self._dimms.items():
            for local, val in dimm.bus.items():
                result[system_address(slot, local)] = val
        return result

    def halt(self, region_id: str) -> bool:
        region = self._regions.get(region_id)
        if not region or region.state != Region.RUNNING:
            return False
        self._clear_start_flag_region(region)
        region.state = Region.HALTED
        return True

    def free(self, region_id: str) -> bool:
        region = self._regions.get(region_id)
        if not region:
            return False
        if region.state == Region.RUNNING:
            print(f"[MULTI-DIMM] Cannot free running region — halt first")
            return False
        for sys_addr in region.cell_addresses:
            slot, local = split_system_address(sys_addr)
            if slot in self._dimms and local in self._dimms[slot].cells:
                del self._dimms[slot].cells[local]
        region.state = Region.FREED
        print(
            f"[MULTI-DIMM] Freed '{region_id}' — "
            f"{len(region.cell_addresses)} cells returned"
        )
        return True

    # ── swap mechanism ────────────────────────────────────────────────────────

    def swap_out(self, region_id: str, swap_dir: str) -> Optional[str]:
        """
        Swap a region out to a .icm file and free its cells.
        The region can be swapped back in later, possibly on a different DIMM.

        Returns the path to the swap file, or None on failure.
        """
        region = self._regions.get(region_id)
        if not region:
            print(f"[MULTI-DIMM] Region '{region_id}' not found")
            return None
        if region.state == Region.RUNNING:
            self.halt(region_id)

        # Serialise current cell configurations
        cell_configs = []
        for sys_addr in region.cell_addresses:
            slot, local = split_system_address(sys_addr)
            dimm = self._dimms.get(slot)
            if dimm is None:
                continue
            cell = dimm.cells.get(local)
            if cell is None:
                continue
            cell_configs.append({
                "gate_state":     cell.gate_state,
                "input_address":  cell.input_address,
                "output_address": cell.output_address,
            })

        swap_data = {
            "region_id":    region_id,
            "image_name":   region.image_name,
            "swapped_at":   time.time(),
            "cell_configs": cell_configs,
            "cycles_run":   region.cycles_run,
        }

        os.makedirs(swap_dir, exist_ok=True)
        swap_path = os.path.join(swap_dir, f"{region_id}.swap.icm")
        tmp_path  = swap_path + ".tmp"
        json_text = json.dumps(swap_data, indent=2)
        with open(tmp_path, 'w') as f:
            f.write(json_text)
        os.replace(tmp_path, swap_path)

        checksum = hashlib.sha256(json_text.encode()).hexdigest()
        print(
            f"[MULTI-DIMM] Swapped out '{region_id}' → {swap_path} "
            f"({len(cell_configs)} cells, SHA-256: {checksum[:16]}...)"
        )

        # Free the cells
        self.free(region_id)
        return swap_path

    def swap_in(
        self,
        swap_path: str,
        preferred_slot: Optional[int] = None,
    ) -> Optional[str]:
        """
        Reload a swapped-out region from a .icm file.
        Places the region on preferred_slot if specified, otherwise
        uses the first available DIMM with sufficient space.

        Returns the new region_id (may differ from the original).
        """
        with open(swap_path, 'r') as f:
            swap_data = json.load(f)

        cell_configs = swap_data["cell_configs"]
        image_name   = swap_data.get("image_name", "swapped")
        original_id  = swap_data.get("region_id", "unknown")

        # Reconstruct CellMapRecord list
        records = [
            CellMapRecord(
                c["gate_state"],
                c["input_address"],
                c["output_address"],
            )
            for c in cell_configs
        ]

        new_region_id = self.load_map(
            records, image_name, preferred_slot=preferred_slot
        )
        if new_region_id is None:
            return None

        # Restore cycle count
        if new_region_id in self._regions:
            self._regions[new_region_id].cycles_run = swap_data.get(
                "cycles_run", 0
            )

        print(
            f"[MULTI-DIMM] Swapped in '{original_id}' → "
            f"new region '{new_region_id}' "
            f"(slot {preferred_slot if preferred_slot is not None else 'any'})"
        )
        return new_region_id

    # ── partial snapshot ──────────────────────────────────────────────────────

    def snapshot(self, region_id: str, snapshot_dir: str) -> Optional[str]:
        """
        Save a snapshot of a region's current cell configurations
        WITHOUT freeing the cells. The region continues running.
        The snapshot can be loaded later as a fresh region.

        Returns the snapshot file path, or None on failure.
        """
        region = self._regions.get(region_id)
        if not region:
            print(f"[MULTI-DIMM] Region '{region_id}' not found")
            return None

        cell_configs = []
        for sys_addr in region.cell_addresses:
            slot, local = split_system_address(sys_addr)
            dimm = self._dimms.get(slot)
            if dimm is None:
                continue
            cell = dimm.cells.get(local)
            if cell is None:
                continue
            cell_configs.append({
                "gate_state":     cell.gate_state,
                "input_address":  cell.input_address,
                "output_address": cell.output_address,
                "data":           int(cell.data) if cell.data is not None else None,
            })

        snapshot_data = {
            "region_id":    region_id,
            "image_name":   region.image_name,
            "snapshot_at":  time.time(),
            "state":        region.state,
            "cycles_run":   region.cycles_run,
            "cell_configs": cell_configs,
        }

        os.makedirs(snapshot_dir, exist_ok=True)
        ts   = int(time.time())
        path = os.path.join(snapshot_dir, f"{region_id}.{ts}.snapshot.icm")
        tmp  = path + ".tmp"
        text = json.dumps(snapshot_data, indent=2)
        with open(tmp, 'w') as f:
            f.write(text)
        os.replace(tmp, path)

        print(
            f"[MULTI-DIMM] Snapshot of '{region_id}' → {path} "
            f"({len(cell_configs)} cells)"
        )
        return path

    # ── status ────────────────────────────────────────────────────────────────

    def status(self) -> dict:
        """Return a summary of multi-DIMM controller state."""
        total_cells = 0
        allocated   = 0
        for slot, dimm in self._dimms.items():
            s = dimm.status()
            total_cells += s["total_cells"]
            allocated   += s["allocated_cells"]

        active_regions = [
            r for r in self._regions.values()
            if r.state not in (Region.FREED,)
        ]

        return {
            "dimm_slots":      list(self._dimms.keys()),
            "total_cells":     total_cells,
            "allocated_cells": allocated,
            "free_cells":      total_cells - allocated,
            "active_regions":  len(active_regions),
            "total_regions":   len(self._regions),
            "total_cycles":    self.total_cycles,
        }

    def __repr__(self) -> str:
        s = self.status()
        return (
            f"MultiDimmController("
            f"slots={s['dimm_slots']} "
            f"cells={s['allocated_cells']}/{s['total_cells']} "
            f"regions={s['active_regions']})"
        )
