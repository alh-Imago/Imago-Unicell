"""
branch.py — BranchPoint and DataTable

Implements the runtime-volatile dispatch mechanism.

Architecture
============

A BranchPoint is a fixed set of cells in the array. What changes between
uses is the DATA loaded into it — the comparand values and the routing
destinations. The same BranchPoint handles any dispatch by loading a
different DataRow each time.

Cell layout:

  cell_a  (storage, in→out) — holds operand A, re-emits every tick
  cell_b  (storage, in→out) — holds comparand B, re-emits every tick
  comparator chain          — XNOR(A,B): output=1 if A==B, 0 if A!=B
  SELECT  (LOOP_MODE)       — reads comparator result:
                                1 (A==B)  → output_address      (true dest)
                                0 (A!=B)  → output_address_alt  (false dest)

The SELECT cell's output_address and output_address_alt ARE the routing
destinations. They are updated at runtime via the lock/load/run protocol:
  1. freeze  — clear start_flags (lock: nothing fires during update)
  2. write   — inject A and B into storage cells, update SELECT cell's
               output addresses via restore_snapshot()
  3. thaw    — assert start_flags (run: all data present, comparator arms)

This makes both the comparison values AND the routing destinations fully
volatile. Load a different DataRow and the BranchPoint dispatches
to completely different places.

DataTable
=========

A DataTable holds named rows, each describing one dispatch decision:
  label      — human name
  a          — operand value being tested
  b          — comparand value
  addr_true  — destination if A == B
  addr_false — destination if A != B

The table is general purpose. Any cell that reads from storage can be
driven by a DataTable row — not just BranchPoints. Loop bounds, tile
call targets, state machine transitions, configuration parameters.
The program state is data. The infrastructure is fixed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from controller import ImagoController

from controller import CellMapRecord
from gate_states import GS_PASS, GS_NOT, GS_SELECT, LOOP_MODE


# ── DataTable row ─────────────────────────────────────────────────────────────

@dataclass
class DataRow:
    """One row in a DataTable — one dispatch decision."""
    label:      str
    a:          int          # operand value
    b:          int          # comparand value
    addr_true:  int          # destination if a == b
    addr_false: int          # destination if a != b
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "label":      self.label,
            "a":          self.a,
            "b":          self.b,
            "addr_true":  hex(self.addr_true),
            "addr_false": hex(self.addr_false),
        }


# ── DataTable ─────────────────────────────────────────────────────────────────

class DataTable:
    """
    A program state block — a named collection of DataRows.

    Holds the dispatch decisions for a program or component. Volatile:
    rows can be added, updated, or removed at runtime. Loading a row
    into a BranchPoint takes effect on the next BranchPoint fire.

    Not limited to branch conditions. Any consumer reading from storage
    can be driven by a DataTable row: loop bounds, tile parameters,
    state machine transitions, configuration values.
    """

    def __init__(self, name: str):
        self.name   = name
        self._rows: dict[str, DataRow] = {}
        self._order: list[str] = []

    def add(self, label: str, a: int, b: int,
            addr_true: int, addr_false: int) -> DataRow:
        """Add or replace a row with explicit addresses."""
        row = DataRow(label=label, a=a, b=b,
                      addr_true=addr_true, addr_false=addr_false)
        if label not in self._rows:
            self._order.append(label)
        self._rows[label] = row
        return row

    def add_from_shore(self, shore, label: str,
                       a: int, b: int,
                       name_true: str,
                       name_false: str,
                       bridge_role_true:  str = "INBOUND",
                       bridge_role_false: str = "INBOUND") -> Optional[DataRow]:
        """
        Add a row using Shore to resolve bridge addresses.

        name_true / name_false: Shore registry names of the destination
          resources (Pond names, bridge names, or any registered entry).
        bridge_role_true/false: which bridge role to use when the entry
          is a Pond (looks up the named bridge within that Pond's bridges).
          Ignored when the entry is already a specific bridge address.

        Shore looks up the current external_address for each named resource.
        If either name is not found in Shore, returns None.

        When the Pond moves and Shore is updated, call refresh_from_shore()
        to update all rows automatically.
        """
        entry_true  = shore.lookup(name_true)
        entry_false = shore.lookup(name_false)

        if entry_true is None:
            print(f"[BRANCH] add_from_shore: '{name_true}' not found in Shore")
            return None
        if entry_false is None:
            print(f"[BRANCH] add_from_shore: '{name_false}' not found in Shore")
            return None

        addr_true  = entry_true.resolve_address()  or 0
        addr_false = entry_false.resolve_address() or 0

        row = self.add(label, a, b, addr_true, addr_false)
        # Record the Shore names so refresh_from_shore can update them later
        row.__dict__['_shore_name_true']  = name_true
        row.__dict__['_shore_name_false'] = name_false
        return row

    def refresh_from_shore(self, shore) -> int:
        """
        Update all rows that were added via add_from_shore().

        When a Pond moves, its bridge external_address changes. Call this
        after Shore has processed the ROUTE_UPDATE to re-resolve all
        Shore-linked rows to their current addresses.

        Returns the count of rows that were updated.
        """
        updated = 0
        for row in self._rows.values():
            name_true  = row.__dict__.get('_shore_name_true')
            name_false = row.__dict__.get('_shore_name_false')
            if name_true is None and name_false is None:
                continue   # raw address row, skip

            changed = False
            if name_true:
                entry = shore.lookup(name_true)
                if entry:
                    new_addr = entry.resolve_address() or 0
                    if new_addr != row.addr_true:
                        row.addr_true = new_addr
                        changed = True

            if name_false:
                entry = shore.lookup(name_false)
                if entry:
                    new_addr = entry.resolve_address() or 0
                    if new_addr != row.addr_false:
                        row.addr_false = new_addr
                        changed = True

            if changed:
                updated += 1

        return updated

    def get(self, label: str) -> Optional[DataRow]:
        return self._rows.get(label)

    def remove(self, label: str) -> bool:
        if label in self._rows:
            del self._rows[label]
            self._order.remove(label)
            return True
        return False

    def update(self, label: str, **kwargs) -> bool:
        row = self._rows.get(label)
        if row is None:
            return False
        for k, v in kwargs.items():
            if hasattr(row, k):
                setattr(row, k, v)
        return True

    def rows(self) -> list[DataRow]:
        return [self._rows[k] for k in self._order]

    def __len__(self) -> int:
        return len(self._rows)

    def __repr__(self) -> str:
        return f"DataTable({self.name!r}, {len(self)} rows)"

    def dump(self) -> str:
        lines = [f"DataTable '{self.name}' — {len(self)} rows"]
        for row in self.rows():
            lines.append(
                f"  [{row.label}] a={row.a} b={row.b} "
                f"true→{hex(row.addr_true)} false→{hex(row.addr_false)}"
            )
        return "\n".join(lines)


# ── BranchPoint ───────────────────────────────────────────────────────────────

class BranchPoint:
    """
    A fixed set of cells implementing volatile runtime dispatch.

    Placed once in the array. Never moves. What changes between uses is
    the data loaded via load_row() — the comparison values A and B, and
    the routing destinations addr_true and addr_false.

    The lock/load/run protocol (using the start_flag as synchronisation
    barrier) guarantees all values are present before anything fires:
      freeze → write A, B, addr_true, addr_false → thaw

    Cell count: 2 storage + ~12 comparator + 1 SELECT = ~15 cells.
    All 1-bit (single-bus-lane) operations.
    """

    def __init__(self,
                 region_id:       str,
                 cell_a_in:       int,
                 cell_b_in:       int,
                 select_phys_addr: int,
                 cell_addresses:  list[int],
                 select_record_idx: int):
        self.region_id         = region_id
        self.cell_a_in         = cell_a_in
        self.cell_b_in         = cell_b_in
        self.select_phys_addr  = select_phys_addr
        self.cell_addresses    = cell_addresses
        self.select_record_idx = select_record_idx
        self._current_row: Optional[DataRow] = None

    @classmethod
    def build(cls, ctrl: "ImagoController",
              name: str = "branch") -> "BranchPoint":
        """
        Build a BranchPoint in the controller's array.

        Allocates cells, loads via load_map, starts frozen.
        Call load_row() to write data and arm.
        """
        from ir import AddressAllocator
        alloc = AddressAllocator()

        # Storage cells: hold A and B comparison values
        a_in  = alloc.alloc(); a_out = alloc.alloc()
        b_in  = alloc.alloc(); b_out = alloc.alloc()

        # v2 comparison using single-cell XNOR + AND(1) to extract clean bit.
        # XNOR(a,b) for 1-bit inputs: equal->0xFFFFFFFF (bit0=1), unequal->0xFFFFFFFE (bit0=0)
        # AND(XNOR, 1): extracts bit 0: equal->1, unequal->0
        # SELECT: nonzero(1=equal)->addr_true, zero(0=unequal)->addr_false
        # Same semantics as v1 (1=equal=true branch). 5 cells vs 12 in v1.
        cmp_xnor = alloc.alloc()   # XNOR cell output
        const1   = alloc.alloc()   # constant 1 for AND mask
        cmp_o    = alloc.alloc()   # AND(XNOR, 1) = clean 0 or 1

        sel_true  = 0x00000001   # placeholder (overwritten at load_row)
        sel_false = 0x00000002

        _xnor_gs = 0b000111100 | 0x00008000   # GS_XNOR | GS_SYNC_WAIT
        _and_gs  = 0b000000111 | 0x00008000   # GS_AND  | GS_SYNC_WAIT

        records = [
            CellMapRecord(GS_PASS, a_in,  a_out, storage_mode=True),
            CellMapRecord(GS_PASS, b_in,  b_out, storage_mode=True),
            # Constant 1: always-armed latch, re-emits 1 every tick
            CellMapRecord(GS_PASS | LOOP_MODE, const1, const1,
                          storage_mode=True, initial_value=1),
            # XNOR(A,B) single cell: equal->0xFFFFFFFF, unequal->0xFFFFFFFE
            CellMapRecord(_xnor_gs, a_out, cmp_xnor, input_b_address=b_out),
            # AND(XNOR, 1): extracts bit 0 -> equal->1, unequal->0
            CellMapRecord(_and_gs, cmp_xnor, cmp_o, input_b_address=const1),
            # SELECT: 1(equal)->addr_true, 0(unequal)->addr_false
            CellMapRecord(GS_SELECT | LOOP_MODE, cmp_o,
                          sel_true, output_address_alt=sel_false),
        ]

        select_record_idx = len(records) - 1   # SELECT is always the last record

        rid = ctrl.load_map(records, name)
        if rid is None:
            raise RuntimeError(f"BranchPoint.build: load_map failed for '{name}'")

        # Start frozen — nothing fires until load_row()
        ctrl.freeze(region_id=rid)

        cell_addresses = ctrl._regions[rid].cell_addresses
        select_phys    = cell_addresses[select_record_idx]

        bp = cls(
            region_id          = rid,
            cell_a_in          = a_in,
            cell_b_in          = b_in,
            select_phys_addr   = select_phys,
            cell_addresses     = cell_addresses,
            select_record_idx  = select_record_idx,
        )
        print(f"[BRANCH] BranchPoint '{name}' built — "
              f"{len(records)} cells, region {rid}")
        return bp

    # ── Load / arm ────────────────────────────────────────────────────────────

    def load_row(self, row: DataRow, ctrl: "ImagoController") -> None:
        """
        Load a DataRow using the lock/load/run protocol.

          1. freeze  — clear all start_flags
          2. write   — inject A and B into storage cells;
                       update SELECT cell's output addresses
          3. thaw    — assert all start_flags

        The SELECT cell's routing destinations are updated directly via
        restore_snapshot — writing the new addr_true and addr_false into
        the cell's output_address and output_address_alt registers while
        it is frozen. This makes routing fully volatile with no extra cells.
        """
        # 1. Lock — freeze all cells (start_flag cleared on all)
        ctrl.freeze(region_id=self.region_id)

        # Clear stale in-transit data from the previous computation.
        # Cells that received data on the tick just before freeze retain
        # cell.data -- they would fire that stale value on the first tick
        # after thaw, corrupting the new computation. bus.clear() alone
        # is not enough; we must also clear cell.data on compute cells.
        for phys_addr in self.cell_addresses:
            cell = ctrl.array.cells.get(phys_addr)
            if cell is not None and not cell.storage_mode:
                cell.data = None

        # 2. Write all four values via restore_snapshot while frozen.
        #    restore_snapshot writes directly to cell state — no bus tick needed.
        #    This avoids the problem where frozen cells can't receive bus data.

        # Update A storage cell: set _stored_value directly
        a_stor = next((c for c in ctrl.array.cells.values()
                       if c.storage_mode and c.input_address == self.cell_a_in), None)
        if a_stor is not None:
            state_a = a_stor.snapshot()
            state_a["stored_value"] = row.a & 1   # 1-bit comparison
            ctrl.restore_snapshot([state_a])

        # Update B storage cell: set _stored_value directly
        b_stor = next((c for c in ctrl.array.cells.values()
                       if c.storage_mode and c.input_address == self.cell_b_in), None)
        if b_stor is not None:
            state_b = b_stor.snapshot()
            state_b["stored_value"] = row.b & 1
            ctrl.restore_snapshot([state_b])

        # Update SELECT cell routing addresses
        sel_cell = ctrl.array.cells.get(self.select_phys_addr)
        if sel_cell is None:
            raise RuntimeError("BranchPoint: SELECT cell not found in array")
        state_sel = sel_cell.snapshot()
        # SELECT: nonzero(=1=equal)->output_address=addr_true, zero(=0=unequal)->output_address_alt=addr_false
        state_sel["output_address"]     = row.addr_true  & 0xFFFFFFFF
        state_sel["output_address_alt"] = row.addr_false & 0xFFFFFFFF
        ctrl.restore_snapshot([state_sel])

        # 3. Clear stale bus values from previous run, then arm.
        #    Without this, stale bus values from the previous computation
        #    would be delivered to comparator cells on the first tick after
        #    thaw, corrupting the result.
        ctrl.array.bus.clear()
        ctrl.thaw(region_id=self.region_id)

        self._current_row = row
        print(f"[BRANCH] Loaded '{row.label}': "
              f"a={row.a} b={row.b} "
              f"true→{hex(row.addr_true)} false→{hex(row.addr_false)}")

    def load(self, ctrl: "ImagoController",
             a: int, b: int,
             addr_true: int, addr_false: int,
             label: str = "direct") -> None:
        """Load values directly without a DataRow."""
        self.load_row(
            DataRow(label=label, a=a, b=b,
                    addr_true=addr_true, addr_false=addr_false),
            ctrl
        )

    def load_from_shore(self, shore, ctrl: "ImagoController",
                        a: int, b: int,
                        name_true: str,
                        name_false: str,
                        label: str = "shore_route") -> bool:
        """
        Load routing from Shore bridge addresses.

        Looks up name_true and name_false in Shore to get their current
        external_address values, then calls load_row() with those addresses.

        This is the standard way to connect a BranchPoint to real Pond
        INBOUND bridges. When a Pond moves and Shore is updated, call
        load_from_shore() again to re-arm with the new addresses.

        Returns True on success, False if either name is not found in Shore.
        """
        entry_true  = shore.lookup(name_true)
        entry_false = shore.lookup(name_false)

        if entry_true is None:
            print(f"[BRANCH] load_from_shore: '{name_true}' not found in Shore")
            return False
        if entry_false is None:
            print(f"[BRANCH] load_from_shore: '{name_false}' not found in Shore")
            return False

        addr_true  = entry_true.resolve_address() or 0
        addr_false = entry_false.resolve_address() or 0

        self.load_row(
            DataRow(label=label, a=a, b=b,
                    addr_true=addr_true, addr_false=addr_false),
            ctrl
        )
        return True

    def freeze(self, ctrl: "ImagoController") -> int:
        return ctrl.freeze(region_id=self.region_id)

    def thaw(self, ctrl: "ImagoController") -> int:
        return ctrl.thaw(region_id=self.region_id)

    @property
    def current_row(self) -> Optional[DataRow]:
        return self._current_row

    def status(self) -> dict:
        return {
            "region_id":        self.region_id,
            "cell_a_in":        hex(self.cell_a_in),
            "cell_b_in":        hex(self.cell_b_in),
            "select_phys_addr": hex(self.select_phys_addr),
            "total_cells":      len(self.cell_addresses),
            "current_row":      self._current_row.to_dict() if self._current_row else None,
        }

    def __repr__(self) -> str:
        row = self._current_row
        loaded = f"row='{row.label}'" if row else "unloaded"
        return f"BranchPoint(region={self.region_id} {loaded})"
