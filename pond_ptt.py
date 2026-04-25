"""
pond_ptt.py -- Pond Translation Table (PTT)

The PTT is a directory living at offset 0 of every Pond. It maps logical
indices (0-2047, fitting in an 11-bit CONFIG packet field) to absolute cell
addresses anywhere in the 32-bit array address space.

This solves three problems at once:

  1. Address range -- CONFIG packets carry 11-bit offsets (0-2047). The PTT
     makes these indices rather than offsets, so a Pond can contain cells
     at any absolute address regardless of size.

  2. Discovery -- Cast/Ripple no longer hunts every corner of the array.
     The PTT IS the Pond manifest. One query gives a complete inventory.

  3. Ward monitoring -- the Ward watches the PTT status column rather than
     scanning individual cells. Anomalies surface immediately.

Two PTT modes
=============

STATIC (Program Pond -- set and forget):
  PTT is built once at first load, frozen with the Pond snapshot.
  Restored cheaply on every subsequent boot -- no rebuild needed.
  The freeze/snapshot captures full PTT state. The frozen Pond IS the
  compiled program.

INCREMENTAL (Workspace Pond -- volatile, dynamic):
  PTT is updated as work happens -- document loaded, paragraph added,
  section deleted. Each change is a timestamped PTT event.
  These events are the raw material for the document history log.
  The Ward has higher churn tolerance for Workspace PTTs.

Entry lifecycle
===============

  RESERVED -> LOADING -> IDLE -> WAITING -> ACTIVE -> COMPLETING -> RESERVED
                                  ?          ?
                               FAULTED    FAULTED

  RESERVED   -- slot allocated, sentry cell exists but disarmed
  LOADING    -- cells being written to array (compiler one-shot write)
  IDLE       -- cells loaded, sentry armed but not yet invoked
  WAITING    -- first input received, sentry now ticking PTT address
  ACTIVE     -- executing and ticking (Ward monitors staleness here only)
  COMPLETING -- output written cleanly, sentry disarming
  FAULTED    -- Ward detected stall during ACTIVE (ticking stopped, no output)

The key distinction: staleness is only checked in ACTIVE state.
IDLE and WAITING are silent by design -- silence is correct there.
The sentry cell transitions IDLE->WAITING on first input arrival,
then ACTIVE->COMPLETING when the tile's output address is written.

Sentry cell (one cell per tile, emitted by compiler):
  input_address  = tile's primary input address
  output_address = this tile's PTT bus address (reserved range)
  gate_state     = GS_SENTRY (GS_LATCH | LOOP_MODE | GS_PASS)

  Phase 1 (IDLE):    watching input_address, not firing
  Phase 2 (WAITING->ACTIVE): first input arrives -> fires to PTT address,
                             LOOP_MODE keeps it ticking every cycle
  Phase 3 (COMPLETING): tile output written -> Ward sees output, clears sentry

PTT bus address range:
  0xFFE00000 - 0xFFFFFFFF  (2M addresses -- 2,097,152 possible entries)
  Each PTT entry has one dedicated bus address in this range.
  Sentry cells write to these addresses. Ward watches them.
  Normal compute cells never use this range.

Event log
=========
Every PTT state change emits a PttEvent. For Workspace Ponds these events
form the document history log -- a complete, ordered record of every change
to the working data. The log is written incrementally, never rebuilt from
scratch. Replay the log to reconstruct any past state.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, Callable
from pond_types import SCOPE_LOCAL, SCOPE_SHORE, SCOPE_EXTENDED


# -- Entry types ---------------------------------------------------------------

TYPE_CELL           = 0   # Individual compute cell
TYPE_TILE_IN        = 1   # Tile input port
TYPE_TILE_OUT       = 2   # Tile output port
TYPE_BRIDGE         = 3   # Bridge cell (Pond boundary) — generic
TYPE_BRIDGE_INBOUND = 7   # INBOUND bridge — carries data into pond
TYPE_BRIDGE_OUTBOUND= 8   # OUTBOUND bridge — carries data out of pond
TYPE_BRIDGE_MONITOR = 9   # MONITOR bridge — observes bus utilisation
TYPE_BRIDGE_LOG     = 10  # LOG bridge — tap for denied/capture events
TYPE_STORAGE        = 4   # Storage/latch cell
TYPE_WORKSPACE      = 5   # Workspace data cell (volatile Pond)
TYPE_SENTRY         = 6   # Sentry/watcher cell -- one per tile, updates PTT

ENTRY_TYPES = {
    TYPE_CELL:            "CELL",
    TYPE_TILE_IN:         "TILE_IN",
    TYPE_TILE_OUT:        "TILE_OUT",
    TYPE_BRIDGE:          "BRIDGE",
    TYPE_BRIDGE_INBOUND:  "BRIDGE_INBOUND",
    TYPE_BRIDGE_OUTBOUND: "BRIDGE_OUTBOUND",
    TYPE_BRIDGE_MONITOR:  "BRIDGE_MONITOR",
    TYPE_BRIDGE_LOG:      "BRIDGE_LOG",
    TYPE_STORAGE:         "STORAGE",
    TYPE_WORKSPACE:       "WORKSPACE",
    TYPE_SENTRY:          "SENTRY",
}

# Staleness thresholds by entry type (seconds).
# Bridges are always-on infrastructure -- longer thresholds than compute tiles.
# Only applies to ACTIVE entries -- IDLE and WAITING are never flagged stale.
STALENESS_DEFAULTS = {
    TYPE_CELL:            5.0,
    TYPE_TILE_IN:         5.0,
    TYPE_TILE_OUT:        5.0,
    TYPE_BRIDGE:          30.0,
    TYPE_BRIDGE_INBOUND:  30.0,
    TYPE_BRIDGE_OUTBOUND: 30.0,
    TYPE_BRIDGE_MONITOR:  30.0,
    TYPE_BRIDGE_LOG:      60.0,
    TYPE_STORAGE:         60.0,
    TYPE_WORKSPACE:       10.0,
    TYPE_SENTRY:          5.0,
}

# -- Entry status --------------------------------------------------------------

STATUS_RESERVED   = 0   # Slot allocated, sentry disarmed
STATUS_LOADING    = 1   # Cells being written to array
STATUS_IDLE       = 2   # Cells loaded, not yet invoked
STATUS_WAITING    = 3   # First input received, sentry ticking
STATUS_ACTIVE     = 4   # Executing and ticking (staleness monitored)
STATUS_COMPLETING = 5   # Output written cleanly, sentry disarming
STATUS_FAULTED    = 6   # Ward detected stall (ACTIVE -> no output)

STATUS_NAMES = {
    STATUS_RESERVED:   "RESERVED",
    STATUS_LOADING:    "LOADING",
    STATUS_IDLE:       "IDLE",
    STATUS_WAITING:    "WAITING",
    STATUS_ACTIVE:     "ACTIVE",
    STATUS_COMPLETING: "COMPLETING",
    STATUS_FAULTED:    "FAULTED",
}

# Valid status transitions
VALID_TRANSITIONS = {
    STATUS_RESERVED:   (STATUS_LOADING,),
    STATUS_LOADING:    (STATUS_IDLE,     STATUS_FAULTED),
    STATUS_IDLE:       (STATUS_WAITING,  STATUS_FAULTED, STATUS_RESERVED),
    STATUS_WAITING:    (STATUS_ACTIVE,   STATUS_FAULTED),
    STATUS_ACTIVE:     (STATUS_COMPLETING, STATUS_FAULTED, STATUS_IDLE),
    STATUS_COMPLETING: (STATUS_IDLE,     STATUS_RESERVED),
    STATUS_FAULTED:    (STATUS_RESERVED,),
}

# -- PTT bus address range ------------------------------------------------------
# Sentry cells write to this reserved range. Normal compute cells never use it.
# The Ward watches writes to this range to track per-tile liveness.
# 0xFFE00000 - 0xFFFFFFFF = 2,097,152 possible PTT addresses
PTT_BUS_BASE = 0xFFE00000   # Start of PTT bus address range
PTT_BUS_TOP  = 0xFFFFFFFF   # End of PTT bus address range

# Values written by sentry cells to PTT bus addresses -- encodes state
PTT_TICK_WAITING    = 0x00000001  # Sentry firing: tile invoked, in progress
PTT_TICK_ACTIVE     = 0x00000002  # Sentry firing: tile executing
PTT_TICK_COMPLETING = 0x00000003  # Sentry firing: tile output written
PTT_TICK_LOADING    = 0x000000FF  # One-shot: compiler marking tile loading
PTT_TICK_IDLE       = 0x0000FF00  # One-shot: tile loaded and ready

def ptt_bus_address(ptt_index: int) -> int:
    """Return the dedicated bus address for a PTT entry sentry cell.
    Each PTT index maps to one address in the reserved PTT range.
    """
    return PTT_BUS_BASE + (ptt_index & 0x1FFFFF)

def is_ptt_bus_address(addr: int) -> bool:
    """Return True if addr falls in the reserved PTT bus address range."""
    return PTT_BUS_BASE <= addr <= PTT_BUS_TOP


# -- PTT entry -----------------------------------------------------------------

@dataclass
class PttEntry:
    """
    One PTT entry -- maps a logical index to a cell in the array.

    index:            logical index (0-2047), used in CONFIG packet offset field
    absolute_address: real bus address of this cell
    entry_type:       what kind of cell this is
    status:           lifecycle state
    notify_on_active: if True, fire a PttEvent when status -> ACTIVE
    label:            human-readable name (tile name, bridge role, etc.)
    metadata:         arbitrary dict for Ward/Shore/COMPANION use
    """
    index:            int
    absolute_address: int             = 0
    entry_type:       int             = TYPE_CELL
    status:           int             = STATUS_RESERVED
    notify_on_active: bool            = True
    label:            str             = ""
    scope:            str             = SCOPE_LOCAL
    object_id:        int             = 0
    metadata:         dict            = field(default_factory=dict)
    created_at:       float           = field(default_factory=time.time)
    updated_at:       float           = field(default_factory=time.time)

    # Sentry cell fields
    sentry_address:       int   = 0     # PTT bus address this sentry writes to
    staleness_threshold:  float = 5.0   # Seconds before ACTIVE->FAULTED
                                        # Override per tile type:
                                        #   fast arithmetic: 0.1s
                                        #   IO/storage:      30.0s
                                        #   AI inference:    120.0s
    last_tick_value:      int   = 0     # Last value written by sentry cell
    tick_count:           int   = 0     # Total sentry ticks received

    @property
    def type_name(self) -> str:
        return ENTRY_TYPES.get(self.entry_type, f"TYPE_{self.entry_type}")

    @property
    def status_name(self) -> str:
        return STATUS_NAMES.get(self.status, f"STATUS_{self.status}")

    @property
    def is_active(self) -> bool:
        return self.status in (STATUS_WAITING, STATUS_ACTIVE, STATUS_COMPLETING)

    @property
    def is_available(self) -> bool:
        return self.status in (STATUS_IDLE, STATUS_WAITING,
                               STATUS_ACTIVE, STATUS_COMPLETING)

    @property
    def is_stale(self) -> bool:
        """True if ACTIVE and updated_at is older than staleness_threshold."""
        if self.status != STATUS_ACTIVE:
            return False
        return (time.time() - self.updated_at) > self.staleness_threshold

    def to_dict(self) -> dict:
        return {
            "index":               self.index,
            "absolute_address":    hex(self.absolute_address),
            "sentry_address":      hex(self.sentry_address),
            "scope":               self.scope,
            "object_id":           self.object_id,
            "type":                self.type_name,
            "status":              self.status_name,
            "label":               self.label,
            "notify_on_active":    self.notify_on_active,
            "updated_at":          self.updated_at,
            "staleness_threshold": self.staleness_threshold,
            "tick_count":          self.tick_count,
            "is_stale":            self.is_stale,
        }


# -- PTT event -----------------------------------------------------------------

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
                f"{old}->{new} addr=0x{self.address:08X} '{self.label}'")


# -- PTT -----------------------------------------------------------------------

class PondPTT:
    """
    Pond Translation Table.

    Maps logical indices (11-bit CONFIG packet offsets) to absolute cell
    addresses. Supports two modes:

      STATIC      -- built once, frozen with Pond snapshot (Program Pond)
      INCREMENTAL -- updated as work happens (Workspace Pond)

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

        # Transition to ACTIVE when cell arms -- triggers notification
        ptt.transition(idx, STATUS_ACTIVE)

        # Resolve a waiting cell's output address
        addr = ptt.resolve(idx)  # returns absolute_address

        # Workspace PTT -- incremental update
        ptt_ws = PondPTT('ws_0001', PondPTT.INCREMENTAL)
        idx = ptt_ws.register(0x00600040, TYPE_WORKSPACE, label='para_7')
        # events are logged automatically
    """

    STATIC      = "STATIC"       # Program Pond -- built once, frozen
    INCREMENTAL = "INCREMENTAL"  # Workspace Pond -- updated as work happens

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

        # The table -- index -> PttEntry
        self._entries:  dict[int, PttEntry] = {}
        self._next_idx: int = 0

        # Event log -- chronological list of all PTT changes
        # For Workspace Ponds this IS the document history
        self._log: list[PttEvent] = []

        # Index of entries waiting for notification when they go ACTIVE
        # index -> list of callbacks
        self._waiters: dict[int, list[Callable[[PttEntry], None]]] = {}

        # Frozen flag -- once frozen, no mutations allowed (STATIC mode)
        self._frozen = False

    # -- Registration ----------------------------------------------------------

    def register(self, address: int,
                 entry_type: int = TYPE_CELL,
                 label: str = "",
                 notify_on_active: bool = True,
                 metadata: Optional[dict] = None) -> int:
        """
        Register a new entry in the PTT.

        Returns the logical index assigned to this entry (0-2047).
        This index is what goes in the CONFIG packet output_offset field.

        For Workspace Ponds, each call emits a REGISTERED event to the log.
        """
        if self._frozen:
            raise RuntimeError(
                f'PTT {self.pond_id!r} is frozen -- no new registrations')

        if len(self._entries) >= self.MAX_ENTRIES:
            raise OverflowError(
                f'PTT {self.pond_id!r} is full ({self.MAX_ENTRIES} entries)')

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

    # -- Status transitions ----------------------------------------------------

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
                  f"{entry.status_name} -> {STATUS_NAMES.get(new_status, '?')}")
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

    # -- Address resolution ----------------------------------------------------

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
        if it is already active, or gets called back when it activates.
        Used by Shore when resolving connections after ROUTE_UPDATE.

        Returns the address if already active, None if waiting.
        """
        entry = self._entries.get(index)
        if entry is None:
            return None
        if entry.is_active:
            callback(entry)
            return entry.absolute_address
        # Register as waiter -- will be called when entry -> ACTIVE
        self._waiters.setdefault(index, []).append(callback)
        return None

    def update_address(self, index: int, new_address: int) -> bool:
        """
        Update the absolute address for a PTT entry.

        Called when a Pond migrates -- the PTT indices stay stable,
        but the absolute addresses behind them change.
        Emits a RESOLVED event.
        """
        if self._frozen:
            raise RuntimeError(f'PTT {self.pond_id!r} is frozen')

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
            raise RuntimeError(f'PTT {self.pond_id!r} is frozen')

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

        # Remove from table -- slot is now free
        del self._entries[index]
        # Make this index the next one offered
        self._next_idx = index
        return True

    # -- Sentry / liveness -----------------------------------------------------

    def register_sentry(self, index: int,
                        staleness_threshold: float = 5.0) -> int:
        """
        Assign a PTT bus address to this entry sentry cell.

        Called by the compiler when emitting a sentry cell for a tile.
        Returns the sentry_address the sentry cell should write to.

        staleness_threshold: seconds before ACTIVE entry is considered
        stale and transitioned to FAULTED. Override per tile type:
          fast arithmetic tiles:  0.1 - 1.0s
          IO / storage tiles:     10.0 - 30.0s
          AI inference tiles:     60.0 - 120.0s
        """
        entry = self._entries.get(index)
        if entry is None:
            return 0
        addr = ptt_bus_address(index)
        entry.sentry_address      = addr
        entry.staleness_threshold = staleness_threshold
        entry.updated_at          = time.time()
        return addr

    def touch(self, index: int) -> None:
        """
        Refresh the updated_at timestamp for a PTT entry.
        Called when the sentry cell fires -- confirms the tile is alive.
        Does not change status.
        """
        entry = self._entries.get(index)
        if entry is not None:
            entry.updated_at = time.time()
            entry.tick_count += 1

    def bus_tick(self, address: int, value: int) -> bool:
        """
        Called when a cell fires at a PTT bus address (0xFFE00000+).

        Decodes the value to determine the state transition:
          PTT_TICK_WAITING    -> transition to WAITING (first invocation)
          PTT_TICK_ACTIVE     -> touch() only (keep-alive tick)
          PTT_TICK_COMPLETING -> transition to COMPLETING
          PTT_TICK_LOADING    -> transition to LOADING
          PTT_TICK_IDLE       -> transition to IDLE

        Returns True if address was a known sentry address, False otherwise.
        """
        if not is_ptt_bus_address(address):
            return False

        # Find entry by sentry_address
        entry = None
        for e in self._entries.values():
            if e.sentry_address == address:
                entry = e
                break
        if entry is None:
            return False

        entry.last_tick_value = value

        if value == PTT_TICK_ACTIVE:
            # Keep-alive tick -- just touch
            self.touch(entry.index)

        elif value == PTT_TICK_WAITING:
            if entry.status == STATUS_IDLE:
                self.transition(entry.index, STATUS_WAITING)
            elif entry.status == STATUS_WAITING:
                self.touch(entry.index)

        elif value == PTT_TICK_COMPLETING:
            if entry.status in (STATUS_ACTIVE, STATUS_WAITING):
                self.transition(entry.index, STATUS_COMPLETING)

        elif value == PTT_TICK_LOADING:
            if entry.status == STATUS_RESERVED:
                self.transition(entry.index, STATUS_LOADING)

        elif value == PTT_TICK_IDLE:
            if entry.status == STATUS_LOADING:
                self.transition(entry.index, STATUS_IDLE)
            elif entry.status == STATUS_COMPLETING:
                self.transition(entry.index, STATUS_IDLE)

        return True

    def check_staleness(self) -> list[int]:
        """
        Scan all ACTIVE entries. Transition any that are stale to FAULTED.

        Staleness = (now - updated_at) > staleness_threshold.
        Only ACTIVE entries are checked -- IDLE and WAITING are silent
        by design and should never be flagged.

        Called by Ward on each tick. Returns list of newly faulted indices.
        """
        faulted = []
        for entry in list(self._entries.values()):
            if entry.is_stale:
                self.transition(entry.index, STATUS_FAULTED,
                                metadata={"reason": "sentry_timeout",
                                          "age":    time.time() - entry.updated_at,
                                          "threshold": entry.staleness_threshold})
                faulted.append(entry.index)
        return faulted

    # -- Freeze / restore ------------------------------------------------------

    def freeze(self) -> dict:
        """
        Freeze the PTT and return its full snapshot.

        For STATIC (Program Pond) PTTs: marks frozen -- no further mutations.
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

        For STATIC Ponds this is the fast path -- no rebuild, no DMA,
        no connection resolution. The PTT is fully populated immediately.
        The frozen Pond IS the program: restore snapshot -> armed -> running.
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

    # -- Query -----------------------------------------------------------------

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

    # -- Event log -------------------------------------------------------------

    @property
    def log(self) -> list[PttEvent]:
        """Full event log -- document history for Workspace Ponds."""
        return list(self._log)

    def log_since(self, timestamp: float) -> list[PttEvent]:
        """Events after the given timestamp -- incremental sync."""
        return [e for e in self._log if e.timestamp > timestamp]

    def _emit(self, event: PttEvent) -> None:
        self._log.append(event)
        if self._on_event:
            self._on_event(event)

    # -- Status ----------------------------------------------------------------

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
        lines = [f'PTT {self.pond_id!r} [{self.mode}] '
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
