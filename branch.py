"""
branch.py — BranchPoint and DataTable

Runtime dispatch mechanism for the Imago spatial computing fabric.

Architecture (2026-05-18, post-silicon validation)
===================================================

Two compiler modes for branching:

MODE 1 — Compiled tree (small decisions, inlined if/else)
  Both branches fully compiled into cells simultaneously.
  Condition must produce a clean 0 or 0xFFFFFFFF signal (1-bit comparison).
  AND-gate masks each branch:
    true  branch: AND(0xFFFFFFFF, input) = input  (passes through)
    false branch: AND(0x00000000, input) = 0      (blocked)
  Both branches exist in silicon; only the gated one fires.
  Emitted by compiler directly — not by BranchPoint.
  Cost: proportional to branch_size × 2.

MODE 2 — PTT dispatch (program tile, loops, larger decisions)
  BranchPoint builds a comparison cell cluster.
  Result fires to a PTT address.
  Ward receives the result and issues CMD_RELEASE / CMD_FREEZE
  to arm the true region and disarm the false region (or vice versa).
  The program tile holds branch target data; Ward selects the entry.
  Cost: ~2 cells for comparison + PTT overhead.

DataTable
=========
A named collection of DataRows — one per dispatch decision.
Each row holds: operand A, comparand B, true destination, false destination.
Can be linked to Shore for dynamic address resolution.
Not limited to branch conditions: loop bounds, tile parameters,
state machine transitions, config values — any runtime data.

BranchPoint
===========
Implements the comparison (XNOR) and fires result to PTT.
Ward inspects the result (0xFFFFFFFF = equal, else = not equal)
and dispatches by arming/disarming the appropriate region.

Cell layout (2 cells):
  cell_a   XNOR + latch_in  — holds A (preloaded), triggered by B
                               Output: 0xFFFFFFFF (equal) or ~(A^B) (not equal)
  cell_eq  XNOR(result, 0xFFFFFFFF) — fires 0xFFFFFFFF to PTT if equal, 0 if not
                               Alternatively: fire result directly; Ward tests for 0xFFFFFFFF

PTT fires -> Ward handler:
  if result == 0xFFFFFFFF: CMD_RELEASE true_region, CMD_FREEZE false_region
  else:                    CMD_RELEASE false_region, CMD_FREEZE true_region

Note on AND-gate pointer cells:
  The 3-cell AND-gate pattern (AND cells gated by XNOR result) does NOT work
  for arbitrary 32-bit addresses. AND(partial_mask, addr) produces a corrupted
  address unless the mask is exactly 0xFFFFFFFF. This requires an OR-reduction
  tree (31 cells) to normalise any comparison to 0/0xFFFFFFFF — too expensive.
  Mode 1 works because the compiler controls condition values to be 0/0xFFFFFFFF.
  Mode 2 avoids the problem by using PTT+Ward for routing.
"""

from __future__ import annotations
import imago_log

import time
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from controller import ImagoController

from controller import CellMapRecord
from gate_states import GS_PASS, GS_NOT, GS_XNOR, GS_LATCH_IN


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

    Holds dispatch decisions for a program or component. Volatile:
    rows can be added, updated, or removed at runtime.

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
        Returns None if either name is not found in Shore.
        """
        entry_true  = shore.lookup(name_true)
        entry_false = shore.lookup(name_false)

        if entry_true is None:
            imago_log.info(f"[BRANCH] add_from_shore: '{name_true}' not found in Shore")
            return None
        if entry_false is None:
            imago_log.info(f"[BRANCH] add_from_shore: '{name_false}' not found in Shore")
            return None

        addr_true  = entry_true.resolve_address()  or 0
        addr_false = entry_false.resolve_address() or 0

        row = self.add(label, a, b, addr_true, addr_false)
        row.__dict__['_shore_name_true']  = name_true
        row.__dict__['_shore_name_false'] = name_false
        return row

    def refresh_from_shore(self, shore) -> int:
        """
        Update all rows added via add_from_shore() with current Shore addresses.
        Returns count of rows updated.
        """
        updated = 0
        for row in self._rows.values():
            name_true  = row.__dict__.get('_shore_name_true')
            name_false = row.__dict__.get('_shore_name_false')
            if name_true is None and name_false is None:
                continue
            changed = False
            if name_true:
                entry = shore.lookup(name_true)
                if entry:
                    new_addr = entry.resolve_address() or 0
                    if new_addr != row.addr_true:
                        row.addr_true = new_addr; changed = True
            if name_false:
                entry = shore.lookup(name_false)
                if entry:
                    new_addr = entry.resolve_address() or 0
                    if new_addr != row.addr_false:
                        row.addr_false = new_addr; changed = True
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
    Comparison cell cluster for PTT-based dispatch (Mode 2).

    Two cells:
      cell_a  (XNOR + latch_in): holds A in a_data. B arrives as trigger.
              Output: 0xFFFFFFFF if A==B, ~(A^B) if A!=B.
              Fires result to ptt_addr.
      cell_b  (XNOR + latch_in): optional second comparator (for different B).

    After cell_a fires, its output reaches ptt_addr. The Ward handler
    registered on ptt_addr receives 0xFFFFFFFF (equal) or partial (not equal),
    and issues CMD_RELEASE/CMD_FREEZE to the appropriate regions.

    This is clean and correct: no AND-gate issue, no address corruption.
    The condition result IS the data; Ward interprets it.

    Lock/load/run protocol:
      freeze → preload A into cell_a → thaw → send B → Ward dispatches
    """

    # Equal condition value (silicon-confirmed: XNOR(A,A) = 0xFFFFFFFF)
    RESULT_EQUAL    = 0xFFFFFFFF
    RESULT_NOTEQUAL = 0           # any non-0xFFFFFFFF value means not-equal

    def __init__(self,
                 region_id:     str,
                 cell_a_in:     int,
                 ptt_addr:      int,
                 cell_addresses: list[int]):
        self.region_id      = region_id
        self.cell_a_in      = cell_a_in   # send A here (first arrival = preload)
                                          # send B here (second arrival = trigger)
        self.ptt_addr       = ptt_addr    # XNOR result fires here → Ward
        self.cell_addresses = cell_addresses
        self._current_row: Optional[DataRow] = None
        self._true_region:  Optional[str]    = None
        self._false_region: Optional[str]    = None

    @classmethod
    def build(cls, ctrl: "ImagoController",
              ptt_addr: int,
              name: str = "branch") -> "BranchPoint":
        """
        Build a BranchPoint — one XNOR+latch_in cell.

        ptt_addr: PTT bus address where XNOR result fires.
                  Ward handler registered on this address interprets
                  0xFFFFFFFF as equal and dispatches accordingly.
        """
        from ir import AddressAllocator
        alloc = AddressAllocator()
        a_in = alloc.alloc()

        records = [
            # XNOR + latch_in: A preloaded as a_data, B is trigger.
            # Fires 0xFFFFFFFF to ptt_addr when equal, ~(A^B) when not.
            CellMapRecord(GS_XNOR | GS_LATCH_IN,
                          input_address=a_in,
                          output_address=ptt_addr),
        ]

        rid = ctrl.load_map(records, name)
        if rid is None:
            raise RuntimeError(f"BranchPoint.build: load_map failed for '{name}'")

        ctrl.freeze(region_id=rid)

        bp = cls(
            region_id      = rid,
            cell_a_in      = a_in,
            ptt_addr       = ptt_addr,
            cell_addresses = ctrl._regions[rid].cell_addresses,
        )
        imago_log.info(f"[BRANCH] BranchPoint '{name}' built — "
              f"1 cell, ptt={ptt_addr:#x}, region {rid}")
        return bp

    def bind_regions(self, true_region: str, false_region: str) -> None:
        """
        Bind this BranchPoint to Ward-managed regions.
        When equal (result=0xFFFFFFFF): release true_region, freeze false_region.
        When not equal: release false_region, freeze true_region.
        Ward handler uses these to dispatch correctly.
        """
        self._true_region  = true_region
        self._false_region = false_region

    def load_row(self, row: DataRow, ctrl: "ImagoController") -> None:
        """
        Preload A for the next comparison.

        Lock/load/run:
          1. freeze  — disarm cell
          2. preload — set a_data = row.a
          3. thaw    — arm cell (send B to trigger)
        """
        ctrl.freeze(region_id=self.region_id)

        # Clear stale state
        for phys_addr in self.cell_addresses:
            cell = ctrl.array.cells.get(phys_addr)
            if cell is not None:
                cell.a_data      = 0
                cell.a_arrived   = False
                cell._output_buf = None
        ctrl.array.bus.clear()
        ctrl.array._carry.clear()
        ctrl.array._injected.clear()

        # Preload A directly into a_data — target by output_address.
        # The XNOR cell writes to ptt_addr. Find it by output_address.
        # Preloaded latch pattern: a_data=A, a_arrived=True.
        # B arrives at input_address → XNOR(A,B) fires immediately.
        cell = next((c for c in ctrl.array.cells.values()
                     if c.output_address == self.ptt_addr), None)
        if cell is not None:
            cell.a_data    = row.a & 0xFFFFFFFF
            cell.a_arrived = True

        ctrl.thaw(region_id=self.region_id)
        self._current_row = row
        imago_log.info(f"[BRANCH] Loaded '{row.label}': a={row.a:#x} b={row.b:#x} "
              f"true→{row.addr_true:#x} false→{row.addr_false:#x}")

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
                        name_true: str, name_false: str,
                        label: str = "shore_route") -> bool:
        """
        Load routing from Shore bridge addresses.
        Returns True on success, False if either name not found.
        """
        entry_true  = shore.lookup(name_true)
        entry_false = shore.lookup(name_false)
        if entry_true is None:
            imago_log.info(f"[BRANCH] load_from_shore: '{name_true}' not found")
            return False
        if entry_false is None:
            imago_log.info(f"[BRANCH] load_from_shore: '{name_false}' not found")
            return False
        self.load_row(
            DataRow(label=label, a=a, b=b,
                    addr_true=entry_true.resolve_address() or 0,
                    addr_false=entry_false.resolve_address() or 0),
            ctrl
        )
        return True

    def dispatch(self, result: int, ctrl: "ImagoController") -> str:
        """
        Ward calls this with the PTT result value.
        Returns 'true' or 'false' and releases/freezes bound regions.
        result=0xFFFFFFFF means equal (true branch).
        """
        if result == self.RESULT_EQUAL:
            branch = 'true'
            if self._true_region:
                ctrl.thaw(region_id=self._true_region)
            if self._false_region:
                ctrl.freeze(region_id=self._false_region)
        else:
            branch = 'false'
            if self._false_region:
                ctrl.thaw(region_id=self._false_region)
            if self._true_region:
                ctrl.freeze(region_id=self._true_region)
        imago_log.info(f"[BRANCH] Dispatch: result={result:#010x} → {branch} branch")
        return branch

    def freeze(self, ctrl: "ImagoController") -> int:
        return ctrl.freeze(region_id=self.region_id)

    def thaw(self, ctrl: "ImagoController") -> int:
        return ctrl.thaw(region_id=self.region_id)

    @property
    def current_row(self) -> Optional[DataRow]:
        return self._current_row

    def status(self) -> dict:
        return {
            "region_id":    self.region_id,
            "cell_a_in":    hex(self.cell_a_in),
            "ptt_addr":     hex(self.ptt_addr),
            "true_region":  self._true_region,
            "false_region": self._false_region,
            "total_cells":  len(self.cell_addresses),
            "current_row":  self._current_row.to_dict() if self._current_row else None,
        }

    def __repr__(self) -> str:
        row = self._current_row
        loaded = f"row='{row.label}'" if row else "unloaded"
        return f"BranchPoint(region={self.region_id} {loaded} ptt={self.ptt_addr:#x})"
