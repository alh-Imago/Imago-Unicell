"""
cast.py — Cast and Ripple Discovery Mechanism

Implements Section 7 of the Pond, UniFlex & Discovery Specification v0.1.

The Cast is an intentional discovery act. The Ripple is what it sets in motion:
a propagation across reachable Ponds returning a unified view of all resources.

Because everything is a Pond, a single Cast discovers everything simultaneously:
compute capacity, mounted files, connected devices, available tiles. No separate
discovery mechanism for different resource types.

Cast types (Section 7.2):
  Pebble Cast    — single named Pond, one hop, direct contact
  Ripple Cast    — all reachable Ponds, outward from origin, hop-limited
  Skipping Stone — multiple named Ponds, targeted hops in sequence
  Silent         — no Cast made, device present but not interacting

Mandatory owner announcement (Section 7.5):
  Every Cast announces to the Pond owner at point of contact.
  Cannot be disabled by Caster or waived by Pond owner.
  Owner always knows. Other occupants see only what the visibility level allows.

Cast visibility levels (Section 7.6):
  ANONYMOUS — announces to owner only; invisible to other occupants and network
  PRIVATE   — announces to owner + previously known contacts
  PUBLIC    — fully visible to all occupants and network
  SILENT    — no Cast made; cannot touch a Pond
"""

from __future__ import annotations

import time
from pond_types import SCOPE_LOCAL, SCOPE_SHORE, SCOPE_EXTENDED
from dataclasses import dataclass, field
from typing import Optional

from pond import Pond, PondManager, OPEN, PRIVATE, HIDDEN

# ── Visibility levels ─────────────────────────────────────────────────────────

VIS_ANONYMOUS = "ANONYMOUS"
VIS_PRIVATE   = "PRIVATE"
VIS_PUBLIC    = "PUBLIC"
VIS_SILENT    = "SILENT"

VISIBILITY_LEVELS = (VIS_ANONYMOUS, VIS_PRIVATE, VIS_PUBLIC, VIS_SILENT)


# ── Stone (one unit of propagation) ──────────────────────────────────────────

@dataclass
class Stone:
    """
    One Cast in flight — a 'stone' thrown into the network.

    caster_id:   identity of the Caster (always announced to owner)
    visibility:  what the Caster shows to other occupants / network
    query:       optional search parameters (pond_type filter, name pattern)
    hop_limit:   max hops for Skipping Stone; 1 for Pebble Cast
    collect_all: if False, stop at first match; if True, collect all
    cast_time:   Unix timestamp of Cast initiation
    """
    caster_id:    str
    visibility:   str  = VIS_ANONYMOUS
    query:        dict = field(default_factory=dict)
    hop_limit:    int  = 1
    collect_all:  bool = True
    process_mask: int  = 0xFFFFFFFF   # caller's identity mask; filters results
    cast_time:   float = field(default_factory=time.time)
    # Scope-ordered search: LOCAL first, SHORE second, EXTENDED last.
    # Stone stops at nearest scope that returns a result (unless collect_all).
    preferred_scope: str = SCOPE_LOCAL   # start scope for search order

    def __post_init__(self):
        if self.visibility not in VISIBILITY_LEVELS:
            raise ValueError(
                f"Invalid visibility '{self.visibility}'. "
                f"Must be one of {VISIBILITY_LEVELS}.")
        if self.visibility == VIS_SILENT:
            raise ValueError(
                "A Silent Cast cannot touch a Pond — "
                "silence and contact are mutually exclusive.")


# ── RippleResult (one Pond's response) ───────────────────────────────────────

@dataclass
class RippleResult:
    """
    What one Pond contributes to a returning wave.

    pond_id:        the responding Pond
    resource_record: the Pond's current resource record
    hop:            how many hops from the Caster's origin
    timestamp:      when this result was collected
    announced_to_owner: True — mandatory, always

    If the Pond has a PTT attached, resource_record["ptt"]["manifest"]
    contains the complete Pond inventory — no array scanning needed.
    Use manifest() to access it directly.
    """
    pond_id:              str
    resource_record:      dict
    hop:                  int
    timestamp:            float
    announced_to_owner:   bool = True   # always True — Section 7.5

    def manifest(self) -> list:
        """
        Return the PTT manifest for this Pond — the complete list of
        tiles, bridges, and storage cells with their types and statuses.

        Returns empty list if no PTT is attached to the Pond.
        This is the Cast/Ripple inventory path — one call, full contents,
        no array scanning.
        """
        ptt = self.resource_record.get("ptt")
        if ptt is None:
            return []
        return ptt.get("manifest", [])

    def find_in_manifest(self, label: str = "",
                         entry_type: str = "",
                         status: str = "ACTIVE") -> list:
        """
        Search the PTT manifest for entries matching the given criteria.

        label:       partial match on entry label (case-insensitive)
        entry_type:  exact match on type (TILE_IN, TILE_OUT, BRIDGE, etc.)
        status:      exact match on status (default: ACTIVE)

        Returns matching manifest entries as dicts.
        """
        results = []
        for entry in self.manifest():
            if status and entry.get("status") != status:
                continue
            if entry_type and entry.get("type") != entry_type:
                continue
            if label and label.lower() not in entry.get("label", "").lower():
                continue
            results.append(entry)
        return results


# ── ReturnWave (assembled results from one Cast) ──────────────────────────────

@dataclass
class ReturnWave:
    """
    The complete set of results returning to the Shore after a Cast.
    Results arrive ordered by hop (nearest Pond first — Section 7.3).
    """
    stone:    Stone
    results:  list[RippleResult] = field(default_factory=list)
    complete: bool               = False

    def add(self, result: RippleResult):
        self.results.append(result)

    def by_hop(self) -> list[RippleResult]:
        return sorted(self.results, key=lambda r: r.hop)

    def first_match(self, pond_type: Optional[str] = None) -> Optional[RippleResult]:
        """Return the nearest result matching pond_type (or any if None)."""
        for r in self.by_hop():
            if pond_type is None:
                return r
            if r.resource_record.get("pond_type") == pond_type:
                return r
        return None

    def summary(self) -> dict:
        by_type: dict[str, int] = {}
        for r in self.results:
            t = r.resource_record.get("pond_type", "UNKNOWN")
            by_type[t] = by_type.get(t, 0) + 1
        return {
            "cast_time":   self.stone.cast_time,
            "caster_id":   self.stone.caster_id[:8] + "...",
            "visibility":  self.stone.visibility,
            "hops":        self.stone.hop_limit,
            "ponds_found": len(self.results),
            "by_type":     by_type,
            "complete":    self.complete,
        }


# ── CastEngine ────────────────────────────────────────────────────────────────

class CastEngine:
    """
    Executes Casts against a PondManager.

    In a physical system the Ripple propagates across UniLink Prism and
    UniLink Wave channels. In the simulator it operates over the in-memory
    PondManager, which holds all registered Ponds as if they were reachable
    over a single-hop local network.

    Mandatory owner announcement (Section 7.5):
      For every Pond touched, the stone announces the caster_id to the
      Pond's owner via the visit log. This cannot be suppressed.
    """

    def __init__(self, pond_manager: PondManager):
        self._manager = pond_manager

    # ── Pebble Cast ───────────────────────────────────────────────────────────

    def pebble_cast(self, caster_id: str, pond_name: str,
                    visibility: str = VIS_ANONYMOUS,
                    query: Optional[dict] = None) -> ReturnWave:
        """
        Cast a stone into a single named Pond (Section 7.2 — Pebble Cast).
        One hop, direct contact, full resource record returned.
        """
        stone = Stone(
            caster_id   = caster_id,
            visibility  = visibility,
            query       = query or {},
            hop_limit   = 1,
            collect_all = False,
        )
        wave = ReturnWave(stone=stone)

        pond = self._manager.get_pond_by_name(pond_name)
        if pond is None:
            wave.complete = True
            return wave

        result = self._touch_pond(pond, stone, hop=1)
        if result is not None:
            wave.add(result)
        wave.complete = True
        return wave

    # ── Ripple Cast ───────────────────────────────────────────────────────────

    def ripple_cast(self, caster_id: str,
                    visibility: str  = VIS_ANONYMOUS,
                    query: Optional[dict] = None,
                    hop_limit: int   = 1,
                    collect_all: bool = True,
                    process_mask: int = 0xFFFFFFFF,
                    preferred_scope: str = SCOPE_LOCAL) -> ReturnWave:
        """
        Cast a ripple across all reachable Ponds (Section 7.2 — Ripple Cast).
        Returns progressive results nearest-first.

        Scope-ordered search: LOCAL → SHORE → EXTENDED
          - LOCAL results are returned before SHORE results
          - SHORE results are returned before EXTENDED results
          - If collect_all=False, stops at first match in nearest scope

        In the simulator all Ponds are treated as reachable.
        Scope order is enforced by sorting results after collection.

        process_mask: caller's identity mask — Ponds with no mask overlap
          are absent from results (not denied — simply not visible).
        """
        stone = Stone(
            caster_id       = caster_id,
            visibility      = visibility,
            query           = query or {},
            hop_limit       = hop_limit,
            collect_all     = collect_all,
            process_mask    = process_mask,
            preferred_scope = preferred_scope,
        )
        wave = ReturnWave(stone=stone)

        # Search order: LOCAL first, SHORE second, EXTENDED last.
        # Each scope is searched completely before moving to the next.
        scope_order = [SCOPE_LOCAL, SCOPE_SHORE, SCOPE_EXTENDED]

        for scope in scope_order:
            scope_results = []
            for pond in self._manager._ponds.values():
                # Scope filter: only touch Ponds at the current scope level
                pond_scope = getattr(pond, 'scope', SCOPE_LOCAL)
                if pond_scope != scope:
                    continue
                result = self._touch_pond(pond, stone, hop=1)
                if result is not None:
                    scope_results.append(result)

            for result in scope_results:
                wave.add(result)
                if not collect_all:
                    wave.complete = True
                    return wave

            # If we found results at this scope and not collecting all,
            # we would have returned above. If collect_all, continue.
            # If preferred_scope matches and results found, we could stop —
            # but collect_all=True means gather everything visible.

        wave.complete = True
        return wave

    # ── Skipping Stone ────────────────────────────────────────────────────────

    def skipping_stone(self, caster_id: str, pond_names: list[str],
                       visibility: str  = VIS_ANONYMOUS,
                       query: Optional[dict] = None) -> ReturnWave:
        """
        Touch multiple named Ponds in sequence (Section 7.2 — Skipping Stone).
        Each hop is one named Pond. Results accumulate as the stone skips.
        Privacy: no Pond knows which other Ponds the stone has touched.
        """
        stone = Stone(
            caster_id   = caster_id,
            visibility  = visibility,
            query       = query or {},
            hop_limit   = len(pond_names),
            collect_all = True,
        )
        wave = ReturnWave(stone=stone)

        for hop, name in enumerate(pond_names, start=1):
            pond = self._manager.get_pond_by_name(name)
            if pond is None:
                continue
            result = self._touch_pond(pond, stone, hop=hop)
            if result is not None:
                wave.add(result)

        wave.complete = True
        return wave

    # ── Core touch logic ──────────────────────────────────────────────────────

    def _touch_pond(self, pond: Pond, stone: Stone,
                    hop: int) -> Optional[RippleResult]:
        """
        Touch one Pond with the stone.

        Mandatory owner announcement (Section 7.5):
          Always announce caster_id to the Pond owner via the visit log.
          This happens before any visibility/whitelist check on the resource
          record. The owner always knows.

        HIDDEN Pond handling:
          If the Pond is HIDDEN and the caster is not whitelisted,
          the stone passes over without contact. No announcement, no log
          entry, no response. The Pond does not exist from the stone's view.
        """
        # HIDDEN check first — before any announcement
        if pond.security_level == HIDDEN:
            if (stone.caster_id != pond.owner_id and
                    stone.caster_id not in pond._whitelist):
                return None   # Stone passes over silently

        # Bidirectional mask check — invisible = nonexistent
        # The stone carries the caller's process_mask.
        # Any bridge mask mismatch means the Pond is invisible.
        process_mask = getattr(stone, 'process_mask', 0xFFFFFFFF)
        if process_mask != 0xFFFFFFFF:
            inbound_bridge = pond._get_bridge("INBOUND")
            if not inbound_bridge.check_mask(process_mask):
                return None   # Mask mismatch — Pond absent, not denied

        # Mandatory owner announcement — always recorded
        inbound = pond._get_bridge("INBOUND")
        inbound.check_access(stone.caster_id, process_mask=process_mask)

        # Apply query filter if provided
        rec = pond.resource_record()
        if not self._matches_query(rec, stone.query):
            return None

        return RippleResult(
            pond_id          = pond.pond_id,
            resource_record  = rec,
            hop              = hop,
            timestamp        = time.time(),
            announced_to_owner = True,
        )

    def _matches_query(self, record: dict, query: dict) -> bool:
        """
        Check if a resource record matches query parameters.
        Empty query matches everything.

        Supported keys:
          pond_type:      exact match on Pond type
          name_contains:  substring match on Pond name
          security_level: exact match on security level
          has_tile:       label substring match in PTT manifest
          ptt_active_min: minimum number of ACTIVE PTT entries
          ptt_faulted:    True = only return Ponds with faulted PTT entries
          ward_state:     exact match on Ward state string
          search_query:   heuristic text search against PTT manifest labels.
                          Matches if any label scores > 0 for this query.
        """
        if not query:
            return True
        if "pond_type" in query:
            if record.get("pond_type") != query["pond_type"]:
                return False
        if "name_contains" in query:
            if query["name_contains"].lower() not in record.get("name","").lower():
                return False
        if "security_level" in query:
            if record.get("security_level") != query["security_level"]:
                return False
        if "ward_state" in query:
            ward = record.get("ward") or {}
            if ward.get("state") != query["ward_state"]:
                return False

        # PTT-based queries — only apply when PTT is present
        ptt = record.get("ptt")
        if "has_tile" in query:
            if ptt is None:
                return False
            needle = query["has_tile"].lower()
            manifest = ptt.get("manifest", [])
            if not any(needle in e.get("label", "").lower()
                       for e in manifest):
                return False
        if "ptt_active_min" in query:
            if ptt is None:
                return False
            if ptt.get("active", 0) < query["ptt_active_min"]:
                return False
        if "ptt_faulted" in query and query["ptt_faulted"]:
            if ptt is None or ptt.get("faulted", 0) == 0:
                return False

        if "search_query" in query:
            if ptt is None:
                return False
            sq = query["search_query"].lower()
            manifest = ptt.get("manifest", [])
            def _score_label(label, q):
                if q == label.lower():
                    return 10
                q_words = set(q.split())
                t_words = set(label.lower().split())
                matched = q_words & t_words
                if not matched:
                    return sum(1 for qw in q_words
                               if any(qw in tw for tw in t_words))
                return 5 * len(matched) if q_words <= t_words else len(matched)
            if not any(_score_label(e.get("label", ""), sq) > 0
                       for e in manifest):
                return False

        return True
