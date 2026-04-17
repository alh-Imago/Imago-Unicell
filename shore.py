"""
shore.py — The Shore: Personal Session State

Implements Section 8 of the Pond, UniFlex & Discovery Specification v0.1.

The Shore is the Caster's device — the personal space from which every Cast
departs and to which every Ripple returns. It maintains the personal token
space, suppression records, session state, discovery history, and preference
settings for one identity.

Shore maintains:
  - Personal token space: stable addresses for all discovered resources
  - Suppression records: Ponds/casts already seen, not to resurface
  - Session state: active Pond connections, allocated cell regions
  - Discovery history: previous Ripple results, cached resource records
  - Preference settings: visibility defaults, cast thresholds, filters
"""

from __future__ import annotations

import time
import hashlib
from dataclasses import dataclass, field
from typing import Optional

from pond import TokenSpace, PointerToken, RT_FILE, RT_DEVICE, RT_TILE
from cast import ReturnWave, RippleResult, VIS_ANONYMOUS


# ── Suppression record ────────────────────────────────────────────────────────

@dataclass
class SuppressionRecord:
    """
    Records that a Pond or cast has been seen and should not resurface
    unless it changes beyond the Shore's threshold.

    pond_id:          the Pond this record covers
    change_signature: hash of the resource record at last surfacing
    suppressed_at:    timestamp of suppression
    threshold:        what change level triggers re-surfacing
                      "any" | "major" | "never"
    """
    pond_id:          str
    change_signature: str
    suppressed_at:    float
    threshold:        str = "major"   # "any" | "major" | "never"

    def should_surface(self, new_signature: str) -> bool:
        """True if the new state is different enough to show again."""
        if self.threshold == "never":
            return False
        if self.threshold == "any":
            return new_signature != self.change_signature
        # "major": only surface if signature changed
        return new_signature != self.change_signature


def _record_signature(resource_record: dict) -> str:
    """Compute a change signature from the key fields of a resource record."""
    fields = {k: resource_record.get(k)
              for k in ("name", "pond_type", "security_level",
                        "free_cells", "file_count", "tokens_used")}
    return hashlib.md5(str(sorted(fields.items())).encode()).hexdigest()[:16]


# ── ActiveSession ─────────────────────────────────────────────────────────────

@dataclass
class ActiveSession:
    """One active connection to a Pond from this Shore."""
    pond_id:          str
    pond_name:        str
    connected_at:     float
    allocated_cells:  list[int] = field(default_factory=list)
    tokens_held:      list[int] = field(default_factory=list)  # token_ids
    last_activity:    float     = field(default_factory=time.time)


# ── ShorePreferences ──────────────────────────────────────────────────────────

@dataclass
class ShorePreferences:
    """
    Configurable Shore behaviour (Section 8).

    default_visibility:  cast visibility level for new casts
    commercial_threshold: when to resurface commercial casts
                          "any" | "major" | "never"
    auto_suppress_repeat: suppress identical casts automatically
    max_history:         how many past wave results to keep
    """
    default_visibility:   str  = VIS_ANONYMOUS
    commercial_threshold: str  = "major"
    auto_suppress_repeat: bool = True
    max_history:          int  = 100


# ── Shore ─────────────────────────────────────────────────────────────────────

class Shore:
    """
    Personal session state for one identity.

    The Shore is the Caster's device — the origin and destination of every
    Cast. It maintains personal token space, suppression records, session
    state, and discovery history for one identity.

    In the full architecture the Shore exists both locally (on the person's
    device) and in the cloud (encrypted, only the person holds the key).
    In the simulator it is an in-memory object attached to an identity.
    """

    # Token space starts well above Pond token space
    _SHORE_TOKEN_BASE = 0x0200_0000_0000_0000

    def __init__(self, identity_id: str,
                 preferences: Optional[ShorePreferences] = None):
        self.identity_id = identity_id
        self.created_at  = time.time()
        self.preferences = preferences or ShorePreferences()

        # Personal token space (Section 8 — "stable addresses for all
        # discovered resources")
        self.tokens = TokenSpace(
            pond_id          = f"shore_{identity_id[:8]}",
            reservation_size = 1_048_576,   # 1M tokens for the Shore
        )

        # Suppression records: pond_id → SuppressionRecord
        self._suppressed: dict[str, SuppressionRecord] = {}

        # Active sessions: pond_id → ActiveSession
        self._sessions: dict[str, ActiveSession] = {}

        # Discovery history: list of ReturnWave summaries (newest first)
        self._history: list[dict] = []

    # ── Discovery history ─────────────────────────────────────────────────────

    def record_wave(self, wave: ReturnWave):
        """
        Record a completed ReturnWave in the discovery history.
        Applies auto-suppression if enabled.
        """
        summary = wave.summary()
        summary["results"] = [
            {
                "pond_id":   r.pond_id,
                "pond_type": r.resource_record.get("pond_type"),
                "name":      r.resource_record.get("name"),
                "hop":       r.hop,
            }
            for r in wave.by_hop()
        ]
        self._history.insert(0, summary)
        # Trim history
        if len(self._history) > self.preferences.max_history:
            self._history = self._history[:self.preferences.max_history]

        # Auto-suppress if enabled
        if self.preferences.auto_suppress_repeat:
            for result in wave.results:
                sig = _record_signature(result.resource_record)
                self._suppressed.setdefault(
                    result.pond_id,
                    SuppressionRecord(
                        pond_id          = result.pond_id,
                        change_signature = sig,
                        suppressed_at    = time.time(),
                        threshold        = self.preferences.commercial_threshold,
                    )
                )

    def filter_wave(self, wave: ReturnWave) -> list[RippleResult]:
        """
        Filter a ReturnWave through Shore suppression records.
        Returns only results that should be surfaced to the user.
        Unsuppressed results are shown; already-seen unchanged ones are hidden.
        """
        surfaced = []
        for result in wave.by_hop():
            rec = self._suppressed.get(result.pond_id)
            if rec is None:
                surfaced.append(result)
            else:
                sig = _record_signature(result.resource_record)
                if rec.should_surface(sig):
                    rec.change_signature = sig   # update
                    surfaced.append(result)
        return surfaced

    # ── Suppression management ────────────────────────────────────────────────

    def suppress(self, pond_id: str,
                 resource_record: dict,
                 threshold: str = "major"):
        """Manually suppress a Pond from future discovery results."""
        sig = _record_signature(resource_record)
        self._suppressed[pond_id] = SuppressionRecord(
            pond_id          = pond_id,
            change_signature = sig,
            suppressed_at    = time.time(),
            threshold        = threshold,
        )

    def unsuppress(self, pond_id: str) -> bool:
        """Remove suppression for a Pond. Returns True if it was suppressed."""
        return self._suppressed.pop(pond_id, None) is not None

    def is_suppressed(self, pond_id: str,
                      resource_record: Optional[dict] = None) -> bool:
        """
        True if this Pond is currently suppressed and its record
        has not changed beyond the suppression threshold.
        """
        rec = self._suppressed.get(pond_id)
        if rec is None:
            return False
        if resource_record is None:
            return True
        sig = _record_signature(resource_record)
        return not rec.should_surface(sig)

    # ── Session management ────────────────────────────────────────────────────

    def connect(self, pond_id: str, pond_name: str) -> ActiveSession:
        """Record a new active session with a Pond."""
        session = ActiveSession(
            pond_id      = pond_id,
            pond_name    = pond_name,
            connected_at = time.time(),
        )
        self._sessions[pond_id] = session
        return session

    def disconnect(self, pond_id: str) -> bool:
        """Close a session. Returns True if it existed."""
        return self._sessions.pop(pond_id, None) is not None

    def get_session(self, pond_id: str) -> Optional[ActiveSession]:
        return self._sessions.get(pond_id)

    @property
    def active_sessions(self) -> list[ActiveSession]:
        return list(self._sessions.values())

    # ── Inspection ────────────────────────────────────────────────────────────

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    @property
    def suppressed_count(self) -> int:
        return len(self._suppressed)

    def status(self) -> dict:
        return {
            "identity_id":     self.identity_id[:8] + "...",
            "created_at":      self.created_at,
            "tokens_used":     self.tokens.used,
            "active_sessions": len(self._sessions),
            "suppressed_ponds": len(self._suppressed),
            "history_entries": len(self._history),
            "preferences":     {
                "default_visibility":   self.preferences.default_visibility,
                "commercial_threshold": self.preferences.commercial_threshold,
                "auto_suppress_repeat": self.preferences.auto_suppress_repeat,
            },
        }

    def __repr__(self):
        return (f"Shore({self.identity_id[:8]}... "
                f"sessions={len(self._sessions)} "
                f"suppressed={len(self._suppressed)} "
                f"history={len(self._history)})")
