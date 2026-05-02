"""
packet_spec.py — Imago 80-bit Communications Packet

Defines the standard 80-bit packet format used for all inter-Pond
communications, Ward announcements, Shore registration, cell configuration,
and routing updates.

Packet layout (80 bits = 10 bytes)
====================================

  bits  0-31:  address      (32 bits) — destination bus address
  bit   32:    CONFIG        (1 bit)  — packet type sentinel
  bits 33-39:  flags         (7 bits) — control signals
  bits 40-79:  data         (40 bits) — payload (interpreted by CONFIG flag)

The CONFIG flag is the primary type sentinel. Receivers check bit 32 first
to determine how to interpret the data field.

Note on the start_flag
=======================

The start_flag is a separate hardware control line per cell — completely
independent of the 32-bit data bus and this packet protocol. Setting or
clearing it does not appear on the data bus. The ARM config_flag in a
CONFIG packet triggers a direct register write to that control line after
the cell is configured — it does not travel on the data bus either.

This separation is fundamental: a frozen Pond (all start_flags cleared)
ignores everything on the data bus regardless of bus state. The control
plane and data plane are physically distinct.

Data field interpretation
==========================

When CONFIG = 0  (data / announcement packet):
  bits 40-71:  value        (32 bits) — address, capability descriptor, etc.
  bits 72-79:  reserved     ( 8 bits) — future use, must be zero

When CONFIG = 1, CFG_BRIDGE not set  (compute cell configuration):
  bits 40-48:  gate_state   ( 9 bits) — full NOR gate topology
  bits 49-57:  input_offset ( 9 bits) — input address as offset from Pond base
  bits 58-68:  output_offset(11 bits) — output address offset (0-2047 cells)
  bits 69-72:  config_flags ( 4 bits) — cell configuration modifiers (see below)
  bits 73-79:  reserved     ( 7 bits) — must be zero

When CONFIG = 1, CFG_BRIDGE set  (bridge cell configuration):
  bits 40-48:  ext_addr[31:23] (9 bits)  — high bits of external output address
                                           gate_state is always 0 for bridges
                                           (PASS cell, NOR gates quiescent)
                                           these 9 bits are repurposed
  bits 49-57:  input_offset    (9 bits)  — inside Pond, Pond-relative (unchanged)
  bits 58-68:  ext_addr[22:12] (11 bits) — mid bits of external output address
  bits 69-72:  config_flags    (4 bits)  — CFG_BRIDGE set, plus ARM/ECC as needed
  bits 73-79:  ext_addr[11:5]  (7 bits)  — low bits of external output address
                                           (was reserved)

  External address reconstruction:
    ext_addr = (bits[40:48] << 23) | (bits[58:68] << 12) | (bits[73:79] << 5)
    Covers aligned addresses 0x00000020 to 0xFFFFFFE0 (32-byte alignment).
    Bridge output addresses are always allocator-assigned and naturally aligned
    so the bottom 5 bits are always zero.

  Addresses beyond this range or beyond 4GB:
    Register with Shore.register_extended() to get a local proxy address.
    Shore holds the real 64-bit address and translates transparently.
    The proxy address fits within the 27-bit range — no special handling needed.
    Shore is the single gate for all extended addressing. No other component
    needs to know about 64-bit addresses.

CONFIG packet config_flags (bits 69-72)
========================================

  bit 69:  STORAGE_MODE — set latch flag on this cell (makes it a storage cell)
  bit 70:  LOOP_MODE    — set loop_mode flag (cell re-arms after firing)
  bit 71:  ECC_ENABLE   — enable ECC on this cell
  bit 72:  ARM          — assert start_flag immediately after configuration
                          Enables streaming load: send N-1 packets with ARM=0,
                          then one final packet with ARM=1. The cell configured
                          by the ARM packet fires last, triggering the whole
                          tile simultaneously. No separate thaw() needed.
  bit 73:  BRIDGE       — this is a bridge cell configuration (see above).
                          Repurposes gate_state and reserved fields to carry
                          the 27-bit external output address.

  Note: CFG_BRIDGE occupies bit 73 which was previously reserved. The
  config_flags field therefore effectively spans bits 69-73 (5 bits) when
  BRIDGE configs are in use. Bits 74-79 remain reserved.

The start_flag is a separate control line (not encoded in the packet data).
The ARM flag causes the receiver to assert that line after writing registers.

DMA block loading (boot / Pond restore)
========================================

For large Pond restores or boot-time loading, the BIOS and DMA controller
bypass the packet protocol entirely and write cell registers directly via
DMA block transfer. This is faster than sending thousands of CONFIG packets
and is handled below the packet layer. The packet protocol handles normal
runtime configuration; DMA handles bulk initialisation.

Flag bits (bits 33-39)
=======================

  bit 33:  ANNOUNCE     — Ward registration or update packet
  bit 34:  ROUTE_UPDATE — a routing address has changed
  bit 35:  READY        — Pond is placed and fully operational
  bit 36:  MOVING       — Pond is about to migrate (hold incoming traffic)
  bit 37:  CAPABILITY   — data field carries a capability descriptor
  bit 38:  ACK          — acknowledgement of a previous packet
  bit 39:  PRIORITY     — bypass queue, deliver immediately

Capability descriptor (32-bit value field when CAPABILITY flag set)
====================================================================

  bits  0- 3:  pond_type      (4 bits) — see POND_TYPE_* constants
  bits  4- 7:  bridge_count   (4 bits) — number of bridges (0-15)
  bits  8-11:  inbound_lanes  (4 bits) — INBOUND bridge lane width
  bits 12-15:  outbound_lanes (4 bits) — OUTBOUND bridge lane width
  bits 16-19:  ward_state     (4 bits) — see WARD_STATE_* constants
  bits 20-22:  security_level (3 bits) — see SECURITY_* constants
  bits 23-31:  pond_id        (9 bits) — local identifier within Shore registry
  (bits 32-39 reserved in full 40-bit data field)

Typical packet combinations
============================

  CONFIG=0, flags=0:              plain data transfer
  CONFIG=0, ANNOUNCE:             Ward announces Pond presence to Shore
  CONFIG=0, ANNOUNCE|CAPABILITY:  full Pond registration (type, health, bridges)
  CONFIG=0, ROUTE_UPDATE:         Shore notifies connected Ponds of address change
  CONFIG=0, READY:                Pond signals it is armed and accepting traffic
  CONFIG=0, MOVING:               Pond signals imminent migration (freeze incoming)
  CONFIG=0, ACK:                  acknowledgement of any of the above
  CONFIG=1, config_flags=0:       cell configuration only
  CONFIG=1, config_flags=ARM:     cell configuration + immediate arm
  CONFIG=1, config_flags=ARM|ECC: cell configuration + arm + ECC enable
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── Packet dimensions ────────────────────────────────────────────────────────

PACKET_BITS  = 80
PACKET_BYTES = 10   # 80 / 8


# ── Field positions (bit indices, inclusive) ──────────────────────────────────

ADDR_LSB      = 0
ADDR_MSB      = 31
ADDR_BITS     = 32

CONFIG_BIT    = 32          # 1 = cell config packet, 0 = data packet

FLAG_LSB      = 33
FLAG_MSB      = 39
FLAG_BITS     = 7

DATA_LSB      = 40
DATA_MSB      = 79
DATA_BITS     = 40          # full data field width

# DATA sub-fields when CONFIG=0
VALUE_LSB     = 40
VALUE_MSB     = 71
VALUE_BITS    = 32

RESERVED_LSB  = 72
RESERVED_MSB  = 79

# DATA sub-fields when CONFIG=1
GS_LSB        = 40
GS_MSB        = 48
GS_BITS       = 9

IN_OFF_LSB    = 49
IN_OFF_MSB    = 57
IN_OFF_BITS   = 9

OUT_OFF_LSB   = 58
OUT_OFF_MSB   = 68
OUT_OFF_BITS  = 11           # 2,048 cell offset range per Pond

# CONFIG cell modifier flags (bits 69-72, plus BRIDGE at bit 73)
CFG_FLAG_LSB       = 69
CFG_FLAG_BITS      = 5      # effectively 5 bits when BRIDGE is included

CFG_STORAGE_MODE   = 0b00001  # bit 69 — make this cell a storage latch
CFG_LOOP_MODE      = 0b00010  # bit 70 — cell re-arms after firing
CFG_ECC_ENABLE     = 0b00100  # bit 71 — enable ECC on this cell
CFG_ARM            = 0b01000  # bit 72 — assert start_flag after config
CFG_BRIDGE         = 0b10000  # bit 73 — bridge cell config (repurposes
                               #          gate_state and reserved fields
                               #          to carry 35-bit external address)
                               #          non-zero ext_xhi = beyond 4GB → Shore

# Bridge CONFIG external address bit layout
# Bridge cells are allocated at 64-byte aligned addresses (BRIDGE_ALIGN_SHIFT=6).
# This allows the 26 encoded bits to cover the full 32-bit address space.
#
# Encoding:
#   ext_hi  = ext_addr[31:23]  — 9 bits, stored in bits 40-48 (was gate_state)
#   ext_mid = ext_addr[22:12]  — 11 bits, stored in bits 58-68 (was out_offset)
#   ext_lo  = ext_addr[11:6]   — 6 bits, stored in bits 74-79
#   bottom 6 bits = 0          — 64-byte alignment
#
# Reconstruction: ext_addr = (hi << 23) | (mid << 12) | (lo << 6)
# Max address: 0xFFFFFFC0
BRIDGE_EXT_HI_LSB  = 40   # bits 40-48: ext_addr[31:23]  (9 bits, was gate_state)
BRIDGE_EXT_HI_BITS = 9
BRIDGE_EXT_MID_LSB = 58   # bits 58-68: ext_addr[22:12]  (11 bits, was out_offset)
BRIDGE_EXT_MID_BITS= 11
BRIDGE_ARM_BIT     = 69   # bit 69: ARM flag (only config_flag needed for bridges)
BRIDGE_EXT_XHI_LSB = 70   # bits 70-72: ext_addr[34:32]  (3 bits, extended range)
BRIDGE_EXT_XHI_BITS= 3    # non-zero = beyond 4GB, pass to Shore for translation
BRIDGE_FLAG_BIT    = 73   # bit 73: CFG_BRIDGE marker (= 1 always for bridge pkts)
BRIDGE_EXT_LO_LSB  = 74   # bits 74-79: ext_addr[11:6]   (6 bits)
BRIDGE_EXT_LO_BITS = 6
BRIDGE_ALIGN_SHIFT = 6    # bottom 6 bits always zero (64-byte alignment)
BRIDGE_ADDR_BITS   = 35   # total addressable range: 32GB direct

# Reconstruction: ext_addr = (xhi<<32) | (hi<<23) | (mid<<12) | (lo<<6)
# Local range (xhi=0):    0x000000000 to 0x0FFFFFFC0
# Extended range (xhi>0): beyond 4GB — Shore translates to full 64-bit address

# Reserved (bits 74-79 when not BRIDGE, or low ext_addr bits when BRIDGE)
CFG_RESERVED_LSB   = 74
CFG_RESERVED_MSB   = 79


# ── Flag constants (bit positions relative to start of flag field) ────────────

FLAG_ANNOUNCE     = 0b0000001   # bit 33 — Ward announcement
FLAG_ROUTE_UPDATE = 0b0000010   # bit 34 — routing address changed
FLAG_READY        = 0b0000100   # bit 35 — Pond placed and operational
FLAG_MOVING       = 0b0001000   # bit 36 — Pond about to migrate
FLAG_CAPABILITY   = 0b0010000   # bit 37 — data field is capability descriptor
FLAG_ACK          = 0b0100000   # bit 38 — acknowledgement
FLAG_PRIORITY     = 0b1000000   # bit 39 — bypass queue

# Common flag combinations
FLAGS_REGISTER    = FLAG_ANNOUNCE | FLAG_CAPABILITY   # full Pond registration
FLAGS_ONLINE      = FLAG_ANNOUNCE | FLAG_READY        # Pond is live
FLAGS_MIGRATING   = FLAG_ANNOUNCE | FLAG_MOVING       # about to move


# ── Capability descriptor field offsets (within 32-bit value) ────────────────

CAP_POND_TYPE_SHIFT    = 0    # bits 0-3
CAP_BRIDGE_COUNT_SHIFT = 4    # bits 4-7
CAP_IN_LANES_SHIFT     = 8    # bits 8-11
CAP_OUT_LANES_SHIFT    = 12   # bits 12-15
CAP_WARD_STATE_SHIFT   = 16   # bits 16-19
CAP_SECURITY_SHIFT     = 20   # bits 20-22
CAP_POND_ID_SHIFT      = 23   # bits 23-31

CAP_POND_TYPE_MASK     = 0xF
CAP_BRIDGE_COUNT_MASK  = 0xF
CAP_LANES_MASK         = 0xF
CAP_WARD_STATE_MASK    = 0xF
CAP_SECURITY_MASK      = 0x7
CAP_POND_ID_MASK       = 0x1FF


# ── Pond type codes (4-bit, fits in capability descriptor) ────────────────────

POND_TYPE_PROCESS    = 0
POND_TYPE_FILE       = 1
POND_TYPE_PERIPHERAL = 2
POND_TYPE_LIBRARY    = 3
POND_TYPE_BOOT       = 4
POND_TYPE_COMPANION  = 5

POND_TYPE_NAMES = {
    POND_TYPE_PROCESS:    "PROCESS",
    POND_TYPE_FILE:       "FILE",
    POND_TYPE_PERIPHERAL: "PERIPHERAL",
    POND_TYPE_LIBRARY:    "LIBRARY",
    POND_TYPE_BOOT:       "BOOT",
    POND_TYPE_COMPANION:  "COMPANION",
}

POND_TYPE_CODES = {v: k for k, v in POND_TYPE_NAMES.items()}


# ── Ward state codes (4-bit) ──────────────────────────────────────────────────

WARD_STATE_IDLE     = 0
WARD_STATE_HEALTHY  = 1
WARD_STATE_DEGRADED = 2
WARD_STATE_STALLED  = 3
WARD_STATE_SILENT   = 4
WARD_STATE_OFFLINE  = 5

WARD_STATE_NAMES = {
    WARD_STATE_IDLE:     "IDLE",
    WARD_STATE_HEALTHY:  "HEALTHY",
    WARD_STATE_DEGRADED: "DEGRADED",
    WARD_STATE_STALLED:  "STALLED",
    WARD_STATE_SILENT:   "SILENT",
    WARD_STATE_OFFLINE:  "OFFLINE",
}


# ── Security level codes (3-bit) ──────────────────────────────────────────────

SECURITY_OPEN    = 0
SECURITY_PRIVATE = 1
SECURITY_HIDDEN  = 2

SECURITY_NAMES = {
    SECURITY_OPEN:    "OPEN",
    SECURITY_PRIVATE: "PRIVATE",
    SECURITY_HIDDEN:  "HIDDEN",
}


# ── Packet dataclass ──────────────────────────────────────────────────────────

@dataclass
class Packet:
    """
    One 80-bit Imago communications packet.

    Construct directly or use the factory methods:
        Packet.data(address, value, flags)
        Packet.config(address, gate_state, input_offset, output_offset)
        Packet.announce(address, capability)
        Packet.route_update(address, new_external_address)
        Packet.ack(address)
    """

    address:        int           # 32-bit destination address
    is_config:      bool  = False # CONFIG flag (bit 32)
    flags:          int   = 0     # 7-bit flag field

    # Data packet fields (CONFIG=0)
    value:          int   = 0     # 32-bit payload value

    # Config packet fields (CONFIG=1)
    gate_state:     int   = 0     # 9-bit NOR topology (0 for bridge cells)
    input_offset:   int   = 0     # 9-bit input address offset (Pond-relative)
    output_offset:  int   = 0     # 11-bit output offset (compute) or
                                  # ext_addr mid bits (bridge)
    config_flags:   int   = 0     # cell modifier flags — CFG_* constants
                                  # bits 0-3: STORAGE/LOOP/ECC/ARM (bits 69-72)
                                  # bit  4:   BRIDGE                (bit 73)
    ext_hi:         int   = 0     # bridge: ext_addr[31:23]  (9 bits, bits 40-48)
    ext_xhi:        int   = 0     # bridge: ext_addr[34:32]  (3 bits, bits 70-72)
    ext_lo:         int   = 0     # bridge: ext_addr[11:6]   (6 bits, bits 74-79)
    bridge_arm:     bool  = False # bridge: ARM flag (bit 69)

    # ── Flag helpers ──────────────────────────────────────────────────────────

    def has_flag(self, flag: int) -> bool:
        return bool(self.flags & flag)

    @property
    def is_announce(self)     -> bool: return self.has_flag(FLAG_ANNOUNCE)
    @property
    def is_route_update(self) -> bool: return self.has_flag(FLAG_ROUTE_UPDATE)
    @property
    def is_ready(self)        -> bool: return self.has_flag(FLAG_READY)
    @property
    def is_moving(self)       -> bool: return self.has_flag(FLAG_MOVING)
    @property
    def is_capability(self)   -> bool: return self.has_flag(FLAG_CAPABILITY)
    @property
    def is_ack(self)          -> bool: return self.has_flag(FLAG_ACK)
    @property
    def is_priority(self)     -> bool: return self.has_flag(FLAG_PRIORITY)

    # ── Serialisation ─────────────────────────────────────────────────────────

    def pack(self) -> int:
        """
        Serialise to an 80-bit integer.
        Bits 0-31: address, bit 32: CONFIG, bits 33-39: flags, bits 40-79: data.
        """
        result = self.address & 0xFFFFFFFF                     # bits 0-31
        if self.is_config:
            result |= (1 << CONFIG_BIT)                        # bit 32
        result |= (self.flags & 0x7F) << FLAG_LSB              # bits 33-39

        if self.is_config:
            is_bridge = bool(self.config_flags & CFG_BRIDGE)
            if is_bridge:
                # Bridge CONFIG: 35-bit address across freed fields
                # bit 69=ARM, bits 70-72=ext_addr[34:32], bit 73=CFG_BRIDGE
                result |= (self.ext_hi        & 0x1FF) << BRIDGE_EXT_HI_LSB  # 40-48
                result |= (self.input_offset  & 0x1FF) << IN_OFF_LSB          # 49-57
                result |= (self.output_offset & 0x7FF) << BRIDGE_EXT_MID_LSB  # 58-68
                if self.bridge_arm:
                    result |= (1 << BRIDGE_ARM_BIT)                            # 69
                result |= (self.ext_xhi       & 0x007) << BRIDGE_EXT_XHI_LSB  # 70-72
                result |= (1                          ) << BRIDGE_FLAG_BIT     # 73
                result |= (self.ext_lo        & 0x03F) << BRIDGE_EXT_LO_LSB   # 74-79
            else:
                # Normal compute cell CONFIG
                result |= (self.gate_state    & 0x1FF) << GS_LSB
                result |= (self.input_offset  & 0x1FF) << IN_OFF_LSB
                result |= (self.output_offset & 0x7FF) << OUT_OFF_LSB
                result |= (self.config_flags  & 0x01F) << CFG_FLAG_LSB
        else:
            result |= (self.value & 0xFFFFFFFF) << VALUE_LSB   # bits 40-71

        return result & ((1 << PACKET_BITS) - 1)

    @classmethod
    def unpack(cls, raw: int) -> "Packet":
        """Deserialise from an 80-bit integer."""
        raw = raw & ((1 << PACKET_BITS) - 1)

        address   = raw & 0xFFFFFFFF
        is_config = bool((raw >> CONFIG_BIT) & 1)
        flags     = (raw >> FLAG_LSB) & 0x7F

        if is_config:
            config_flags  = (raw >> CFG_FLAG_LSB) & 0x01F
            input_offset  = (raw >> IN_OFF_LSB)   & 0x1FF
            is_bridge     = bool(config_flags & CFG_BRIDGE)

            if is_bridge:
                ext_hi        = (raw >> BRIDGE_EXT_HI_LSB)  & 0x1FF
                output_offset = (raw >> BRIDGE_EXT_MID_LSB) & 0x7FF
                bridge_arm    = bool((raw >> BRIDGE_ARM_BIT) & 1)
                ext_xhi       = (raw >> BRIDGE_EXT_XHI_LSB) & 0x007
                ext_lo        = (raw >> BRIDGE_EXT_LO_LSB)  & 0x03F
                return cls(address=address, is_config=True, flags=flags,
                           gate_state=0,
                           input_offset=input_offset,
                           output_offset=output_offset,
                           config_flags=config_flags,
                           ext_hi=ext_hi, ext_xhi=ext_xhi,
                           ext_lo=ext_lo, bridge_arm=bridge_arm)
            else:
                gate_state    = (raw >> GS_LSB)      & 0x1FF
                output_offset = (raw >> OUT_OFF_LSB) & 0x7FF
                return cls(address=address, is_config=True, flags=flags,
                           gate_state=gate_state,
                           input_offset=input_offset,
                           output_offset=output_offset,
                           config_flags=config_flags)
        else:
            value = (raw >> VALUE_LSB) & 0xFFFFFFFF
            return cls(address=address, is_config=False, flags=flags,
                       value=value)

    def to_bytes(self) -> bytes:
        """Serialise to 10 bytes (big-endian)."""
        raw = self.pack()
        return raw.to_bytes(PACKET_BYTES, byteorder='big')

    @classmethod
    def from_bytes(cls, data: bytes) -> "Packet":
        """Deserialise from 10 bytes (big-endian)."""
        raw = int.from_bytes(data[:PACKET_BYTES], byteorder='big')
        return cls.unpack(raw)

    # ── Factory methods ───────────────────────────────────────────────────────

    @classmethod
    def data(cls, address: int, value: int, flags: int = 0) -> "Packet":
        """Plain data transfer packet."""
        return cls(address=address, is_config=False, flags=flags, value=value)

    @property
    def external_address(self) -> int:
        """
        Reconstruct the 32-bit external output address from a BRIDGE_CONFIG packet.
        Returns 0 for non-bridge packets.
        """
        if not (self.config_flags & CFG_BRIDGE):
            return 0
        return ((self.ext_xhi       << 32) |
                (self.ext_hi        << 23) |
                (self.output_offset << 12) |
                (self.ext_lo        <<  6))

    @property
    def is_extended_address(self) -> bool:
        """True if bridge address is beyond 4GB — requires Shore translation."""
        return bool(self.ext_xhi)

    @classmethod
    def bridge_config(cls, address: int,
                      input_offset: int,
                      ext_output_address: int,
                      config_flags: int = CFG_BRIDGE) -> "Packet":
        """
        Bridge cell configuration packet.

        Packs a 27-bit aligned external output address into the packet fields
        that are unused for bridge cells (gate_state is always 0, NOR gates
        are quiescent). Addresses beyond the 27-bit range should be registered
        with Shore first to get a local proxy address.

        address:            physical address of the bridge cell to configure
        input_offset:       inside the Pond — offset from Pond base (9 bits)
        ext_output_address: external absolute bus address where this bridge
                            sends its output. Must be 64-byte aligned.
                            Bridge cells are allocated at 64-byte boundaries
                            by the array allocator. For non-aligned or >4GB
                            addresses, register with Shore.register_extended()
                            to get a local proxy (which is always aligned).
        config_flags:       CFG_BRIDGE is always set; add CFG_ARM to arm
                            the bridge immediately after configuration
        """
        cfg = config_flags | CFG_BRIDGE
        # Verify 64-byte alignment — bridge cells must be allocated aligned
        if ext_output_address & 0x3F:
            raise ValueError(
                f"Bridge output address 0x{ext_output_address:08X} is not "
                f"64-byte aligned. Bridge cells must be allocated at 64-byte "
                f"boundaries. Use Shore for non-aligned or >4GB addresses."
            )
        addr    = ext_output_address
        ext_xhi = (addr >> 32) & 0x7    # bits 34-32 (0=local, non-zero=>4GB Shore)
        ext_hi  = (addr >> 23) & 0x1FF  # bits 31-23
        mid     = (addr >> 12) & 0x7FF  # bits 22-12
        ext_lo  = (addr >>  6) & 0x03F  # bits 11-6
        arm = bool(cfg & CFG_ARM)
        return cls(address=address, is_config=True, flags=0,
                   gate_state=0,
                   input_offset=input_offset,
                   output_offset=mid,
                   config_flags=cfg,
                   ext_hi=ext_hi, ext_xhi=ext_xhi,
                   ext_lo=ext_lo, bridge_arm=arm)

    @classmethod
    def config(cls, address: int,
               gate_state: int,
               input_offset: int,
               output_offset: int,
               flags: int = 0,
               config_flags: int = 0) -> "Packet":
        """
        Cell configuration packet.

        address:       physical cell address to configure
        gate_state:    9-bit NOR topology
        input_offset:  cell input address as offset from Pond base (9 bits, 0-511)
        output_offset: cell output address as offset from Pond base (11 bits, 0-2047)
        config_flags:  cell modifiers — combine CFG_* constants:
                         CFG_STORAGE_MODE  — make this cell a storage latch
                         CFG_LOOP_MODE     — cell re-arms after firing
                         CFG_ECC_ENABLE    — enable ECC on this cell
                         CFG_ARM           — assert start_flag after config
                       Example: CFG_ARM | CFG_ECC_ENABLE

        The start_flag is a separate hardware control line. CFG_ARM causes
        the receiver to assert it after writing the cell registers — the flag
        itself does not travel on the data bus.
        """
        return cls(address=address, is_config=True, flags=flags,
                   gate_state=gate_state,
                   input_offset=input_offset,
                   output_offset=output_offset,
                   config_flags=config_flags)

    @classmethod
    def announce(cls, shore_address: int,
                 capability: "CapabilityDescriptor",
                 extra_flags: int = 0) -> "Packet":
        """
        Ward announcement packet — registers or updates a Pond with Shore.
        Carries full capability descriptor in the value field.
        """
        return cls(address=shore_address,
                   is_config=False,
                   flags=FLAGS_REGISTER | extra_flags,
                   value=capability.pack())

    @classmethod
    def ready(cls, shore_address: int,
              capability: "CapabilityDescriptor") -> "Packet":
        """Pond is placed and operational."""
        return cls(address=shore_address,
                   is_config=False,
                   flags=FLAGS_ONLINE,
                   value=capability.pack())

    @classmethod
    def moving(cls, shore_address: int,
               capability: "CapabilityDescriptor") -> "Packet":
        """Pond is about to migrate — Shore should hold incoming traffic."""
        return cls(address=shore_address,
                   is_config=False,
                   flags=FLAGS_MIGRATING,
                   value=capability.pack())

    @classmethod
    def route_update(cls, dest_address: int,
                     new_external_address: int) -> "Packet":
        """
        Shore notifies a connected Pond that a route has changed.
        dest_address:        the routing cell to update (BranchPoint storage)
        new_external_address: the new absolute address to route to
        """
        return cls(address=dest_address,
                   is_config=False,
                   flags=FLAG_ROUTE_UPDATE,
                   value=new_external_address)

    @classmethod
    def ack(cls, dest_address: int) -> "Packet":
        """Acknowledgement packet."""
        return cls(address=dest_address,
                   is_config=False,
                   flags=FLAG_ACK,
                   value=0)

    # ── Display ───────────────────────────────────────────────────────────────

    def describe(self) -> str:
        """Human-readable description."""
        flag_names = []
        if self.is_announce:     flag_names.append("ANNOUNCE")
        if self.is_route_update: flag_names.append("ROUTE_UPDATE")
        if self.is_ready:        flag_names.append("READY")
        if self.is_moving:       flag_names.append("MOVING")
        if self.is_capability:   flag_names.append("CAPABILITY")
        if self.is_ack:          flag_names.append("ACK")
        if self.is_priority:     flag_names.append("PRIORITY")
        flags_str = "|".join(flag_names) if flag_names else "none"

        if self.is_config:
            cfg_parts = []
            if self.config_flags & CFG_STORAGE_MODE: cfg_parts.append("STORAGE")
            if self.config_flags & CFG_LOOP_MODE:    cfg_parts.append("LOOP")
            if self.config_flags & CFG_ECC_ENABLE:   cfg_parts.append("ECC")
            if self.config_flags & CFG_ARM:          cfg_parts.append("ARM")
            if self.config_flags & CFG_BRIDGE:       cfg_parts.append("BRIDGE")
            cfg_str = "|".join(cfg_parts) if cfg_parts else "none"
            if self.config_flags & CFG_BRIDGE:
                ext  = self.external_address
                xbit = " [EXTENDED→Shore]" if self.is_extended_address else ""
                arm  = " ARM" if self.bridge_arm else ""
                return (f"Packet[BRIDGE_CONFIG] addr=0x{self.address:08X} "
                        f"in_off=0x{self.input_offset:03X} "
                        f"ext=0x{ext:010X}{xbit}{arm}")
            return (f"Packet[CONFIG] addr=0x{self.address:08X} "
                    f"gs=0b{self.gate_state:09b} "
                    f"in_off=0x{self.input_offset:03X} "
                    f"out_off=0x{self.output_offset:03X} "
                    f"cfg={cfg_str}")
        else:
            return (f"Packet[DATA] addr=0x{self.address:08X} "
                    f"flags={flags_str} "
                    f"value=0x{self.value:08X}")

    def __repr__(self) -> str:
        return self.describe()


# ── CapabilityDescriptor ──────────────────────────────────────────────────────

@dataclass
class CapabilityDescriptor:
    """
    32-bit capability descriptor carried in announcement packets.

    Describes a Pond's type, bridge configuration, Ward health state,
    security level, and local Shore registry identifier.
    Packed into the 32-bit value field of a data packet.

    The Ward fills this from its own state and the Pond's configuration.
    Shore reads it to update the address book and capability registry.
    """

    pond_type:      int   # POND_TYPE_* constant
    bridge_count:   int   # number of bridges (0-15)
    inbound_lanes:  int   # INBOUND bridge lane width (0-15)
    outbound_lanes: int   # OUTBOUND bridge lane width (0-15)
    ward_state:     int   # WARD_STATE_* constant
    security_level: int   # SECURITY_* constant
    pond_id:        int   # local Shore registry ID (0-511)

    def pack(self) -> int:
        """Serialise to 32-bit integer."""
        return (
            ((self.pond_type      & CAP_POND_TYPE_MASK)    << CAP_POND_TYPE_SHIFT)  |
            ((self.bridge_count   & CAP_BRIDGE_COUNT_MASK) << CAP_BRIDGE_COUNT_SHIFT) |
            ((self.inbound_lanes  & CAP_LANES_MASK)        << CAP_IN_LANES_SHIFT)   |
            ((self.outbound_lanes & CAP_LANES_MASK)        << CAP_OUT_LANES_SHIFT)  |
            ((self.ward_state     & CAP_WARD_STATE_MASK)   << CAP_WARD_STATE_SHIFT) |
            ((self.security_level & CAP_SECURITY_MASK)     << CAP_SECURITY_SHIFT)   |
            ((self.pond_id        & CAP_POND_ID_MASK)      << CAP_POND_ID_SHIFT)
        )

    @classmethod
    def unpack(cls, value: int) -> "CapabilityDescriptor":
        """Deserialise from 32-bit integer."""
        return cls(
            pond_type      = (value >> CAP_POND_TYPE_SHIFT)    & CAP_POND_TYPE_MASK,
            bridge_count   = (value >> CAP_BRIDGE_COUNT_SHIFT) & CAP_BRIDGE_COUNT_MASK,
            inbound_lanes  = (value >> CAP_IN_LANES_SHIFT)     & CAP_LANES_MASK,
            outbound_lanes = (value >> CAP_OUT_LANES_SHIFT)    & CAP_LANES_MASK,
            ward_state     = (value >> CAP_WARD_STATE_SHIFT)   & CAP_WARD_STATE_MASK,
            security_level = (value >> CAP_SECURITY_SHIFT)     & CAP_SECURITY_MASK,
            pond_id        = (value >> CAP_POND_ID_SHIFT)      & CAP_POND_ID_MASK,
        )

    @classmethod
    def from_pond(cls, pond, pond_id: int = 0) -> "CapabilityDescriptor":
        """
        Build a capability descriptor from a live Pond object.
        The Ward calls this when composing an announcement packet.
        """
        from pond import (PROCESS, FILE, PERIPHERAL, LIBRARY, BOOT, COMPANION,
                          OPEN, PRIVATE, HIDDEN)

        type_map = {
            PROCESS:    POND_TYPE_PROCESS,
            FILE:       POND_TYPE_FILE,
            PERIPHERAL: POND_TYPE_PERIPHERAL,
            LIBRARY:    POND_TYPE_LIBRARY,
            BOOT:       POND_TYPE_BOOT,
            COMPANION:  POND_TYPE_COMPANION,
        }
        sec_map  = {OPEN: SECURITY_OPEN, PRIVATE: SECURITY_PRIVATE,
                    HIDDEN: SECURITY_HIDDEN}

        # Ward state — map string to code
        ward_state_code = WARD_STATE_IDLE
        if pond.ward is not None:
            state_map = {
                "IDLE":     WARD_STATE_IDLE,
                "HEALTHY":  WARD_STATE_HEALTHY,
                "DEGRADED": WARD_STATE_DEGRADED,
                "STALLED":  WARD_STATE_STALLED,
                "SILENT":   WARD_STATE_SILENT,
                "OFFLINE":  WARD_STATE_OFFLINE,
            }
            ward_state_code = state_map.get(pond.ward.state, WARD_STATE_IDLE)

        # Bridge lanes
        inbound_lanes  = 0
        outbound_lanes = 0
        for b in pond.bridges:
            if b.role == "INBOUND":
                inbound_lanes = b.lane_width
            elif b.role == "OUTBOUND":
                outbound_lanes = b.lane_width

        return cls(
            pond_type      = type_map.get(pond.pond_type, POND_TYPE_PROCESS),
            bridge_count   = min(len(pond.bridges), 15),
            inbound_lanes  = min(inbound_lanes,  15),
            outbound_lanes = min(outbound_lanes, 15),
            ward_state     = ward_state_code,
            security_level = sec_map.get(pond.security_level, SECURITY_OPEN),
            pond_id        = pond_id & CAP_POND_ID_MASK,
        )

    def describe(self) -> str:
        return (
            f"CapabilityDescriptor("
            f"type={POND_TYPE_NAMES.get(self.pond_type, '?')} "
            f"bridges={self.bridge_count} "
            f"in={self.inbound_lanes} out={self.outbound_lanes} "
            f"ward={WARD_STATE_NAMES.get(self.ward_state, '?')} "
            f"security={SECURITY_NAMES.get(self.security_level, '?')} "
            f"id={self.pond_id})"
        )

    def __repr__(self) -> str:
        return self.describe()


# ── Convenience: decode a raw packet value field as capability ────────────────

def decode_capability(value: int) -> CapabilityDescriptor:
    """Decode the value field of a CAPABILITY-flagged packet."""
    return CapabilityDescriptor.unpack(value)
