"""
branch.py — BranchPoint and DataTable

Runtime dispatch mechanism for the Imago spatial computing fabric.

Architecture (2026-05-19)
=========================

Two compiler modes for branching:

MODE 1 — Compiled tree (small decisions, inlined if/else)
  Both branches fully compiled into cells simultaneously.
  Condition gates each branch with AND(condition, data).
  Emitted by run_compiled_function — not by BranchPoint.
  Cost: proportional to branch_size × 2.

MODE 2 — PTT dispatch (program tile, loops, larger decisions)  ← THIS FILE
  BranchPoint builds a comparison cell cluster.
  XNOR result fires to ptt_addr (0xFFFFFFFF=equal, 0=not equal).
  Ward (or test harness) reads result and routes to addr_true/addr_false.
  Cost: 1 XNOR cell + caller-side routing.

  Cell layout (1 cell):
    cell_xnor  XNOR + latch_in — holds A (preloaded), triggered by B.
                                  Output: 0xFFFFFFFF (equal) or 0 (not equal).
    ptt_addr   — where result fires. Ward dispatches from here.

  Lock/load/run protocol:
    freeze → preload A into cell_xnor → thaw → send B → result at ptt_addr.

DataTable
=========
A named collection of DataRows — one per dispatch decision.
Each row holds: operand A, comparand B, true destination, false destination.
"""

from __future__ import annotations
import imago_log

import time
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from controller import ImagoController

from controller import CellMapRecord
from gate_states import GS_XNOR, GS_LATCH_IN


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
    """

    def __init__(self, name: str):
        self.name   = name
        self._rows: dict[str, DataRow] = {}
        self._order: list[str] = []

    def add(self, label: str, a: int, b: int,
            addr_true: int, addr_false: int) -> DataRow:
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

    One cell:
      cell_xnor (XNOR + latch_in): holds A in a_data. B arrives as trigger.
                Output: 0xFFFFFFFF if A==B, 0 if A!=B.
                Fires result to ptt_addr.

    After cell_xnor fires, Ward (or test harness) reads result at ptt_addr:
      0xFFFFFFFF → equal  → release true_region, freeze false_region
      0          → not equal → release false_region, freeze true_region

    Lock/load/run:
      freeze → preload A → thaw → send B → result at ptt_addr → dispatch

    MODE 2 hook: BranchPoint.build() is the entry point for PTT dispatch.
    Mode 1 (compiled tree) uses run_compiled_function — does not use this class.
    """

    RESULT_EQUAL    = 0xFFFFFFFF
    RESULT_NOTEQUAL = 0

    def __init__(self,
                 region_id:      str,
                 cell_a_in:      int,
                 ptt_addr:       int,
                 cell_addresses: list[int],
                 _addr_true:     int = 0,
                 _addr_false:    int = 0):
        self.region_id      = region_id
        self.cell_a_in      = cell_a_in
        self.ptt_addr       = ptt_addr
        self.cell_addresses = cell_addresses
        self._current_row:  Optional[DataRow] = None
        self._true_region:  Optional[str]     = None
        self._false_region: Optional[str]     = None
        # Routing addresses — updated by load_row, used by dispatch()
        self._addr_true     = _addr_true
        self._addr_false    = _addr_false

    @classmethod
    def build(cls, ctrl: "ImagoController",
              name: str = "branch") -> "BranchPoint":
        """
        Build a BranchPoint — allocates all addresses internally.

        Returns a BranchPoint ready for load_row() calls.
        Call bind_regions() to attach Ward-managed regions.

        MODE 2 hook: ptt_addr is where the Ward handler listens.
        """
        from ir import AddressAllocator
        alloc = AddressAllocator()
        a_in     = alloc.alloc()
        ptt_addr = alloc.alloc()

        records = [
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
        self._true_region  = true_region
        self._false_region = false_region

    def load_row(self, row: DataRow, ctrl: "ImagoController") -> None:
        """
        Preload A and set routing addresses for the next comparison.
        Lock/load/run: freeze → set a_data → thaw.
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

        # Preload A into the XNOR cell's a_data
        cell = next((c for c in ctrl.array.cells.values()
                     if c.output_address == self.ptt_addr), None)
        if cell is not None:
            cell.a_data    = row.a & 0xFFFFFFFF
            cell.a_arrived = True

        # Store routing addresses for dispatch()
        self._addr_true  = row.addr_true
        self._addr_false = row.addr_false

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

    def run(self, ctrl: "ImagoController",
            b: int, max_ticks: int = 30) -> str:
        """
        Inject B, run until result fires, dispatch and return 'true'/'false'.
        For use without a Ward — test harness and simple programs.
        """
        ctrl.array._injected[self.cell_a_in] = (b & 0xFFFFFFFF, 0)
        for _ in range(max_ticks):
            ctrl.array.tick()
            if self.ptt_addr in ctrl.array.bus:
                result = ctrl.array.bus[self.ptt_addr][0]
                return self.dispatch(result, ctrl)
        return 'timeout'

    def dispatch(self, result: int, ctrl: "ImagoController") -> str:
        """
        Called with PTT result (0xFFFFFFFF=equal, 0=not-equal).
        Injects a marker value at addr_true or addr_false so callers
        can observe which path was taken on the bus.
        Returns 'true' or 'false'.
        """
        if result == self.RESULT_EQUAL:
            branch = 'true'
            ctrl.array._injected[self._addr_true] = (self.RESULT_EQUAL, 0)
            if self._true_region:
                ctrl.thaw(region_id=self._true_region)
            if self._false_region:
                ctrl.freeze(region_id=self._false_region)
        else:
            branch = 'false'
            ctrl.array._injected[self._addr_false] = (self.RESULT_NOTEQUAL + 1, 0)
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
