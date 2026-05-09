"""
pond_types.py — Pond Type Registry

Defines every recognised Pond type as a PondTypeSpec in a central
registry. Pond.py reads from here rather than having type behaviour
hardcoded. New types are added by registering a new PondTypeSpec —
no changes to Pond itself.

Every Pond type specifies:

  type_id:          short string identifier used in create_pond()
  description:      human readable
  default_lanes:    (inbound, outbound) default bridge lane widths
  security:         forced security level, or None to let caller decide
  permanent_anchor: True = cannot be destroyed without heritage=True
  ward_active:      False = Ward always returns HEALTHY (ROM / passive)
  ptt_mode:         STATIC or INCREMENTAL (from PondPTT)
  min_bridges:      minimum bridge count
  max_bridges:      maximum bridge count (None = unlimited)
  allow_migrate:    True = Pond can be relocated at runtime
  metadata:         arbitrary extra config passed through to Pond

Built-in types
==============
  PROCESS    — running program or long-running service
  WORKSPACE  — volatile working data, document-backed, incremental PTT
  FILE       — file data in loopback storage cells
  PERIPHERAL — array-side representation of hardware
  LIBRARY    — pre-compiled tile configurations (shared, read-only)
  BOOT       — bootstrap and FS decoder tiles (ROM, no Ward logic)
  COMPANION  — permanent base OS anchor (HIDDEN, single instance)
  DEVICE     — external device bridge (connects hardware to the array)
  SHORE      — system registry Pond (Shore lives inside one of these)
  FS         — filesystem index and metadata Pond

Extending
=========
Register new types at startup:

    from pond_types import registry
    registry.register(PondTypeSpec(
        type_id     = "AI_MODEL",
        description = "Language model inference Pond",
        default_lanes = (1, 4),
        ptt_mode    = "STATIC",
        metadata    = {"model_type": "causal_lm"},
    ))

    # Then use it:
    pond = mgr.create_pond('llama', 'companion', pond_type='AI_MODEL')
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── Security level constants (mirrors pond.py) ────────────────────────────────

OPEN    = "OPEN"
PRIVATE = "PRIVATE"
HIDDEN  = "HIDDEN"

# ── PTT mode constants ────────────────────────────────────────────────────────

PTT_STATIC      = "STATIC"       # built once, frozen — Program Ponds
PTT_INCREMENTAL = "INCREMENTAL"  # updated live — Workspace Ponds
PTT_NONE        = "NONE"         # no PTT (BOOT, minimal Ponds)


# ── Object scope constants ────────────────────────────────────────────────────
# Every object in Claudette belongs to exactly one scope level.
# The scope determines which PTT table holds the object's ID and
# which ShoreKeeper tier manages its routing.
#
# LOCAL    — owned by this stack, visible only within this die group
#            32-bit ID assigned by local Ward / die ShoreKeeper
#            lookup: on-die SRAM, nanoseconds
#
# SHORE    — visible to this card, managed by card ShoreKeeper
#            32-bit ID assigned by ShoreKeeper
#            lookup: on-card bus, microseconds
#
# EXTENDED — visible beyond this card, managed by HyperShore
#            32-bit ID assigned by HyperShore / HyperCompanion
#            lookup: cross-card bus, milliseconds
#
# The bridge navigates between scopes transparently:
#   local miss → shore lookup → extended lookup → not found
# Each hop is one 32-bit lookup + one mask check.

SCOPE_LOCAL    = "LOCAL"      # this stack only
SCOPE_SHORE    = "SHORE"      # this card
SCOPE_EXTENDED = "EXTENDED"   # beyond this card

# Default scope per broad category
SCOPE_DEFAULT_CELL    = SCOPE_LOCAL     # cells are always local
SCOPE_DEFAULT_POND    = SCOPE_LOCAL     # most Ponds start local
SCOPE_DEFAULT_BRIDGE  = SCOPE_SHORE     # bridges are card-visible
SCOPE_DEFAULT_SESSION = SCOPE_SHORE     # sessions are card-wide
SCOPE_DEFAULT_DISPLAY = SCOPE_SHORE     # displays are card-visible
SCOPE_DEFAULT_REMOTE  = SCOPE_EXTENDED  # cross-card objects


# ── PondTypeSpec ──────────────────────────────────────────────────────────────

@dataclass
class PondTypeSpec:
    """
    Complete specification for one Pond type.

    type_id:          unique string identifier — used in create_pond(pond_type=)
    description:      human-readable purpose
    default_lanes:    (inbound, outbound) default bridge lane widths
    security:         forced security level (None = caller decides)
    permanent_anchor: cannot be destroyed without heritage=True
    ward_active:      False = Ward always HEALTHY (BOOT / passive types)
    ptt_mode:         STATIC, INCREMENTAL, or NONE
    min_bridges:      minimum required bridge count
    max_bridges:      maximum bridge count (None = no limit)
    allow_migrate:    True = can be hot-migrated (FREEZE_BODY)
    stall_threshold:  consecutive zero-emission cycles before MONITOR flags stall
    anomaly_threshold: rejection % in rolling window that triggers anomaly flag
    metadata:         arbitrary extra config for COMPANION / Shore
    """
    type_id:          str
    description:      str          = ""
    default_lanes:    tuple        = (2, 2)
    security:         Optional[str]= None    # None = let caller decide
    permanent_anchor: bool         = False
    ward_active:      bool         = True
    ptt_mode:         str          = PTT_STATIC
    min_bridges:      int          = 2
    max_bridges:      Optional[int]= None
    allow_migrate:    bool         = True
    default_scope:    str          = SCOPE_LOCAL   # which PTT level owns this type
    stall_threshold:  int          = 50      # consecutive zero cycles → stall
    anomaly_threshold: float       = 50.0   # rejection % → routing anomaly flag
    metadata:         dict         = field(default_factory=dict)

    def validate_bridge_count(self, count: int) -> bool:
        if count < self.min_bridges:
            return False
        if self.max_bridges is not None and count > self.max_bridges:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "type_id":          self.type_id,
            "description":      self.description,
            "default_lanes":    self.default_lanes,
            "security":         self.security,
            "permanent_anchor": self.permanent_anchor,
            "ward_active":      self.ward_active,
            "ptt_mode":         self.ptt_mode,
            "min_bridges":      self.min_bridges,
            "max_bridges":      self.max_bridges,
            "allow_migrate":    self.allow_migrate,
            "default_scope":    self.default_scope,
            "stall_threshold":  self.stall_threshold,
            "anomaly_threshold": self.anomaly_threshold,
            "metadata":         self.metadata,
        }

    def __repr__(self) -> str:
        return (f"PondTypeSpec('{self.type_id}' "
                f"lanes={self.default_lanes} "
                f"ptt={self.ptt_mode})")


# ── PondTypeRegistry ──────────────────────────────────────────────────────────

class PondTypeRegistry:
    """
    Central registry of all known Pond types.

    Usage:
        from pond_types import registry

        # Look up a type
        spec = registry.get('PROCESS')

        # Register a new type
        registry.register(PondTypeSpec('AI_MODEL', ...))

        # List all types
        for name, spec in registry.items():
            print(name, spec.description)

        # Validate a type string
        if registry.is_valid('WORKSPACE'):
            ...
    """

    def __init__(self):
        self._types: dict[str, PondTypeSpec] = {}

    def register(self, spec: PondTypeSpec) -> None:
        """Register a Pond type. Overwrites if type_id already exists."""
        self._types[spec.type_id] = spec

    def get(self, type_id: str) -> Optional[PondTypeSpec]:
        """Return spec for type_id, or None if not registered."""
        return self._types.get(type_id)

    def require(self, type_id: str) -> PondTypeSpec:
        """Return spec for type_id, raising ValueError if not found."""
        spec = self._types.get(type_id)
        if spec is None:
            raise ValueError(
                f"Unknown Pond type '{type_id}'. "
                f"Registered types: {sorted(self._types)}"
            )
        return spec

    def is_valid(self, type_id: str) -> bool:
        return type_id in self._types

    def all_types(self) -> list[str]:
        return sorted(self._types.keys())

    def items(self):
        return self._types.items()

    def __len__(self) -> int:
        return len(self._types)

    def __contains__(self, type_id: str) -> bool:
        return type_id in self._types

    def dump(self) -> str:
        lines = [f"PondTypeRegistry ({len(self)} types):"]
        for tid, spec in sorted(self._types.items()):
            anchor = " [ANCHOR]" if spec.permanent_anchor else ""
            hidden = f" [{spec.security}]" if spec.security else ""
            lines.append(
                f"  {tid:<14s} lanes={spec.default_lanes}  "
                f"ptt={spec.ptt_mode:<12s} "
                f"ward={'ON' if spec.ward_active else 'OFF'}"
                f"{anchor}{hidden}  {spec.description}"
            )
        return "\n".join(lines)


# ── Built-in type definitions ─────────────────────────────────────────────────

_BUILTIN_TYPES = [

    PondTypeSpec(
        type_id       = "PROCESS",
        description   = "Running program or long-running service. "
                        "Input arrives via INBOUND bridges, results "
                        "leave via OUTBOUND bridges.",
        default_lanes = (4, 4),
        ptt_mode      = PTT_STATIC,
        allow_migrate = True,
        default_scope = SCOPE_LOCAL,
        stall_threshold   = 100,   # programs may idle between inputs
        anomaly_threshold = 50.0,
    ),

    PondTypeSpec(
        type_id       = "WORKSPACE",
        description   = "Volatile working data Pond. Document-backed. "
                        "PTT updated incrementally as content changes. "
                        "One Workspace Pond per open document/session.",
        default_lanes = (4, 4),
        ptt_mode      = PTT_INCREMENTAL,
        allow_migrate = True,
        metadata      = {"volatile": True},
        default_scope = SCOPE_LOCAL,
        stall_threshold   = 50,    # workspace should stay active during a session
        anomaly_threshold = 50.0,
    ),

    PondTypeSpec(
        type_id       = "FILE",
        description   = "File data in loopback storage cells or pointer "
                        "tokens to physical media. Read-heavy traffic.",
        default_lanes = (4, 2),
        ptt_mode      = PTT_STATIC,
        allow_migrate = True,
        default_scope = SCOPE_SHORE,
        stall_threshold   = 200,   # files may be idle for long periods
        anomaly_threshold = 30.0,  # access patterns should be predictable
    ),

    PondTypeSpec(
        type_id       = "PERIPHERAL",
        description   = "Array-side representation of a piece of hardware. "
                        "Bridges map to physical device registers. "
                        "Ward watches for silence (device disconnect).",
        default_lanes = (2, 2),
        ptt_mode      = PTT_STATIC,
        allow_migrate = False,   # peripherals are location-specific
        metadata      = {"device_pond": True},
        default_scope = SCOPE_LOCAL,
        stall_threshold   = 20,    # hardware should emit regularly; silence = disconnect
        anomaly_threshold = 25.0,  # hardware access is well-defined
    ),

    PondTypeSpec(
        type_id       = "LIBRARY",
        description   = "Pre-compiled tile configurations. Shared across "
                        "Ponds. Read-only at runtime. Single inbound "
                        "request channel, wide outbound result bus.",
        default_lanes = (1, 4),
        ptt_mode      = PTT_STATIC,
        allow_migrate = True,
        default_scope = SCOPE_SHORE,
        stall_threshold   = 200,   # libraries idle between requests
        anomaly_threshold = 40.0,
    ),

    PondTypeSpec(
        type_id       = "BOOT",
        description   = "Bootstrap and FS decoder tiles. ROM only. "
                        "No runtime writes. Ward always reports HEALTHY.",
        default_lanes = (1, 1),
        ward_active   = False,
        ptt_mode      = PTT_NONE,
        allow_migrate = False,
        metadata      = {"rom": True},
        default_scope = SCOPE_LOCAL,
        stall_threshold   = 500,   # ROM is mostly silent; ward_active=False anyway
        anomaly_threshold = 80.0,
    ),

    PondTypeSpec(
        type_id       = "COMPANION",
        description   = "Permanent base OS anchor. Keys, tile provision, "
                        "region allocation, Ward escalation. Single "
                        "instance. Cannot be destroyed without heritage.",
        default_lanes = (1, 1),
        security      = HIDDEN,
        permanent_anchor = True,
        ptt_mode      = PTT_STATIC,
        allow_migrate = False,
        max_bridges   = 2,
        metadata      = {"os_anchor": True},
        default_scope = SCOPE_SHORE,
        stall_threshold   = 200,   # companion is always-on but may be quiet
        anomaly_threshold = 20.0,  # companion access is tightly controlled
    ),

    PondTypeSpec(
        type_id       = "DEVICE",
        description   = "External device bridge. Connects hardware to the "
                        "array via BRIDGE cells. Each connected device "
                        "has its own DEVICE Pond. Disconnect = Ward SILENT.",
        default_lanes = (2, 2),
        ptt_mode      = PTT_STATIC,
        allow_migrate = False,   # tied to physical device address
        metadata      = {"device_pond": True, "external": True},
        default_scope = SCOPE_SHORE,
        stall_threshold   = 15,    # device silence quickly = disconnect
        anomaly_threshold = 25.0,
    ),

    PondTypeSpec(
        type_id       = "SHORE",
        description   = "System registry Pond. Shore lives inside one of "
                        "these. Holds address book, connection table, "
                        "translation table. Hidden from normal discovery.",
        default_lanes = (2, 4),
        security      = HIDDEN,
        ptt_mode      = PTT_STATIC,
        allow_migrate = True,
        metadata      = {"registry": True},
        default_scope = SCOPE_SHORE,
        stall_threshold   = 100,   # Shore may be quiet between lookups
        anomaly_threshold = 15.0,  # registry access should be very predictable
    ),

    PondTypeSpec(
        type_id       = "FS",
        description   = "Filesystem index and metadata Pond. Holds the "
                        "PTT for open files, directory entries, and "
                        "inode mappings. One FS Pond per mounted volume.",
        default_lanes = (4, 2),
        ptt_mode      = PTT_INCREMENTAL,   # updates as files open/close
        allow_migrate = True,
        metadata      = {"filesystem": True},
        default_scope = SCOPE_SHORE,
        stall_threshold   = 150,   # FS may be quiet between file operations
        anomaly_threshold = 35.0,
    ),

]


# ── Module-level registry ─────────────────────────────────────────────────────

registry = PondTypeRegistry()
for _spec in _BUILTIN_TYPES:
    registry.register(_spec)


# ── Convenience constants (backwards compatibility with pond.py) ──────────────
# These string constants match what pond.py currently uses.
# Import them from here instead of defining them in pond.py.

PROCESS     = "PROCESS"
WORKSPACE   = "WORKSPACE"
FILE        = "FILE"
PERIPHERAL  = "PERIPHERAL"
LIBRARY     = "LIBRARY"
BOOT        = "BOOT"
COMPANION   = "COMPANION"
DEVICE      = "DEVICE"
SHORE_TYPE  = "SHORE"      # SHORE to avoid conflict with shore_v2.ShoreV2
FS          = "FS"
CONDITIONAL = "CONDITIONAL"  # Pond with explicit lifecycle contract
SHOREKEEPER = "SHOREKEEPER"  # Per-card Shore + Ward collective + boundary
HYPERSHORE  = "HYPERSHORE"   # Global registry on master card

# Register new types
registry.register(PondTypeSpec(
    type_id        = CONDITIONAL,
    default_scope  = SCOPE_LOCAL,
    description    = (
        "Pond with an explicit lifecycle contract set at creation. "
        "dissolve_condition: TIME | RETURN | COMPLETE | EXTERNAL | COMPOUND. "
        "dissolve_action: DISSOLVE | FREEZE | CHECKPOINT. "
        "Ward evaluates conditions each heartbeat and executes action when met."
    ),
    default_lanes  = (4, 4),
    permanent_anchor = False,
    security       = None,
))

registry.register(PondTypeSpec(
    type_id        = SHOREKEEPER,
    default_scope  = SCOPE_SHORE,
    description    = (
        "Per-card Shore registry + Ward collective + boundary authority. "
        "Self-hosted on card NOR cells. Reports aggregated heartbeats to "
        "HyperShore on master card. Validates all cross-card traffic."
    ),
    default_lanes  = (2, 4),
    permanent_anchor = True,
    security       = "HIDDEN",
))

registry.register(PondTypeSpec(
    type_id        = HYPERSHORE,
    default_scope  = SCOPE_EXTENDED,
    description    = (
        "Global registry on master card. Aggregates ShoreKeeper heartbeats "
        "from all cards. Managed by HyperCompanion."
    ),
    default_lanes  = (2, 8),
    permanent_anchor = True,
    security       = "HIDDEN",
))

# All built-in type IDs — used for validation
POND_TYPES = tuple(registry.all_types())

# Dissolve condition types for CONDITIONAL ponds
DISSOLVE_TIME     = "TIME"       # dissolve after N ticks
DISSOLVE_RETURN   = "RETURN"     # dissolve when process P returns value V
DISSOLVE_COMPLETE = "COMPLETE"   # dissolve when process P finishes
DISSOLVE_EXTERNAL = "EXTERNAL"   # dissolve when session/connection closes
DISSOLVE_COMPOUND = "COMPOUND"   # ANY(...) or ALL(...) of above

# Dissolve action types
ACTION_DISSOLVE    = "DISSOLVE"    # clean termination
ACTION_FREEZE      = "FREEZE"      # halt cells, preserve state for debug
ACTION_CHECKPOINT  = "CHECKPOINT"  # save VM image then dissolve
ACTION_RESTART     = "RESTART"     # restart the Pond (COMPANION rule engine)
ACTION_ISOLATE     = "ISOLATE"     # isolate Pond from Shore (COMPANION fallback)
ACTION_MIGRATE     = "MIGRATE"     # migrate to cooler stack (thermal response)
