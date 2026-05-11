"""
pond.py — Imago Pond: Shared UniCell Resource Pool

A Pond is a named, bounded region of cells within a UniCell array that
can be shared with other identities. It is the fundamental unit of the
Imago distributed resource model.

Security levels (set at creation, changeable by owner):
  OPEN    — any identity may use the Pond's cells; no whitelist checked
  PRIVATE — only whitelisted identities may use the Pond's cells
  HIDDEN  — Pond does not announce itself; only whitelisted identities
             that explicitly know its name can reach it

Pond types:
  PROCESS    — a running program or long-running service. Input arrives
               through INBOUND, results leave through OUTBOUND.
  FILE       — file data in loopback storage cells or pointer tokens to
               physical media. The bridge controls read/write access.
  PERIPHERAL — the array-side representation of a piece of hardware.
               Contains the driver logic, data format handling, and
               protocol tiles. The hardware lives outside the array.
  LIBRARY    — pre-compiled tile configurations. Feed inputs through
               the declared bridge, collect results at pipeline depth.
  BOOT       — bootstrap and FS decoder tiles. ROM only; no runtime access.
  COMPANION  — permanent anchor Pond. Structurally HIDDEN; cannot be
               dissolved except by owner command or Heritage succession.
               Coordinates the Ward population and manages Shore integrity.

Bridge cells:
  Every Pond has 2–4 logical bridge cells at its boundary. These are
  real UniCells configured as PASS gates, but with monitoring and access
  control logic layered above them at the Pond level.

  Bridge 0 (INBOUND)  — gates data entering the Pond from outside
  Bridge 1 (OUTBOUND) — gates data leaving the Pond to outside
  Bridge 2 (MONITOR)  — optional; counts emissions, tracks bandwidth
  Bridge 3 (LOG)      — optional; records every access event with
                        identity and timestamp

Resource record:
  Each Pond maintains a live resource record describing its current
  state: available cells, security level, active sessions, visit log.
  This record is what a Cast (discovery mechanism) would query.
"""

from __future__ import annotations
import imago_log

import time
import hashlib
from dataclasses import dataclass, field
from typing import Optional
from unicell_array import UniCellArray, BusSegment
from unicell import FUNCTION_LOAD_PATTERN
from controller import CellMapRecord

# ── Security levels ───────────────────────────────────────────────────────────

OPEN    = "OPEN"     # any identity admitted; no whitelist checked
PRIVATE = "PRIVATE"  # whitelist enforced; unknown identities rejected
HIDDEN  = "HIDDEN"   # not discoverable; only whitelisted identities admitted

SECURITY_LEVELS = (OPEN, PRIVATE, HIDDEN)

# ── Pond types — now defined in pond_types.py ────────────────────────────────
# Type constants imported for backwards compatibility.
# New code should import from pond_types directly.
# Register new types with pond_types.registry at startup — no changes here.

from pond_types import (
    registry    as _pond_type_registry,
    PROCESS, FILE, PERIPHERAL, LIBRARY, BOOT, COMPANION,
    WORKSPACE, DEVICE, SHORE_TYPE, FS,
    POND_TYPES,

    SCOPE_LOCAL, SCOPE_SHORE, SCOPE_EXTENDED,
)

# Backwards-compatible aliases
COMPUTE      = PROCESS
STORAGE      = FILE
TILE_LIBRARY = LIBRARY


# ── Pointer token ─────────────────────────────────────────────────────────────

import struct

# Resource type codes (8-bit)
RT_FILE       = 0x01
RT_CELL_RANGE = 0x02
RT_DEVICE     = 0x03
RT_TILE       = 0x04
RT_HANDLER    = 0x05

RT_NAMES = {
    RT_FILE: "FILE", RT_CELL_RANGE: "CELL_RANGE",
    RT_DEVICE: "DEVICE", RT_TILE: "TILE", RT_HANDLER: "HANDLER",
}

@dataclass
class PointerToken:
    """
    A stable address in the UniFlex address space that refers to a resource
    regardless of its physical location (Section 4 of the spec).

    token_id:     64-bit stable address in the UniFlex address space
    pond_id:      ID of the Pond that owns this token
    resource_type: RT_FILE / RT_CELL_RANGE / RT_DEVICE / RT_TILE / RT_HANDLER
    physical_ref: physical address of the resource within its Pond
    checksum:     CRC32 over token_id + pond_id + physical_ref
    label:        human-readable name (filename, device name, tile name, etc.)
    """
    token_id:      int
    pond_id:       str
    resource_type: int
    physical_ref:  int
    checksum:      int   = 0
    label:         str   = ""

    def __post_init__(self):
        if self.checksum == 0:
            self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> int:
        import zlib
        data = (f"{self.token_id}:{self.pond_id}:{self.physical_ref}"
                .encode())
        return zlib.crc32(data) & 0xFFFFFFFF

    def is_valid(self) -> bool:
        return self.checksum == self._compute_checksum()

    def type_name(self) -> str:
        return RT_NAMES.get(self.resource_type, f"0x{self.resource_type:02X}")

    def __repr__(self):
        return (f"Token(0x{self.token_id:016X} "
                f"type={self.type_name()} "
                f"pond={self.pond_id} "
                f"ref=0x{self.physical_ref:08X} "
                f"label={self.label!r})")


# ── Token space ───────────────────────────────────────────────────────────────

class TokenSpace:
    """
    Manages the pointer token address space for one Pond (Section 4.3).

    Allocates sequential token_ids within a reserved block.
    Provides token resolution (token_id → PointerToken).
    Validates token integrity (checksum).
    """

    # Token address space starts well above cell addresses
    BASE_ADDRESS = 0x0100_0000_0000_0000   # 64-bit, upper region

    def __init__(self, pond_id: str, reservation_size: int = 65536):
        self._pond_id    = pond_id
        self._size       = reservation_size
        self._base       = TokenSpace.BASE_ADDRESS
        self._next       = self._base
        self._tokens: dict[int, PointerToken] = {}   # token_id -> token
        self._by_label: dict[str, int] = {}           # label -> token_id
        TokenSpace.BASE_ADDRESS += reservation_size  # advance global base

    def register(self, resource_type: int, physical_ref: int,
                 label: str = "") -> PointerToken:
        """
        Register a resource and return its token.
        Raises RuntimeError if the reservation is full.
        """
        if self._next >= self._base + self._size:
            raise RuntimeError(
                f"TokenSpace for pond {self._pond_id} is full "
                f"(size={self._size})")
        token_id = self._next
        self._next += 1
        tok = PointerToken(
            token_id      = token_id,
            pond_id       = self._pond_id,
            resource_type = resource_type,
            physical_ref  = physical_ref,
            label         = label,
        )
        self._tokens[token_id] = tok
        if label:
            self._by_label[label] = token_id
        return tok

    def resolve(self, token_id: int) -> Optional[PointerToken]:
        """Resolve a token_id to a PointerToken. Returns None if not found."""
        tok = self._tokens.get(token_id)
        if tok and not tok.is_valid():
            return None   # tampered
        return tok

    def resolve_by_label(self, label: str) -> Optional[PointerToken]:
        tid = self._by_label.get(label)
        return self.resolve(tid) if tid is not None else None

    def deregister(self, token_id: int) -> bool:
        tok = self._tokens.pop(token_id, None)
        if tok:
            self._by_label.pop(tok.label, None)
            return True
        return False

    @property
    def used(self) -> int:
        return len(self._tokens)

    @property
    def free(self) -> int:
        return self._size - self.used

    def list_tokens(self) -> list[PointerToken]:
        return list(self._tokens.values())


# ── Access grant ──────────────────────────────────────────────────────────────

@dataclass
class AccessGrant:
    """
    One entry in a Pond's whitelist.

    identity_id:  SHA-256 hash of the identity's public key or machine key
    expires_at:   Unix timestamp; 0 = permanent; negative = already expired
    single_use:   if True, grant is revoked after first successful admission
    region_scope: if set, identity may only use cells in this address range
                  (start_addr, end_addr); None = full Pond access
    schedule:     list of (start_hour, end_hour) pairs (24h) defining permitted
                  windows; empty list = always permitted
    label:        human-readable label for the grant (e.g. "alice_device")
    """
    identity_id:  str
    expires_at:   float                    = 0.0      # 0 = permanent
    single_use:   bool                     = False
    region_scope: Optional[tuple]          = None     # (start_addr, end_addr)
    schedule:     list                     = field(default_factory=list)
    label:        str                      = ""

    def is_valid(self, now: Optional[float] = None) -> bool:
        """True if grant has not expired."""
        if self.expires_at <= 0:
            return True                        # permanent
        return (now or time.time()) < self.expires_at

    def is_permitted_now(self, now: Optional[float] = None) -> bool:
        """True if current time falls within the schedule (or no schedule)."""
        if not self.schedule:
            return True
        t = now or time.time()
        hour = time.localtime(t).tm_hour
        return any(start <= hour < end for start, end in self.schedule)


# ── Visit log entry ───────────────────────────────────────────────────────────

@dataclass
class BridgeCrossingRecord:
    """
    One recorded event at a Pond bridge.

    Replaces VisitLogEntry with a richer structure that captures
    enough context to reconstruct what happened at the boundary.

    Two retention policies:
      denied_log   -- permanent, denial events only, capped at DENIED_CAP
      capture_log  -- rolling window, normally empty, Ward/ShoreKeeper activated

    Fields marked [silicon] map to real hardware observable state.
    Fields marked [os] are OS-layer metadata with no direct silicon equivalent.
    """
    # Required fields (no defaults)
    timestamp:    float
    sequence:     int
    identity_id:  str
    bridge_role:  str
    admitted:     bool
    reason:       str
    # Optional fields (with defaults)
    ptt_index:    int | None = None
    data_value:   int | None = None
    handshake:    int        = 0
    duration:     float | None = None
    metadata:     dict       = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "sequence":    self.sequence,
            "timestamp":   self.timestamp,
            "identity":    self.identity_id[:8] + "...",
            "bridge_role": self.bridge_role,
            "admitted":    self.admitted,
            "reason":      self.reason,
            "ptt_index":   self.ptt_index,
            "handshake":   self.handshake,
            "duration":    self.duration,
            "metadata":    self.metadata,
        }


class BridgeLog:
    """
    Two-tier bridge event log for a Pond.

    denied_log   -- permanent record of all denied crossings.
                    Capped at DENIED_CAP (oldest dropped when full).
                    Owner-readable only. Pushed to ShoreKeeper on each denial.
                    This is the security audit trail.

    capture_log  -- rolling window of ALL crossings (admitted and denied).
                    Normally empty (zero overhead). Activated by:
                      - Ward transition to DEGRADED/OFFLINE
                      - ShoreKeeper requesting a capture window
                      - High-bandwidth spike above capture_threshold
                    Captures N entries then stops automatically.
                    Also pushed to ShoreKeeper when capture completes.

    Design principle: at server scale with thousands of ponds, the default
    state produces zero log traffic. Events are pushed upward to ShoreKeeper
    rather than accumulated locally. The pond holds almost nothing.
    """
    DENIED_CAP    = 1000   # Max permanent denial records per pond
    CAPTURE_CAP   = 64     # Max entries per capture window

    def __init__(self):
        self._denied:   list[BridgeCrossingRecord] = []
        self._capture:  list[BridgeCrossingRecord] = []
        self._sequence: int  = 0          # monotonic crossing counter
        self._capturing: bool = False     # capture window active
        self._capture_remaining: int = 0  # entries left in capture window
        self._shorekeeper = None          # reference set at pond registration

    def attach_shorekeeper(self, sk) -> None:
        """Attach ShoreKeeper for push-based event forwarding."""
        self._shorekeeper = sk

    def start_capture(self, n: int = None) -> None:
        """
        Activate capture window. Records next N crossings (admitted + denied).
        If n is None, uses CAPTURE_CAP. Called by Ward or ShoreKeeper.
        """
        n = min(n or self.CAPTURE_CAP, self.CAPTURE_CAP)
        self._capturing        = True
        self._capture_remaining = n
        self._capture.clear()

    def stop_capture(self) -> list[BridgeCrossingRecord]:
        """Stop capture and return collected records."""
        self._capturing = False
        self._capture_remaining = 0
        result = list(self._capture)
        if self._shorekeeper is not None and result:
            self._shorekeeper.receive_capture(result)
        return result

    @property
    def is_capturing(self) -> bool:
        return self._capturing

    def record(self, identity_id: str, bridge_role: str,
               admitted: bool, reason: str,
               ptt_index: int = None, data_value: int = None,
               handshake: int = 0, metadata: dict = None) -> BridgeCrossingRecord:
        """
        Record one crossing event.

        Always increments sequence. Denied crossings always go to denied_log
        and are pushed to ShoreKeeper. All crossings go to capture_log if
        a capture window is active.
        """
        self._sequence += 1
        rec = BridgeCrossingRecord(
            timestamp   = time.time(),
            sequence    = self._sequence,
            identity_id = identity_id,
            bridge_role = bridge_role,
            admitted    = admitted,
            reason      = reason,
            ptt_index   = ptt_index,
            data_value  = data_value,
            handshake   = handshake,
            metadata    = metadata or {},
        )

        if not admitted:
            # Permanent denial record -- cap at DENIED_CAP
            if len(self._denied) >= self.DENIED_CAP:
                self._denied.pop(0)
            self._denied.append(rec)
            # Push to ShoreKeeper immediately
            if self._shorekeeper is not None:
                self._shorekeeper.receive_denial(rec)

        if self._capturing:
            self._capture.append(rec)
            self._capture_remaining -= 1
            if self._capture_remaining <= 0:
                self.stop_capture()

        return rec

    def denied_count(self) -> int:
        return len(self._denied)

    def has_denials(self) -> bool:
        return len(self._denied) > 0

    def get_denied(self, requester_id: str,
                   owner_id: str) -> list[dict]:
        """Return denied log. Owner-gated."""
        if requester_id != owner_id:
            raise PermissionError("Only the Pond owner may read the denied log")
        return [r.to_dict() for r in self._denied]

    def get_capture(self, requester_id: str,
                    owner_id: str) -> list[dict]:
        """Return current capture buffer. Owner-gated."""
        if requester_id != owner_id:
            raise PermissionError("Only the Pond owner may read the capture log")
        return [r.to_dict() for r in self._capture]

    def status(self) -> dict:
        """Summary visible to Cast/Ripple via resource_record()."""
        return {
            "denied_count":  len(self._denied),
            "has_denials":   self.has_denials(),
            "is_capturing":  self._capturing,
            "capture_depth": len(self._capture),
            "sequence":      self._sequence,
        }


# ── PondBridge ────────────────────────────────────────────────────────────────

class PondBridge:
    """
    One bridge at the boundary of a Pond.

    Bridge Interface Contract Specification v0.1:

    Each bridge occupies lane_width UniCells configured as PASS gates.
    INBOUND and OUTBOUND bridges have variable lane_width (N >= 1),
    set at Pond creation from peripheral tile metadata or defaults.
    MONITOR and LOG bridges are always single-cell — they observe and
    record but do not carry data.

    Lane model:
      capacity_per_cycle = lane_width
      utilisation_pct    = (mean emissions over window) / capacity * 100
      is_throttled       = utilisation_pct >= throttle_threshold
                           for at least utilisation_window cycles

    Troll model: the bridge checks your papers (identity), logs your
    visit (visit log), and counts how many are crossing at once (lanes).
    """

    INBOUND  = "INBOUND"
    OUTBOUND = "OUTBOUND"
    MONITOR  = "MONITOR"
    LOG      = "LOG"

    # MONITOR and LOG are always single-cell regardless of requested width
    _FIXED_WIDTH_ROLES = (MONITOR, LOG)

    def __init__(self, cell_addresses: list[int], role: str, pond: "Pond",
                 throttle_threshold: float = 80.0,
                 utilisation_window: int   = 100,
                 monitor_capacity: Optional[int] = None,
                 internal_offset: int = 0):
        """
        cell_addresses:   list of UniCell addresses (one per lane).
        monitor_capacity: for MONITOR bridges, the capacity to measure
          utilisation against — should be the Pond's inbound_lanes count.
          If None, defaults to lane_width (always 1 for MONITOR).
        internal_offset:  this bridge's offset from its Pond's base_address.
          Cells inside the Pond use base_address + internal_offset to reach
          this bridge. The offset never changes even when the Pond moves.
          0 = legacy mode (no relative addressing).
        """
        self.cell_addresses  = cell_addresses
        self.cell_address    = cell_addresses[0]       # primary (backward compat)
        self.lane_width      = len(cell_addresses)
        self.role            = role
        self.pond            = pond
        self.access_mask: int = 0xFFFFFFFF  # 32-bit mask — 0xFFFFFFFF = open to all

        # Two-address model:
        #   internal_offset — stable offset from Pond base, known by internal cells
        #   external_address — current absolute bus address, registered with Shore
        #     When the Pond moves to a new base, external_address is updated once.
        #     The internal_offset never changes.
        self.internal_offset   = internal_offset
        self.external_address  = (pond.base_address + internal_offset
                                   if pond is not None and pond.base_address
                                   else cell_addresses[0])

        # Throughput parameters
        # MONITOR uses the Pond's inbound capacity, not its own single lane
        self.capacity_per_cycle  = (monitor_capacity if monitor_capacity is not None
                                    else self.lane_width)
        self.throttle_threshold  = throttle_threshold
        self.utilisation_window  = utilisation_window

        # Counters
        self.packets_passed   = 0
        self.packets_rejected = 0
        self.bytes_passed     = 0

        # Utilisation tracking (MONITOR bridge)
        self._emission_history: list[int] = []   # per-cycle emission counts
        self.peak_utilisation  = 0               # highest single-cycle count
        self.cycles_throttled  = 0               # cumulative throttled cycles
        self._is_throttled     = False

        # ── Anomaly detection (MONITOR bridge) ───────────────────────────────
        # These flags are set by record_cycle() and cleared by clear_anomalies().
        # They surface in status() and resource_record() for Cast/Ward consumption.

        # Stall: MONITOR saw non-zero emissions, then zero for stall_threshold cycles.
        # Physical footprint: a PROCESS Pond's computation has halted unexpectedly.
        # Thresholds come from the pond PondTypeSpec so each type has
        # appropriate sensitivity. Falls back to 50/50.0 if unavailable.
        _type_spec = None
        if pond is not None:
            from pond_types import registry as _pt_registry
            _type_spec = _pt_registry.get(pond.pond_type)

        self.stall_threshold:    int  = (_type_spec.stall_threshold
                                         if _type_spec is not None else 50)
        self._consecutive_zeros: int  = 0
        self._had_nonzero:       bool = False     # ever seen nonzero emissions?
        self.is_stalled:         bool = False
        self.cycles_stalled:     int  = 0

        # Spike: single-cycle emissions exceed capacity by spike_factor.
        # Physical footprint: a burst beyond declared bandwidth — possible
        # malformed request flooding or misconfigured image.
        self.spike_factor:       float = 2.0      # emissions > factor * capacity → spike
        self.is_spiked:          bool  = False    # set when spike detected
        self.spike_count:        int   = 0        # cumulative spike events
        self.last_spike_emission: int  = 0        # emission count at last spike

        # Routing anomaly: rejection rate in a rolling window exceeds threshold.
        # Physical footprint: identities that aren't declared are probing the bridge.
        self.anomaly_window:     int   = 20       # access events to track
        self.anomaly_threshold:  float = (_type_spec.anomaly_threshold
                                          if _type_spec is not None else 50.0)
        self._access_window:     list  = []       # rolling list of bool (True=admitted)
        self.is_routing_anomaly: bool  = False
        self.routing_anomaly_count: int = 0       # cumulative anomaly events

        # ── Handshake state (INBOUND and OUTBOUND bridges only) ───────────────
        # Bridge-level ACK/REQ signalling via Bus 1 bits 18-21.
        # MONITOR and LOG bridges do not participate in handshaking.
        # The Ward monitors these counters — persistent BUSY or high NAK/DENY
        # rates surface as bridge health concerns in the PTT.
        self.hs_enabled: bool = role in (self.INBOUND, self.OUTBOUND)

        # Last handshake state sent/received on this bridge
        self.last_hs_sent:     int = 0   # HANDSHAKE_* value last sent
        self.last_hs_received: int = 0   # HANDSHAKE_* value last received

        # Cumulative handshake counters
        self.hs_ack_count:     int = 0   # packets acknowledged
        self.hs_nak_count:     int = 0   # packets rejected
        self.hs_busy_count:    int = 0   # packets queued/deferred
        self.hs_retry_count:   int = 0   # retry requests received
        self.hs_request_count: int = 0   # resource requests received
        self.hs_grant_count:   int = 0   # requests granted
        self.hs_deny_count:    int = 0   # requests denied

        # Consecutive BUSY cycles — Ward flags if this exceeds busy_threshold
        self.busy_threshold:        int  = 10    # consecutive BUSYs -> concern
        self._consecutive_busy:     int  = 0
        self.is_busy_stalled:       bool = False

        # PTT registration — set when the bridge is registered in the pond PTT.
        # The PTT entry carries all health flags (stalled, spiked, anomaly) as
        # status transitions and metadata, replacing the old boolean attributes.
        # None until register_in_ptt() is called after pond PTT is created.
        self.ptt_index: int | None = None

    def register_in_ptt(self, ptt) -> int:
        """
        Register this bridge as a PTT entry.

        Called once after the Pond PTT is created. Each bridge gets its
        own PTT entry with role-specific type and staleness threshold.
        The entry carries all health state as PTT status and metadata --
        no separate boolean flags needed on the bridge object.

        Returns the PTT index assigned to this bridge.
        """
        from pond_ptt import (
            TYPE_BRIDGE_INBOUND, TYPE_BRIDGE_OUTBOUND,
            TYPE_BRIDGE_MONITOR, TYPE_BRIDGE_LOG, TYPE_BRIDGE,
            STATUS_LOADING, STATUS_IDLE, STATUS_WAITING, STATUS_ACTIVE,
            STALENESS_DEFAULTS,
        )

        role_to_type = {
            PondBridge.INBOUND:  TYPE_BRIDGE_INBOUND,
            PondBridge.OUTBOUND: TYPE_BRIDGE_OUTBOUND,
            PondBridge.MONITOR:  TYPE_BRIDGE_MONITOR,
            PondBridge.LOG:      TYPE_BRIDGE_LOG,
        }
        entry_type = role_to_type.get(self.role, TYPE_BRIDGE)
        threshold  = STALENESS_DEFAULTS.get(entry_type, 30.0)

        # Use first lane address as the PTT entry address
        primary_addr = self.cell_addresses[0] if self.cell_addresses else 0

        idx = ptt.register(
            address          = primary_addr,
            entry_type       = entry_type,
            label            = f"{self.role}_bridge",
            notify_on_active = False,   # bridges don't use active callbacks
            metadata         = {
                "role":       self.role,
                "lane_width": self.lane_width,
                "lanes":      self.cell_addresses,
            },
        )
        # Bridges start ACTIVE immediately -- they are always-on infrastructure.
        # They bypass the WAITING state (which applies to user tiles that must
        # wait for their first input). Bridges are ready from creation.
        ptt.transition(idx, STATUS_LOADING)
        ptt.transition(idx, STATUS_IDLE)
        ptt.transition(idx, STATUS_WAITING)   # bridges skip straight through
        ptt.transition(idx, STATUS_ACTIVE)

        # Register sentry cell with role-appropriate staleness threshold
        ptt.register_sentry(idx, staleness_threshold=threshold)

        self.ptt_index = idx
        return idx

    def ptt_fault(self, ptt, reason: str, detail: dict = None) -> None:
        """
        Transition this bridge PTT entry to FAULTED with reason detail.

        Replaces the old boolean flag pattern (is_stalled, is_spiked etc).
        The Ward reads PTT FAULTED entries directly -- no separate flags needed.
        """
        if self.ptt_index is None or ptt is None:
            return
        from pond_ptt import STATUS_FAULTED
        meta = {"reason": reason}
        if detail:
            meta.update(detail)
        ptt.transition(self.ptt_index, STATUS_FAULTED, metadata=meta)

    def ptt_recover(self, ptt) -> None:
        """Transition this bridge PTT entry back to ACTIVE after a fault clears."""
        if self.ptt_index is None or ptt is None:
            return
        from pond_ptt import STATUS_RESERVED, STATUS_LOADING, STATUS_IDLE, STATUS_WAITING, STATUS_ACTIVE
        ptt.transition(self.ptt_index, STATUS_RESERVED)
        ptt.transition(self.ptt_index, STATUS_LOADING)
        ptt.transition(self.ptt_index, STATUS_IDLE)
        ptt.transition(self.ptt_index, STATUS_WAITING)
        ptt.transition(self.ptt_index, STATUS_ACTIVE)

    def ptt_touch(self, ptt) -> None:
        """Touch this bridge PTT entry -- confirms bridge is alive this cycle."""
        if self.ptt_index is not None and ptt is not None:
            ptt.touch(self.ptt_index)

    def update_external_address(self, new_base: int) -> int:
        """
        Recompute external_address after the Pond moves to new_base.

        Called by Pond.relocate() when the Pond migrates to a new base
        address. The internal_offset never changes -- only the resolved
        absolute address changes.

        Returns the new external_address.
        """
        if new_base:
            # Pond has a base address -- external is always base + offset
            # (offset=0 is valid and means the first bridge slot)
            self.external_address = new_base + self.internal_offset
        else:
            # Legacy bridge -- external_address tracks cell_address[0]
            self.external_address = self.cell_addresses[0]
        return self.external_address

    @property
    def bridge_addresses(self) -> dict:
        """
        Return both addresses for this bridge:
          internal_offset:  offset from Pond base (for internal cells)
          external_address: current absolute bus address (for Shore / external callers)
        """
        return {
            "internal_offset":  self.internal_offset,
            "external_address": self.external_address,
        }

    # ── Access control ────────────────────────────────────────────────────────

    def check_mask(self, process_mask: int) -> bool:
        """
        Bidirectional mask check: (process_mask & bridge.access_mask) != 0.
        Returns True if allowed. 0xFFFFFFFF = open to all.
        """
        if self.access_mask == 0xFFFFFFFF:
            return True
        return bool(process_mask & self.access_mask)

    def set_access_mask(self, mask: int) -> None:
        """Set the bridge access mask. Inherited from creator at bridge creation."""
        self.access_mask = mask & 0xFFFFFFFF

    def check_access(self, identity_id: str,
                     now: Optional[float] = None,
                     process_mask: int = 0xFFFFFFFF) -> tuple[bool, str]:
        """
        Check whether identity_id may pass through this bridge.
        Applies bidirectional mask check then whitelist check.
        Returns (admitted, reason).

        process_mask: caller's 32-bit identity mask from PTT hidden field.
                      Defaults to 0xFFFFFFFF for backward compatibility.
        """
        t = now or time.time()

        # Bidirectional mask check first -- O(1), no side effects
        if not self.check_mask(process_mask):
            self.pond.bridge_log.record(
                identity_id = identity_id,
                bridge_role = self.role,
                admitted    = False,
                reason      = "MASK_MISMATCH",
                metadata    = {"bridge_ptt_index": self.ptt_index},
            )
            self.packets_rejected += 1
            return False, "MASK_MISMATCH"

        admitted, reason = self.pond._check_identity(identity_id, t)

        self.pond.bridge_log.record(
            identity_id = identity_id,
            bridge_role = self.role,
            admitted    = admitted,
            reason      = reason,
            metadata    = {"bridge_ptt_index": self.ptt_index},
        )

        if admitted:
            self.packets_passed  += 1
            self.bytes_passed    += 4
            self.pond.last_active_at = t   # update pond activity timestamp
        else:
            self.packets_rejected += 1

        # Routing anomaly: track admission outcomes in a rolling window.
        # Only checked on INBOUND bridge — that is where identity probing lands.
        if self.role == PondBridge.INBOUND:
            self._access_window.append(admitted)
            if len(self._access_window) > self.anomaly_window:
                self._access_window.pop(0)
            if len(self._access_window) >= self.anomaly_window:
                rejection_pct = (
                    self._access_window.count(False)
                    / len(self._access_window) * 100
                )
                if rejection_pct >= self.anomaly_threshold:
                    if not self.is_routing_anomaly:
                        self.routing_anomaly_count += 1
                        self.is_routing_anomaly = True
                        if self.pond is not None:
                            self.ptt_fault(self.pond._ptt, "routing_anomaly", {
                                "rejection_pct": round(rejection_pct, 1),
                                "threshold":     self.anomaly_threshold,
                                "window":        self.anomaly_window,
                            })
                else:
                    if self.is_routing_anomaly:
                        self.is_routing_anomaly = False
                        if self.pond is not None:
                            self.ptt_recover(self.pond._ptt)

        return admitted, reason

    # ── Handshake (INBOUND and OUTBOUND bridges only) ─────────────────────────

    def record_handshake_sent(self, hs: int) -> None:
        """Record a handshake value sent on this bridge. Updates counters."""
        if not self.hs_enabled:
            return
        from command_interface import (HANDSHAKE_ACK, HANDSHAKE_NAK,
                                       HANDSHAKE_BUSY, HANDSHAKE_RETRY,
                                       HANDSHAKE_GRANT, HANDSHAKE_DENY)
        self.last_hs_sent = hs
        if hs == HANDSHAKE_ACK:     self.hs_ack_count   += 1
        elif hs == HANDSHAKE_NAK:   self.hs_nak_count   += 1
        elif hs == HANDSHAKE_BUSY:
            self.hs_busy_count += 1
            self._consecutive_busy += 1
            if self._consecutive_busy >= self.busy_threshold:
                self.is_busy_stalled = True
        elif hs == HANDSHAKE_RETRY: self.hs_retry_count += 1
        elif hs == HANDSHAKE_GRANT: self.hs_grant_count += 1
        elif hs == HANDSHAKE_DENY:  self.hs_deny_count  += 1
        if hs != HANDSHAKE_BUSY:
            self._consecutive_busy = 0
            self.is_busy_stalled   = False

    def record_handshake_received(self, hs: int) -> None:
        """Record a handshake value received on this bridge. Updates counters."""
        if not self.hs_enabled:
            return
        from command_interface import HANDSHAKE_REQUEST
        self.last_hs_received = hs
        if hs == HANDSHAKE_REQUEST:
            self.hs_request_count += 1

    def handshake_status(self) -> dict:
        """Return current handshake health summary for Ward/PTT consumption."""
        return {
            "enabled":          self.hs_enabled,
            "last_sent":        self.last_hs_sent,
            "last_received":    self.last_hs_received,
            "ack_count":        self.hs_ack_count,
            "nak_count":        self.hs_nak_count,
            "busy_count":       self.hs_busy_count,
            "retry_count":      self.hs_retry_count,
            "request_count":    self.hs_request_count,
            "grant_count":      self.hs_grant_count,
            "deny_count":       self.hs_deny_count,
            "is_busy_stalled":  self.is_busy_stalled,
            "consecutive_busy": self._consecutive_busy,
        }

    # ── Utilisation (MONITOR bridge) ──────────────────────────────────────────

    def record_cycle(self, emissions: int = 0):
        """
        Record the emission count for one clock cycle.
        Call on the MONITOR bridge once per tick with the count of
        cells that emitted within the Pond's address space this cycle.
        Updates utilisation history, peak, and throttle status.
        """
        self._emission_history.append(emissions)
        if len(self._emission_history) > self.utilisation_window:
            self._emission_history.pop(0)

        if emissions > self.peak_utilisation:
            self.peak_utilisation = emissions

        mean = (sum(self._emission_history) / len(self._emission_history)
                if self._emission_history else 0)
        util_pct = (mean / self.capacity_per_cycle * 100
                    if self.capacity_per_cycle > 0 else 0)

        self._is_throttled = util_pct >= self.throttle_threshold
        if self._is_throttled:
            self.cycles_throttled += 1

        # Also count as a passed packet on the MONITOR bridge
        self.packets_passed += emissions
        self.bytes_passed   += emissions * 4

        # ── Stall detection ───────────────────────────────────────────────
        if emissions > 0:
            self._had_nonzero       = True
            self._consecutive_zeros = 0
            if self.is_stalled:
                self.is_stalled = False
                # Recover PTT entry from FAULTED back to ACTIVE
                if self.pond is not None:
                    self.ptt_recover(self.pond._ptt)
        else:
            self._consecutive_zeros += 1

        if (self._had_nonzero
                and self._consecutive_zeros >= self.stall_threshold):
            if not self.is_stalled:
                self.cycles_stalled += 1
                self.is_stalled = True
                # Transition PTT entry to FAULTED
                if self.pond is not None:
                    self.ptt_fault(self.pond._ptt, "stalled", {
                        "consecutive_zeros": self._consecutive_zeros,
                        "threshold":         self.stall_threshold,
                    })

        # ── Spike detection ───────────────────────────────────────────────
        if (self.capacity_per_cycle > 0
                and emissions > self.spike_factor * self.capacity_per_cycle):
            self.is_spiked           = True
            self.spike_count        += 1
            self.last_spike_emission = emissions
            # Spike is transient -- fault PTT with spike detail
            if self.pond is not None:
                self.ptt_fault(self.pond._ptt, "spiked", {
                    "emissions":        emissions,
                    "capacity":         self.capacity_per_cycle,
                    "spike_factor":     self.spike_factor,
                })
            # High bandwidth spike -- trigger LOG bridge capture window
            # so the context around the spike is preserved for the Ward
            if self.pond is not None and not self.pond.bridge_log.is_capturing:
                self.pond.bridge_log.start_capture()
        else:
            if self.is_spiked and self.pond is not None:
                self.ptt_recover(self.pond._ptt)
            self.is_spiked = False

        # Touch PTT entry every cycle -- confirms bridge is alive
        if self.pond is not None:
            self.ptt_touch(self.pond._ptt)

    def record_emission(self):
        """Single-emission record (backward compat). Increments pass count."""
        self.packets_passed += 1
        self.bytes_passed   += 4

    def clear_anomalies(self) -> None:
        """
        Reset all anomaly flags. Called by the Ward or system layer after
        an anomaly has been acknowledged and the Pond has been recovered.
        Does not reset counters (spike_count, routing_anomaly_count,
        cycles_stalled) — those are the permanent audit record.
        """
        self.is_stalled          = False
        self._consecutive_zeros  = 0
        self._had_nonzero        = False
        self.is_spiked           = False
        self.is_routing_anomaly  = False
        self._access_window      = []

    @property
    def is_throttled(self) -> bool:
        return self._is_throttled

    @property
    def utilisation_pct(self) -> float:
        if not self._emission_history or self.capacity_per_cycle == 0:
            return 0.0
        mean = sum(self._emission_history) / len(self._emission_history)
        return mean / self.capacity_per_cycle * 100

    # ── Status ────────────────────────────────────────────────────────────────

    def status(self) -> dict:
        d = {
            "role":             self.role,
            "lane_width":       self.lane_width,
            "capacity_per_cycle": self.capacity_per_cycle,
            "cell_addresses":   [f"0x{a:08X}" for a in self.cell_addresses],
            "internal_offset":  self.internal_offset,
            "external_address": f"0x{self.external_address:08X}",
            "packets_passed":   self.packets_passed,
            "packets_rejected": self.packets_rejected,
            "bytes_passed":     self.bytes_passed,
            "utilisation_pct":  round(self.utilisation_pct, 1),
            "peak_utilisation": self.peak_utilisation,
            "is_throttled":     self.is_throttled,
            "cycles_throttled": self.cycles_throttled,
        }
        # Anomaly fields (MONITOR/INBOUND only — others always False/0)
        if self.role in (PondBridge.MONITOR, PondBridge.INBOUND):
            d.update({
                "is_stalled":            self.is_stalled,
                "cycles_stalled":        self.cycles_stalled,
                "is_spiked":             self.is_spiked,
                "spike_count":           self.spike_count,
                "last_spike_emission":   self.last_spike_emission,
                "is_routing_anomaly":    self.is_routing_anomaly,
                "routing_anomaly_count": self.routing_anomaly_count,
            })
        # Handshake fields (INBOUND and OUTBOUND bridges only)
        if self.hs_enabled:
            d["handshake"] = self.handshake_status()
        return d

    def __repr__(self):
        return (f"PondBridge({self.role} lanes={self.lane_width} "
                f"@ {[hex(a) for a in self.cell_addresses]} "
                f"passed={self.packets_passed} "
                f"throttled={self.is_throttled})")


# ── Pond ──────────────────────────────────────────────────────────────────────

class Pond:
    """
    A named, bounded shared UniCell resource pool.

    The Pond is carved from an existing UniCellArray. It holds a contiguous
    (or non-contiguous) set of cell addresses designated as shared capacity.
    Bridge cells sit at the boundary and gate all access.

    Security levels:
      OPEN    — anyone may use the Pond; whitelist ignored
      PRIVATE — whitelist enforced; unknown identities rejected
      HIDDEN  — not discoverable; only whitelisted identities admitted

    Bridges (allocated from the array on Pond creation):
      Bridge 0 INBOUND  — always present
      Bridge 1 OUTBOUND — always present
      Bridge 2 MONITOR  — created if bridge_count >= 3
      Bridge 3 LOG      — created if bridge_count == 4
    """

    _id_counter = 0

    # Default lane widths — now from PondTypeRegistry.
    # Kept as fallback for unregistered types.
    _DEFAULT_LANES = {
        PROCESS:    (4, 4),
        FILE:       (4, 2),
        PERIPHERAL: (2, 2),
        LIBRARY:    (1, 4),
        BOOT:       (1, 1),
        COMPANION:  (1, 1),
        WORKSPACE:  (4, 4),
        DEVICE:     (2, 2),
        SHORE_TYPE: (2, 4),
        FS:         (4, 2),
    }

    def __init__(self,
                 name: str,
                 array: UniCellArray,
                 owner_id: str,
                 security_level: str  = OPEN,
                 pond_type: str       = COMPUTE,
                 bridge_count: int    = 2,
                 segment_id: int      = 0,
                 token_reservation: int  = 65536,
                 inbound_lanes: int   = 0,
                 outbound_lanes: int  = 0,
                 throttle_threshold: float = 80.0,
                 utilisation_window: int   = 100,
                 base_address: int    = 0,
                 region_size: int     = 0,
                 scope: str           = None,
                 object_id: int       = 0):
        """
        Create a Pond within `array`.

        inbound_lanes:      INBOUND bridge lane count (0 = use type default)
        outbound_lanes:     OUTBOUND bridge lane count (0 = use type default)
        throttle_threshold: % utilisation to flag throttle (default 80)
        utilisation_window: cycles for rolling mean (default 100)
        base_address:       absolute bus address of this Pond's address space
                            origin. When non-zero, all internal offsets are
                            relative to this base. Bridges derive their
                            external_address as base + internal_offset.
                            0 = legacy mode (absolute addressing, no region).
        region_size:        number of address slots this Pond owns (base to
                            base+region_size-1). Used by Shore to register
                            the Pond's address space. 0 = unspecified.
        """
        if security_level not in SECURITY_LEVELS:
            raise ValueError(
                f"Invalid security_level '{security_level}'. "
                f"Must be one of {SECURITY_LEVELS}."
            )
        if not _pond_type_registry.is_valid(pond_type):
            raise ValueError(
                f"Invalid pond_type '{pond_type}'. "
                f"Registered types: {_pond_type_registry.all_types()}"
            )

        # COMPANION ponds are structurally HIDDEN — override silently if
        # caller passed a different security level, since HIDDEN is an
        # invariant of the type, not a configuration option.
        # Apply forced security from registry (e.g. COMPANION/SHORE → HIDDEN)
        _type_spec = _pond_type_registry.get(pond_type)
        if _type_spec and _type_spec.security and security_level != _type_spec.security:
            security_level = _type_spec.security
            imago_log.info(f"[POND] '{name}' ({pond_type}): "
                  f"security_level forced to {security_level}")
        if not (2 <= bridge_count <= 4):
            raise ValueError("bridge_count must be 2, 3, or 4.")

        # Resolve lane widths: explicit > type default
        _ts_lanes = _pond_type_registry.get(pond_type)
        _def_in, _def_out = (_ts_lanes.default_lanes if _ts_lanes
                             else Pond._DEFAULT_LANES.get(pond_type, (2, 2)))
        self._inbound_lanes      = inbound_lanes      if inbound_lanes  > 0 else _def_in
        self._outbound_lanes     = outbound_lanes     if outbound_lanes > 0 else _def_out
        self._throttle_threshold = throttle_threshold
        self._utilisation_window = utilisation_window

        Pond._id_counter += 1
        self.pond_id        = f"pond_{Pond._id_counter:04d}"
        self.name           = name
        self.owner_id       = owner_id
        self.security_level = security_level
        self.pond_type      = pond_type
        self.created_at     = time.time()
        # Address space — base_address=0 means legacy absolute addressing.
        # When set, all bridge internal_offsets are relative to this base.
        self.base_address   = base_address
        self.region_size    = region_size
        self._next_offset   = 0   # next available offset within this Pond's space
        # Object model — scope + 32-bit object ID
        # scope: which PTT level owns this Pond (LOCAL/SHORE/EXTENDED)
        # object_id: 32-bit ID within that scope's PTT
        # Neither replaces base_address — that is the flat bus address
        # used by cells. scope/object_id are used by the OS for routing.
        _ts_scope = _pond_type_registry.get(pond_type)
        self.scope     = scope or (_ts_scope.default_scope
                                   if _ts_scope else SCOPE_LOCAL)
        self.object_id = object_id   # assigned by ShoreKeeper at registration
        # COMPANION ponds carry a permanent anchor — they cannot be dissolved
        # by destroy_pond() without the heritage flag.
        _ts_pa = _pond_type_registry.get(pond_type)
        self.permanent_anchor: bool = (
            _ts_pa.permanent_anchor if _ts_pa else False)
        # Token space: reserved block of UniFlex addresses for this Pond
        self.tokens = TokenSpace(self.pond_id, token_reservation)

        self._array        = array
        self._segment_id   = segment_id

        # Cells allocated to this Pond for contributor workloads
        self._pool_cells: list[int] = []           # physical addresses

        # Whitelist: identity_id -> AccessGrant
        self._whitelist: dict[str, AccessGrant] = {}

        # Bridge log -- two-tier event log (denied + capture)
        # Normally produces zero traffic. Denials pushed to ShoreKeeper.
        # Capture activated by Ward or ShoreKeeper on anomaly/request.
        self.bridge_log: BridgeLog = BridgeLog()

        # Last activity timestamp -- updated on every admitted crossing
        # Used by PondManager.reap_stale() for pond reclamation
        self.last_active_at: float = time.time()

        # Allocate bridge cells from the array.
        # INBOUND gets _inbound_lanes cells, OUTBOUND gets _outbound_lanes.
        # MONITOR and LOG are always single-cell.
        bridge_roles = [
            PondBridge.INBOUND,
            PondBridge.OUTBOUND,
            PondBridge.MONITOR,
            PondBridge.LOG,
        ][:bridge_count]

        self.bridges: list[PondBridge] = []
        for role in bridge_roles:
            if role == PondBridge.INBOUND:
                n_lanes = self._inbound_lanes
            elif role == PondBridge.OUTBOUND:
                n_lanes = self._outbound_lanes
            else:
                n_lanes = 1   # MONITOR and LOG always single-cell

            lane_addresses = []
            for _ in range(n_lanes):
                cell = array.allocate_cell()
                array.write_config(cell.address, [
                    FUNCTION_LOAD_PATTERN,
                    0b000000000,   # GS_PASS
                    0x00000000,    # placeholder
                    0x00000000,    # placeholder
                ])
                if segment_id in array._segments:
                    array.assign_segment(cell.address, segment_id)
                lane_addresses.append(cell.address)

            # When Pond has a base_address, assign the bridge an internal offset.
            # The offset is the bridge's position within the Pond's address space.
            # external_address = base_address + internal_offset (computed in PondBridge).
            _offset = self.allocate_offset(1)[0] if self.base_address else 0

            # MONITOR measures utilisation against the Pond's inbound capacity,
            # not its own single lane — it observes, not carries.
            _cap = (self._inbound_lanes
                    if role == PondBridge.MONITOR else None)
            self.bridges.append(PondBridge(
                cell_addresses     = lane_addresses,
                role               = role,
                pond               = self,
                throttle_threshold = self._throttle_threshold,
                utilisation_window = self._utilisation_window,
                monitor_capacity   = _cap,
                internal_offset    = _offset,
            ))

        # Attach Ward — watchdog process scaled to this Pond's type.
        # BOOT ponds return None (ROM image; nothing to watch at runtime).
        from ward import make_ward
        self.ward = make_ward(self)

        # PTT — auto-created from the pond type registry's ptt_mode.
        # STATIC:      built once, frozen with snapshot (program Ponds)
        # INCREMENTAL: updated live (workspace/FS Ponds)
        # NONE:        no PTT (BOOT ponds)
        from pond_ptt import PondPTT
        from pond_types import PTT_STATIC, PTT_INCREMENTAL, PTT_NONE
        _ptt_mode_str = _type_spec.ptt_mode if _type_spec else PTT_STATIC
        if _ptt_mode_str == PTT_NONE:
            self._ptt = None
        elif _ptt_mode_str == PTT_INCREMENTAL:
            self._ptt = PondPTT(self.pond_id, PondPTT.INCREMENTAL)
            self.ward.attach_ptt(self._ptt)
        else:  # STATIC (default)
            self._ptt = PondPTT(self.pond_id, PondPTT.STATIC)
            self.ward.attach_ptt(self._ptt)

        # Register each bridge as a PTT entry.
        # This is the single source of truth for bridge health state --
        # the old boolean flags (is_stalled, is_spiked etc) are replaced
        # by PTT status transitions and metadata on these entries.
        if self._ptt is not None:
            for bridge in self.bridges:
                bridge.register_in_ptt(self._ptt)

        print(
            f"[POND] Created '{self.name}' ({self.pond_id}) "
            f"type={self.pond_type} "
            f"owner={owner_id[:8]}... "
            f"security={self.security_level} "
            f"bridges={bridge_count}"
        )

    # ── Security level management ─────────────────────────────────────────────

    def allocate_offset(self, count: int = 1) -> list[int]:
        """
        Allocate `count` sequential offsets within this Pond's address space.

        Returns a list of offset values (not absolute addresses).
        Callers resolve to absolute addresses as: base_address + offset.

        Only available when base_address is set (non-zero).
        For legacy Ponds (base_address=0) this returns empty list.
        """
        if not self.base_address:
            return []
        offsets = list(range(self._next_offset,
                             self._next_offset + count))
        self._next_offset += count
        return offsets

    def relocate(self, new_base_address: int) -> dict:
        """
        Move this Pond to a new base address.

        Updates base_address and recomputes external_address for all bridges.
        The internal_offset of each bridge never changes — internal cells
        always find their bridges at base_address + internal_offset.

        This is the Pond migration step. Caller is responsible for:
          1. freeze() the Pond before calling relocate()
          2. Physically moving cells to new array addresses if needed
          3. Calling Shore to update the address book with new external addresses
          4. thaw() after migration is complete

        Returns dict of {bridge_role: new_external_address} for Shore to update.
        """
        old_base = self.base_address
        self.base_address = new_base_address

        updated = {}
        for bridge in self.bridges:
            new_ext = bridge.update_external_address(new_base_address)
            updated[bridge.role] = new_ext

        imago_log.info(f"[POND] '{self.name}' relocated "
              f"0x{old_base:08X} → 0x{new_base_address:08X}")
        for role, addr in updated.items():
            imago_log.info(f"[POND]   {role} external_address → 0x{addr:08X}")

        return updated

    def migrate(self, new_base_address: int,
                shore=None,
                controller=None,
                mode: str = "FREEZE_BODY") -> dict:
        """
        Move this Pond to a new base address.

        Two freeze modes:

        FREEZE_FULL — everything stops. All bridges frozen. Connected Ponds
          receive nothing during the move. Use for: complete snapshots,
          powered-down migration, debug capture.

        FREEZE_BODY — internal cells frozen, bridges stay registered with
          Shore. Connected Ponds keep running — data flows to the old
          address and arrives nowhere briefly, like unplugging USB.
          Shore updates all routes when the new address is confirmed.
          Data resumes automatically. Duration: ~95 array ticks.
          Use for: hot migration of Workspace or Program Ponds.

        The move sequence for FREEZE_BODY:
          1. Shore suspends connections (marks SUSPENDED)
          2. Internal cells frozen (bridges remain in Shore registry)
          3. relocate() updates base_address and bridge external addresses
          4. Shore restores connections (ROUTE_UPDATE to connected Ponds)
          5. Internal cells thaw at new location

        Returns dict of {bridge_role: new_external_address}.
        """
        FREEZE_FULL = "FREEZE_FULL"
        FREEZE_BODY = "FREEZE_BODY"

        imago_log.info(f"[POND] '{self.name}' migrating "
              f"0x{self.base_address:08X} → 0x{new_base_address:08X} "
              f"[{mode}]")

        # Step 1 — suspend connections if Shore is available
        suspended_conns = []
        if shore and mode == FREEZE_BODY:
            for bridge in self.bridges:
                suspended_conns.extend(
                    shore.suspend_connections(
                        f"{self.name}_{bridge.role}"))
            # Also suspend by Pond name
            suspended_conns.extend(shore.suspend_connections(self.name))

        # Step 2 — freeze internal cells
        if controller:
            # Freeze all regions belonging to this Pond
            # (bridges are always-armed storage cells — leave them)
            for rid, region in controller._regions.items():
                # Skip bridge regions — they stay live
                if not any(b.internal_offset == 0 and
                           region.cell_addresses and
                           self.base_address + b.internal_offset
                           in region.cell_addresses
                           for b in self.bridges):
                    controller.freeze(region_id=rid)

        # Step 3 — relocate
        updated = self.relocate(new_base_address)

        # Step 4 — restore connections with new addresses
        if shore and mode == FREEZE_BODY:
            for bridge in self.bridges:
                new_ext = self.base_address + bridge.internal_offset
                shore.restore_connections(
                    f"{self.name}_{bridge.role}", new_ext)
            shore.restore_connections(self.name, new_base_address)

            # Update Shore registry entries
            shore.update(self.name, local_address=new_base_address,
                         base_address=new_base_address)
            for bridge in self.bridges:
                bridge_name = f"{self.name}_{bridge.role}"
                if shore.lookup(bridge_name):
                    shore.update(bridge_name,
                                 local_address=bridge.external_address,
                                 base_address=new_base_address)

        # Step 5 — thaw internal cells
        if controller and mode == FREEZE_BODY:
            for rid in controller._regions:
                controller.thaw(region_id=rid)

        imago_log.info(f"[POND] '{self.name}' migration complete "
              f"({'bridges live throughout' if mode == FREEZE_BODY else 'full freeze'})")

        return updated


    def restart(self,
                controller=None,
                shore=None,
                command_interface=None) -> bool:
        """
        Restart a stalled or failed Pond.

        Restart sequence:
          1. Freeze all internal cells (halt any stuck computation)
          2. Drain the bus — clear any stale values on bridge addresses
          3. Reset bridge anomaly counters and stall trackers
          4. Reset Ward health counters
          5. Re-arm bridge cells (INBOUND/OUTBOUND back to listening)
          6. Shore state updated to HEALTHY

        Returns True if restart completed, False if cells missing/unresponsive.

        Called by COMPANION _execute_action() when ACTION_RESTART is decided.
        """
        imago_log.info(f"[POND] '{self.name}' restarting...")

        # Step 1 — freeze all bridge cells via CommandInterface or direct
        if command_interface is not None:
            for bridge in self.bridges:
                for addr in bridge.cell_addresses:
                    command_interface.freeze(addr)
        elif controller is not None:
            for bridge in self.bridges:
                for addr in bridge.cell_addresses:
                    cell = controller.array.cells.get(addr)
                    if cell:
                        cell.start_flag = False
        else:
            # No controller — just reset software state
            pass

        # Step 2 — drain stale bus values on bridge addresses
        if controller is not None:
            for bridge in self.bridges:
                for addr in bridge.cell_addresses:
                    controller.array.bus.pop(addr, None)

        # Step 3 — reset bridge anomaly counters and stall trackers
        for bridge in self.bridges:
            bridge.clear_anomalies()
            bridge._consecutive_zeros = 0
            bridge._emission_history.clear()

        # Step 4 — reset pool cell stall tracking if any
        self._restart_count = getattr(self, '_restart_count', 0) + 1
        self._last_restart  = __import__('time').time()

        # Step 5 — re-arm bridge cells
        if command_interface is not None:
            for bridge in self.bridges:
                for addr in bridge.cell_addresses:
                    command_interface.release(addr)
        elif controller is not None:
            for bridge in self.bridges:
                for addr in bridge.cell_addresses:
                    cell = controller.array.cells.get(addr)
                    if cell:
                        cell.start_flag = True

        # Step 6 — update Shore state
        if shore is not None:
            if hasattr(shore, 'update'):
                shore.update(self.name,       ward_state="HEALTHY")
                shore.update(self.pond_id,    ward_state="HEALTHY")

        imago_log.info(f"[POND] '{self.name}' restart complete "
              f"(restart #{self._restart_count})")
        return True

    def checkpoint(self,
                   controller=None,
                   shore=None) -> dict:
        """
        Save Pond state for later restore (CONDITIONAL pond dissolve_action=CHECKPOINT).

        Returns a dict containing:
          - pond metadata (name, type, security, addresses)
          - bridge states (addresses, lane counts, anomaly counts)
          - pool cell addresses
          - restart history

        Does NOT save cell register values — that requires vm_image.save().
        This is the Pond-level manifest; vm_image handles the array state.
        """
        return {
            "pond_id":        self.pond_id,
            "name":           self.name,
            "owner_id":       self.owner_id,
            "pond_type":      self.pond_type,
            "security_level": self.security_level,
            "base_address":   self.base_address,
            "region_size":    self.region_size,
            "bridges": [
                {
                    "role":           b.role,
                    "lane_addresses": b.cell_addresses,
                    "capacity":       b.capacity_per_cycle,
                    "anomaly_count":  len(getattr(b, 'anomalies', [])),
                }
                for b in self.bridges
            ],
            "pool_cells":     list(self._pool_cells),
            "restart_count":  getattr(self, '_restart_count', 0),
            "last_restart":   getattr(self, '_last_restart', None),
            "created_at":     self.created_at,
            "checkpointed_at":__import__('time').time(),
        }

    def freeze_pond(self, controller=None, command_interface=None) -> None:
        """
        Freeze all cells in this Pond (CONDITIONAL pond dissolve_action=FREEZE).
        Halts execution mid-flight for debug inspection.
        All cell values preserved exactly as-is.
        """
        if command_interface is not None:
            for bridge in self.bridges:
                for addr in bridge.cell_addresses:
                    command_interface.freeze(addr)
            for addr in self._pool_cells:
                command_interface.freeze(addr)
        elif controller is not None:
            for bridge in self.bridges:
                for addr in bridge.cell_addresses:
                    cell = controller.array.cells.get(addr)
                    if cell:
                        cell.start_flag = False
            for addr in self._pool_cells:
                cell = controller.array.cells.get(addr)
                if cell:
                    cell.start_flag = False
        imago_log.info(f"[POND] '{self.name}' frozen for debug inspection")

    def set_security_level(self, level: str, requester_id: str) -> bool:
        """
        Change the security level. Only the owner may do this.
        Returns True on success.
        """
        if requester_id != self.owner_id:
            imago_log.info(f"[POND] '{self.name}': security change rejected — "
                  f"requester is not owner")
            return False
        if level not in SECURITY_LEVELS:
            imago_log.info(f"[POND] '{self.name}': invalid security level '{level}'")
            return False
        old = self.security_level
        self.security_level = level
        imago_log.info(f"[POND] '{self.name}': security level changed "
              f"{old} → {level}")
        return True

    # ── Whitelist management ──────────────────────────────────────────────────

    def grant_access(self, identity_id: str,
                     label: str = "",
                     expires_at: float = 0.0,
                     single_use: bool = False,
                     region_scope: Optional[tuple] = None,
                     schedule: Optional[list] = None,
                     requester_id: Optional[str] = None) -> AccessGrant:
        """
        Add an identity to the whitelist. Only the owner may grant access.
        Returns the AccessGrant created.
        """
        if requester_id is not None and requester_id != self.owner_id:
            raise PermissionError(
                f"Only the Pond owner may grant access "
                f"(requester={requester_id[:8]}...)"
            )
        grant = AccessGrant(
            identity_id  = identity_id,
            expires_at   = expires_at,
            single_use   = single_use,
            region_scope = region_scope,
            schedule     = schedule or [],
            label        = label or identity_id[:8],
        )
        self._whitelist[identity_id] = grant
        expiry_str = (
            "permanent" if expires_at <= 0
            else f"expires {time.strftime('%Y-%m-%d %H:%M', time.localtime(expires_at))}"
        )
        imago_log.info(f"[POND] '{self.name}': granted access to "
              f"{label or identity_id[:8]}... ({expiry_str}"
              + (" single-use" if single_use else "") + ")")
        return grant

    def revoke_access(self, identity_id: str,
                      requester_id: Optional[str] = None) -> bool:
        """
        Remove an identity from the whitelist. Only the owner may revoke.
        Returns True if the identity was found and removed.
        """
        if requester_id is not None and requester_id != self.owner_id:
            raise PermissionError("Only the Pond owner may revoke access")
        if identity_id in self._whitelist:
            label = self._whitelist[identity_id].label
            del self._whitelist[identity_id]
            imago_log.info(f"[POND] '{self.name}': revoked access for {label}")
            return True
        return False

    def _check_identity(self, identity_id: str,
                        now: Optional[float] = None) -> tuple[bool, str]:
        """
        Core access check. Returns (admitted: bool, reason: str).
        Called by bridge cells.
        """
        t = now or time.time()

        # Owner always admitted
        if identity_id == self.owner_id:
            return True, "OWNER"

        # OPEN: admit everyone
        if self.security_level == OPEN:
            return True, "OPEN"

        # PRIVATE / HIDDEN: check whitelist
        grant = self._whitelist.get(identity_id)
        if grant is None:
            return False, "REJECTED"

        # Check expiry
        if not grant.is_valid(t):
            return False, "EXPIRED"

        # Check schedule
        if not grant.is_permitted_now(t):
            return False, "OUTSIDE_SCHEDULE"

        # Admit — handle single-use
        if grant.single_use:
            del self._whitelist[identity_id]
            imago_log.info(f"[POND] '{self.name}': single-use grant consumed "
                  f"for {grant.label}")

        return True, "WHITELISTED"

    # ── Pool cell management ──────────────────────────────────────────────────

    def contribute_cells(self, count: int) -> list[int]:
        """
        Allocate `count` cells from the array into this Pond's pool.
        Returns list of allocated cell addresses.
        """
        allocated = []
        for _ in range(count):
            cell = self._array.allocate_cell()
            self._pool_cells.append(cell.address)
            allocated.append(cell.address)
        imago_log.info(f"[POND] '{self.name}': +{count} cells contributed "
              f"(pool now {len(self._pool_cells)})")
        return allocated

    def request_cells(self, identity_id: str,
                      count: int) -> tuple[list[int], str]:
        """
        Request `count` cells from the Pond pool for an identity's workload.

        Serves cells from the existing pool (_pool_cells).  If the identity
        has a region_scope grant, only cells whose addresses fall within
        [lo, hi] are eligible — the selection is filtered before allocation
        so the check never fails spuriously on freshly-allocated addresses.

        Returns (cell_addresses, reason).
        cell_addresses is empty if access was denied or pool is insufficient.
        """
        # Check access via inbound bridge
        inbound = self._get_bridge(PondBridge.INBOUND)
        admitted, reason = inbound.check_access(identity_id)

        if not admitted:
            imago_log.info(f"[POND] '{self.name}': cell request from "
                  f"{identity_id[:8]}... denied ({reason})")
            return [], reason

        # Determine eligible pool cells (scope filter applied before allocation)
        grant = self._whitelist.get(identity_id)
        if grant and grant.region_scope:
            lo, hi = grant.region_scope
            eligible = [a for a in self._pool_cells if lo <= a <= hi]
        else:
            eligible = list(self._pool_cells)

        if len(eligible) < count:
            scoped = " within scope" if (grant and grant.region_scope) else ""
            imago_log.info(f"[POND] '{self.name}': insufficient cells{scoped} "
                  f"(requested {count}, available {len(eligible)})")
            return [], "INSUFFICIENT_CELLS"

        # Serve the first `count` eligible cells and remove from pool
        allocated = eligible[:count]
        for a in allocated:
            self._pool_cells.remove(a)

        imago_log.info(f"[POND] '{self.name}': {count} cells granted to "
              f"{identity_id[:8]}...")
        return allocated, "GRANTED"

    def release_cells(self, cell_addresses: list[int],
                      identity_id: str) -> int:
        """
        Return cells to the Pond pool. Records via outbound bridge.
        Only cells not already in the pool are re-added (prevents duplicates).
        Returns count of cells actually released.
        """
        outbound = self._get_bridge(PondBridge.OUTBOUND)
        outbound.check_access(identity_id)

        pool_set = set(self._pool_cells)
        released = 0
        for addr in cell_addresses:
            if addr not in pool_set:
                self._pool_cells.append(addr)
                pool_set.add(addr)
                released += 1
        imago_log.info(f"[POND] '{self.name}': {released} cells released by "
              f"{identity_id[:8]}...")
        return released

    # ── Bridge helpers ────────────────────────────────────────────────────────

    def _get_bridge(self, role: str) -> PondBridge:
        for b in self.bridges:
            if b.role == role:
                return b
        # Fall back to inbound if role not present
        return self.bridges[0]

    def has_bridge(self, role: str) -> bool:
        return any(b.role == role for b in self.bridges)

    # ── Resource record ───────────────────────────────────────────────────────

    @property
    def free_cells(self) -> int:
        """Remaining cells in the Pond pool (not yet allocated to sessions)."""
        return len(self._pool_cells)

    def attach_ptt(self, ptt) -> None:
        """
        Attach a PondPTT to this Pond.

        Once attached, resource_record() includes the full PTT manifest.
        Cast/Ripple reads the PTT directly — no array scanning needed.
        Ward queries the PTT status column automatically.

        For STATIC Ponds: attach once after DMA load, freeze with the Pond.
        For INCREMENTAL Ponds: attach at creation, PTT updates live.
        """
        self._ptt = ptt
        if self.ward is not None:
            self.ward.attach_ptt(ptt)

    def _bridge_ptt_faulted(self) -> bool:
        """True if any bridge PTT entry is currently FAULTED."""
        if self._ptt is None:
            return False
        from pond_ptt import STATUS_FAULTED
        return any(
            self._ptt.get(b.ptt_index) is not None and
            self._ptt.get(b.ptt_index).status == STATUS_FAULTED
            for b in self.bridges
            if b.ptt_index is not None
        )

    def _bridge_ptt_fault_detail(self) -> list[dict]:
        """Return fault detail for all faulted bridge PTT entries."""
        if self._ptt is None:
            return []
        from pond_ptt import STATUS_FAULTED
        result = []
        for b in self.bridges:
            if b.ptt_index is None:
                continue
            entry = self._ptt.get(b.ptt_index)
            if entry is not None and entry.status == STATUS_FAULTED:
                result.append({
                    "role":       b.role,
                    "ptt_index":  b.ptt_index,
                    "reason":     entry.metadata.get("reason", "unknown"),
                    "detail":     entry.metadata,
                    "updated_at": entry.updated_at,
                })
        return result

    def _ptt_summary(self) -> Optional[dict]:
        """Return a PTT summary for resource_record(). None if no PTT."""
        if self._ptt is None:
            return None
        from pond_ptt import STATUS_IDLE, STATUS_LOADING
        return {
            "mode":     self._ptt.mode,
            "frozen":   self._ptt.is_frozen,
            "entries":  len(self._ptt),
            "active":   self._ptt.active_count(),
            "idle":     len(self._ptt.entries_by_status(STATUS_IDLE)),
            "loading":  len(self._ptt.entries_by_status(STATUS_LOADING)),
            "faulted":  self._ptt.faulted_count(),
            "manifest": [
                {
                    "index":   e.index,
                    "type":    e.type_name,
                    "status":  e.status_name,
                    "label":   e.label,
                    "address": hex(e.absolute_address),
                }
                for e in sorted(self._ptt._entries.values(),
                                key=lambda x: x.index)
                if e.status_name != "RESERVED"
            ],
        }

    def resource_record(self) -> dict:
        """
        The Pond's current resource record — what a Cast/Ripple would query.

        For HIDDEN ponds: only whitelisted identities receive this record.
        For PRIVATE ponds: returned to any querying Cast but cells require auth.
        For OPEN ponds: fully public.
        """
        # Bridge utilisation summary (Bridge Interface Contract Spec §6)
        _is_throttled = any(b.is_throttled for b in self.bridges
                            if b.role == PondBridge.MONITOR)
        _peak_util    = max((b.utilisation_pct for b in self.bridges
                             if b.role == PondBridge.MONITOR), default=0.0)
        _total_bridge = sum(b.lane_width for b in self.bridges)

        return {
            "pond_id":        self.pond_id,
            "name":           self.name,
            "pond_type":      self.pond_type,
            "security_level": self.security_level,
            "owner_id":       self.owner_id[:8] + "...",
            "created_at":     self.created_at,
            "pool_cells":     len(self._pool_cells),
            "free_cells":     self.free_cells,
            "bridge_count":   len(self.bridges),
            "bridges":        [b.status() for b in self.bridges],
            "whitelist_size": len(self._whitelist),
            "log":            self.bridge_log.status(),
            "tokens_used":    self.tokens.used,
            "tokens_free":    self.tokens.free,
            # Address space (base_address=0 means legacy absolute addressing)
            "base_address":   hex(self.base_address) if self.base_address else None,
            "region_size":    self.region_size,
            # Bridge contract fields
            "total_bridge_cells":   _total_bridge,
            "is_throttled":         _is_throttled,
            "peak_utilisation_pct": round(_peak_util, 1),
            # Anomaly summary -- kept for backward compat, now also PTT-backed
            "is_stalled":        any(getattr(b, "is_stalled", False)
                                     for b in self.bridges),
            "is_spiked":         any(getattr(b, "is_spiked", False)
                                     for b in self.bridges),
            "is_routing_anomaly": any(getattr(b, "is_routing_anomaly", False)
                                      for b in self.bridges),
            # PTT-authoritative bridge health -- Cast/Ripple uses this
            "bridge_faulted":      self._bridge_ptt_faulted(),
            "bridge_fault_detail": self._bridge_ptt_fault_detail(),
            "bridge_utilisation":   [
                {"role":            b.role,
                 "lane_width":      b.lane_width,
                 "utilisation_pct": round(b.utilisation_pct, 1),
                 "is_throttled":    b.is_throttled,
                 "ptt_index":       b.ptt_index}
                for b in self.bridges
            ],
            # Ward health state (None for BOOT ponds)
            "ward": self.ward.status.to_dict() if self.ward is not None else None,
            # PTT manifest — complete Pond inventory for Cast/Ripple
            "ptt": self._ptt_summary(),
        }

    # ── Visit log ─────────────────────────────────────────────────────────────

    def get_denied_log(self, requester_id: str) -> list[dict]:
        """
        Return permanent denied-access log. Owner-gated.
        This is the security audit trail -- all rejection reasons preserved.
        """
        return self.bridge_log.get_denied(requester_id, self.owner_id)

    def get_capture_log(self, requester_id: str) -> list[dict]:
        """
        Return current capture buffer. Owner-gated.
        Empty unless a capture window is active or recently completed.
        """
        return self.bridge_log.get_capture(requester_id, self.owner_id)

    def start_capture(self, requester_id: str, n: int = None) -> bool:
        """
        Activate a capture window. Owner or Ward may call this.
        Records next N crossings (admitted + denied) then stops automatically.
        Returns True if capture started.
        """
        if requester_id != self.owner_id:
            raise PermissionError("Only the Pond owner may start a capture")
        self.bridge_log.start_capture(n)
        return True

    # ── repr ──────────────────────────────────────────────────────────────────

    def __repr__(self):
        return (
            f"Pond('{self.name}' {self.pond_id} "
            f"type={self.pond_type} "
            f"security={self.security_level} "
            f"pool={len(self._pool_cells)} "
            f"bridges={len(self.bridges)} "
            f"denials={self.bridge_log.denied_count()})"
        )


# ── PondManager ───────────────────────────────────────────────────────────────

class PondManager:
    """
    Manages all Ponds within a system.

    The PondManager sits alongside the ImagoController and handles:
      - Pond creation and destruction
      - Pond discovery (for OPEN and PRIVATE ponds)
      - Identity-based routing to the correct Pond

    In the full architecture this would be part of the BIOS-plus chip's
    orchestration layer. In the simulator it wraps the UniCellArray.
    """

    def __init__(self, array: UniCellArray):
        self._array = array
        self._ponds: dict[str, Pond] = {}   # pond_id -> Pond
        self._name_index: dict[str, str] = {}  # name -> pond_id

    def create_pond(self,
                    name: str,
                    owner_id: str,
                    security_level: str  = OPEN,
                    pond_type: str       = PROCESS,
                    bridge_count: int    = 2,
                    segment_id: int      = 0,
                    token_reservation: int  = 65536,
                    inbound_lanes: int   = 0,
                    outbound_lanes: int  = 0,
                    throttle_threshold: float = 80.0,
                    utilisation_window: int   = 100,
                    base_address: int    = 0,
                    region_size: int     = 0) -> Pond:
        """
        Create a new Pond. security_level defaults to OPEN, pond_type
        to COMPUTE. Lane widths default to type-appropriate values.

        base_address: absolute bus address of this Pond's address space.
                      0 = legacy mode (no contiguous region).
        region_size:  number of address slots owned by this Pond.
        """
        if name in self._name_index:
            raise ValueError(
                f"A Pond named '{name}' already exists "
                f"({self._name_index[name]})"
            )
        pond = Pond(
            name               = name,
            array              = self._array,
            owner_id           = owner_id,
            security_level     = security_level,
            pond_type          = pond_type,
            bridge_count       = bridge_count,
            segment_id         = segment_id,
            token_reservation  = token_reservation,
            inbound_lanes      = inbound_lanes,
            outbound_lanes     = outbound_lanes,
            throttle_threshold = throttle_threshold,
            utilisation_window = utilisation_window,
            base_address       = base_address,
            region_size        = region_size,
        )
        self._ponds[pond.pond_id] = pond
        self._name_index[name]    = pond.pond_id
        return pond

    def spawn_pond_from_icm(self,
                             icm: dict,
                             owner_id: str,
                             name: str = None,
                             security_level: str = None,
                             cell_count: int = 8192) -> "Pond":
        """
        Full ICM-to-pond bootstrap sequence.

        Given a loaded .icm dict, creates a PROCESS pond, attaches a Ward
        and PTT, loads the cell map into the controller, registers each
        tile as a TYPE_PRIMITIVE PTT entry with its sentry cluster, then
        arms the pond and returns it ready to receive inputs.

        This is the OS-level path called by COMPANION / ShoreKeeper when
        a new program pond is requested. The sequence is:

          1. Create pond  (Ward + PTT auto-created by Pond.__init__)
          2. Register each named output as a PTT primitive entry
          3. Load cell map into controller with ptt= (wires _ptt_ref,
             patches sentry placeholder addresses)
          4. Transition each primitive entry RESERVED → LOADING → IDLE
          5. Arm the pond (cells ready to tick)

        Returns the fully bootstrapped Pond, ready to receive inputs.
        Raises RuntimeError if any step fails.
        """
        from controller import ImagoController, CellMapRecord
        from pond_ptt import (
            TYPE_PRIMITIVE, TYPE_TILE_IN, STALENESS_DEFAULTS,
            STATUS_LOADING, STATUS_IDLE,
        )
        from pond_types import PROCESS

        # ── 1. Resolve ICM fields ─────────────────────────────────────────────
        program_name = name or icm.get("name", "program")
        sec_level    = security_level or PRIVATE

        records_raw = icm.get("records", [])
        records = [
            CellMapRecord(
                r["gs"],
                r["in"],
                r["out"],
                input_b_address = r.get("inB"),
                initial_value   = r.get("init"),
            )
            for r in records_raw
        ]

        inputs  = icm.get("inputs",  {})
        outputs = icm.get("outputs", {})
        inputs  = {k: int(v, 16) if isinstance(v, str) else int(v)
                   for k, v in inputs.items()}
        outputs = {k: int(v, 16) if isinstance(v, str) else int(v)
                   for k, v in outputs.items()}

        # ICM metadata for PTT entries
        icm_pipeline_depth = icm.get("composer_meta", {}).get("pipeline_depth", 0)
        icm_cell_count     = len(records)

        # ── 2. Create pond (Ward + PTT created in __init__) ───────────────────
        pond = self.create_pond(
            name           = program_name,
            owner_id       = owner_id,
            security_level = sec_level,
            pond_type      = PROCESS,
        )

        # ── 3. Register each named input as a TYPE_TILE_IN PTT entry ──────────
        # Input entries let the Ward and ShoreKeeper distinguish "waiting for
        # user input" from "actively computing". Without these, a pond that
        # has never received an input looks the same as one that is mid-run.
        # The workspace model depends on this: ws set a=5 should transition
        # the 'a' entry from IDLE to WAITING/ACTIVE so the Ward knows the
        # pond has been engaged.
        input_staleness = STALENESS_DEFAULTS.get(TYPE_TILE_IN, 5.0)
        input_ptt_indices = {}   # {input_name: ptt_index}

        for port_name, bus_addr in inputs.items():
            idx = pond._ptt.register(
                address          = bus_addr,
                entry_type       = TYPE_TILE_IN,
                label            = f"{program_name}.{port_name}",
                notify_on_active = False,   # inputs don't trigger active callbacks
                metadata         = {
                    "port":    port_name,
                    "program": program_name,
                    "kind":    "input",
                },
            )
            input_ptt_indices[port_name] = idx

        # ── 4. Register each named output as a TYPE_PRIMITIVE PTT entry ───────
        # One entry per named output port. Each entry gets its own sentry
        # cell (sentry_address assigned here; cell patched in load_map).
        staleness = STALENESS_DEFAULTS.get(TYPE_PRIMITIVE, 5.0)
        ptt_indices = {}   # {output_name: ptt_index}

        for port_name, bus_addr in outputs.items():
            idx = pond._ptt.register(
                address          = bus_addr,
                entry_type       = TYPE_PRIMITIVE,
                label            = f"{program_name}.{port_name}",
                notify_on_active = True,
                metadata         = {
                    "port":           port_name,
                    "program":        program_name,
                    "pipeline_depth": icm_pipeline_depth,
                    "cell_count":     icm_cell_count,
                },
            )
            pond._ptt.register_sentry(idx, staleness_threshold=staleness)

            # Set pipeline_depth and max_instances on the entry
            entry = pond._ptt.get(idx)
            if entry is not None:
                entry.pipeline_depth = icm_pipeline_depth
                entry.max_instances  = 1   # single-instance program pond

            ptt_indices[port_name] = idx

        # ── 5. Load cell map → wires _ptt_ref, patches sentry addresses ───────
        ctrl = ImagoController(cell_count=cell_count)
        known_values = icm.get("known_values", {})
        known_values = {
            (int(k, 16) if isinstance(k, str) else k): v
            for k, v in known_values.items()
        }

        rid = ctrl.load_map(
            records,
            program_name,
            known_values = known_values,
            ptt          = pond._ptt,
        )
        if rid is None:
            self.destroy_pond(pond.pond_id, owner_id)
            raise RuntimeError(
                f"spawn_pond_from_icm: controller rejected cell map for '{program_name}'"
            )

        # Attach controller and region to pond for later run/freeze/query
        pond._controller       = ctrl
        pond._region_id        = rid
        pond._input_map        = inputs
        pond._output_map       = outputs
        pond._ptt_indices      = ptt_indices
        pond._input_ptt_indices = input_ptt_indices

        # ── 6. Transition all PTT entries RESERVED → LOADING → IDLE ──────────
        # Input entries (TILE_IN) go to IDLE — waiting for user to supply values.
        # Output entries (PRIMITIVE) go to IDLE — waiting for inputs to arrive.
        for idx in input_ptt_indices.values():
            pond._ptt.transition(idx, STATUS_LOADING)
            pond._ptt.transition(idx, STATUS_IDLE)

        for idx in ptt_indices.values():
            pond._ptt.transition(idx, STATUS_LOADING)
            pond._ptt.transition(idx, STATUS_IDLE)

        imago_log.info(
            f"[POND_MANAGER] Spawned '{program_name}' pond {pond.pond_id} — "
            f"{len(records)} cells, "
            f"{len(input_ptt_indices)} input port(s) (TILE_IN), "
            f"{len(ptt_indices)} output port(s) (PRIMITIVE)"
        )

        return pond

    def spawn_workspace(self,
                        owner_id: str,
                        name: str = "workspace") -> "Pond":
        """
        Create a WORKSPACE pond for an interactive user session.

        The WORKSPACE pond is the user's desk — it bridges to program ponds
        via connect(), receives their outputs through its INBOUND bridge, and
        delivers inputs to them through its OUTBOUND bridge.

        Security model:
          - The WORKSPACE is PRIVATE by default — only explicitly connected
            program ponds (granted by owner) may use its bridges.
          - Each program pond spawned for this workspace gets the workspace's
            owner_id on its whitelist, and vice versa.
          - Multiple program ponds may connect to the same workspace
            simultaneously (multi-program session).

        Returns the WORKSPACE Pond. The caller stores it as their session root.
        Use connect(workspace, program_pond) to wire program ponds to it.
        """
        from pond_types import WORKSPACE
        from pond_ptt import TYPE_WORKSPACE

        # WORKSPACE ponds are PRIVATE — only whitelisted program ponds admitted.
        # The owner is always admitted (checked in _check_identity before whitelist).
        pond = self.create_pond(
            name           = name,
            owner_id       = owner_id,
            security_level = PRIVATE,
            pond_type      = WORKSPACE,
        )

        # Register the workspace itself as a PTT entry so the Ward tracks it
        if pond._ptt is not None:
            pond._ptt.register(
                address    = pond.bridges[0].external_address if pond.bridges else 0,
                entry_type = TYPE_WORKSPACE,
                label      = f"{name}.session",
                metadata   = {"owner": owner_id, "kind": "workspace_root"},
            )

        imago_log.info(
            f"[POND_MANAGER] Spawned WORKSPACE '{name}' ({pond.pond_id}) "
            f"owner={owner_id[:8]}..."
        )
        return pond

    def connect(self,
                workspace: "Pond",
                program: "Pond") -> dict:
        """
        Wire a program pond's output back to the workspace, and the workspace's
        output to the program pond's input. Grant whitelist access both ways.

        Bus wiring (zero overhead — one write, one tick latency):
          workspace OUTBOUND external_address → program INBOUND external_address
          program OUTBOUND external_address   → workspace INBOUND external_address

        In practice on the wired-OR bus these are just address assignments —
        when the workspace fires its OUTBOUND cells at the program's INBOUND
        address, the program sees the value on the next tick. Same in reverse.

        Whitelist grants:
          - workspace grants program's owner_id access (program may write to workspace)
          - program grants workspace's owner_id access (workspace may write to program)

        Returns a connection descriptor dict with the wired addresses.
        Raises ValueError if either pond lacks INBOUND or OUTBOUND bridges.
        """
        # Get bridges by role
        ws_inbound  = next((b for b in workspace.bridges
                            if b.role == PondBridge.INBOUND),  None)
        ws_outbound = next((b for b in workspace.bridges
                            if b.role == PondBridge.OUTBOUND), None)
        pg_inbound  = next((b for b in program.bridges
                            if b.role == PondBridge.INBOUND),  None)
        pg_outbound = next((b for b in program.bridges
                            if b.role == PondBridge.OUTBOUND), None)

        if not all([ws_inbound, ws_outbound, pg_inbound, pg_outbound]):
            missing = []
            if not ws_inbound:  missing.append("workspace INBOUND")
            if not ws_outbound: missing.append("workspace OUTBOUND")
            if not pg_inbound:  missing.append("program INBOUND")
            if not pg_outbound: missing.append("program OUTBOUND")
            raise ValueError(
                f"connect(): missing bridges: {', '.join(missing)}"
            )

        # ── Bus wiring ────────────────────────────────────────────────────────
        # The OUTBOUND bridge's external_address is where it writes its output.
        # Setting it to the peer's INBOUND external_address means every value
        # the OUTBOUND fires goes directly into the INBOUND lane — no routing hop.
        #
        # ws OUTBOUND → pg INBOUND: workspace delivers inputs to the program
        ws_outbound.external_address = pg_inbound.external_address

        # pg OUTBOUND → ws INBOUND: program delivers results back to workspace
        pg_outbound.external_address = ws_inbound.external_address

        # ── Whitelist grants ──────────────────────────────────────────────────
        # Workspace grants program pond's owner access (so program can write back)
        workspace.grant_access(
            identity_id = program.owner_id,
            label       = f"program:{program.name}",
        )
        # Program grants workspace owner access (so workspace can write inputs)
        program.grant_access(
            identity_id = workspace.owner_id,
            label       = f"workspace:{workspace.name}",
        )

        # ── Register connection in workspace PTT ──────────────────────────────
        # Adds a PRIMITIVE entry for the program's output port so the workspace
        # PTT shows all active program ponds and their liveness.
        if workspace._ptt is not None:
            from pond_ptt import TYPE_PRIMITIVE, STALENESS_DEFAULTS, STATUS_LOADING, STATUS_IDLE
            staleness = STALENESS_DEFAULTS.get(TYPE_PRIMITIVE, 5.0)
            for port_name, bus_addr in getattr(program, '_output_map', {}).items():
                idx = workspace._ptt.register(
                    address    = bus_addr,
                    entry_type = TYPE_PRIMITIVE,
                    label      = f"{program.name}.{port_name}",
                    metadata   = {
                        "program_pond": program.pond_id,
                        "program_name": program.name,
                        "port":         port_name,
                        "kind":         "connected_program_output",
                    },
                )
                workspace._ptt.register_sentry(idx, staleness_threshold=staleness)
                workspace._ptt.transition(idx, STATUS_LOADING)
                workspace._ptt.transition(idx, STATUS_IDLE)

        connection = {
            "workspace_pond":    workspace.pond_id,
            "program_pond":      program.pond_id,
            "program_name":      program.name,
            "ws_outbound_addr":  ws_outbound.external_address,
            "ws_inbound_addr":   ws_inbound.external_address,
            "pg_inbound_addr":   pg_inbound.external_address,
            "pg_outbound_addr":  pg_outbound.external_address,
        }

        imago_log.info(
            f"[POND_MANAGER] Connected '{program.name}' ({program.pond_id}) "
            f"↔ workspace '{workspace.name}' ({workspace.pond_id})"
        )
        return connection

    def destroy_pond(self, pond_id: str, requester_id: str,
                     heritage: bool = False) -> bool:
        """
        Destroy a Pond. Only the owner may destroy their Pond.

        COMPANION ponds carry a permanent_anchor and cannot be dissolved
        by normal means. Destruction requires either:
          - The owner calling with heritage=True (Heritage succession event)
          - The owner's explicit command (heritage=False, requester=owner)
        Even the owner cannot accidentally destroy a COMPANION pond without
        the heritage flag — this is the structural permanence guarantee.

        Bridge cells are freed back to the array.
        """
        pond = self._ponds.get(pond_id)
        if pond is None:
            return False
        if requester_id != pond.owner_id:
            imago_log.info(f"[POND_MANAGER] Destroy rejected — not owner")
            return False
        # Permanent anchor types require explicit heritage flag
        _pspec = _pond_type_registry.get(pond.pond_type)
        if _pspec and _pspec.permanent_anchor and not heritage:
            imago_log.info(f"[POND_MANAGER] Dissolution of {pond.pond_type} pond "
                  f"'{pond.name}' requires heritage=True")
            return False
        # Free bridge cells
        for bridge in pond.bridges:
            if bridge.cell_address in self._array.cells:
                del self._array.cells[bridge.cell_address]
        del self._ponds[pond_id]
        del self._name_index[pond.name]
        imago_log.info(f"[POND_MANAGER] Pond '{pond.name}' ({pond_id}) destroyed")
        return True

    def discover(self, identity_id: str) -> list[dict]:
        """
        Return resource records for all discoverable Ponds.

        OPEN and PRIVATE Ponds are returned.
        HIDDEN Ponds are returned only if the identity is whitelisted.
        """
        results = []
        for pond in self._ponds.values():
            if pond.security_level == HIDDEN:
                # Only reveal to whitelisted identities or owner
                if (identity_id != pond.owner_id and
                        identity_id not in pond._whitelist):
                    continue
            results.append(pond.resource_record())
        return results

    def get_pond(self, pond_id: str) -> Optional[Pond]:
        return self._ponds.get(pond_id)

    def get_pond_by_name(self, name: str) -> Optional[Pond]:
        pid = self._name_index.get(name)
        return self._ponds.get(pid) if pid else None

    def attach_shorekeeper(self, sk) -> None:
        """
        Attach a ShoreKeeper to all current ponds.
        The ShoreKeeper receives pushed denial events and capture completions.
        """
        self._shorekeeper = sk
        for pond in self._ponds.values():
            pond.bridge_log.attach_shorekeeper(sk)

    def reap_stale(self, idle_threshold: float = 3600.0) -> list[str]:
        """
        Reclaim ponds idle for longer than idle_threshold seconds.

        Stale ponds are frozen, cells freed, removed from the manager.
        Permanent anchor types (COMPANION etc) are never reaped.
        Returns list of reaped pond_ids.
        Called periodically by ShoreKeeper as background maintenance.
        """
        now = time.time()
        reaped = []
        for pond_id, pond in list(self._ponds.items()):
            _pspec = _pond_type_registry.get(pond.pond_type)
            if _pspec and _pspec.permanent_anchor:
                continue
            idle_secs = now - pond.last_active_at
            if idle_secs < idle_threshold:
                continue
            imago_log.info(f"[POND_MANAGER] Reaping stale pond '{pond.name}' "
                  f"({pond_id}) -- idle {idle_secs:.0f}s")
            for bridge in pond.bridges:
                addr = getattr(bridge, 'cell_address', None)
                if addr and hasattr(self._array, 'cells') and addr in self._array.cells:
                    del self._array.cells[addr]
            del self._ponds[pond_id]
            del self._name_index[pond.name]
            reaped.append(pond_id)
        return reaped

    def status(self) -> dict:
        return {
            "total_ponds":      len(self._ponds),
            "open_ponds":       sum(1 for p in self._ponds.values()
                                    if p.security_level == OPEN),
            "private_ponds":    sum(1 for p in self._ponds.values()
                                    if p.security_level == PRIVATE),
            "hidden_ponds":     sum(1 for p in self._ponds.values()
                                    if p.security_level == HIDDEN),
            "process_ponds":    sum(1 for p in self._ponds.values()
                                    if p.pond_type == PROCESS),
            "file_ponds":       sum(1 for p in self._ponds.values()
                                    if p.pond_type == FILE),
            "peripheral_ponds": sum(1 for p in self._ponds.values()
                                    if p.pond_type == PERIPHERAL),
            "library_ponds":    sum(1 for p in self._ponds.values()
                                    if p.pond_type == LIBRARY),
            "companion_ponds":  sum(1 for p in self._ponds.values()
                                    if p.pond_type == COMPANION),
            "total_pool_cells": sum(len(p._pool_cells)
                                    for p in self._ponds.values()),
        }

    def __repr__(self):
        return f"PondManager({len(self._ponds)} ponds)"
