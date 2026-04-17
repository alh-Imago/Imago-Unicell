"""
pond_ptt.py — Pond Translation Table (PTT)

The PTT is a directory living at offset 0 of every Pond. It maps logical
indices (0-2047, fitting in an 11-bit CONFIG packet field) to absolute cell
addresses anywhere in the 32-bit array address space.

This solves three problems at once:

  1. Address range — CONFIG packets carry 11-bit offsets (0-2047). The PTT
     makes these indices rather than offsets, so a Pond can contain cells
     at any absolute address regardless of size.

  2. Discovery — Cast/Ripple no longer hunts every corner of the array.
     The PTT IS the Pond manifest. One query gives a complete inventory.

  3. Ward monitoring — the Ward watches the PTT status column rather than
     scanning individual cells. Anomalies surface immediately.

Two PTT modes
=============

STATIC (Program Pond — set and forget):
  PTT is built once at first load, frozen with the Pond snapshot.
  Restored cheaply on every subsequent boot — no rebuild needed.
  The freeze/snapshot captures full PTT state. The frozen Pond IS the
  compiled program.

INCREMENTAL (Workspace Pond — volatile, dynamic):
  PTT is updated as work happens — document loaded, paragraph added,
  section deleted. Each change is a timestamped PTT event.
  These events are the raw material for the document history log.
  The Ward has higher churn tolerance for Workspace PTTs.

Entry lifecycle
===============

  RESERVED → LOADING → IDLE → ACTIVE → FAULTED
                ↑                ↓
           DMA/CONFIG        Ward detects
           writing cells     anomaly

PTT entry (40 bits):
  absolute_address (32 bits)
  type             ( 4 bits): CELL/TILE_IN/TILE_OUT/BRIDGE/STORAGE/WORKSPACE
  status           ( 3 bits): RESERVED/LOADING/IDLE/ACTIVE/FAULTED
  notify_on_active ( 1 bit):  fire event when → ACTIVE

Event log
=========
Every PTT state change emits a PttEvent. For Workspace Ponds these events
form the document history log — a complete, ordered record of every change
to the working data. The log is written incrementally, never rebuilt from
scratch. Replay the log to reconstruct any past state.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, Callable
from pond_types import SCOPE_LOCAL, SCOPE_SHORE, SCOPE_EXTENDED


# ── Entry types ───────────────────────────────────────────────────────────────

TYPE_CELL       = 0   # Individual compute cell
TYPE_TILE_IN    = 1   # Tile input port
TYPE_TILE_OUT   = 2   # Tile output port
TYPE_BRIDGE     = 3   # Bridge cell (Pond boundary)
TYPE_STORAGE    = 4   # Storage/latch cell
TYPE_WORKSPACE  = 5   # Workspace data cell (volatile Pond)

ENTRY_TYPES = {
    TYPE_CELL:      "CELL",
    TYPE_TILE_IN:   "TILE_IN",
    TYPE_TILE_OUT:  "TILE_OUT",
    TYPE_BRIDGE:    "BRIDGE",
    TYPE_STORAGE:   "STORAGE",
    TYPE_WORKSPACE: "WORKSPACE",
}

# ── Entry status ──────────────────────────────────────────────────────────────

STATUS_RESERVED = 0   # Slot allocated, nothing loaded
STATUS_LOADING  = 1   # DMA or CONFIG packets being written
STATUS_IDLE     = 2   # Cells loaded, not yet armed
STATUS_ACTIVE   = 3   # Cells armed and firing
STATUS_FAULTED  = 4   # Ward detected anomaly

STATUS_NAMES = {
    STATUS_RESERVED: "RESERVED",
    STATUS_LOADING:  "LOADING",
    STATUS_IDLE:     "IDLE",
    STATUS_ACTIVE:   "ACTIVE",
    STATUS_FAULTED:  "FAULTED",
}

# Valid status transitions
VALID_TRANSITIONS = {
    STATUS_RESERVED: (STATUS_LOADING,),
    STATUS_LOADING:  (STATUS_IDLE,   STATUS_FAULTED),
    STATUS_IDLE:     (STATUS_ACTIVE, STATUS_FAULTED, STATUS_RESERVED),
    STATUS_ACTIVE:   (STATUS_IDLE,   STATUS_FAULTED, STATUS_RESERVED),
    STATUS_FAULTED:  (STATUS_RESERVED,),
}


# ── PTT entry ─────────────────────────────────────────────────────────────────

@dataclass
class PttEntry:
    """
    One PTT entry — maps a logical index to a cell in the array.

    index:            logical index (0-2047), used in CONFIG packet offset field
    absolute_address: real bus address of this cell
    entry_type:       what kind of cell this is
    status:           lifecycle state
    notify_on_active: if True, fire a PttEvent when status → ACTIVE
    label:            human-readable name (tile name, bridge role, etc.)
    metadata:         arbitrary dict for Ward/Shore/COMPANION use
    """
    index:            int
    absolute_address: int             = 0
    entry_type:       int             = TYPE_CELL
    status:           int             = STATUS_RESERVED
    notify_on_active: bool            = True
    label:            str             = ""
    # Object model fields — scope + 32-bit object ID
    # These sit alongside absolute_address (the flat bus address)
    # absolute_address is used by cells for communication
    # object_id is used by the OS for routing and discovery
    scope:            str             = SCOPE_LOCAL
    object_id:        int             = 0    # 32-bit ID within scope's PTT
    metadata:         dict            = field(default_factory=dict)
    created_at:       float           = field(default_factory=time.time)
    updated_at:       float           = field(default_factory=time.time)

    @property
    def type_name(self) -> str:
        return ENTRY_TYPES.get(self.entry_type, f"TYPE_{self.entry_type}")

    @property
    def status_name(self) -> str:
        return STATUS_NAMES.get(self.status, f"STATUS_{self.status}")

    @property
    def is_active(self) -> bool:
        return self.status == STATUS_ACTIVE

    @property
    def is_available(self) -> bool:
        return self.status in (STATUS_IDLE, STATUS_ACTIVE)

    def to_dict(self) -> dict:
        return {
            "index":            self.index,
            "absolute_address": hex(self.absolute_address),
            "scope":            self.scope,
            "object_id":        self.object_id,
            "type":             self.type_name,
            "status":           self.status_name,
            "label":            self.label,
            "notify_on_active": self.notify_on_active,
            "updated_at":       self.updated_at,
        }


# ── PTT event ─────────────────────────────────────────────────────────────────

@dataclass
class PttEvent:
    """
    A single PTT state-change event.

    For Workspace Ponds these events form the document history log.
    Each event is timestamped and carries the full before/after state,
    giving a complete, replayable record of every change to the Pond.

    event_type:  what happened
    index:       which PTT entry changed
    old_status:  previous status (None for new entries)
    new_status:  current status
    address:     absolute address at time of event
    label:       entry label
    pond_id:     which Pond this belongs to
    timestamp:   when the event occurred
    metadata:    extra context (document position, user action, etc.)
    """
    event_type:  str
    index:       int
    new_status:  int
    address:     int
    label:       str        = ""
    old_status:  Optional[int] = None
    pond_id:     str        = ""
    timestamp:   float      = field(default_factory=time.time)
    metadata:    dict       = field(default_factory=dict)

    # Event types
    REGISTERED   = "REGISTERED"    # new entry added
    TRANSITION   = "TRANSITION"    # status changed
    RESOLVED     = "RESOLVED"      # address written (was 0)
    RELEASED     = "RELEASED"      # entry cleared back to RESERVED
    FAULTED      = "FAULTED"       # entry faulted

    def __str__(self) -> str:
        old = STATUS_NAMES.get(self.old_status, "?") if self.old_status is not None else "NEW"
        new = STATUS_NAMES.get(self.new_status, "?")
        t   = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        return (f"[{t}] {self.event_type} PTT[{self.index}] "
                f"{old}→{new} addr=0x{self.address:08X} '{self.label}'")


# ── PTT ───────────────────────────────────────────────────────────────────────

class PondPTT:
    """
    Pond Translation Table.

    Maps logical indices (11-bit CONFIG packet offsets) to absolute cell
    addresses. Supports two modes:

      STATIC      — built once, frozen with Pond snapshot (Program Pond)
      INCREMENTAL — updated as work happens (Workspace Pond)

    Usage:
        # Create PTT for a Program Pond
        ptt = PondPTT(pond_id='pond_0001', mode=PondPTT.STATIC)

        # Register a tile's cells
        idx = ptt.register(address=0x00400040,
                           entry_type=TYPE_TILE_IN, label='INT32_ADD.input')

        # Transition to LOADING when DMA starts
        ptt.transition(idx, STATUS_LOADING)

        # Transition to IDLE when DMA completes
        ptt.transition(idx, STATUS_IDLE)

        # Transition to ACTIVE when cell arms — triggers notification
        ptt.transition(idx, STATUS_ACTIVE)

        # Resolve a waiting cell's output address
        addr = ptt.resolve(idx)  # returns absolute_address

        # Workspace PTT — incremental update
        ptt_ws = PondPTT('ws_0001', PondPTT.INCREMENTAL)
        idx = ptt_ws.register(0x00600040, TYPE_WORKSPACE, label='para_7')
        # events are logged automatically
    """

    STATIC      = "STATIC"       # Program Pond — built once, frozen
    INCREMENTAL = "INCREMENTAL"  # Workspace Pond — updated as work happens

    MAX_ENTRIES = 2048

    def __init__(self, pond_id: str,
                 mode: str = STATIC,
                 on_event: Optional[Callable[[PttEvent], None]] = None):
        """
        pond_id:   the Pond this PTT belongs to
        mode:      STATIC or INCREMENTAL
        on_event:  optional callback fired on every PTT event
                   For Workspace Ponds, wire this to the history log writer
        """
        self.pond_id   = pond_id
        self.mode      = mode
        self._on_event = on_event

        # The table — index → PttEntry
        self._entries:  dict[int, PttEntry] = {}
        self._next_idx: int = 0

        # Event log — chronological list of all PTT changes
        # For Workspace Ponds this IS the document history
        self._log: list[PttEvent] = []

        # Index of entries waiting for notification when they go ACTIVE
        # index → list of callbacks
        self._waiters: dict[int, list[Callable[[PttEntry], None]]] = {}

        # Frozen flag — once frozen, no mutations allowed (STATIC mode)
        self._frozen = False

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, address: int,
                 entry_type: int = TYPE_CELL,
                 label: str = "",
                 notify_on_active: bool = True,
                 metadata: Optional[dict] = None) -> int:
        """
        Register a new entry in the PTT.

        Returns the logical index assigned to this entry (0-2047).
        This index is what goes in the CONFIG packet's output_offset field.

        For Workspace Ponds, each call emits a REGISTERED event to the log.
        """
        if self._frozen:
            raise RuntimeError(
                f"PTT '{self.pond_id}' is frozen — no new registrations")

        if len(self._entries) >= self.MAX_ENTRIES:
            raise OverflowError(
                f"PTT '{self.pond_id}' is full ({self.MAX_ENTRIES} entries)")

        # Find next free index
        while self._next_idx in self._entries:
            self._next_idx += 1
            if self._next_idx >= self.MAX_ENTRIES:
                self._next_idx = 0

        idx = self._next_idx
        self._next_idx += 1

        entry = PttEntry(
            index            = idx,
            absolute_address = address,
            entry_type       = entry_type,
            status           = STATUS_RESERVED,
            notify_on_active = notify_on_active,
            label            = label,
            metadata         = metadata or {},
        )
        self._entries[idx] = entry

        self._emit(PttEvent(
            event_type = PttEvent.REGISTERED,
            index      = idx,
            new_status = STATUS_RESERVED,
            address    = address,
            label      = label,
            pond_id    = self.pond_id,
            metadata   = metadata or {},
        ))

        return idx

    # ── Status transitions ────────────────────────────────────────────────────

    def transition(self, index: int, new_status: int,
                   metadata: Optional[dict] = None) -> bool:
        """
        Transition a PTT entry to a new status.

        Validates the transition is legal. Emits an event.
        If new_status is ACTIVE and notify_on_active is set, fires waiters.

        Returns True on success, False if entry not found or transition invalid.
        """
        entry = self._entries.get(index)
        if entry is None:
            return False

        allowed = VALID_TRANSITIONS.get(entry.status, ())
        if new_status not in allowed:
            print(f"[PTT] Invalid transition PTT[{index}]: "
                  f"{entry.status_name} → {STATUS_NAMES.get(new_status, '?')}")
            return False

        old_status = entry.status
        entry.status     = new_status
        entry.updated_at = time.time()

        evt_type = (PttEvent.FAULTED if new_status == STATUS_FAULTED
                    else PttEvent.TRANSITION)

        self._emit(PttEvent(
            event_type = evt_type,
            index      = index,
            old_status = old_status,
            new_status = new_status,
            address    = entry.absolute_address,
            label      = entry.label,
            pond_id    = self.pond_id,
            metadata   = metadata or {},
        ))

        # Fire waiters when entry goes ACTIVE
        if new_status == STATUS_ACTIVE and entry.notify_on_active:
            for cb in self._waiters.pop(index, []):
                cb(entry)

        return True

    # ── Address resolution ────────────────────────────────────────────────────

    def resolve(self, index: int) -> Optional[int]:
        """
        Resolve a PTT index to an absolute cell address.

        Returns the address if the entry exists and is available,
        None if not found, RESERVED, or LOADING.

        This is what the CONFIG packet receiver calls to get the real
        address for an 11-bit output_offset field.
        """
        entry = self._entries.get(index)
        if entry is None or not entry.is_available:
            return None
        return entry.absolute_address

    def resolve_or_wait(self, index: int,
                        callback: Callable[[PttEntry], None]) -> Optional[int]:
        """
        Resolve a PTT index. If not yet ACTIVE, register a callback for
        when it becomes ACTIVE.

        This is the late-binding path: the caller gets the address immediately
        if it's already active, or gets called back when it activates.
        Used by Shore when resolving connections after ROUTE_UPDATE.

        Returns the address if already active, None if waiting.
        """
        entry = self._entries.get(index)
        if entry is None:
            return None
        if entry.is_active:
            callback(entry)
            return entry.absolute_address
        # Register as waiter — will be called when entry → ACTIVE
        self._waiters.setdefault(index, []).append(callback)
        return None

    def update_address(self, index: int, new_address: int) -> bool:
        """
        Update the absolute address for a PTT entry.

        Called when a Pond migrates — the PTT indices stay stable,
        but the absolute addresses behind them change.
        Emits a RESOLVED event.
        """
        if self._frozen:
            raise RuntimeError(f"PTT '{self.pond_id}' is frozen")

        entry = self._entries.get(index)
        if entry is None:
            return False

        old_addr             = entry.absolute_address
        entry.absolute_address = new_address
        entry.updated_at     = time.time()

        self._emit(PttEvent(
            event_type = PttEvent.RESOLVED,
            index      = index,
            old_status = entry.status,
            new_status = entry.status,
            address    = new_address,
            label      = entry.label,
            pond_id    = self.pond_id,
            metadata   = {"old_address": hex(old_addr),
                          "new_address": hex(new_address)},
        ))
        return True

    def release(self, index: int) -> bool:
        """
        Release a PTT entry back to RESERVED and clear its address.

        Used when a tile is unloaded from a Workspace Pond (e.g. a
        paragraph is deleted). The index slot becomes available for reuse.
        Emits a RELEASED event to the history log.
        """
        if self._frozen:
            raise RuntimeError(f"PTT '{self.pond_id}' is frozen")

        entry = self._entries.get(index)
        if entry is None:
            return False

        old_status           = entry.status
        entry.status         = STATUS_RESERVED
        entry.absolute_address = 0
        entry.updated_at     = time.time()

        self._emit(PttEvent(
            event_type = PttEvent.RELEASED,
            index      = index,
            old_status = old_status,
            new_status = STATUS_RESERVED,
            address    = 0,
            label      = entry.label,
            pond_id    = self.pond_id,
        ))

        # Remove from table — slot is now free
        del self._entries[index]
        # Make this index the next one offered
        self._next_idx = index
        return True

    # ── Freeze / restore ──────────────────────────────────────────────────────

    def freeze(self) -> dict:
        """
        Freeze the PTT and return its full snapshot.

        For STATIC (Program Pond) PTTs: marks frozen — no further mutations.
        For INCREMENTAL (Workspace Pond) PTTs: snapshot of current state,
        PTT remains mutable (workspace keeps running).

        The snapshot is stored alongside the Pond cell snapshot. Restoring
        both gives the complete Pond state with no rebuild needed.
        """
        snapshot = {
            "pond_id":  self.pond_id,
            "mode":     self.mode,
            "entries":  {str(k): v.to_dict() for k, v in self._entries.items()},
            "frozen_at": time.time(),
        }
        if self.mode == self.STATIC:
            self._frozen = True
        return snapshot

    @classmethod
    def restore(cls, snapshot: dict,
                on_event: Optional[Callable[[PttEvent], None]] = None
                ) -> "PondPTT":
        """
        Restore a PTT from a snapshot.

        For STATIC Ponds this is the fast path — no rebuild, no DMA,
        no connection resolution. The PTT is fully populated immediately.
        The frozen Pond IS the program: restore snapshot → armed → running.
        """
        ptt = cls(pond_id=snapshot["pond_id"],
                  mode=snapshot["mode"],
                  on_event=on_event)

        for idx_str, entry_dict in snapshot["entries"].items():
            idx   = int(idx_str)
            # Reverse-map type and status from names
            etype = next((k for k, v in ENTRY_TYPES.items()
                          if v == entry_dict["type"]), TYPE_CELL)
            estat = next((k for k, v in STATUS_NAMES.items()
                          if v == entry_dict["status"]), STATUS_IDLE)
            addr  = int(entry_dict["absolute_address"], 16)
            ptt._entries[idx] = PttEntry(
                index            = idx,
                absolute_address = addr,
                entry_type       = etype,
                status           = estat,
                notify_on_active = entry_dict.get("notify_on_active", True),
                label            = entry_dict.get("label", ""),
                updated_at       = entry_dict.get("updated_at", 0.0),
            )

        if snapshot["mode"] == cls.STATIC:
            ptt._frozen = True

        return ptt

    # ── Query ─────────────────────────────────────────────────────────────────

    def get(self, index: int) -> Optional[PttEntry]:
        """Return entry by index, or None."""
        return self._entries.get(index)

    def entries_by_status(self, status: int) -> list[PttEntry]:
        """Return all entries with the given status."""
        return [e for e in self._entries.values() if e.status == status]

    def entries_by_type(self, entry_type: int) -> list[PttEntry]:
        """Return all entries of the given type."""
        return [e for e in self._entries.values()
                if e.entry_type == entry_type]

    def active_count(self) -> int:
        return sum(1 for e in self._entries.values()
                   if e.status == STATUS_ACTIVE)

    def faulted_count(self) -> int:
        return sum(1 for e in self._entries.values()
                   if e.status == STATUS_FAULTED)

    # ── Event log ─────────────────────────────────────────────────────────────

    @property
    def log(self) -> list[PttEvent]:
        """Full event log — document history for Workspace Ponds."""
        return list(self._log)

    def log_since(self, timestamp: float) -> list[PttEvent]:
        """Events after the given timestamp — incremental sync."""
        return [e for e in self._log if e.timestamp > timestamp]

    def _emit(self, event: PttEvent) -> None:
        self._log.append(event)
        if self._on_event:
            self._on_event(event)

    # ── Status ────────────────────────────────────────────────────────────────

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    def status(self) -> dict:
        by_status = {}
        for s, name in STATUS_NAMES.items():
            count = sum(1 for e in self._entries.values() if e.status == s)
            if count:
                by_status[name] = count
        return {
            "pond_id":   self.pond_id,
            "mode":      self.mode,
            "frozen":    self._frozen,
            "entries":   len(self._entries),
            "capacity":  self.MAX_ENTRIES,
            "by_status": by_status,
            "log_events": len(self._log),
        }

    def dump(self) -> str:
        lines = [f"PTT '{self.pond_id}' [{self.mode}] "
                 f"{'FROZEN ' if self._frozen else ''}"
                 f"({len(self._entries)}/{self.MAX_ENTRIES} entries)"]
        for entry in sorted(self._entries.values(), key=lambda e: e.index):
            lines.append(
                f"  [{entry.index:>4d}] {entry.status_name:<8s} "
                f"{entry.type_name:<10s} "
                f"0x{entry.absolute_address:08X}  '{entry.label}'"
            )
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return (f"PondPTT('{self.pond_id}' {self.mode} "
                f"entries={len(self._entries)} "
                f"frozen={self._frozen})")
