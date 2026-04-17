"""
shore_v2.py — Shore System Registry (v2)

The Shore is the authoritative system registry — the single source of
truth for everything that exists in the array, where it lives, and how
to reach it. It serves three distinct roles:

  1. Address book        — maps every Pond, tile, bridge, and resource
                           to its current absolute address. Updated by
                           Ward announcements. Read by anyone wanting
                           to reach a resource.

  2. Extended address    — translates between the local 32-bit bus
     translation         (4GB address space) and the 64-bit world
                           beyond it. Proxy addresses in the reserved
                           range 0xF0000000-0xFFFFFFFF are forwarded
                           via the 64-bit bus. The BIOS populates the
                           initial translation table at boot.

  3. Filesystem anchor   — Shore's registry IS the root of the UniFlex
                           filesystem view. Every registered resource
                           has a path. The filesystem is Shore's index
                           made navigable.

Internal architecture
=====================

Shore's internal tables are themselves tiles — each table is a separate
region in the controller with its own region_id. This gives each table:

  - Independent freeze/thaw (relocate one without disturbing others)
  - Independent snapshot/restore (migrate individual tables)
  - Ward health monitoring (the same as any other tile)
  - Growth within Shore's address space (allocate more cells as needed)
  - Shrinkage when entries are removed (free cells back to Shore's pool)

Shore's outer boundary is fixed at construction:
  outer_size = estimated_cell_count * 1.15  (15% headroom)

Within that boundary Shore manages its own internal pool. Tables grow
by allocating from the pool. When a table outgrows its current region
it is relocated to a new contiguous block within Shore's space (or
requests expansion via COMPANION if the pool is exhausted).

Four internal tables
====================

  registry       — {name → ShoreEntry}    every known resource
  address_map    — {local_addr → name}    reverse address lookup
  translation    — {proxy_addr → ExtAddr} extended address translations
  connections    — {conn_id → Connection} open connections between Ponds

Shore directory
===============

The first cells at Shore's base address hold the directory — where each
table lives, its current region_id, base_offset, capacity, and entry
count. The directory never moves. Everything else can relocate freely
because the directory always knows where to find it.

Packet integration
==================

Shore accepts Ward announcement packets (Packet.announce / Packet.ready /
Packet.moving) and updates its registry accordingly. The packet format
is defined in packet_spec.py.
"""

from __future__ import annotations

import time
import math
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from controller import ImagoController

from packet_spec import (
    Packet, CapabilityDescriptor,
    FLAG_ANNOUNCE, FLAG_ROUTE_UPDATE, FLAG_READY, FLAG_MOVING,
    FLAG_CAPABILITY, FLAG_ACK,
    POND_TYPE_NAMES, WARD_STATE_NAMES, SECURITY_NAMES,
    SECURITY_OPEN, SECURITY_PRIVATE, SECURITY_HIDDEN,
)


# ── Extended address ──────────────────────────────────────────────────────────

# Proxy address range for extended (>4GB) resources
PROXY_BASE = 0xF0000000
PROXY_TOP  = 0xFFFFFFFF
PROXY_SIZE = PROXY_TOP - PROXY_BASE + 1


@dataclass
class ExtAddr:
    """
    A 64-bit extended address with its local 32-bit proxy.

    proxy_addr:   local bus address in the reserved proxy range
                  (0xF0000000 - 0xFFFFFFFF). Cells send to this
                  address; Shore forwards to the real destination.
    real_addr:    the actual 64-bit address of the resource.
    description:  human-readable name (e.g. "nvme_storage", "network_0")
    registered_at: when this translation was added
    """
    proxy_addr:    int
    real_addr:     int
    description:   str   = ""
    registered_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "proxy_addr":  hex(self.proxy_addr),
            "real_addr":   hex(self.real_addr),
            "description": self.description,
        }


# ── Shore entry ───────────────────────────────────────────────────────────────

@dataclass
class ShoreEntry:
    """
    One entry in Shore's registry — a complete description of one resource.

    name:            unique identifier within Shore (e.g. "pond_7_inbound")
    resource_type:   "POND", "BRIDGE", "TILE", "CELL", "EXTERNAL"
    local_address:   current absolute 32-bit bus address (None if external-only)
    base_address:    Pond base address (for relative-addressed resources)
    offset:          address offset from base (internal address within Pond)
    extended_addr:   64-bit address if beyond 4GB (None if local)
    pond_id:         Shore registry ID (0-511)
    capabilities:    CapabilityDescriptor (for Ponds and bridges)
    ward_state:      current Ward health state string
    last_seen:       timestamp of most recent Ward announcement
    metadata:        arbitrary extra fields
    """
    name:          str
    resource_type: str
    local_address: Optional[int]            = None
    base_address:  Optional[int]            = None
    offset:        int                      = 0
    extended_addr: Optional[int]            = None
    pond_id:       int                      = 0
    capabilities:  Optional[CapabilityDescriptor] = None
    ward_state:    str                      = "IDLE"
    last_seen:     float                    = field(default_factory=time.time)
    metadata:      dict                     = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name":          self.name,
            "resource_type": self.resource_type,
            "local_address": hex(self.local_address) if self.local_address else None,
            "base_address":  hex(self.base_address) if self.base_address else None,
            "offset":        hex(self.offset),
            "extended_addr": hex(self.extended_addr) if self.extended_addr else None,
            "pond_id":       self.pond_id,
            "capabilities":  self.capabilities.describe() if self.capabilities else None,
            "ward_state":    self.ward_state,
            "last_seen":     self.last_seen,
            "metadata":      self.metadata,
        }

    def resolve_address(self) -> Optional[int]:
        """
        Return the effective local address for this entry.
        If base_address is set, returns base + offset.
        Otherwise returns local_address directly.
        """
        if self.base_address is not None:
            return self.base_address + self.offset
        return self.local_address


# ── Connection record ─────────────────────────────────────────────────────────

@dataclass
class Connection:
    """
    A live connection between two resources tracked by Shore.

    When a route changes (Pond moves), Shore finds all connections
    involving that Pond and sends ROUTE_UPDATE packets to the other end.
    """
    conn_id:         str
    source_name:     str
    dest_name:       str
    source_address:  int
    dest_address:    int
    established_at:  float = field(default_factory=time.time)
    last_activity:   float = field(default_factory=time.time)
    active:          bool  = True

    def to_dict(self) -> dict:
        return {
            "conn_id":        self.conn_id,
            "source_name":    self.source_name,
            "dest_name":      self.dest_name,
            "source_address": hex(self.source_address),
            "dest_address":   hex(self.dest_address),
            "established_at": self.established_at,
            "active":         self.active,
        }


# ── ShoreTile — one internal table as a tile region ──────────────────────────

class ShoreTile:
    """
    One of Shore's internal tables, implemented as a tile region.

    Each table is a separate region in the controller — independently
    freezable, snapshottable, and relocatable. The table stores its
    entries in Python dicts for now (the cell-level storage model is
    the architectural target; this implementation gives the same
    interface and behaviour while remaining testable).

    The tile tracks its own capacity and entry count. When entries
    exceed capacity * GROWTH_THRESHOLD, it signals that it needs
    to grow. Growth is handled by Shore's internal pool manager.

    region_id:   controller region holding this tile's cells
    name:        human-readable table name ("registry", "address_map", etc.)
    capacity:    maximum entries before growth is needed
    """

    GROWTH_THRESHOLD = 0.85    # signal growth at 85% full
    INITIAL_CAPACITY = 64      # default starting capacity

    def __init__(self,
                 name:      str,
                 capacity:  int = INITIAL_CAPACITY,
                 region_id: Optional[str] = None):
        self.name       = name
        self.capacity   = capacity
        self.region_id  = region_id    # set when loaded into controller
        self._entries:  dict = {}      # keyed by entry identifier
        self._created_at = time.time()
        self._resizes    = 0

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    @property
    def utilisation(self) -> float:
        return self.entry_count / self.capacity if self.capacity > 0 else 0.0

    @property
    def needs_growth(self) -> bool:
        return self.utilisation >= self.GROWTH_THRESHOLD

    @property
    def is_full(self) -> bool:
        return self.entry_count >= self.capacity

    def get(self, key: str):
        return self._entries.get(key)

    def put(self, key: str, value) -> bool:
        """
        Store an entry. Returns True on success, False if full.
        Existing entries are always updated regardless of capacity.
        """
        if key not in self._entries and self.is_full:
            return False
        self._entries[key] = value
        return True

    def remove(self, key: str) -> bool:
        """Remove an entry. Returns True if it existed."""
        if key in self._entries:
            del self._entries[key]
            return True
        return False

    def keys(self) -> list:
        return list(self._entries.keys())

    def values(self) -> list:
        return list(self._entries.values())

    def items(self) -> list:
        return list(self._entries.items())

    def grow(self, additional_capacity: int) -> None:
        """Expand capacity by additional_capacity entries."""
        self.capacity += additional_capacity
        self._resizes += 1
        print(f"[SHORE] Table '{self.name}' grew to capacity {self.capacity} "
              f"(resize #{self._resizes})")

    def shrink_to_fit(self) -> int:
        """
        Reduce capacity to current entry count + 20% headroom.
        Returns cells freed.
        """
        new_capacity = max(self.INITIAL_CAPACITY,
                           int(self.entry_count * 1.2))
        freed = max(0, self.capacity - new_capacity)
        self.capacity = new_capacity
        return freed

    def snapshot(self) -> dict:
        """Capture complete table state for migration or backup."""
        return {
            "name":       self.name,
            "capacity":   self.capacity,
            "region_id":  self.region_id,
            "entries":    dict(self._entries),
            "resizes":    self._resizes,
        }

    def restore(self, state: dict) -> None:
        """Restore table state from a snapshot."""
        self.capacity   = state["capacity"]
        self.region_id  = state.get("region_id")
        self._entries   = dict(state.get("entries", {}))
        self._resizes   = state.get("resizes", 0)

    def status(self) -> dict:
        return {
            "name":        self.name,
            "entry_count": self.entry_count,
            "capacity":    self.capacity,
            "utilisation": round(self.utilisation * 100, 1),
            "needs_growth":self.needs_growth,
            "region_id":   self.region_id,
            "resizes":     self._resizes,
        }

    def __repr__(self) -> str:
        return (f"ShoreTile('{self.name}' "
                f"{self.entry_count}/{self.capacity} "
                f"= {self.utilisation*100:.0f}%)")


# ── Shore v2 ──────────────────────────────────────────────────────────────────

class ShoreV2:
    """
    System registry — authoritative record of everything in the array.

    Four internal tables, each a ShoreTile (independent region):
      registry:     name → ShoreEntry       all known resources
      address_map:  local_addr → name       reverse address lookup
      translation:  proxy_addr → ExtAddr    extended address translations
      connections:  conn_id → Connection    live inter-Pond connections

    Shore's outer boundary = estimated_size * 1.15 (15% headroom).
    Tables grow within that boundary. Shore requests COMPANION
    coordination if the pool is exhausted.

    Accepts Ward announcement packets via receive_packet().
    Sends ROUTE_UPDATE packets to affected connections when a
    resource moves.
    """

    # Reserved proxy address range for extended (>4GB) resources
    PROXY_BASE = PROXY_BASE
    PROXY_TOP  = PROXY_TOP

    # Default initial capacity per table
    DEFAULT_TABLE_CAPACITY = 64

    # Growth increment when a table needs more space
    GROWTH_INCREMENT = 32

    def __init__(self,
                 shore_id:       str = "shore_0",
                 base_address:   int = 0x00500000,
                 initial_capacity: int = DEFAULT_TABLE_CAPACITY):
        self.shore_id      = shore_id
        self.base_address  = base_address
        self.created_at    = time.time()
        self._next_proxy   = PROXY_BASE    # next available proxy address
        self._next_conn_id = 0             # connection ID counter
        self._pond_id_counter = 0          # Shore registry ID counter
        self._packet_log:  list[dict] = [] # received packet history

        # Four internal tables
        self._registry    = ShoreTile("registry",    initial_capacity)
        self._address_map = ShoreTile("address_map", initial_capacity)
        self._translation = ShoreTile("translation", initial_capacity // 4)
        self._connections = ShoreTile("connections", initial_capacity // 2)

        # Shore's own entry in its registry
        self._registry.put("__shore__", ShoreEntry(
            name          = shore_id,
            resource_type = "SHORE",
            local_address = base_address,
            base_address  = base_address,
            offset        = 0,
            metadata      = {"version": 2, "created_at": self.created_at},
        ))

        print(f"[SHORE] '{shore_id}' initialised at 0x{base_address:08X}")

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, entry: ShoreEntry) -> bool:
        """
        Register a resource with Shore.

        If the table needs growth, it is grown automatically using
        Shore's internal growth mechanism.

        Returns True on success.
        """
        if self._registry.needs_growth:
            self._grow_table(self._registry)

        ok = self._registry.put(entry.name, entry)
        if not ok:
            self._grow_table(self._registry)
            ok = self._registry.put(entry.name, entry)

        if ok and entry.local_address is not None:
            # Also update reverse address map
            if self._address_map.needs_growth:
                self._grow_table(self._address_map)
            self._address_map.put(str(entry.local_address), entry.name)

        return ok

    def deregister(self, name: str) -> bool:
        """
        Remove a resource from Shore's registry.
        Also removes its address map entry and closes any connections.
        Returns True if the entry existed.
        """
        entry = self._registry.get(name)
        if entry is None:
            return False

        self._registry.remove(name)

        if entry.local_address is not None:
            self._address_map.remove(str(entry.local_address))

        # Close any connections involving this resource
        for conn_id, conn in list(self._connections.items()):
            if conn.source_name == name or conn.dest_name == name:
                conn.active = False

        return True

    def update(self, name: str, **kwargs) -> bool:
        """
        Update fields of an existing registry entry.
        If local_address changes, the address map is updated accordingly.
        Returns True if the entry existed and was updated.
        """
        entry = self._registry.get(name)
        if entry is None:
            return False

        old_addr = entry.local_address

        for k, v in kwargs.items():
            if hasattr(entry, k):
                setattr(entry, k, v)
        entry.last_seen = time.time()

        # Update address map if address changed
        new_addr = entry.local_address
        if old_addr != new_addr:
            if old_addr is not None:
                self._address_map.remove(str(old_addr))
            if new_addr is not None:
                self._address_map.put(str(new_addr), name)

        return True

    # ── Lookup ────────────────────────────────────────────────────────────────

    def lookup(self, name: str) -> Optional[ShoreEntry]:
        """Look up a resource by name."""
        return self._registry.get(name)

    def lookup_address(self, local_address: int) -> Optional[ShoreEntry]:
        """Reverse lookup — find a resource by its local bus address."""
        name = self._address_map.get(str(local_address))
        if name is None:
            return None
        return self._registry.get(name)

    def lookup_pond(self, pond_id: int) -> Optional[ShoreEntry]:
        """Find a Pond entry by its Shore registry ID."""
        for entry in self._registry.values():
            if entry.pond_id == pond_id:
                return entry
        return None

    def find_by_type(self, resource_type: str) -> list[ShoreEntry]:
        """Return all entries of a given resource type."""
        return [e for e in self._registry.values()
                if e.resource_type == resource_type]

    def find_by_ward_state(self, state: str) -> list[ShoreEntry]:
        """Return all entries with a given Ward state."""
        return [e for e in self._registry.values()
                if e.ward_state == state]

    # ── Extended address translation ──────────────────────────────────────────

    def register_extended(self, real_addr: int,
                           description: str = "") -> int:
        """
        Register a 64-bit extended address.

        Allocates a local proxy address in the reserved range
        (0xF0000000 - 0xFFFFFFFF). Returns the proxy address.
        Any cell sending to the proxy address will be forwarded
        to real_addr via the 64-bit bus.

        Returns 0 if the proxy range is exhausted.
        """
        if self._next_proxy > PROXY_TOP:
            print("[SHORE] ERROR: proxy address range exhausted")
            return 0

        proxy = self._next_proxy
        self._next_proxy += 1

        ext = ExtAddr(proxy_addr=proxy, real_addr=real_addr,
                      description=description)

        if self._translation.needs_growth:
            self._grow_table(self._translation)
        self._translation.put(str(proxy), ext)

        # Also register in main registry
        self.register(ShoreEntry(
            name          = description or f"ext_{hex(real_addr)}",
            resource_type = "EXTERNAL",
            local_address = proxy,
            extended_addr = real_addr,
            metadata      = {"proxy": hex(proxy), "real": hex(real_addr)},
        ))

        print(f"[SHORE] Extended: {description} "
              f"proxy=0x{proxy:08X} → real=0x{real_addr:016X}")
        return proxy

    def resolve_extended(self, proxy_addr: int) -> Optional[ExtAddr]:
        """
        Look up the real 64-bit address for a proxy address.
        Returns None if the proxy is not registered.
        """
        return self._translation.get(str(proxy_addr))

    def is_proxy(self, address: int) -> bool:
        """True if this address is in the extended proxy range."""
        return PROXY_BASE <= address <= PROXY_TOP

    # ── Connection management ─────────────────────────────────────────────────

    def connect(self, source_name: str, dest_name: str) -> Optional[str]:
        """
        Record a connection between two resources.
        Returns the connection ID, or None if either resource is unknown.
        """
        src = self._registry.get(source_name)
        dst = self._registry.get(dest_name)
        if src is None or dst is None:
            return None

        conn_id = f"conn_{self._next_conn_id:04d}"
        self._next_conn_id += 1

        conn = Connection(
            conn_id        = conn_id,
            source_name    = source_name,
            dest_name      = dest_name,
            source_address = src.resolve_address() or 0,
            dest_address   = dst.resolve_address() or 0,
        )

        if self._connections.needs_growth:
            self._grow_table(self._connections)
        self._connections.put(conn_id, conn)

        return conn_id

    def disconnect(self, conn_id: str) -> bool:
        """Close a connection."""
        conn = self._connections.get(conn_id)
        if conn is None:
            return False
        conn.active = False
        return True

    def connections_for(self, name: str) -> list[Connection]:
        """Return all active connections involving a named resource."""
        return [c for c in self._connections.values()
                if c.active and (c.source_name == name
                                  or c.dest_name == name)]

    # ── Packet handling ───────────────────────────────────────────────────────

    def receive_packet(self, packet: Packet) -> Optional[Packet]:
        """
        Process an incoming packet.

        Ward announcement packets update the registry.
        Route update requests generate ROUTE_UPDATE packets to
        affected connections.

        Returns a response packet if one is needed, else None.
        """
        self._packet_log.append({
            "received_at": time.time(),
            "packet":      packet.describe(),
        })

        # CONFIG packets — cell configuration, not registry updates
        if packet.is_config:
            return None

        # ANNOUNCE + CAPABILITY — Ward registering or updating a Pond
        if packet.is_announce and packet.is_capability:
            cap = CapabilityDescriptor.unpack(packet.value)
            self._handle_announce(packet.address, cap)
            return Packet.ack(packet.address)

        # READY — Pond is operational
        if packet.is_ready:
            cap = CapabilityDescriptor.unpack(packet.value)
            self._handle_ready(packet.address, cap)
            return Packet.ack(packet.address)

        # MOVING — Pond about to migrate
        if packet.is_moving:
            self._handle_moving(packet.address)
            return Packet.ack(packet.address)

        # ROUTE_UPDATE — address has changed, update connections
        if packet.is_route_update:
            self._handle_route_update(packet.address, packet.value)
            return None

        return None

    def _handle_announce(self, address: int,
                          cap: CapabilityDescriptor) -> None:
        """Handle ANNOUNCE packet — register or update a Pond."""
        pond_type_name = POND_TYPE_NAMES.get(cap.pond_type, "PROCESS")
        ward_state_name = WARD_STATE_NAMES.get(cap.ward_state, "IDLE")
        security_name = {0: "OPEN", 1: "PRIVATE", 2: "HIDDEN"}.get(
            cap.security_level, "OPEN")

        name = f"pond_{cap.pond_id}"
        existing = self._registry.get(name)

        if existing is not None:
            # Update existing entry
            self.update(name,
                        local_address = address,
                        capabilities  = cap,
                        ward_state    = ward_state_name,
                        metadata      = {
                            "pond_type":   pond_type_name,
                            "security":    security_name,
                            "bridge_count": cap.bridge_count,
                        })
        else:
            # New registration
            pond_id = self._pond_id_counter
            self._pond_id_counter += 1
            self.register(ShoreEntry(
                name          = name,
                resource_type = "POND",
                local_address = address,
                pond_id       = cap.pond_id,
                capabilities  = cap,
                ward_state    = ward_state_name,
                metadata      = {
                    "pond_type":    pond_type_name,
                    "security":     security_name,
                    "bridge_count": cap.bridge_count,
                },
            ))
            print(f"[SHORE] Registered '{name}' at 0x{address:08X} "
                  f"type={pond_type_name} ward={ward_state_name}")

    def _handle_ready(self, address: int,
                       cap: CapabilityDescriptor) -> None:
        """Handle READY packet — mark Pond as operational."""
        name = f"pond_{cap.pond_id}"
        self.update(name, ward_state="HEALTHY", local_address=address)
        print(f"[SHORE] '{name}' READY at 0x{address:08X}")

    def _handle_moving(self, address: int) -> None:
        """Handle MOVING packet — flag Pond as migrating."""
        entry = self.lookup_address(address)
        if entry:
            self.update(entry.name, ward_state="MOVING")
            print(f"[SHORE] '{entry.name}' MOVING from 0x{address:08X}")

    def _handle_route_update(self, old_address: int,
                              new_address: int) -> None:
        """
        Handle route update — a resource has moved to a new address.
        Updates Shore's registry and notifies affected connections.
        """
        entry = self.lookup_address(old_address)
        if entry is None:
            return

        old_name = entry.name
        self.update(old_name, local_address=new_address)
        print(f"[SHORE] '{old_name}' moved "
              f"0x{old_address:08X} → 0x{new_address:08X}")

        # Notify connections that reference the old address
        for conn in self.connections_for(old_name):
            if conn.source_address == old_address:
                conn.source_address = new_address
            if conn.dest_address == old_address:
                conn.dest_address = new_address
            conn.last_activity = time.time()

    # ── Table growth ──────────────────────────────────────────────────────────

    def _grow_table(self, table: ShoreTile) -> None:
        """
        Grow a table by GROWTH_INCREMENT entries.

        In the full implementation this allocates from Shore's internal
        cell pool, potentially relocating the table to a new contiguous
        region if needed. Here we grow the Python-level capacity directly,
        which gives the same interface and triggers the same signals.
        """
        table.grow(self.GROWTH_INCREMENT)

    def request_expansion(self, additional_cells: int) -> None:
        """
        Request Shore outer boundary expansion.
        In production: sends a packet to COMPANION to coordinate
        with the array allocator. Here: logged for COMPANION to act on.
        """
        print(f"[SHORE] Requesting {additional_cells} additional cells "
              f"from COMPANION")
        # COMPANION integration point — handled in phase 4

    # ── Snapshot and migration ────────────────────────────────────────────────

    def snapshot(self) -> dict:
        """
        Capture complete Shore state for migration or backup.
        All four tables are snapshotted independently.
        """
        return {
            "shore_id":      self.shore_id,
            "base_address":  self.base_address,
            "created_at":    self.created_at,
            "next_proxy":    self._next_proxy,
            "next_conn_id":  self._next_conn_id,
            "pond_id_counter": self._pond_id_counter,
            "registry":      self._registry.snapshot(),
            "address_map":   self._address_map.snapshot(),
            "translation":   self._translation.snapshot(),
            "connections":   self._connections.snapshot(),
        }

    def restore(self, state: dict) -> None:
        """Restore Shore from a snapshot."""
        self.shore_id       = state["shore_id"]
        self.base_address   = state["base_address"]
        self._next_proxy    = state["next_proxy"]
        self._next_conn_id  = state["next_conn_id"]
        self._pond_id_counter = state["pond_id_counter"]
        self._registry.restore(state["registry"])
        self._address_map.restore(state["address_map"])
        self._translation.restore(state["translation"])
        self._connections.restore(state["connections"])

    def relocate(self, new_base_address: int) -> None:
        """
        Migrate Shore to a new base address.
        Updates all relative addresses in the registry.
        """
        old_base = self.base_address
        delta    = new_base_address - old_base
        self.base_address = new_base_address

        # Update any entries that were relative to the old base
        for entry in self._registry.values():
            if entry.base_address == old_base:
                entry.base_address = new_base_address
                if entry.local_address is not None:
                    old_addr = entry.local_address
                    entry.local_address = old_addr + delta

        print(f"[SHORE] Relocated from 0x{old_base:08X} "
              f"to 0x{new_base_address:08X} (delta={delta:+d})")

    # ── Status and inspection ─────────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "shore_id":      self.shore_id,
            "base_address":  hex(self.base_address),
            "tables": {
                "registry":    self._registry.status(),
                "address_map": self._address_map.status(),
                "translation": self._translation.status(),
                "connections": self._connections.status(),
            },
            "total_entries":   self._registry.entry_count,
            "active_connections": sum(
                1 for c in self._connections.values() if c.active),
            "proxy_addresses_used": self._next_proxy - PROXY_BASE,
        }

    def dump(self) -> str:
        """Human-readable dump of Shore contents."""
        lines = [
            f"Shore '{self.shore_id}' @ 0x{self.base_address:08X}",
            f"  Registry ({self._registry.entry_count} entries):",
        ]
        for name, entry in self._registry.items():
            addr = f"0x{entry.local_address:08X}" if entry.local_address else "none"
            lines.append(f"    {name}: {entry.resource_type} @ {addr} "
                         f"ward={entry.ward_state}")
        if self._connections.entry_count:
            lines.append(f"  Connections ({self._connections.entry_count}):")
            for cid, conn in self._connections.items():
                status = "ACTIVE" if conn.active else "CLOSED"
                lines.append(f"    {cid}: {conn.source_name} → "
                             f"{conn.dest_name} [{status}]")
        if self._translation.entry_count:
            lines.append(f"  Extended translations "
                         f"({self._translation.entry_count}):")
            for _, ext in self._translation.items():
                lines.append(f"    0x{ext.proxy_addr:08X} → "
                             f"0x{ext.real_addr:016X} ({ext.description})")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (f"ShoreV2('{self.shore_id}' "
                f"entries={self._registry.entry_count} "
                f"connections={self._connections.entry_count})")
