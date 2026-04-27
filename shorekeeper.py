"""
shorekeeper.py — ShoreKeeper: per-card Shore + Ward collective + boundary authority

The ShoreKeeper is a SHOREKEEPER-type Pond that:
  1. Acts as the local Shore registry for one physical card
  2. Aggregates individual Pond Ward states into a card health picture
  3. Validates all cross-card traffic (auth + mask check at boundary)
  4. Reports aggregated heartbeat summaries to HyperShore on the master card
  5. Manages thermal accounting across the card

Architecture
============

    Individual Wards  →  ShoreKeeper (aggregates)
    ShoreKeeper       →  HyperShore  (one heartbeat packet per interval)
    HyperShore        →  HyperCompanion (global policy)

One ShoreKeeper per physical card. Self-hosted on the card's own NOR cells.
Runs as a SHOREKEEPER pond — permanent_anchor=True, security=HIDDEN.

Cross-card traffic validation:
    Source Pond → Source ShoreKeeper: auth check + mask check + PTT translate
    Target ShoreKeeper: inbound mask check + PTT translate + deliver

Heartbeat packet structure:
    {card_id, timestamp, healthy_ponds, degraded_ponds, isolated_ponds,
     thermal_load, thermal_trend, peak_zone, armed_cells, bus_utilisation,
     escalations}

Usage
=====

    from shorekeeper import ShoreKeeper

    sk = ShoreKeeper(card_id="card_0", controller=ctrl, pond_manager=mgr)

    # Register ponds with this ShoreKeeper
    sk.register_pond(pond)

    # Call each tick (or on a heartbeat interval)
    heartbeat = sk.tick()

    # Get current card health
    health = sk.card_health()
"""

from __future__ import annotations

import time
from pond_types import SCOPE_LOCAL, SCOPE_SHORE, SCOPE_EXTENDED
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from controller import ImagoController
    from pond import PondManager, Pond
    from ward import Ward


# ── Heartbeat packet ──────────────────────────────────────────────────────────

@dataclass
class ShoreKeeperHeartbeat:
    """
    Aggregated health summary sent to HyperShore each heartbeat interval.
    This is the only cross-card traffic for monitoring — never raw cell data.
    """
    card_id:          str
    timestamp:        float
    tick_count:       int
    healthy_ponds:    int   = 0
    degraded_ponds:   int   = 0
    isolated_ponds:   int   = 0
    stalled_ponds:    int   = 0
    thermal_load:     float = 0.0   # aggregate % of thermal budget
    thermal_trend:    float = 0.0   # rate of change per heartbeat
    peak_zone:        str   = ""    # hottest block ID
    armed_cells:      int   = 0     # total armed cells across card
    bus_utilisation:  float = 0.0   # % bus capacity used
    escalations:      list  = field(default_factory=list)  # non-empty = needs HyperCompanion
    # Object model — counts per scope level for routing decisions
    local_objects:    int   = 0    # LOCAL PTT entry count
    shore_objects:    int   = 0    # SHORE PTT entry count
    extended_objects: int   = 0    # EXTENDED PTT entry count
    denial_count:     int   = 0    # cumulative denied crossings since last heartbeat
    has_incidents:    bool  = False # any denials or capture windows pending

    def to_dict(self) -> dict:
        return {
            "card_id":         self.card_id,
            "timestamp":       self.timestamp,
            "tick_count":      self.tick_count,
            "healthy_ponds":   self.healthy_ponds,
            "degraded_ponds":  self.degraded_ponds,
            "isolated_ponds":  self.isolated_ponds,
            "stalled_ponds":   self.stalled_ponds,
            "thermal_load":    round(self.thermal_load, 2),
            "thermal_trend":   round(self.thermal_trend, 4),
            "peak_zone":       self.peak_zone,
            "armed_cells":     self.armed_cells,
            "bus_utilisation": round(self.bus_utilisation, 2),
            "escalations":     self.escalations,
            "scope_counts": {
                SCOPE_LOCAL:    self.local_objects,
                SCOPE_SHORE:    self.shore_objects,
                SCOPE_EXTENDED: self.extended_objects,
            },
        }


# ── ShoreKeeper ───────────────────────────────────────────────────────────────

class ShoreKeeper:
    """
    Per-card Shore + Ward collective + boundary authority.

    One instance per physical card. Aggregates Ward states from all
    registered Ponds into a single card health picture. Sends heartbeat
    summaries to HyperShore rather than forwarding raw data.
    """

    def __init__(self,
                 card_id:      str,
                 controller:   "ImagoController" = None,
                 pond_manager: "PondManager"     = None,
                 heartbeat_interval: int         = 100):
        """
        card_id:            unique identifier for this card (e.g. "card_0")
        controller:         ImagoController for this card
        pond_manager:       PondManager for this card
        heartbeat_interval: ticks between heartbeat packets (default 100)
        """
        self.card_id             = card_id
        self._ctrl               = controller
        self._pond_manager       = pond_manager
        self._heartbeat_interval = heartbeat_interval

        self._tick_count:  int   = 0
        self._ponds:       dict  = {}      # pond_id -> Pond
        self._hyper_shore        = None    # reference to HyperShore on master card
        self._last_heartbeat_at: int = 0
        self._heartbeat_history: list = []

        # Auth token for this card (set at boot by CommandInterface.boot_all_cells)
        self._auth_token: int = 0

        # Incident aggregation -- pushed from pond bridge logs
        # denial_incidents: rolling list of denial events across all ponds
        # capture_incidents: completed capture windows from spike/fault events
        # Both are capped to prevent unbounded growth at server scale
        self._denial_incidents:  list = []   # BridgeCrossingRecord dicts
        self._capture_incidents: list = []   # lists of BridgeCrossingRecord dicts
        self.DENIAL_CAP  = 5000    # max denial records across all ponds on card
        self.CAPTURE_CAP = 100     # max capture windows kept

        print(f"[SHOREKEEPER] '{card_id}' initialised")

    # ── Pond registration ─────────────────────────────────────────────────────

    def register_pond(self, pond: "Pond") -> None:
        """Register a Pond with this ShoreKeeper for monitoring."""
        self._ponds[pond.pond_id] = pond
        # Attach this ShoreKeeper as the bridge log recipient
        pond.bridge_log.attach_shorekeeper(self)
        # Set thermal config on pond's Ward
        if hasattr(pond, 'ward') and pond.ward is not None:
            pond.ward.set_thermal_config(
                limit=100.0,
                zone=self._assign_zone(pond)
            )

    def unregister_pond(self, pond_id: str) -> None:
        """Remove a Pond from ShoreKeeper monitoring."""
        self._ponds.pop(pond_id, None)

    # ── Bridge log incident aggregation ───────────────────────────────────────

    def receive_denial(self, record) -> None:
        """
        Receive a pushed denial event from a pond bridge log.
        Called automatically by BridgeLog when a crossing is denied.
        Aggregates across all ponds on this card.
        """
        d = record.to_dict() if hasattr(record, 'to_dict') else record
        if len(self._denial_incidents) >= self.DENIAL_CAP:
            self._denial_incidents.pop(0)
        self._denial_incidents.append(d)

    def receive_capture(self, records: list) -> None:
        """
        Receive a completed capture window from a pond bridge log.
        Called automatically by BridgeLog when a capture window completes
        (spike detected, Ward trigger, or N entries collected).
        """
        window = [r.to_dict() if hasattr(r, 'to_dict') else r for r in records]
        if len(self._capture_incidents) >= self.CAPTURE_CAP:
            self._capture_incidents.pop(0)
        self._capture_incidents.append({
            "completed_at": __import__('time').time(),
            "record_count": len(window),
            "records":      window,
        })

    def get_denial_incidents(self, limit: int = 100) -> list[dict]:
        """Return recent denial incidents across all ponds on this card."""
        return self._denial_incidents[-limit:]

    def get_capture_incidents(self, limit: int = 10) -> list[dict]:
        """Return recent capture windows across all ponds on this card."""
        return self._capture_incidents[-limit:]

    def incident_summary(self) -> dict:
        """Summary of incidents for Cast/Ripple and heartbeat."""
        return {
            "denial_count":   len(self._denial_incidents),
            "capture_count":  len(self._capture_incidents),
            "has_incidents":  len(self._denial_incidents) > 0,
        }

    def _assign_zone(self, pond: "Pond") -> str:
        """Assign a thermal zone label based on cell addresses."""
        cells = set()
        for bridge in getattr(pond, 'bridges', []):
            cells.update(getattr(bridge, 'cell_addresses', []))
        cells.update(getattr(pond, '_pool_cells', []))
        if not cells:
            return ""
        # Zone = block index (65536 cells per block)
        base_cell = min(cells)
        block_idx = base_cell // 65536
        return f"block_{block_idx}"

    # ── HyperShore connection ─────────────────────────────────────────────────

    def connect_hyper_shore(self, hyper_shore: "HyperShore") -> None:
        """Connect this ShoreKeeper to HyperShore on the master card."""
        self._hyper_shore = hyper_shore
        print(f"[SHOREKEEPER] '{self.card_id}' connected to HyperShore")

    # ── Tick / heartbeat ──────────────────────────────────────────────────────

    def tick(self) -> Optional[ShoreKeeperHeartbeat]:
        """
        Advance ShoreKeeper one tick.

        Calls _update_thermal() on all registered Pond Wards.
        Returns a heartbeat packet every heartbeat_interval ticks,
        or None on intermediate ticks.
        """
        self._tick_count += 1

        # Update thermal for all ponds
        for pond in self._ponds.values():
            w = getattr(pond, 'ward', None)
            if w and hasattr(w, '_update_thermal'):
                w._update_thermal()

        if (self._tick_count - self._last_heartbeat_at) >= self._heartbeat_interval:
            hb = self._build_heartbeat()
            self._last_heartbeat_at = self._tick_count
            self._heartbeat_history.append(hb)
            if len(self._heartbeat_history) > 100:
                self._heartbeat_history.pop(0)
            # Forward to HyperShore
            if self._hyper_shore is not None:
                self._hyper_shore.receive_heartbeat(hb)
            return hb
        return None

    def _build_heartbeat(self) -> ShoreKeeperHeartbeat:
        """Aggregate all Pond Ward states into a heartbeat packet."""
        healthy = degraded = isolated = stalled = 0
        thermal_loads  = []
        thermal_trends = []
        zone_loads:    dict = {}
        armed_total    = 0
        escalations    = []

        for pond in self._ponds.values():
            w = getattr(pond, 'ward', None)
            if w is None:
                continue

            state = getattr(w, '_state', 'UNKNOWN')
            if state in ('HEALTHY', 'IDLE'):  healthy  += 1
            elif state == 'DEGRADED':         degraded += 1
            elif state == 'ISOLATED':         isolated += 1
            elif state == 'STALLED':
                stalled  += 1
                escalations.append({
                    "pond_id": pond.pond_id,
                    "state":   state,
                    "reason":  getattr(w, '_anomaly_reason', ''),
                })

            tload = getattr(w, 'thermal_load', 0.0)
            tlimit= getattr(w, 'thermal_limit', 100.0)
            tpct  = (tload / tlimit * 100) if tlimit > 0 else 0.0
            thermal_loads.append(tpct)
            thermal_trends.append(getattr(w, 'thermal_trend', 0.0))

            zone = getattr(w, 'thermal_zone', '')
            if zone:
                zone_loads[zone] = zone_loads.get(zone, 0.0) + tpct

            # Approximate armed cells from Ward thermal state
            if self._ctrl:
                pond_cells = set()
                for bridge in getattr(pond, 'bridges', []):
                    pond_cells.update(getattr(bridge, 'cell_addresses', []))
                pond_cells.update(getattr(pond, '_pool_cells', []))
                armed_total += len(pond_cells & self._ctrl.array._armed)

        avg_thermal = sum(thermal_loads) / len(thermal_loads) if thermal_loads else 0.0
        avg_trend   = sum(thermal_trends) / len(thermal_trends) if thermal_trends else 0.0
        peak_zone   = max(zone_loads, key=zone_loads.get) if zone_loads else ""

        # Bus utilisation — armed cells as % of array capacity
        bus_util = 0.0
        if self._ctrl:
            total_cells = self._ctrl.array._cell_count
            if total_cells > 0:
                bus_util = armed_total / total_cells * 100

        # Scope counts — how many objects at each level
        local_count = shore_count = extended_count = 0
        for pond in self._ponds.values():
            scope = getattr(pond, 'scope', SCOPE_LOCAL)
            if scope == SCOPE_LOCAL:    local_count    += 1
            elif scope == SCOPE_SHORE:  shore_count    += 1
            else:                       extended_count += 1

        incidents = self.incident_summary()

        return ShoreKeeperHeartbeat(
            card_id          = self.card_id,
            timestamp        = time.time(),
            tick_count       = self._tick_count,
            healthy_ponds    = healthy,
            degraded_ponds   = degraded,
            isolated_ponds   = isolated,
            stalled_ponds    = stalled,
            thermal_load     = round(avg_thermal, 2),
            thermal_trend    = round(avg_trend, 6),
            peak_zone        = peak_zone,
            armed_cells      = armed_total,
            bus_utilisation  = round(bus_util, 2),
            escalations      = escalations,
            local_objects    = local_count,
            shore_objects    = shore_count,
            extended_objects = extended_count,
            denial_count     = incidents["denial_count"],
            has_incidents    = incidents["has_incidents"],
        )

    # ── Card health ───────────────────────────────────────────────────────────

    def card_health(self) -> dict:
        """Current card health summary (from latest heartbeat or live aggregation)."""
        if self._heartbeat_history:
            return self._heartbeat_history[-1].to_dict()
        hb = self._build_heartbeat()
        return hb.to_dict()

    def pond_count(self) -> int:
        return len(self._ponds)

    def last_heartbeat(self) -> Optional[ShoreKeeperHeartbeat]:
        return self._heartbeat_history[-1] if self._heartbeat_history else None

    def __repr__(self) -> str:
        return (f"ShoreKeeper('{self.card_id}', "
                f"{len(self._ponds)} ponds, "
                f"tick={self._tick_count})")


# ── HyperShore ────────────────────────────────────────────────────────────────

class HyperShore:
    """
    Global registry on master card. Aggregates ShoreKeeper heartbeats.
    Managed by HyperCompanion.

    Receives one heartbeat packet per card per heartbeat_interval ticks.
    Cross-card bus carries only these packets — never raw cell data.
    """

    def __init__(self):
        self._cards:      dict = {}   # card_id → latest heartbeat
        self._history:    dict = {}   # card_id → list of heartbeats
        self._callbacks:  list = []   # [(card_id_filter, fn)] escalation callbacks

        print("[HYPERSHORE] Master registry initialised")

    def register_card(self, card_id: str) -> None:
        """Register a card with HyperShore."""
        self._cards[card_id]   = None
        self._history[card_id] = []
        print(f"[HYPERSHORE] Card '{card_id}' registered")

    def receive_heartbeat(self, hb: ShoreKeeperHeartbeat) -> None:
        """Receive and store a heartbeat from a ShoreKeeper."""
        self._cards[hb.card_id] = hb
        if hb.card_id not in self._history:
            self._history[hb.card_id] = []
        self._history[hb.card_id].append(hb)
        if len(self._history[hb.card_id]) > 100:
            self._history[hb.card_id].pop(0)

        # Notify escalation callbacks
        if hb.escalations:
            for card_filter, fn in self._callbacks:
                if card_filter is None or card_filter == hb.card_id:
                    fn(hb)

    def on_escalation(self, fn, card_id: str = None) -> None:
        """Register a callback for escalations (HyperCompanion uses this)."""
        self._callbacks.append((card_id, fn))

    def global_health(self) -> dict:
        """Aggregated health across all cards."""
        total_healthy = total_degraded = total_stalled = 0
        total_thermal = 0.0
        card_count    = 0

        for hb in self._cards.values():
            if hb is None:
                continue
            card_count    += 1
            total_healthy += hb.healthy_ponds
            total_degraded+= hb.degraded_ponds
            total_stalled += hb.stalled_ponds
            total_thermal += hb.thermal_load

        return {
            "cards":           card_count,
            "total_healthy":   total_healthy,
            "total_degraded":  total_degraded,
            "total_stalled":   total_stalled,
            "avg_thermal_pct": round(total_thermal / card_count, 2) if card_count else 0.0,
            "card_states":     {cid: hb.to_dict() if hb else None
                                for cid, hb in self._cards.items()},
        }

    def hottest_card(self) -> Optional[str]:
        """Return card_id of the card with highest thermal load."""
        loaded = {cid: hb.thermal_load
                  for cid, hb in self._cards.items() if hb}
        return max(loaded, key=loaded.get) if loaded else None

    def coolest_card(self) -> Optional[str]:
        """Return card_id of the card with lowest thermal load."""
        loaded = {cid: hb.thermal_load
                  for cid, hb in self._cards.items() if hb}
        return min(loaded, key=loaded.get) if loaded else None

    def cards(self) -> list:
        return list(self._cards.keys())

    def __repr__(self) -> str:
        return f"HyperShore({len(self._cards)} cards)"
