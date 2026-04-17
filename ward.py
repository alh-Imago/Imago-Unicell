"""
ward.py — The Ward: Per-Pond Watchdog Process

The Ward is the immune system of a Pond. It sits inside the bounded region,
consumes data from the MONITOR bridge, and maintains a health state that is
visible in the Pond's resource record and to the Cast/Ripple discovery mesh.

Ward complexity scales with Pond type:

  FILE       — almost nothing. Confirms the bridge is allocated and pool
               cells haven't vanished. Barely awake.

  PERIPHERAL — watches data flow rates from the device. Detects unexpected
               silence: if the device was emitting and has gone quiet, the
               Ward raises SILENT. Hardware disconnection has a physical
               footprint.

  LIBRARY    — usage statistics. Tracks inbound requests and outbound
               responses. Flags if requests arrive but responses stop
               (DEGRADED) or if the pond is completely idle for too long.

  PROCESS    — the most active role. Watches emission rates, detects stalls
               (zero emissions on a pond that had active computation), flags
               throttle conditions, tracks activity windows.

  COMPANION  — pulse check only. The Companion largely manages itself.
               Ward just confirms the bridge is alive.

  BOOT       — no Ward. ROM image; nothing changes at runtime.

Ward states:
  IDLE      — no data yet; Ward is initialised but hasn't observed a cycle
  HEALTHY   — normal operation; all checks pass
  DEGRADED  — threshold breached (throttle, high error rate, request/response
               mismatch); Pond is stressed but still operating
  STALLED   — PROCESS only: zero emissions on a Pond that had active traffic;
               computation has halted unexpectedly
  SILENT    — PERIPHERAL only: device has stopped emitting after a period of
               activity; hardware may have disconnected
  OFFLINE   — bridge health check failed; Pond's bridge cells are gone

The Ward.tick(emissions) method is called once per clock cycle (or sampling
interval) with the current emission count from the MONITOR bridge. It updates
internal state and returns the current WardStatus.

The Ward does NOT modify the Pond. It observes and reports. Actions in
response to Ward flags are the responsibility of the COMPANION Pond and the
system-level orchestration layer (Phase 4 / anomaly detection).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pond import Pond, PondBridge

# ── Ward state constants ──────────────────────────────────────────────────────

IDLE     = "IDLE"
HEALTHY  = "HEALTHY"
DEGRADED = "DEGRADED"
STALLED  = "STALLED"    # PROCESS only
SILENT   = "SILENT"     # PERIPHERAL only
OFFLINE  = "OFFLINE"

WARD_STATES = (IDLE, HEALTHY, DEGRADED, STALLED, SILENT, OFFLINE)


# ── WardStatus ────────────────────────────────────────────────────────────────

@dataclass
class WardStatus:
    """
    Snapshot of Ward health at one point in time.
    This is what resource_record() and Cast queries see.
    """
    state:            str            # one of WARD_STATES
    pond_type:        str
    cycles_observed:  int   = 0      # total tick() calls processed
    cycles_healthy:   int   = 0
    cycles_degraded:  int   = 0
    cycles_stalled:   int   = 0      # PROCESS only
    cycles_silent:    int   = 0      # PERIPHERAL only
    last_anomaly_at:  Optional[float] = None   # wall-clock time of last anomaly
    anomaly_reason:   str   = ""
    # Emission statistics
    mean_emissions:   float = 0.0
    peak_emissions:   int   = 0
    last_nonzero_at:  Optional[float] = None   # wall-clock time of last nonzero emission

    # PTT health — populated when PTT is attached to the Ward
    ptt_entries:      int   = 0
    ptt_active:       int   = 0
    ptt_faulted:      int   = 0
    ptt_idle:         int   = 0
    ptt_faulted_labels: list = field(default_factory=list)

    def is_healthy(self) -> bool:
        return self.state == HEALTHY

    def has_anomaly(self) -> bool:
        return (self.state in (DEGRADED, STALLED, SILENT, OFFLINE)
                or self.ptt_faulted > 0)

    def to_dict(self) -> dict:
        d = {
            "state":           self.state,
            "pond_type":       self.pond_type,
            "cycles_observed": self.cycles_observed,
            "cycles_healthy":  self.cycles_healthy,
            "cycles_degraded": self.cycles_degraded,
            "cycles_stalled":  self.cycles_stalled,
            "cycles_silent":   self.cycles_silent,
            "last_anomaly_at": self.last_anomaly_at,
            "anomaly_reason":  self.anomaly_reason,
            "mean_emissions":  round(self.mean_emissions, 2),
            "peak_emissions":  self.peak_emissions,
            "last_nonzero_at": self.last_nonzero_at,
        }
        if self.ptt_entries:
            d["ptt"] = {
                "entries": self.ptt_entries,
                "active":  self.ptt_active,
                "idle":    self.ptt_idle,
                "faulted": self.ptt_faulted,
                "faulted_labels": self.ptt_faulted_labels,
            }
        return d


# ── Ward ─────────────────────────────────────────────────────────────────────

class Ward:
    """
    Watchdog process for a single Pond.

    Usage:
        ward = Ward(pond)
        # Called each clock cycle (or sampling interval):
        status = ward.tick(emissions=monitor_bridge.packets_passed_this_cycle)
        # Read state at any time:
        print(ward.status.state)

    The Ward is created by the Pond at construction time and stored as
    pond.ward. Callers feed it emission counts; it maintains the health
    state machine.
    """

    # How many consecutive zero-emission cycles before STALLED (PROCESS)
    STALL_THRESHOLD: int = 50

    # How many consecutive zero-emission cycles before SILENT (PERIPHERAL)
    SILENCE_THRESHOLD: int = 30

    # How many cycles of history to keep for mean calculation
    HISTORY_WINDOW: int = 100

    # Minimum cycles of activity before stall/silence detection activates.
    # Prevents newly-created Ponds from immediately flagging as stalled.
    WARMUP_CYCLES: int = 10

    def __init__(self, pond: "Pond"):
        from pond import PROCESS, FILE, PERIPHERAL, LIBRARY, COMPANION, BOOT

        self._pond       = pond
        self._pond_type  = pond.pond_type
        self._created_at = time.time()

        # State machine
        self._state: str = IDLE

        # Counters
        self._cycles_observed  = 0
        self._cycles_healthy   = 0
        self._cycles_degraded  = 0
        self._cycles_stalled   = 0
        self._cycles_silent    = 0

        # Emission tracking
        self._emission_history: list[int] = []
        self._peak_emissions   = 0
        self._consecutive_zeros = 0
        self._had_activity      = False   # has the pond ever emitted?
        self._last_nonzero_at: Optional[float] = None

        # Anomaly record
        self._last_anomaly_at: Optional[float] = None
        self._anomaly_reason   = ""

        # BOOT ponds have no Ward logic — they're ROM
        self._active = (pond.pond_type != BOOT)

        # PTT reference — attached via attach_ptt() after Pond creation
        self._ptt = None

        # CONDITIONAL pond lifecycle contract (hidden in PTT)
        # Set via set_dissolve_contract() — never readable by the Pond itself
        self._dissolve_condition: Optional[dict] = None
        self._dissolve_action:    Optional[str]  = None
        self._dissolve_triggered: bool           = False
        self._tick_count:         int            = 0

        # Thermal fields (in PTT — updated each tick by ShoreKeeper or Ward)
        self.thermal_load:   float = 0.0    # current thermal units
        self.thermal_limit:  float = 80.0   # throttle threshold (% budget)
        self.thermal_trend:  float = 0.0    # rate of change per tick
        self.thermal_zone:   str   = ""     # which block this Pond's cells occupy

        # Thermal simulation constants (can be overridden per Pond)
        self._thermal_active_cost: float = 0.001   # per armed cell per tick
        self._thermal_idle_cost:   float = 0.0001  # leakage per cell per tick
        self._thermal_decay:       float = 0.999   # decay per tick

    # ── Public interface ──────────────────────────────────────────────────────

    def attach_ptt(self, ptt) -> None:
        """
        Attach a PondPTT to this Ward.

        Once attached, tick() queries the PTT status column each cycle.
        PTT health appears in WardStatus. FAULTED entries escalate to
        DEGRADED automatically.

        For STATIC Ponds: attach once after restore.
        For INCREMENTAL Ponds: attach at creation; PTT updates live.
        The Ward only reads from the PTT — it does not own it.
        """
        self._ptt = ptt

    def _update_thermal(self) -> None:
        """
        Update simulated thermal load from Pond cell activity.

        Called each tick. Uses the same decay model as ShoreKeeper
        so thermal fields in Ward stay consistent with card-level aggregation.

        thermal_load:   absolute units (armed × active_cost + idle × idle_cost)
        thermal_trend:  change since last tick (positive = heating)
        """
        pond = self._pond
        array = getattr(pond, '_array', None)
        if array is None:
            return

        # Count armed vs idle cells belonging to this Pond
        pond_cells = set(getattr(pond, '_pool_cells', []))
        for bridge in getattr(pond, 'bridges', []):
            pond_cells.update(getattr(bridge, 'cell_addresses', []))

        armed_cells = len(pond_cells & getattr(array, '_armed', set()))
        idle_cells  = max(0, len(pond_cells) - armed_cells)

        heat = (armed_cells * self._thermal_active_cost +
                idle_cells  * self._thermal_idle_cost)

        prev = self.thermal_load
        self.thermal_load  = self.thermal_load * self._thermal_decay + heat
        self.thermal_trend = self.thermal_load - prev

        # Thermal escalation check
        if self.thermal_load > self.thermal_limit * 1.5:
            # Override state to DEGRADED if severe thermal overrun
            if self._state not in ("DEGRADED", "STALLED"):
                self._anomaly_reason = (
                    f"THERMAL: {self.thermal_load:.1f} > "
                    f"{self.thermal_limit * 1.5:.1f} (migrate threshold)")
                self._last_anomaly_at = __import__('time').time()

    @property
    def thermal_state(self) -> str:
        """NOMINAL | THROTTLE | FREEZE | MIGRATE based on load vs limit."""
        if self.thermal_limit <= 0:
            return "NOMINAL"
        ratio = self.thermal_load / self.thermal_limit
        if ratio >= 1.50: return "MIGRATE"
        if ratio >= 1.20: return "FREEZE"
        if ratio >= 1.00: return "THROTTLE"
        return "NOMINAL"

    def set_thermal_config(self,
                           limit: float = 80.0,
                           zone:  str   = "") -> None:
        """Set thermal limit and zone (called by ShoreKeeper at Pond creation)."""
        self.thermal_limit = max(1.0, limit)
        self.thermal_zone  = zone

    def thermal_summary(self) -> dict:
        """Compact thermal snapshot for ShoreKeeper heartbeat."""
        return {
            "load":   round(self.thermal_load, 4),
            "limit":  self.thermal_limit,
            "pct":    round(self.thermal_load / self.thermal_limit * 100
                           if self.thermal_limit > 0 else 0.0, 2),
            "trend":  round(self.thermal_trend, 6),
            "state":  self.thermal_state,
            "zone":   self.thermal_zone,
        }

    def set_dissolve_contract(self,
                              condition: dict,
                              action: str) -> None:
        """
        Set the lifecycle contract for a CONDITIONAL pond (hidden from Pond).

        condition: dict with keys:
            type: TIME | RETURN | COMPLETE | EXTERNAL | COMPOUND
            For TIME:     {"type":"TIME", "ticks": int}
            For RETURN:   {"type":"RETURN", "process_id": str, "value": int}
            For COMPLETE: {"type":"COMPLETE", "process_id": str}
            For EXTERNAL: {"type":"EXTERNAL", "session_id": str}
            For COMPOUND: {"type":"COMPOUND", "op":"ANY"|"ALL",
                            "conditions": [condition, ...]}

        action: DISSOLVE | FREEZE | CHECKPOINT

        Called by COMPANION at Pond creation. Never exposed to the Pond.
        """
        from pond_types import (DISSOLVE_TIME, DISSOLVE_RETURN,
                                 DISSOLVE_COMPLETE, DISSOLVE_EXTERNAL,
                                 DISSOLVE_COMPOUND,
                                 ACTION_DISSOLVE, ACTION_FREEZE,
                                 ACTION_CHECKPOINT)
        valid_actions = {ACTION_DISSOLVE, ACTION_FREEZE, ACTION_CHECKPOINT}
        if action not in valid_actions:
            raise ValueError(f"Invalid dissolve action '{action}'. "
                             f"Must be one of {valid_actions}.")
        self._dissolve_condition = condition
        self._dissolve_action    = action
        self._dissolve_triggered = False

    def evaluate_dissolve(self, context: dict = None) -> Optional[str]:
        """
        Evaluate the dissolve condition against current context.

        context: optional dict with runtime values:
            - tick_count:   current array tick
            - process_states: {process_id: state}
            - return_values:  {process_id: value}
            - active_sessions: set of active session IDs

        Returns the dissolve action string if condition is met, else None.
        Called by Ward.tick() each cycle for CONDITIONAL ponds.
        """
        if self._dissolve_condition is None:
            return None
        if self._dissolve_triggered:
            return None   # already fired

        ctx = context or {}
        met = self._check_condition(self._dissolve_condition, ctx)
        if met:
            self._dissolve_triggered = True
            print(f"[WARD] '{self._pond.name}' dissolve condition met — "
                  f"action: {self._dissolve_action}")
            return self._dissolve_action
        return None

    def _check_condition(self, cond: dict, ctx: dict) -> bool:
        """Recursively evaluate a dissolve condition."""
        from pond_types import (DISSOLVE_TIME, DISSOLVE_RETURN,
                                 DISSOLVE_COMPLETE, DISSOLVE_EXTERNAL,
                                 DISSOLVE_COMPOUND)
        ctype = cond.get("type")

        if ctype == DISSOLVE_TIME:
            return self._tick_count >= cond.get("ticks", 0)

        if ctype == DISSOLVE_RETURN:
            pid = cond.get("process_id")
            val = cond.get("value")
            return ctx.get("return_values", {}).get(pid) == val

        if ctype == DISSOLVE_COMPLETE:
            pid = cond.get("process_id")
            return ctx.get("process_states", {}).get(pid) == "COMPLETE"

        if ctype == DISSOLVE_EXTERNAL:
            sid = cond.get("session_id")
            return sid not in ctx.get("active_sessions", set())

        if ctype == DISSOLVE_COMPOUND:
            op   = cond.get("op", "ANY")
            subs = cond.get("conditions", [])
            results = [self._check_condition(c, ctx) for c in subs]
            if op == "ALL":
                return all(results)
            return any(results)  # ANY is default

        return False

    def tick(self, emissions: int = 0) -> WardStatus:
        """
        Advance the Ward by one cycle.

        emissions: count of cells that emitted within this Pond's address
          space this cycle. Typically sourced from MONITOR.packets_passed
          per-cycle delta, or passed directly from the array tick loop.

        Returns the current WardStatus.
        """
        self._tick_count += 1

        # Update thermal load from Pond activity
        self._update_thermal()

        if not self._active:
            # BOOT ward: always HEALTHY, no state machine
            self._state = HEALTHY
            return self.status

        self._cycles_observed += 1

        # ── Update emission history ───────────────────────────────────────
        self._emission_history.append(emissions)
        if len(self._emission_history) > self.HISTORY_WINDOW:
            self._emission_history.pop(0)

        if emissions > self._peak_emissions:
            self._peak_emissions = emissions

        if emissions > 0:
            self._had_activity   = True
            self._consecutive_zeros = 0
            self._last_nonzero_at = time.time()
        else:
            self._consecutive_zeros += 1

        # ── Bridge health check (all types) ──────────────────────────────
        if not self._bridge_alive():
            self._set_anomaly(OFFLINE, "bridge cells deallocated")
            return self.status

        # ── Type-specific state machine ───────────────────────────────────
        from pond import PROCESS, PERIPHERAL, LIBRARY, FILE, COMPANION

        if self._pond_type == PROCESS:
            self._tick_process()

        elif self._pond_type == PERIPHERAL:
            self._tick_peripheral()

        elif self._pond_type == LIBRARY:
            self._tick_library()

        elif self._pond_type in (FILE, COMPANION):
            # Minimal: bridge alive (already checked) → healthy
            self._set_healthy()

        # Update counters
        if self._state == HEALTHY:
            self._cycles_healthy += 1
        elif self._state == DEGRADED:
            self._cycles_degraded += 1
        elif self._state == STALLED:
            self._cycles_stalled += 1
        elif self._state == SILENT:
            self._cycles_silent += 1

        # PTT health check
        if self._ptt is not None:
            self._check_ptt()

        return self.status

    @property
    def state(self) -> str:
        return self._state

    @property
    def status(self) -> WardStatus:
        from pond_ptt import STATUS_ACTIVE, STATUS_FAULTED, STATUS_IDLE
        mean = (sum(self._emission_history) / len(self._emission_history)
                if self._emission_history else 0.0)

        ptt_entries = ptt_active = ptt_faulted = ptt_idle = 0
        ptt_faulted_labels: list = []
        if self._ptt is not None:
            ptt_entries = len(self._ptt)
            ptt_active  = self._ptt.active_count()
            ptt_faulted = self._ptt.faulted_count()
            ptt_idle    = len(self._ptt.entries_by_status(STATUS_IDLE))
            if ptt_faulted:
                faulted = self._ptt.entries_by_status(STATUS_FAULTED)
                ptt_faulted_labels = [e.label or f"PTT[{e.index}]"
                                      for e in faulted[:10]]

        return WardStatus(
            state               = self._state,
            pond_type           = self._pond_type,
            cycles_observed     = self._cycles_observed,
            cycles_healthy      = self._cycles_healthy,
            cycles_degraded     = self._cycles_degraded,
            cycles_stalled      = self._cycles_stalled,
            cycles_silent       = self._cycles_silent,
            last_anomaly_at     = self._last_anomaly_at,
            anomaly_reason      = self._anomaly_reason,
            mean_emissions      = mean,
            peak_emissions      = self._peak_emissions,
            last_nonzero_at     = self._last_nonzero_at,
            ptt_entries         = ptt_entries,
            ptt_active          = ptt_active,
            ptt_faulted         = ptt_faulted,
            ptt_idle            = ptt_idle,
            ptt_faulted_labels  = ptt_faulted_labels,
        )

    def reset(self) -> None:
        """
        Reset the Ward state machine to IDLE.
        Called when a Pond is recovered after an anomaly, or on test reset.
        """
        self._state             = IDLE
        self._cycles_observed   = 0
        self._cycles_healthy    = 0
        self._cycles_degraded   = 0
        self._cycles_stalled    = 0
        self._cycles_silent     = 0
        self._emission_history  = []
        self._peak_emissions    = 0
        self._consecutive_zeros = 0
        self._had_activity      = False
        self._last_nonzero_at   = None
        self._last_anomaly_at   = None
        self._anomaly_reason    = ""

    # ── Type-specific state machines ──────────────────────────────────────────

    def _tick_process(self) -> None:
        """
        PROCESS Ward: watch for stalls and throttle.

        A stall is consecutive zero emissions after a period of activity
        (warmup complete AND had_activity). Throttle from the MONITOR
        bridge raises DEGRADED.
        """
        monitor = self._get_monitor()

        # Throttle check (takes priority over stall — degraded not stalled
        # if the Pond is busy but overwhelmed)
        if monitor and monitor.is_throttled:
            self._set_anomaly(DEGRADED,
                              f"throttled at {round(monitor.utilisation_pct, 1)}%")
            return

        # Stall check: only after warmup and after the Pond has been active
        if (self._had_activity
                and self._cycles_observed >= self.WARMUP_CYCLES
                and self._consecutive_zeros >= self.STALL_THRESHOLD):
            self._set_anomaly(STALLED,
                              f"zero emissions for {self._consecutive_zeros} cycles")
            return

        self._set_healthy()

    def _tick_peripheral(self) -> None:
        """
        PERIPHERAL Ward: watch for unexpected device silence.

        SILENT is raised when a device that was emitting goes quiet for
        SILENCE_THRESHOLD consecutive cycles. This is the physical footprint
        of disconnection or failure.
        """
        if (self._had_activity
                and self._cycles_observed >= self.WARMUP_CYCLES
                and self._consecutive_zeros >= self.SILENCE_THRESHOLD):
            self._set_anomaly(SILENT,
                              f"device silent for {self._consecutive_zeros} cycles")
            return

        self._set_healthy()

    def _tick_library(self) -> None:
        """
        LIBRARY Ward: track request/response balance.

        DEGRADED if inbound requests are arriving but outbound responses
        have dropped to zero — tiles are being requested but not returning
        results. This suggests a pipeline depth mismatch or tile failure.
        """
        inbound  = self._get_bridge_role("INBOUND")
        outbound = self._get_bridge_role("OUTBOUND")

        if (inbound and outbound
                and inbound.packets_passed > 0
                and outbound.packets_passed == 0
                and self._cycles_observed >= self.WARMUP_CYCLES):
            self._set_anomaly(DEGRADED,
                              "inbound requests with zero outbound responses")
            return

        self._set_healthy()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _bridge_alive(self) -> bool:
        """True if the Pond still has at least one bridge cell allocated."""
        return len(self._pond.bridges) > 0

    def _check_ptt(self) -> None:
        """
        Scan the PTT status column for anomalies.

        O(n) over PTT entries, not over array cells. For a 2048-entry
        PTT this is a small fixed cost per tick.

        FAULTED entries → escalates Ward to DEGRADED (unless already
        in a worse state) and includes labels in anomaly_reason.
        """
        from pond_ptt import STATUS_FAULTED
        faulted = self._ptt.entries_by_status(STATUS_FAULTED)
        if faulted:
            labels = [e.label or f"PTT[{e.index}]" for e in faulted[:5]]
            reason = f"PTT faulted: {', '.join(labels)}"
            if len(faulted) > 5:
                reason += f" (+{len(faulted)-5} more)"
            if self._state not in (OFFLINE, STALLED):
                self._set_anomaly(DEGRADED, reason)

    def _get_monitor(self) -> Optional["PondBridge"]:
        for b in self._pond.bridges:
            if b.role == "MONITOR":
                return b
        return None

    def _get_bridge_role(self, role: str) -> Optional["PondBridge"]:
        for b in self._pond.bridges:
            if b.role == role:
                return b
        return None

    def _set_healthy(self) -> None:
        if self._state == IDLE or self._state != HEALTHY:
            # Transition into HEALTHY — clear any prior anomaly reason
            # but preserve the history of when the last anomaly occurred
            pass
        self._state = HEALTHY

    def _set_anomaly(self, new_state: str, reason: str) -> None:
        self._state           = new_state
        self._anomaly_reason  = reason
        self._last_anomaly_at = time.time()

    def __repr__(self) -> str:
        return (f"Ward({self._pond.name!r} "
                f"type={self._pond_type} "
                f"state={self._state} "
                f"cycles={self._cycles_observed})")


# ── Ward factory ─────────────────────────────────────────────────────────────

def make_ward(pond: "Pond") -> Ward:
    """
    Create the appropriate Ward for a Pond.
    Currently all types use the same Ward class with type-based dispatch.
    Returns None for BOOT ponds (no Ward needed — ROM is static).
    """
    from pond import BOOT
    if pond.pond_type == BOOT:
        return None
    return Ward(pond)
