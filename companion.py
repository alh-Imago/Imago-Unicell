"""
companion.py — COMPANION Base OS Controller

The COMPANION is the base OS of the Imago array. It is the first Pond
created at boot, the last destroyed, and the authority every other
component defers to for:

  Key management     — issues and validates access tokens for Pond
                       identity, bridge whitelists, and security grants.

  Tool provision     — the tile library lives here. Any Pond needing
                       a compiled tile requests it through COMPANION.

  Array allocation   — owns the master cell allocation table. Ponds
                       request address regions through COMPANION.

  Ward escalation    — receives STALLED/OFFLINE/DEGRADED flags from
                       Shore and decides the response: restart, migrate,
                       expand, or escalate to the AI layer.

  Boot sequence      — initialises Shore, the tile library, and the
                       base address space. Everything else starts after
                       COMPANION signals READY.

Architecture
============

COMPANION is a HIDDEN LIBRARY Pond with permanent_anchor=True. It
cannot be destroyed without heritage=True. It has a single INBOUND
bridge (requests in) and single OUTBOUND bridge (responses out).

All other Ponds are guests. COMPANION is the host.

AI layer
========

The COMPANION has an optional AI inference bridge. When a language
model is attached (e.g. TinyLlama-1.1B), Ward escalation decisions
are routed through the model. Without the AI layer, COMPANION uses
a built-in rule engine for all decisions.

The AI layer is completely optional — COMPANION functions fully
without it. Attach it with companion.attach_ai(model_path).
"""

from __future__ import annotations

import time
import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from controller import ImagoController
    from unicell_array import UniCellArray
    from shore_v2 import ShoreV2


# ── Key types ─────────────────────────────────────────────────────────────────

KEY_IDENTITY  = "IDENTITY"   # Pond identity token
KEY_BRIDGE    = "BRIDGE"     # Bridge access grant
KEY_TILE      = "TILE"       # Tile library access
KEY_REGION    = "REGION"     # Address region allocation
KEY_ADMIN     = "ADMIN"      # Administrative authority (COMPANION-only issue)

KEY_TYPES = (KEY_IDENTITY, KEY_BRIDGE, KEY_TILE, KEY_REGION, KEY_ADMIN)


# ── Access key ────────────────────────────────────────────────────────────────

@dataclass
class AccessKey:
    """
    A cryptographic access token issued by COMPANION.

    key_id:      unique identifier
    key_type:    what this key grants access to
    holder_id:   pond_id of the key holder
    resource:    what resource this key unlocks (bridge name, tile name, etc.)
    issued_at:   timestamp
    expires_at:  None = never expires
    revoked:     True if COMPANION has revoked this key
    """
    key_id:     str
    key_type:   str
    holder_id:  str
    resource:   str
    issued_at:  float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    revoked:    bool = False

    def is_valid(self) -> bool:
        if self.revoked:
            return False
        if self.expires_at and time.time() > self.expires_at:
            return False
        return True

    def to_dict(self) -> dict:
        return {
            "key_id":     self.key_id,
            "key_type":   self.key_type,
            "holder_id":  self.holder_id,
            "resource":   self.resource,
            "issued_at":  self.issued_at,
            "expires_at": self.expires_at,
            "valid":      self.is_valid(),
        }


# ── Region allocation record ──────────────────────────────────────────────────

@dataclass
class RegionRecord:
    """
    One allocated address region in COMPANION's allocation table.

    base:        start address of the region
    size:        number of address slots
    owner_id:    pond_id that owns this region
    allocated_at: timestamp
    """
    base:         int
    size:         int
    owner_id:     str
    allocated_at: float = field(default_factory=time.time)

    @property
    def end(self) -> int:
        return self.base + self.size - 1

    def contains(self, address: int) -> bool:
        return self.base <= address <= self.end

    def to_dict(self) -> dict:
        return {
            "base":         hex(self.base),
            "end":          hex(self.end),
            "size":         self.size,
            "owner_id":     self.owner_id,
            "allocated_at": self.allocated_at,
        }


# ── Ward escalation action ────────────────────────────────────────────────────

@dataclass
class EscalationAction:
    """
    An action COMPANION has decided to take in response to a Ward flag.

    action:    what to do — see ACTION_* constants
    target:    pond_id or tile name this action applies to
    reason:    why this action was chosen
    source:    "rules" (built-in rule engine) or "ai" (language model)
    timestamp: when the decision was made
    """
    action:    str
    target:    str
    reason:    str
    source:    str = "rules"
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "action":    self.action,
            "target":    self.target,
            "reason":    self.reason,
            "source":    self.source,
            "timestamp": self.timestamp,
        }


# ── OS Identity ──────────────────────────────────────────────────────────────

OS_NAME        = "Claudette"
OS_VERSION     = "1.2"
OS_FULL_NAME   = f"{OS_NAME} v{OS_VERSION}"
OS_DESCRIPTION = (
    "Claudette v1.2 — Imago spatial computing OS. "
    "Extended to 64-bit addressing via config register upper half. "
    "Three-tier object model (LOCAL/SHORE/EXTENDED). "
    "3×64-bit command bus with scope-ordered Cast/Ripple search. "
    "GS_ADDR_LATCH bridge primitive. Shore proxy mechanism retired. "
    "LLVM frontend and IR mapper. DisplayPond host window. "
    "45 test suites, 2584 tests."
)


ACTION_RESTART     = "RESTART"     # restart a stalled Pond
ACTION_MIGRATE     = "MIGRATE"     # move a Pond to a new region
ACTION_EXPAND      = "EXPAND"      # grow a Pond's address region
ACTION_REVOKE      = "REVOKE"      # revoke keys for a Pond
ACTION_ISOLATE     = "ISOLATE"     # cut off a misbehaving Pond
ACTION_NOOP        = "NOOP"        # no action needed
ACTION_ESCALATE    = "ESCALATE"    # requires human/AI attention


# ── COMPANION ─────────────────────────────────────────────────────────────────

class Companion:
    """
    The COMPANION base OS controller.

    Created once at boot via Companion.boot(). Never destroyed during
    normal operation.

    Usage:
        companion = Companion.boot(array, shore, controller)
        # System is now initialised — Shore populated, tiles available

        # Issue a key
        key = companion.issue_key(KEY_TILE, holder_id='pond_0001',
                                   resource='INT32_ADD')

        # Request a tile
        tile = companion.request_tile('INT32_ADD', 'pond_0001', key.key_id)

        # Allocate an address region
        region = companion.allocate_region(size=256, owner_id='pond_0001')

        # Handle a Ward flag
        action = companion.handle_ward_flag('pond_0007', 'STALLED')
    """

    # Address space layout
    # COMPANION owns the master allocation table.
    # Regions are handed out sequentially from REGION_BASE.
    COMPANION_BASE   = 0x00100000   # COMPANION's own address space
    COMPANION_SIZE   = 0x00010000   # 64K slots for COMPANION internals
    REGION_BASE      = 0x00200000   # start of allocatable address space
    REGION_TOP       = 0xEFFFFFFF   # top of local 32-bit space
                                    # (0xF0000000+ reserved for proxy addresses)

    def __init__(self,
                 pond,
                 shore:      "ShoreV2",
                 controller: "ImagoController",
                 tile_library):
        self._pond       = pond
        self._shore      = shore
        self._ctrl       = controller
        self._tiles      = tile_library
        self._booted_at  = time.time()
        self._ready      = False

        # Key store: key_id -> AccessKey
        self._keys: dict[str, AccessKey] = {}
        self._key_counter = 0

        # Allocation table: list of RegionRecord, ordered by base address
        self._regions: list[RegionRecord] = []
        self._next_base = self.REGION_BASE

        # Reserve COMPANION's own region
        self._regions.append(RegionRecord(
            base     = self.COMPANION_BASE,
            size     = self.COMPANION_SIZE,
            owner_id = "companion",
        ))

        # Escalation log
        self._escalation_log: list[EscalationAction] = []

        # AI bridge — attached later via attach_ai()
        self._ai = None

    # ── Boot ──────────────────────────────────────────────────────────────────

    @classmethod
    def boot(cls,
             array:      "UniCellArray",
             shore:      "ShoreV2",
             controller: "ImagoController") -> "Companion":
        """
        Initialise the COMPANION and bring the system online.

        Boot sequence:
          1. Create the COMPANION Pond (HIDDEN LIBRARY, permanent anchor)
          2. Load the tile library
          3. Register COMPANION with Shore
          4. Issue the master ADMIN key
          5. Signal READY

        Returns the live Companion instance.
        """
        from pond import PondManager, COMPANION, HIDDEN
        from fp_tiles import TileLibrary
        from shore_v2 import ShoreEntry

        print("[COMPANION] Booting...")

        # 1. Create the COMPANION Pond
        mgr  = PondManager(array)
        pond = mgr.create_pond(
            name           = "companion",
            owner_id       = "system",
            pond_type      = COMPANION,
            bridge_count   = 2,
            base_address   = cls.COMPANION_BASE,
            region_size    = cls.COMPANION_SIZE,
        )

        # 2. Load the tile library
        tiles = TileLibrary()
        print(f"[COMPANION] Tile library: "
              f"{len(tiles.available())} tiles available")

        # 3. Create the Companion instance
        comp = cls(pond=pond, shore=shore,
                   controller=controller, tile_library=tiles)

        # 4. Register COMPANION with Shore
        inbound = next((b for b in pond.bridges
                        if b.role == "INBOUND"), None)
        if inbound:
            shore.register(ShoreEntry(
                name          = "companion_inbound",
                resource_type = "BRIDGE",
                local_address = inbound.external_address,
                base_address  = pond.base_address,
                offset        = inbound.internal_offset,
                pond_id       = 0,
                ward_state    = "HEALTHY",
                metadata      = {"role": "COMPANION_INBOUND"},
            ))
            shore.register(ShoreEntry(
                name          = "companion",
                resource_type = "POND",
                local_address = pond.base_address,
                base_address  = pond.base_address,
                pond_id       = 0,
                ward_state    = "HEALTHY",
                metadata      = {"type": "COMPANION", "boot_time": comp._booted_at},
            ))

        # 5. Issue master ADMIN key
        admin_key = comp._issue_key_internal(
            key_type  = KEY_ADMIN,
            holder_id = "companion",
            resource  = "*",
        )
        print(f"[COMPANION] Admin key issued: {admin_key.key_id}")

        # 6. Issue tile library key for system use
        comp._issue_key_internal(
            key_type  = KEY_TILE,
            holder_id = "system",
            resource  = "*",
        )

        comp._ready = True
        print(f"[COMPANION] READY — "
              f"uptime=0s "
              f"tiles={len(tiles.available())} "
              f"regions=1 (self)")

        return comp

    # ── Key management ────────────────────────────────────────────────────────

    def issue_key(self, key_type:   str,
                  holder_id:        str,
                  resource:         str,
                  requesting_key:   Optional[str] = None,
                  expires_in:       Optional[float] = None) -> Optional[AccessKey]:
        """
        Issue an access key to a Pond.

        key_type:       what this key grants (KEY_IDENTITY, KEY_BRIDGE, etc.)
        holder_id:      pond_id receiving the key
        resource:       what resource this unlocks
        requesting_key: the key_id of the requester's existing key.
                        Required for ADMIN and TILE keys.
                        Identity and Bridge keys can be self-requested.
        expires_in:     seconds until expiry. None = never expires.

        Returns the key on success, None if the request is denied.
        """
        # Validate the requester
        if key_type in (KEY_ADMIN, KEY_TILE, KEY_REGION):
            if requesting_key is None:
                print(f"[COMPANION] Key request denied: "
                      f"{key_type} requires an authorising key")
                return None
            auth = self._keys.get(requesting_key)
            if auth is None or not auth.is_valid():
                print(f"[COMPANION] Key request denied: "
                      f"authorising key invalid or expired")
                return None
            # Only ADMIN keys can issue ADMIN keys
            if key_type == KEY_ADMIN and auth.key_type != KEY_ADMIN:
                print(f"[COMPANION] Key request denied: "
                      f"only ADMIN key can issue ADMIN keys")
                return None

        expires_at = time.time() + expires_in if expires_in else None
        return self._issue_key_internal(key_type, holder_id,
                                         resource, expires_at)

    def validate_key(self, key_id: str,
                     key_type: Optional[str] = None,
                     resource: Optional[str] = None) -> bool:
        """
        Validate that a key exists, is not revoked, and matches
        the requested type and resource (if specified).
        """
        key = self._keys.get(key_id)
        if key is None or not key.is_valid():
            return False
        if key_type and key.key_type != key_type:
            # ADMIN key is valid for everything
            if key.key_type != KEY_ADMIN:
                return False
        if resource and key.resource not in (resource, "*"):
            return False
        return True

    def revoke_key(self, key_id: str,
                   authorising_key: str) -> bool:
        """
        Revoke a key. Requires an ADMIN key to authorise.
        Returns True if the key was found and revoked.
        """
        auth = self._keys.get(authorising_key)
        if auth is None or not auth.is_valid() or auth.key_type != KEY_ADMIN:
            return False
        key = self._keys.get(key_id)
        if key is None:
            return False
        key.revoked = True
        print(f"[COMPANION] Key revoked: {key_id}")
        return True

    def _issue_key_internal(self, key_type: str, holder_id: str,
                             resource: str,
                             expires_at: Optional[float] = None) -> AccessKey:
        """Issue a key without authorisation check (internal use only)."""
        self._key_counter += 1
        raw = f"{key_type}:{holder_id}:{resource}:{self._key_counter}"
        key_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
        key = AccessKey(
            key_id     = key_id,
            key_type   = key_type,
            holder_id  = holder_id,
            resource   = resource,
            expires_at = expires_at,
        )
        self._keys[key_id] = key
        return key

    # ── Tool provision ────────────────────────────────────────────────────────

    def request_tile(self, tile_name: str,
                     requesting_pond: str,
                     key_id: str) -> Optional[object]:
        """
        Provide a compiled tile to a requesting Pond.

        The requester must hold a valid TILE or ADMIN key.
        Returns the Tile object on success, None on failure.
        """
        if not self.validate_key(key_id, KEY_TILE, tile_name):
            print(f"[COMPANION] Tile request denied: "
                  f"'{requesting_pond}' lacks TILE key for '{tile_name}'")
            return None

        try:
            tile = self._tiles.get(tile_name)
            print(f"[COMPANION] Tile '{tile_name}' provided to '{requesting_pond}'")
            return tile
        except KeyError:
            print(f"[COMPANION] Tile '{tile_name}' not found in library")
            return None

    def available_tiles(self) -> list[str]:
        """Return list of all available tile names."""
        return self._tiles.available()

    def issue_tile_key(self, holder_id: str,
                       tile_name: str,
                       admin_key: str) -> Optional[AccessKey]:
        """
        Issue a TILE key to a Pond for a specific tile (or '*' for all).
        Requires an ADMIN key.
        """
        return self.issue_key(KEY_TILE, holder_id, tile_name,
                               requesting_key=admin_key)

    # ── Address region allocation ─────────────────────────────────────────────

    def allocate_region(self, size: int,
                        owner_id: str,
                        key_id: Optional[str] = None) -> Optional[RegionRecord]:
        """
        Allocate a contiguous address region.

        size:     number of address slots needed
        owner_id: pond_id that will own this region
        key_id:   REGION or ADMIN key (optional for system calls)

        Returns a RegionRecord on success, None if space exhausted.
        """
        if key_id and not self.validate_key(key_id, KEY_REGION):
            print(f"[COMPANION] Region allocation denied: invalid key")
            return None

        # Find next available base (simple linear allocator)
        base = self._next_base
        if base + size > self.REGION_TOP:
            print(f"[COMPANION] Region allocation failed: "
                  f"address space exhausted")
            return None

        record = RegionRecord(base=base, size=size, owner_id=owner_id)
        self._regions.append(record)
        self._next_base = base + size

        # Register with Shore
        self._shore.register_from_companion(record) if hasattr(
            self._shore, 'register_from_companion') else None

        print(f"[COMPANION] Region allocated: "
              f"0x{base:08X}-0x{base+size-1:08X} "
              f"({size} slots) → '{owner_id}'")
        return record

    def free_region(self, base: int, owner_id: str) -> bool:
        """
        Free a previously allocated region.
        Only the owner can free their own region.
        Returns True if found and freed.
        """
        for i, rec in enumerate(self._regions):
            if rec.base == base and rec.owner_id == owner_id:
                self._regions.pop(i)
                print(f"[COMPANION] Region freed: 0x{base:08X} ('{owner_id}')")
                return True
        return False

    def region_for_address(self, address: int) -> Optional[RegionRecord]:
        """Return the region that contains this address, or None."""
        for rec in self._regions:
            if rec.contains(address):
                return rec
        return None

    # ── Ward escalation ───────────────────────────────────────────────────────

    def handle_ward_flag(self, pond_id: str,
                          ward_state: str,
                          context: Optional[dict] = None) -> EscalationAction:
        """
        Handle a Ward health flag from Shore.

        pond_id:   which Pond is flagging
        ward_state: the Ward state (STALLED, OFFLINE, DEGRADED, SILENT)
        context:   optional extra information (emission counts, etc.)

        If an AI bridge is attached, routes to the model.
        Otherwise uses the built-in rule engine.

        Returns the EscalationAction decided.
        """
        if self._ai is not None:
            action = self._ai_decide(pond_id, ward_state, context or {})
        else:
            action = self._rule_decide(pond_id, ward_state, context or {})

        self._escalation_log.append(action)
        self._execute_action(action)
        return action

    def _rule_decide(self, pond_id: str,
                      ward_state: str,
                      context: dict) -> EscalationAction:
        """Built-in rule engine for Ward escalation decisions."""

        if ward_state == "STALLED":
            # Stalled PROCESS Pond — try restart first
            return EscalationAction(
                action = ACTION_RESTART,
                target = pond_id,
                reason = f"PROCESS Pond STALLED — attempting restart",
                source = "rules",
            )

        elif ward_state == "OFFLINE":
            # Bridge deallocated — isolate and revoke keys
            return EscalationAction(
                action = ACTION_ISOLATE,
                target = pond_id,
                reason = "Bridge cells gone — isolating Pond",
                source = "rules",
            )

        elif ward_state == "DEGRADED":
            # Check if it's a throttle issue — expand the region
            if context.get("is_throttled"):
                return EscalationAction(
                    action = ACTION_EXPAND,
                    target = pond_id,
                    reason = "Throttled — requesting region expansion",
                    source = "rules",
                )
            return EscalationAction(
                action = ACTION_NOOP,
                target = pond_id,
                reason = "DEGRADED but not throttled — monitoring",
                source = "rules",
            )

        elif ward_state == "SILENT":
            # PERIPHERAL gone quiet — notify but don't intervene
            return EscalationAction(
                action = ACTION_ESCALATE,
                target = pond_id,
                reason = "PERIPHERAL silent — hardware may have disconnected",
                source = "rules",
            )

        # Default — no action
        return EscalationAction(
            action = ACTION_NOOP,
            target = pond_id,
            reason = f"Ward state '{ward_state}' — no rule applies",
            source = "rules",
        )

    def _execute_action(self, action: EscalationAction) -> None:
        """
        Execute a decided escalation action.

        RESTART  — mark Pond as restarting in Shore; clear its Ward escalation
                   flag so it can be re-monitored after recovery.
        ISOLATE  — revoke all keys held by the Pond; mark ISOLATED in Shore;
                   suspend all its connections so no data flows in/out.
        EXPAND   — allocate an additional region for the Pond.
        MIGRATE  — request Shore to move the Pond (hot migration via FREEZE_BODY).
        REVOKE   — revoke all keys held by the Pond without full isolation.
        ESCALATE — log for human/AI attention; no automatic structural change.
        NOOP     — nothing to do; log and continue.
        """
        print(f"[COMPANION] Action: {action.action} → '{action.target}' "
              f"({action.reason}) [{action.source}]")

        if action.action == ACTION_RESTART:
            # Mark RESTARTING so watchers know it's being handled
            if self._shore.lookup(action.target):
                self._shore.update(action.target, ward_state="RESTARTING")
            if hasattr(self._shore, 'clear_escalation'):
                self._shore.clear_escalation(action.target)

            # Find the Pond object and call restart()
            pond_obj = None
            if hasattr(self, '_pond_manager') and self._pond_manager:
                pond_obj = self._pond_manager.get_pond(action.target)

            if pond_obj is not None:
                # Build a system CommandInterface if we have a controller
                cmd_iface = None
                if hasattr(self, '_controller') and self._controller:
                    from command_interface import make_system_interface
                    # Use the card auth token from Shore if available
                    auth = 0
                    auth_entry = self._shore.lookup("card_auth_0")
                    if auth_entry and hasattr(auth_entry, 'metadata'):
                        auth = auth_entry.metadata.get("auth_token", 0)
                    cmd_iface = make_system_interface(self._controller, auth)

                success = pond_obj.restart(
                    controller=getattr(self, '_controller', None),
                    shore=self._shore,
                    command_interface=cmd_iface,
                )
                if success:
                    print(f"[COMPANION]   '{action.target}' restarted successfully")
                else:
                    print(f"[COMPANION]   '{action.target}' restart failed — "
                          f"escalating to ISOLATE")
                    # Escalate to isolation if restart fails
                    self._execute_action(EscalationAction(
                        action=ACTION_ISOLATE,
                        target=action.target,
                        reason="Restart failed — isolating",
                        source="restart_fallback",
                    ))
            else:
                print(f"[COMPANION]   '{action.target}' marked RESTARTING — "
                      f"Pond object not found, manual reload required")

        elif action.action == ACTION_ISOLATE:
            # Revoke all keys held by this Pond
            revoked = 0
            for key in list(self._keys.values()):
                if key.holder_id == action.target and not key.revoked:
                    key.revoked = True
                    revoked += 1
            # Suspend all Shore connections (no data in or out)
            if hasattr(self._shore, 'suspend_connections'):
                suspended = self._shore.suspend_connections(action.target)
                print(f"[COMPANION]   '{action.target}' isolated — "
                      f"{revoked} keys revoked, "
                      f"{len(suspended)} connections suspended")
            if self._shore.lookup(action.target):
                self._shore.update(action.target, ward_state="ISOLATED")

        elif action.action == ACTION_EXPAND:
            # Allocate additional region for the Pond
            extra = self.allocate_region(size=256, owner_id=action.target)
            if extra:
                print(f"[COMPANION]   Expansion region allocated: "
                      f"0x{extra.base:08X} ({extra.size} slots) "
                      f"for '{action.target}'")
            else:
                print(f"[COMPANION]   Warning: could not allocate expansion "
                      f"region for '{action.target}'")

        elif action.action == ACTION_MIGRATE:
            # Hot migration — Shore handles address update and route refresh
            # The actual FREEZE_BODY migration happens via Pond.migrate() which
            # the caller is responsible for triggering with a new base address.
            # COMPANION marks it so the orchestrator can pick it up.
            if self._shore.lookup(action.target):
                self._shore.update(action.target, ward_state="MIGRATING")
            print(f"[COMPANION]   '{action.target}' flagged for migration — "
                  f"orchestrator must call Pond.migrate()")

        elif action.action == ACTION_REVOKE:
            # Revoke keys without full isolation (softer than ISOLATE)
            revoked = 0
            for key in list(self._keys.values()):
                if key.holder_id == action.target and not key.revoked:
                    key.revoked = True
                    revoked += 1
            print(f"[COMPANION]   {revoked} keys revoked for '{action.target}'")

        elif action.action == ACTION_ESCALATE:
            # Requires human or AI attention — log and surface
            print(f"[COMPANION]   ESCALATE: '{action.target}' needs attention. "
                  f"Reason: {action.reason}")
            # Shore entry gets flagged for external visibility
            if self._shore.lookup(action.target):
                self._shore.update(action.target, ward_state="NEEDS_ATTENTION")

        elif action.action == ACTION_NOOP:
            pass  # nothing to do; already logged above


    # ── AI bridge ─────────────────────────────────────────────────────────────

    def attach_ai(self, model_path: str,
                  device: str = "cuda",
                  max_new_tokens: int = 128) -> bool:
        """
        Attach a language model as the COMPANION's reasoning layer.

        model_path:     HuggingFace model name or local path.
                        e.g. "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        device:         "cuda" for GPU, "cpu" for CPU fallback
        max_new_tokens: maximum tokens in AI response

        Returns True if the model loaded successfully.
        """
        try:
            from transformers import AutoTokenizer, AutoModelForCausalLM
            import torch

            print(f"[COMPANION] Loading AI model: {model_path} "
                  f"on {device}...")

            dtype = torch.float16 if device == "cuda" else torch.float32
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                torch_dtype   = dtype,
                device_map    = device,
                low_cpu_mem_usage = True,
            )

            self._ai = CompanionAI(
                model          = model,
                tokenizer      = tokenizer,
                device         = device,
                max_new_tokens = max_new_tokens,
            )
            print(f"[COMPANION] AI bridge ready: {model_path}")
            return True

        except ImportError:
            print("[COMPANION] AI bridge requires: pip install transformers torch")
            return False
        except Exception as e:
            print(f"[COMPANION] AI bridge failed to load: {e}")
            return False

    def _ai_decide(self, pond_id: str,
                    ward_state: str,
                    context: dict) -> EscalationAction:
        """Route an escalation decision through the AI model."""
        if self._ai is None:
            return self._rule_decide(pond_id, ward_state, context)

        # Build the status summary for the model
        status_lines = [f"- {pond_id} ({ward_state})"]
        for k, v in context.items():
            status_lines.append(f"  {k}: {v}")

        # Add Shore context
        entry = self._shore.lookup(pond_id)
        if entry:
            status_lines.append(f"  resource_type: {entry.resource_type}")
            status_lines.append(f"  capabilities: {entry.capabilities}")

        status_text = "\n".join(status_lines)
        action_dict = self._ai.decide(status_text)

        return EscalationAction(
            action = action_dict.get("action", ACTION_NOOP),
            target = action_dict.get("target", pond_id),
            reason = action_dict.get("reason", "AI decision"),
            source = "ai",
        )

    @property
    def ai_attached(self) -> bool:
        return self._ai is not None

    # ── Status and inspection ─────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def uptime(self) -> float:
        return time.time() - self._booted_at

    def status(self) -> dict:
        valid_keys   = sum(1 for k in self._keys.values() if k.is_valid())
        revoked_keys = sum(1 for k in self._keys.values() if k.revoked)
        return {
            "ready":           self._ready,
            "uptime_s":        round(self.uptime, 1),
            "total_keys":      len(self._keys),
            "valid_keys":      valid_keys,
            "revoked_keys":    revoked_keys,
            "regions":         len(self._regions),
            "next_base":       hex(self._next_base),
            "tiles_available": len(self._tiles.available()),
            "escalations":     len(self._escalation_log),
            "ai_attached":     self.ai_attached,
        }

    def dump_escalation_log(self) -> str:
        if not self._escalation_log:
            return "No escalations recorded."
        lines = [f"Escalation log ({len(self._escalation_log)} entries):"]
        for a in self._escalation_log[-10:]:   # last 10
            lines.append(f"  [{a.action}] {a.target} — {a.reason} ({a.source})")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (f"Companion(ready={self._ready} "
                f"uptime={self.uptime:.0f}s "
                f"keys={len(self._keys)} "
                f"regions={len(self._regions)} "
                f"ai={self.ai_attached})")


# ── AI inference bridge ───────────────────────────────────────────────────────

class CompanionAI:
    """
    Language model bridge for COMPANION reasoning.

    Wraps a HuggingFace causal LM (TinyLlama, DistilGPT2, etc.) and
    provides a structured interface for Ward escalation decisions.

    The model receives a system prompt explaining the COMPANION role
    and a status summary, and responds with a JSON action dict.
    """

    SYSTEM_PROMPT = """\
You are the COMPANION — the base OS controller for an Imago UniCell \
spatial computing array.
You receive system status reports and respond with exactly one JSON \
action object.

Available actions:
  RESTART  — restart a stalled Pond (use for STALLED state)
  MIGRATE  — move a Pond to a new address region
  EXPAND   — grow a Pond's address region (use for throttled/full)
  REVOKE   — revoke keys for a misbehaving Pond
  ISOLATE  — cut off a Pond from the system (use for OFFLINE)
  NOOP     — no action needed (use for minor/transient issues)
  ESCALATE — requires human attention (use for unknown situations)

Respond with ONLY a JSON object, no explanation:
{"action": "ACTION_NAME", "target": "pond_id", "reason": "brief reason"}
"""

    def __init__(self, model, tokenizer, device: str,
                 max_new_tokens: int = 128):
        self._model          = model
        self._tokenizer      = tokenizer
        self._device         = device
        self._max_new_tokens = max_new_tokens

    def decide(self, status_text: str) -> dict:
        """
        Ask the model to decide on an escalation action.

        status_text: formatted status lines from the COMPANION
        Returns a dict with 'action', 'target', 'reason' keys.
        """
        import torch

        # Build prompt in TinyLlama chat format
        prompt = (
            f"<|system|>\n{self.SYSTEM_PROMPT}</s>\n"
            f"<|user|>\nSystem status:\n{status_text}\n"
            f"What action should be taken?</s>\n"
            f"<|assistant|>\n"
        )

        inputs = self._tokenizer(prompt, return_tensors="pt")
        if self._device == "cuda":
            inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens  = self._max_new_tokens,
                do_sample       = False,
                temperature     = 1.0,
                pad_token_id    = self._tokenizer.eos_token_id,
            )

        # Decode only the new tokens
        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        response   = self._tokenizer.decode(new_tokens,
                                             skip_special_tokens=True).strip()

        return self._parse_response(response)

    def _parse_response(self, response: str) -> dict:
        """
        Parse the model's JSON response.
        Falls back gracefully if the model produces malformed output.
        """
        # Try to extract JSON from the response
        try:
            # Find the first { ... } block
            start = response.find("{")
            end   = response.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(response[start:end])
                # Validate required fields
                if "action" in data and "target" in data:
                    return data
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback — parse keyword hints from free text
        response_upper = response.upper()
        for action in (ACTION_RESTART, ACTION_MIGRATE, ACTION_EXPAND,
                       ACTION_REVOKE, ACTION_ISOLATE, ACTION_ESCALATE):
            if action in response_upper:
                return {
                    "action": action,
                    "target": "unknown",
                    "reason": f"AI response (parsed): {response[:80]}",
                }

        return {
            "action": ACTION_NOOP,
            "target": "unknown",
            "reason": f"AI response unparseable: {response[:80]}",
        }
