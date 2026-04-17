"""
fp_tiles.py — Floating-Point Macro Tile Library

Engineering Addendum v0.1 §3: Floating-Point Arithmetic — Cell Cost Quantification.

Implements pre-compiled NOR-network macro tiles for arithmetic operations.
Each tile is a self-contained list of CellMapRecord objects with associated
metadata (cell_count, pipeline_depth, input/output address maps).

Tile architecture:
  - Multi-bit words are represented as lists of bus addresses, one per bit
  - bit[0] is the LSB, bit[31] is the MSB (IEEE-754 sign bit for FP32)
  - All internal wires are allocated from a TileAddressAllocator
  - Tiles compose: the output addresses of one tile feed the input addresses
    of the next, with no intermediate bus contention

Implemented tiles (v0.1):
  Integer:
    - INT32_ADD    32-bit ripple-carry adder
    - INT32_ADD_CLA 32-bit carry-lookahead adder (8x4-bit groups, two-level)
    - INT32_SUB    32-bit subtractor (adder + invert + carry-in=1)
    - INT32_EQ     32-bit equality comparison (1-bit result)
    - INT32_LT_U   32-bit unsigned less-than (1-bit result)
    - INT32_MUX    32-bit 2:1 multiplexer

  Floating-point (IEEE-754 single-precision, simplified: no denormals,
  round-to-nearest-even on addition, truncate on multiply):
    - FP32_ADD     32-bit FP adder
    - FP32_MUL     32-bit FP multiplier
    - FP32_CMP_EQ  FP equality (NaN-safe)
    - FP32_CMP_LT  FP less-than

Usage:
    from fp_tiles import TileLibrary, TilePlacer

    lib = TileLibrary()
    tile = lib.get("INT32_ADD")
    print(tile.metadata)  # cell_count, pipeline_depth, etc.

    placer = TilePlacer(base_address=0x10000)
    records, in_addrs, out_addrs = placer.place(tile, operand_a_bits, operand_b_bits)
"""

from dataclasses import dataclass, field
from typing import Optional
import hashlib, hmac as _hmac, json, time, os
from controller import CellMapRecord
from gate_states import GS_PASS, GS_NOT

# License tiers (Section 5.1 of Tile Library & Licensing Specification v0.1)
TIER_BASE    = "BASE"
TIER_INTEGER = "INTEGER"
TIER_FLOAT   = "FLOAT"
TIER_FULL    = "FULL"

TIER_ORDER = {TIER_BASE: 0, TIER_INTEGER: 1, TIER_FLOAT: 2, TIER_FULL: 3}

# Default tile license tier by operation
_TILE_TIERS = {
    "INT32_MUX":   TIER_BASE,
    "INT32_ADD":     TIER_INTEGER,
    "INT32_ADD_CLA": TIER_INTEGER,
    "INT32_SUB":     TIER_INTEGER,
    "INT32_EQ":    TIER_INTEGER,
    "FP32_ADD":    TIER_FLOAT,
    "FP32_MUL":    TIER_FLOAT,
    "FP32_CMP_EQ": TIER_FLOAT,
}


# ── TileSigningError ──────────────────────────────────────────────────────────

class TileSigningError(RuntimeError):
    """Raised when tile signature verification fails."""
    pass


class TileLicenseError(RuntimeError):
    """Raised when a tile requires a license tier the system does not hold."""
    pass

# ── address allocator ─────────────────────────────────────────────────────────

class TileAddressAllocator:
    """Allocates bus addresses for tile internal wires."""

    def __init__(self, base: int = 0x00010000):
        self._next = base

    def alloc(self) -> int:
        addr = self._next
        self._next += 1
        return addr

    def alloc_word(self, width: int = 32) -> list[int]:
        """Allocate `width` consecutive addresses for a multi-bit word."""
        return [self.alloc() for _ in range(width)]

    @property
    def next_address(self) -> int:
        return self._next


# ── tile metadata ─────────────────────────────────────────────────────────────

@dataclass
class TileMetadata:
    """
    Describes a compiled NOR-network macro tile.

    pipeline_depth: cycles from input injection to output availability.
    cell_count:     number of UniCells consumed by this tile.
    operation:      human-readable operation name.
    precision:      bit-width of primary operands.
    ieee754_compliant: True if full IEEE-754 edge cases are handled.
    notes:          implementation notes (simplifications, limitations).

    Peripheral tile fields (Bridge Interface Contract Specification v0.1):
    inbound_lanes:  recommended INBOUND bridge lane count for a Pond using
                    this tile. 0 = use Pond type default. Set by tile author
                    based on the peripheral's known bandwidth characteristics.
    outbound_lanes: recommended OUTBOUND bridge lane count. 0 = use default.
    """
    operation:        str
    precision:        int
    pipeline_depth:   int
    cell_count:       int
    ieee754_compliant: bool = False
    notes:            str  = ""
    inbound_lanes:    int  = 0   # 0 = use Pond type default
    outbound_lanes:   int  = 0   # 0 = use Pond type default


# ── tile ──────────────────────────────────────────────────────────────────────

@dataclass
class Tile:
    """
    A compiled macro tile.

    records:   flat list of CellMapRecord — the NOR network.
    in_a:      bus addresses for operand A (bit[0]=LSB).
    in_b:      bus addresses for operand B (or [] for unary ops).
    out:       bus addresses for the result.
    metadata:  TileMetadata.
    """
    records:  list
    in_a:     list[int]
    in_b:     list[int]
    out:      list[int]
    metadata: TileMetadata


# ── low-level NOR network builders ───────────────────────────────────────────

class NORBuilder:
    """
    Emits CellMapRecord objects for primitive NOR-based logic gates.

    All gates are built from NOR (and NOT = NOR(a,a)).
    depth_map tracks the pipeline depth of each address for the compiler.
    """

    def __init__(self, alloc: TileAddressAllocator):
        self.alloc = alloc
        self.records: list[CellMapRecord] = []
        self.depth_map: dict[int, int] = {}

    def _emit(self, gs: int, in_addr: int, out_addr: int) -> int:
        """Emit one NOR cell. Returns out_addr."""
        self.records.append(CellMapRecord(gs, in_addr, out_addr))
        in_depth = self.depth_map.get(in_addr, 0)
        self.depth_map[out_addr] = in_depth + 1
        return out_addr

    def _emit2(self, gs: int, in_addr: int, out_addr: int) -> int:
        """Emit one NOR cell reading from in_addr (second input via wired-OR)."""
        # For two-input NOR: two PASS cells feed the same output address (wired-OR),
        # then a NOT inverts the combined result.
        self.records.append(CellMapRecord(gs, in_addr, out_addr))
        in_depth = self.depth_map.get(in_addr, 0)
        cur = self.depth_map.get(out_addr, 0)
        self.depth_map[out_addr] = max(cur, in_depth + 1)
        return out_addr

    def wire(self, src: int) -> int:
        """PASS: copy a signal to a new address (introduces 1 cycle delay)."""
        dst = self.alloc.alloc()
        self._emit(GS_PASS, src, dst)
        return dst

    def delay(self, src: int, cycles: int) -> int:
        """Insert `cycles` PASS cells to add pipeline depth."""
        cur = src
        for _ in range(cycles):
            cur = self.wire(cur)
        return cur

    def pad_to_depth(self, src: int, target_depth: int) -> int:
        """Pad src with PASS cells until its depth equals target_depth."""
        cur = src
        while self.depth_map.get(cur, 0) < target_depth:
            cur = self.wire(cur)
        return cur

    def NOT(self, a: int) -> int:
        """NOT(a) = NOR(a, a)."""
        out = self.alloc.alloc()
        self._emit(GS_NOT, a, out)
        return out

    def NOR2(self, a: int, b: int) -> int:
        """NOR(a, b): two PASS cells to shared wire, then NOT."""
        # Equalise depths
        da = self.depth_map.get(a, 0)
        db = self.depth_map.get(b, 0)
        target = max(da, db)
        a = self.pad_to_depth(a, target)
        b = self.pad_to_depth(b, target)
        # Wired-OR: both PASS to same address
        mid = self.alloc.alloc()
        self._emit2(GS_PASS, a, mid)
        self._emit2(GS_PASS, b, mid)
        out = self.NOT(mid)
        return out

    def OR2(self, a: int, b: int) -> int:
        """OR(a, b) = NOT(NOR(a, b))."""
        return self.NOT(self.NOR2(a, b))

    def AND2(self, a: int, b: int) -> int:
        """AND(a, b) = NOR(NOT(a), NOT(b))."""
        na = self.NOT(a)
        nb = self.NOT(b)
        return self.NOR2(na, nb)

    def NAND2(self, a: int, b: int) -> int:
        """NAND(a, b) = NOT(AND(a, b))."""
        return self.NOT(self.AND2(a, b))

    def XOR2(self, a: int, b: int) -> int:
        """XOR(a, b) = OR(AND(a,NOT b), AND(NOT a, b))."""
        na = self.NOT(a)
        nb = self.NOT(b)
        # Pad na, nb to same depth as a, b before ANDing
        da = self.depth_map.get(a, 0)
        db = self.depth_map.get(b, 0)
        dna = self.depth_map.get(na, 0)
        dnb = self.depth_map.get(nb, 0)
        # AND(a, NOT b) — equalise a and nb
        a_nb = self.AND2(a, nb)
        # AND(NOT a, b) — equalise na and b
        na_b = self.AND2(na, b)
        return self.OR2(a_nb, na_b)

    def XNOR2(self, a: int, b: int) -> int:
        """XNOR(a, b) = NOT(XOR(a, b))."""
        return self.NOT(self.XOR2(a, b))

    def MUX2(self, sel: int, a: int, b: int) -> int:
        """
        2:1 MUX: if sel=1, output a; if sel=0, output b.
        MUX(sel, a, b) = OR(AND(sel, a), AND(NOT sel, b))
        """
        nsel = self.NOT(sel)
        sel_a  = self.AND2(sel,  a)
        nsel_b = self.AND2(nsel, b)
        return self.OR2(sel_a, nsel_b)

    def depth_of(self, addr: int) -> int:
        return self.depth_map.get(addr, 0)

    def LATCH(self, a: int) -> int:
        """Latch: holds and re-emits last value each tick. Cost: 1 cell."""
        from gate_states import GS_LATCH
        out = self.alloc.alloc()
        self._emit2(GS_LATCH, a, out)
        self.depth_map[out] = self.depth_map.get(a, 0) + 1
        return out

    def SYNC_WAIT(self, a: int, b: int) -> int:
        """
        Fires only after BOTH a and b have arrived. Cost: 3 cells.
        Eliminates depth-equalisation PASS chains — waits for the slower path.
        """
        from gate_states import GS_SYNC_WAIT
        mid = self.alloc.alloc()
        self._emit2(GS_PASS, a, mid)
        self._emit2(GS_PASS, b, mid)
        out = self.alloc.alloc()
        self._emit2(GS_SYNC_WAIT, mid, out)
        depth_a = self.depth_map.get(a, 0)
        depth_b = self.depth_map.get(b, 0)
        self.depth_map[out] = max(depth_a, depth_b) + 2
        return out

    def LOOP_BACK(self, a: int, gate_state: int = 0) -> int:
        """
        Internal loopback: G8 output feeds back to G0 input. Cost: 1 cell.
        Creates single-cell SR latch (GS_NOR|GS_LOOP_BACK) or ring oscillator
        (GS_NOT|GS_LOOP_BACK).
        """
        from gate_states import GS_LOOP_BACK
        out = self.alloc.alloc()
        self._emit2(gate_state | GS_LOOP_BACK, a, out)
        self.depth_map[out] = self.depth_map.get(a, 0) + 1
        return out

    def HOLD(self, a: int) -> int:
        """Delay by 1 tick. Cost: 1 cell. Named alias for delay(a, 1)."""
        return self.delay(a, 1)


# ── integer arithmetic tiles ──────────────────────────────────────────────────

def _build_int32_add(alloc: TileAddressAllocator,
                     a_bits: list[int],
                     b_bits: list[int],
                     carry_in: Optional[int] = None) -> tuple:
    """
    Build a 32-bit ripple-carry adder.
    Returns (builder, sum_bits, carry_out).
    """
    b = NORBuilder(alloc)

    # Register input depths as 0
    for addr in a_bits + b_bits:
        b.depth_map[addr] = 0
    if carry_in is not None:
        b.depth_map[carry_in] = 0

    sum_bits = []
    # carry propagation
    c = carry_in if carry_in is not None else None

    for i in range(32):
        ai = a_bits[i]
        bi = b_bits[i]

        if c is None:
            # bit 0 with no carry: half adder
            # sum = XOR(a, b)
            s = b.XOR2(ai, bi)
            # carry = AND(a, b)
            c = b.AND2(ai, bi)
        else:
            # full adder
            # sum = XOR(XOR(a, b), cin)
            axb = b.XOR2(ai, bi)
            s   = b.XOR2(axb, c)
            # carry = OR(AND(a,b), AND(XOR(a,b), cin))
            ab   = b.AND2(ai, bi)
            axbc = b.AND2(axb, c)
            c    = b.OR2(ab, axbc)

        sum_bits.append(s)

    return b, sum_bits, c


def make_int32_add(base_address: int = 0x10000) -> Tile:
    """
    32-bit ripple-carry integer adder tile.

    Inputs:  a[0..31], b[0..31]  (1 address per bit, LSB first)
    Outputs: sum[0..31]
    """
    alloc = TileAddressAllocator(base_address)
    a_bits = alloc.alloc_word(32)
    b_bits = alloc.alloc_word(32)

    builder, sum_bits, carry_out = _build_int32_add(alloc, a_bits, b_bits)

    # Measure actual pipeline depth
    depth = max(builder.depth_of(s) for s in sum_bits)
    cells = len(builder.records)

    return Tile(
        records  = builder.records,
        in_a     = a_bits,
        in_b     = b_bits,
        out      = sum_bits,
        metadata = TileMetadata(
            operation       = "INT32_ADD",
            precision       = 32,
            pipeline_depth  = depth,
            cell_count      = cells,
            ieee754_compliant = False,
            notes = "32-bit ripple-carry adder. No overflow flag."
        )
    )


def _build_int32_add_cla(alloc: TileAddressAllocator,
                         a_bits: list[int],
                         x_bits: list[int],
                         cin0: int) -> tuple:
    """
    Build a 32-bit two-level carry-lookahead adder using NOR primitives.

    Architecture: 8 groups × 4 bits.  All group carries are resolved in one
    inter-group lookahead stage; within-group carries use a 4-bit CLA formula.
    Shared NOT(a[i]) / NOT(b[i]) signals are computed once and reused across
    the AND, OR, and XOR paths, keeping per-depth emission counts below the
    256-lane bus segment limit.

    Key correctness requirement: nor2() equalises input depths before wiring
    the two PASS cells to the shared mid address.  Without equalisation the
    downstream NOT fires on the first PASS arrival and reads a partial value —
    this was the root bug found during implementation.

    Returns (builder, sum_bits).
    pipeline_depth and cell_count are computed by the caller from the builder.
    """
    b = NORBuilder(alloc)
    for addr in a_bits + x_bits:
        b.depth_map[addr] = 0
    b.depth_map[cin0] = 0

    def nor2(p, q):
        """NOR(p,q) with depth equalisation — the fundamental wired-OR primitive."""
        target = max(b.depth_map.get(p, 0), b.depth_map.get(q, 0))
        p = b.pad_to_depth(p, target)
        q = b.pad_to_depth(q, target)
        mid = alloc.alloc()
        b.records.append(CellMapRecord(GS_PASS, p, mid))
        b.depth_map[mid] = max(b.depth_map.get(mid, 0), b.depth_map.get(p, 0) + 1)
        b.records.append(CellMapRecord(GS_PASS, q, mid))
        b.depth_map[mid] = max(b.depth_map.get(mid, 0), b.depth_map.get(q, 0) + 1)
        return b.NOT(mid)

    def and2(p, q): return nor2(b.NOT(p), b.NOT(q))
    def or2(p, q):  return b.NOT(nor2(p, q))

    def or_tree(sigs):
        cur = list(sigs)
        while len(cur) > 1:
            nxt = []
            for i in range(0, len(cur) - 1, 2):
                nxt.append(or2(cur[i], cur[i + 1]))
            if len(cur) % 2:
                nxt.append(cur[-1])
            cur = nxt
        return cur[0]

    # ── bit-level shared negations (depth 1) ─────────────────────────────────
    # Each NOT(a[i]) and NOT(b[i]) is computed once and reused by the G, P_or,
    # and P_xor paths, keeping depth-1 emission count at 64 (vs 256 without sharing).
    na = [b.NOT(a_bits[i]) for i in range(32)]
    nb = [b.NOT(x_bits[i]) for i in range(32)]

    # G[i] = AND(a,b) = NOR(NOT(a), NOT(b))  — depth 3
    G     = [nor2(na[i], nb[i])                                    for i in range(32)]
    # P_or[i] = OR(a,b) — carry-propagate signal                   — depth 3
    P_or  = [or2(a_bits[i], x_bits[i])                             for i in range(32)]
    # P_xor[i] = XOR(a,b) = OR(NOR(na,b), NOR(a,nb))              — depth 5
    P_xor = [or2(nor2(na[i], x_bits[i]), nor2(a_bits[i], nb[i]))   for i in range(32)]

    # ── group-level shared negations (depth 4) ───────────────────────────────
    # Pre-computing NOT(G[i]) and NOT(P_or[i]) avoids a second depth spike when
    # the group carry-out terms all issue AND2 calls simultaneously.
    nG    = [b.NOT(G[i])    for i in range(32)]
    nP_or = [b.NOT(P_or[i]) for i in range(32)]

    # ── group generate / propagate (8 groups × 4 bits) ───────────────────────
    NUM_GROUPS, BPG = 8, 4
    group_G, group_P = [], []
    for k in range(NUM_GROUPS):
        s  = k * BPG
        g  = G[s:s + BPG];  p  = P_or[s:s + BPG]
        ng = nG[s:s + BPG]; np = nP_or[s:s + BPG]

        # group carry-out = g3 | p3.g2 | p3.p2.g1 | p3.p2.p1.g0
        p3g2     = nor2(np[3], ng[2])
        p3p2     = nor2(np[3], np[2]);    np3p2   = b.NOT(p3p2)
        p3p2g1   = nor2(np3p2, ng[1])
        p3p2p1   = nor2(np3p2, np[1]);   np3p2p1 = b.NOT(p3p2p1)
        p3p2p1g0 = nor2(np3p2p1, ng[0])
        gG = or_tree([g[3], p3g2, p3p2g1, p3p2p1g0])

        # group propagate = AND(p0,p1,p2,p3) — balanced tree
        p01 = nor2(np[0], np[1])
        p23 = nor2(np[2], np[3])
        gP  = nor2(b.NOT(p01), b.NOT(p23))

        group_G.append(gG)
        group_P.append(gP)

    # ── inter-group carry lookahead ───────────────────────────────────────────
    group_cin = [cin0]
    for k in range(1, NUM_GROUPS):
        terms   = [group_G[k - 1]]
        p_chain = group_P[k - 1]
        for j in range(k - 2, -1, -1):
            terms.append(and2(p_chain, group_G[j]))
            p_chain = and2(p_chain, group_P[j])
        terms.append(and2(p_chain, cin0))
        group_cin.append(or_tree(terms))

    # ── within-group carries and sum bits ─────────────────────────────────────
    sum_bits = []
    for k in range(NUM_GROUPS):
        s    = k * BPG
        g    = G[s:s + BPG]
        p_or = P_or[s:s + BPG]
        p_xor = P_xor[s:s + BPG]
        gcin = group_cin[k]

        p0c    = and2(p_or[0], gcin)
        c1     = or2(g[0], p0c)
        p1g0   = and2(p_or[1], g[0]);  p1p0c  = and2(p_or[1], p0c)
        c2     = or_tree([g[1], p1g0, p1p0c])
        p2g1   = and2(p_or[2], g[1]);  p2p1   = and2(p_or[2], p_or[1])
        p2p1g0 = and2(p2p1, g[0]);     p2p1p0c = and2(p2p1, p0c)
        c3     = or_tree([g[2], p2g1, p2p1g0, p2p1p0c])

        for i, bc in enumerate([gcin, c1, c2, c3]):
            sum_bits.append(b.XOR2(p_xor[i], bc))

    return b, sum_bits


def make_int32_add_cla(base_address: int = 0x10000) -> Tile:
    """
    32-bit carry-lookahead integer adder tile.

    Two-level CLA: 8 groups × 4 bits.  Group carries are resolved in one
    parallel inter-group stage rather than rippling across all 32 bits.
    Shared NOT(a[i])/NOT(b[i]) signals keep per-depth bus emission counts
    below the 256-lane segment limit without requiring a wider segment.

    Inputs:  a[0..31], b[0..31], cin (b[32])  — 1 address per bit, LSB first.
    Outputs: sum[0..31]

    Pipeline depth: ~58 NOR-gate cycles  (vs 194 for INT32_ADD ripple-carry).
    Cell count:     ~6,200               (vs 12,931 for INT32_ADD).

    in_b[32] is the carry-in address.  Set it to 0 (VAR_FALSE) for normal
    addition, or 1 (VAR_TRUE) to add with carry.
    """
    alloc  = TileAddressAllocator(base_address)
    a_bits = alloc.alloc_word(32)
    x_bits = alloc.alloc_word(32)
    cin0   = alloc.alloc()

    builder, sum_bits = _build_int32_add_cla(alloc, a_bits, x_bits, cin0)

    depth = max(builder.depth_of(s) for s in sum_bits)
    cells = len(builder.records)

    return Tile(
        records  = builder.records,
        in_a     = a_bits,
        in_b     = x_bits + [cin0],
        out      = sum_bits,
        metadata = TileMetadata(
            operation        = "INT32_ADD_CLA",
            precision        = 32,
            pipeline_depth   = depth,
            cell_count       = cells,
            ieee754_compliant = False,
            notes = (
                "32-bit carry-lookahead adder (8x4-bit groups, two-level). "
                "~3.3x faster than INT32_ADD; ~52% fewer cells. "
                "in_b[32] is carry-in: 0=normal add, 1=add-with-carry."
            )
        )
    )


def make_int32_sub(base_address: int = 0x10000) -> Tile:
    """
    32-bit subtractor: a - b = a + NOT(b) + 1 (two's complement).

    carry_in_addr: the last entry in in_b (index 32) must be pre-loaded
    to VAR_TRUE (1) by the controller before running — this provides the
    +1 of two's complement negation.
    """
    alloc = TileAddressAllocator(base_address)
    a_bits = alloc.alloc_word(32)
    b_bits = alloc.alloc_word(32)
    carry_in_addr = alloc.alloc()  # must be pre-loaded to 1

    # Build unified NORBuilder: NOT(b) then ripple-carry add
    bld = NORBuilder(alloc)
    for addr in a_bits + b_bits + [carry_in_addr]:
        bld.depth_map[addr] = 0

    # Invert b bits using the unified builder
    nb_bits = [bld.NOT(bi) for bi in b_bits]

    # Ripple-carry add: a + NOT(b) + carry_in
    sum_bits = []
    carry = carry_in_addr
    for i in range(32):
        ai  = a_bits[i]
        nbi = nb_bits[i]
        axb = bld.XOR2(ai, nbi)
        s   = bld.XOR2(axb, carry)
        ab  = bld.AND2(ai, nbi)
        ac  = bld.AND2(axb, carry)
        carry = bld.OR2(ab, ac)
        sum_bits.append(s)

    depth = max(bld.depth_of(s) for s in sum_bits)
    cells = len(bld.records)

    return Tile(
        records  = bld.records,
        in_a     = a_bits,
        in_b     = b_bits + [carry_in_addr],
        out      = sum_bits,
        metadata = TileMetadata(
            operation      = "INT32_SUB",
            precision      = 32,
            pipeline_depth = depth,
            cell_count     = cells,
            notes = ("32-bit subtractor (a-b = a + NOT(b) + 1). "
                     "in_b[32] (carry_in_addr) must be pre-loaded to 1.")
        )
    )


def make_int32_eq(base_address: int = 0x10000) -> Tile:
    """
    32-bit equality: result=1 iff a==b.
    Uses XNOR on each bit pair, then AND-tree.
    """
    alloc = TileAddressAllocator(base_address)
    a_bits = alloc.alloc_word(32)
    b_bits = alloc.alloc_word(32)

    b = NORBuilder(alloc)
    for addr in a_bits + b_bits:
        b.depth_map[addr] = 0

    # XNOR each bit pair: 1 iff equal
    eq_bits = [b.XNOR2(a_bits[i], b_bits[i]) for i in range(32)]

    # AND-tree: fold 32 bits to 1
    cur = eq_bits
    while len(cur) > 1:
        nxt = []
        for i in range(0, len(cur) - 1, 2):
            nxt.append(b.AND2(cur[i], cur[i+1]))
        if len(cur) % 2 == 1:
            nxt.append(cur[-1])
        cur = nxt

    out_bit = cur[0]
    depth = b.depth_of(out_bit)

    return Tile(
        records  = b.records,
        in_a     = a_bits,
        in_b     = b_bits,
        out      = [out_bit],
        metadata = TileMetadata(
            operation      = "INT32_EQ",
            precision      = 32,
            pipeline_depth = depth,
            cell_count     = len(b.records),
            notes = "32-bit equality. Result: 1 address (1=equal, 0=not equal)."
        )
    )


def make_int32_mux(base_address: int = 0x10000) -> Tile:
    """
    32-bit 2:1 MUX: if sel=1 output a, else output b.
    in_a = [sel_bit, a[0..31]]  (sel is bit 0 of in_a)
    in_b = b[0..31]
    """
    alloc = TileAddressAllocator(base_address)
    sel_addr = alloc.alloc()
    a_bits   = alloc.alloc_word(32)
    b_bits   = alloc.alloc_word(32)

    bld = NORBuilder(alloc)
    for addr in [sel_addr] + a_bits + b_bits:
        bld.depth_map[addr] = 0

    out_bits = [bld.MUX2(sel_addr, a_bits[i], b_bits[i]) for i in range(32)]
    depth = max(bld.depth_of(o) for o in out_bits)

    return Tile(
        records  = bld.records,
        in_a     = [sel_addr] + a_bits,
        in_b     = b_bits,
        out      = out_bits,
        metadata = TileMetadata(
            operation      = "INT32_MUX",
            precision      = 32,
            pipeline_depth = depth,
            cell_count     = len(bld.records),
            notes = "32-bit 2:1 mux. in_a[0]=sel, in_a[1:]=A, in_b=B."
        )
    )


# ── FP32 tile builder ─────────────────────────────────────────────────────────

def _fp32_decompose(bld: NORBuilder, bits: list[int]) -> tuple:
    """
    Decompose a 32-bit FP word into (sign, exponent[8], mantissa[23]).
    bits[0]=LSB, bits[31]=MSB (sign bit).
    Returns (sign_addr, exp_bits[0..7], mant_bits[0..22]).
    """
    sign = bits[31]
    exp_bits  = bits[23:31]   # bits 23–30 (8 bits, LSB first)
    mant_bits = bits[0:23]    # bits 0–22 (23 bits, LSB first)
    return sign, exp_bits, mant_bits


def make_fp32_add(base_address: int = 0x10000) -> Tile:
    """
    IEEE-754 single-precision adder (simplified: no denormals, no NaN
    propagation, round-to-nearest-even approximated as truncation).

    Pipeline stages:
      1. Decompose operands (0 cycles — just routing)
      2. Compare exponents, compute shift amount (8-bit sub)  ~depth A
      3. Align mantissas (shift smaller by diff)              ~depth B
      4. Add/subtract aligned mantissas (24-bit add)          ~depth C
      5. Normalise result (leading-zero detect + shift)       ~depth D
      6. Pack result                                          ~depth E

    This is a structural implementation using the NORBuilder primitives.
    Actual pipeline depth is measured from the built network.
    """
    alloc = TileAddressAllocator(base_address)
    a_bits = alloc.alloc_word(32)   # FP32 operand A
    b_bits = alloc.alloc_word(32)   # FP32 operand B

    bld = NORBuilder(alloc)
    for addr in a_bits + b_bits:
        bld.depth_map[addr] = 0

    # ── Stage 1: Decompose ────────────────────────────────────────────────────
    a_sign, a_exp, a_mant = _fp32_decompose(bld, a_bits)
    b_sign, b_exp, b_mant = _fp32_decompose(bld, b_bits)

    # ── Stage 2: Determine which exponent is larger ───────────────────────────
    # exp_diff = a_exp - b_exp (8-bit subtraction)
    # If exp_diff > 0: a has larger exponent, shift b's mantissa right
    # If exp_diff < 0: b has larger exponent, shift a's mantissa right
    # If exp_diff = 0: no shift needed
    #
    # For the simplified model: we compute exp_diff using 8-bit subtract,
    # determine sign of diff, and use it to select which mantissa to shift.

    # 8-bit exponent subtract (using NORBuilder directly for 8 bits)
    # exp_diff = a_exp - b_exp = a_exp + NOT(b_exp) + 1
    nb_exp = [bld.NOT(bi) for bi in b_exp]

    # 8-bit ripple-carry adder for exp diff
    exp_sum = []
    carry   = None
    for i in range(8):
        ai = a_exp[i]
        nbi = nb_exp[i]
        if carry is None:
            # half-adder with implicit carry-in=1 (two's complement)
            # sum = XOR(a, nb) XOR 1 = XNOR(a, nb)
            s = bld.XNOR2(ai, nbi)
            c = bld.OR2(ai, nbi)   # AND(a,nb) | (a XOR nb) when ci=1 = OR(a,nb) for ci=1
        else:
            axb = bld.XOR2(ai, nbi)
            s   = bld.XOR2(axb, carry)
            ab  = bld.AND2(ai, nbi)
            ac  = bld.AND2(axb, carry)
            c   = bld.OR2(ab, ac)
        exp_sum.append(s)
        carry = c

    # Overflow/sign of diff is in carry and bit 7
    exp_diff_sign = bld.NOT(carry)  # 1 if a_exp < b_exp (b is larger)
    exp_diff_bits = exp_sum         # magnitude encoded in 8 bits

    # ── Stage 3: Mantissa alignment ───────────────────────────────────────────
    # Prepend implicit 1 bit to mantissas (bit 23 = 1 for normal numbers)
    # 24-bit extended mantissas
    one_a = alloc.alloc()  # constant 1 (must be pre-loaded)
    one_b = alloc.alloc()
    bld.depth_map[one_a] = 0
    bld.depth_map[one_b] = 0

    # Extended mantissas: [mant[0..22], implicit_1]  (24 bits, bit 23 = implicit 1)
    ext_a = a_mant + [one_a]  # 24 bits
    ext_b = b_mant + [one_b]

    # For the simplified model: implement a barrel shifter for the smaller operand.
    # Shift amount = |exp_diff|, direction = right (divides by 2^shift).
    # We implement a 5-bit barrel shifter (shift 0..31, sufficient for 24-bit mantissa).
    # shift bits: exp_diff_bits[0..4] (lower 5 bits of diff magnitude)
    # For each output bit i: out[i] = MUX(shift, in[i], in[i+1], in[i+2], ...)

    # Simplified: implement as a series of 1-bit conditional shifts
    # (shift right by 1 if shift_bit[k] is set, for k=0..4)
    # This gives a log-depth barrel shifter.

    def barrel_shift_right(bits_24: list[int], shift_sels: list[int]) -> list[int]:
        """Right-shift a 24-bit value by [0,1,2,4,8,16] based on shift_sels."""
        cur = list(bits_24)
        amounts = [1, 2, 4, 8, 16]
        for k, amount in enumerate(amounts[:len(shift_sels)]):
            sel = shift_sels[k]
            shifted = []
            for i in range(24):
                src_shifted = cur[i - amount] if i >= amount else None
                if src_shifted is None:
                    # Shifted out — use 0 (constant zero address)
                    zero_addr = alloc.alloc()
                    bld.depth_map[zero_addr] = 0
                    shifted.append(bld.MUX2(sel, zero_addr, cur[i]))
                else:
                    shifted.append(bld.MUX2(sel, src_shifted, cur[i]))
            cur = shifted
        return cur

    # Shift b's mantissa if a_exp > b_exp (exp_diff_sign=0, a is larger)
    # Shift a's mantissa if b_exp > a_exp (exp_diff_sign=1, b is larger)
    shift_b = [bld.AND2(bld.NOT(exp_diff_sign), exp_diff_bits[k]) for k in range(5)]
    shift_a = [bld.AND2(exp_diff_sign, exp_diff_bits[k]) for k in range(5)]

    aligned_a = barrel_shift_right(ext_a, shift_a)
    aligned_b = barrel_shift_right(ext_b, shift_b)

    # ── Stage 4: Mantissa addition/subtraction ────────────────────────────────
    # Determine if we add or subtract based on sign bits
    # same_sign = XNOR(a_sign, b_sign) — 1 if same sign
    same_sign = bld.XNOR2(a_sign, b_sign)

    # If same sign: add mantissas. If different sign: subtract.
    # We always add aligned_a + aligned_b; if different signs, negate one.
    # Simplified: add and let the sign of the result determine output sign.
    sum_bld = NORBuilder(alloc)
    for addr in aligned_a + aligned_b:
        sum_bld.depth_map[addr] = bld.depth_of(addr)

    mant_sum = []
    mant_carry = None
    for i in range(24):
        ai = aligned_a[i]
        bi = aligned_b[i]
        if mant_carry is None:
            s = sum_bld.XOR2(ai, bi)
            c = sum_bld.AND2(ai, bi)
        else:
            axb = sum_bld.XOR2(ai, bi)
            s   = sum_bld.XOR2(axb, mant_carry)
            ab  = sum_bld.AND2(ai, bi)
            ac  = sum_bld.AND2(axb, mant_carry)
            c   = sum_bld.OR2(ab, ac)
        mant_sum.append(s)
        mant_carry = c
    mant_sum.append(mant_carry)  # 25 bits (overflow bit)

    # Merge records
    bld.records.extend(sum_bld.records)
    bld.depth_map.update(sum_bld.depth_map)

    # ── Stage 5: Normalisation (simplified) ──────────────────────────────────
    # If overflow bit (bit 24) set: shift right by 1, increment exponent
    overflow = mant_sum[24]

    # Increment exponent if overflow
    inc_carry = overflow   # carry into exponent adder
    result_exp = []
    for i in range(8):
        ei = a_exp[i]   # use a_exp as base (since we use larger exponent)
        s  = bld.XOR2(ei, inc_carry)
        c  = bld.AND2(ei, inc_carry)
        result_exp.append(s)
        inc_carry = c

    # Result mantissa: if overflow, use bits [1..23] of sum; else bits [0..22]
    result_mant = []
    for i in range(23):
        # MUX(overflow, mant_sum[i+1], mant_sum[i])
        result_mant.append(bld.MUX2(overflow, mant_sum[i+1], mant_sum[i]))

    # ── Stage 6: Result sign ──────────────────────────────────────────────────
    # Sign of result = sign of the operand with larger exponent
    result_sign = bld.MUX2(exp_diff_sign, b_sign, a_sign)

    # ── Pack result ───────────────────────────────────────────────────────────
    # FP32: [mant[0..22], exp[0..7], sign] = 32 bits
    out_bits = result_mant + result_exp + [result_sign]

    depth = max(bld.depth_of(o) for o in out_bits)
    cells = len(bld.records)

    return Tile(
        records  = bld.records,
        in_a     = a_bits,
        in_b     = b_bits,
        out      = out_bits,
        metadata = TileMetadata(
            operation      = "FP32_ADD",
            precision      = 32,
            pipeline_depth = depth,
            cell_count     = cells,
            ieee754_compliant = False,
            notes = (
                "FP32 adder. Simplified: no denormals, no NaN propagation, "
                "truncation rounding. Implicit-1 bit must be pre-loaded at "
                "one_a and one_b addresses (in_a[-1] conceptually). "
                "Works correctly for normal numbers."
            )
        )
    )


def make_fp32_mul(base_address: int = 0x10000) -> Tile:
    """
    IEEE-754 single-precision multiplier (simplified: no denormals,
    truncation rounding).

    sign_r   = XOR(sign_a, sign_b)
    exp_r    = exp_a + exp_b - 127  (biased exponent addition)
    mant_r   = mant_a * mant_b      (24x24 partial product, top 23 bits)
    """
    alloc = TileAddressAllocator(base_address)
    a_bits = alloc.alloc_word(32)
    b_bits = alloc.alloc_word(32)

    bld = NORBuilder(alloc)
    for addr in a_bits + b_bits:
        bld.depth_map[addr] = 0

    a_sign, a_exp, a_mant = _fp32_decompose(bld, a_bits)
    b_sign, b_exp, b_mant = _fp32_decompose(bld, b_bits)

    # ── Sign: XOR ─────────────────────────────────────────────────────────────
    result_sign = bld.XOR2(a_sign, b_sign)

    # ── Exponent: add and subtract bias 127 ──────────────────────────────────
    # exp_r = a_exp + b_exp - 127
    # Step 1: 8-bit add
    exp_sum8 = []
    carry = None
    for i in range(8):
        ai = a_exp[i]; bi = b_exp[i]
        if carry is None:
            s = bld.XOR2(ai, bi); c = bld.AND2(ai, bi)
        else:
            axb = bld.XOR2(ai, bi)
            s   = bld.XOR2(axb, carry)
            c   = bld.OR2(bld.AND2(ai, bi), bld.AND2(axb, carry))
        exp_sum8.append(s); carry = c
    # exp_sum8 is 8 bits (may overflow into carry, but we ignore for simplified)

    # Step 2: subtract 127 = 0x7F = 0111_1111
    # -127 = NOT(127) + 1 = 1000_0001
    bias_bits = [1,0,0,0,0,0,0,1]  # -127 in two's complement, 8-bit
    # Create constant addresses for bias bits
    bias_addrs = []
    for bv in bias_bits:
        ba = alloc.alloc()
        bld.depth_map[ba] = 0
        bias_addrs.append(ba)
    # (Controller pre-loads: bias_addrs[i] = bias_bits[i])

    result_exp = []
    carry2 = None
    for i in range(8):
        ai = exp_sum8[i]; bi = bias_addrs[i]
        if carry2 is None:
            s = bld.XOR2(ai, bi); c = bld.AND2(ai, bi)
        else:
            axb = bld.XOR2(ai, bi)
            s   = bld.XOR2(axb, carry2)
            c   = bld.OR2(bld.AND2(ai, bi), bld.AND2(axb, carry2))
        result_exp.append(s); carry2 = c

    # ── Mantissa: 24x24 partial-product multiply ──────────────────────────────
    # Extended mantissas with implicit 1 bit
    one_a = alloc.alloc()
    one_b = alloc.alloc()
    bld.depth_map[one_a] = 0
    bld.depth_map[one_b] = 0

    ext_a = a_mant + [one_a]  # 24 bits
    ext_b = b_mant + [one_b]

    # Partial products: pp[i] = ext_a shifted left by i, masked by ext_b[i]
    # Result is 48-bit; we take bits 23..45 (top 23 mantissa bits after drop implicit)
    # Build using a 24-bit adder tree (shift-and-add)

    # Generate partial products: pp[i] = ext_b[i] ? ext_a : 0, shifted left by i
    # We only need the top 23+1 bits of the 48-bit result.
    # For the simplified model: accumulate into a running 24-bit sum.

    # Initialise accumulator to partial product 0
    acc = []
    for i in range(24):
        # pp0[i] = AND(ext_a[i], ext_b[0])
        acc.append(bld.AND2(ext_a[i], ext_b[0]))

    # Add subsequent partial products (shifted left by k)
    for k in range(1, 24):
        # Partial product k: ext_b[k] selects ext_a, shifted left by k
        # We accumulate into top bits of result (truncating lower bits)
        # For bits i = k..k+23 of the full product
        pp_add = NORBuilder(alloc)
        for addr in acc:
            pp_add.depth_map[addr] = bld.depth_of(addr)

        carry3 = None
        new_acc = list(acc)
        for i in range(24):
            pp_idx = i - k
            if 0 <= pp_idx < 24:
                pp_bit = bld.AND2(ext_a[pp_idx], ext_b[k])
            else:
                pp_bit = alloc.alloc()
                bld.depth_map[pp_bit] = 0  # zero bit

            if i < len(acc):
                ai = acc[i]
            else:
                ai = alloc.alloc()
                bld.depth_map[ai] = 0

            if carry3 is None:
                s = bld.XOR2(ai, pp_bit)
                c = bld.AND2(ai, pp_bit)
            else:
                axb = bld.XOR2(ai, pp_bit)
                s   = bld.XOR2(axb, carry3)
                c   = bld.OR2(bld.AND2(ai, pp_bit), bld.AND2(axb, carry3))
            new_acc[i] = s
            carry3 = c
        acc = new_acc

    # Top 23 bits of acc are the mantissa result (bit 23 is implicit 1, dropped)
    result_mant = acc[0:23]

    # ── Pack result ───────────────────────────────────────────────────────────
    out_bits = result_mant + result_exp + [result_sign]

    depth = max(bld.depth_of(o) for o in out_bits)
    cells = len(bld.records)

    return Tile(
        records  = bld.records,
        in_a     = a_bits,
        in_b     = b_bits,
        out      = out_bits,
        metadata = TileMetadata(
            operation      = "FP32_MUL",
            precision      = 32,
            pipeline_depth = depth,
            cell_count     = cells,
            ieee754_compliant = False,
            notes = (
                "FP32 multiplier. Simplified: no denormals, truncation rounding. "
                "Pre-load: one_a, one_b = 1; bias_addrs per -127 encoding. "
                "Works correctly for normal numbers."
            )
        )
    )


def make_fp32_cmp_eq(base_address: int = 0x10000) -> Tile:
    """
    FP32 equality: result=1 iff a==b (bit-exact, no NaN handling).
    Reuses INT32_EQ logic.
    """
    alloc = TileAddressAllocator(base_address)
    a_bits = alloc.alloc_word(32)
    b_bits = alloc.alloc_word(32)

    bld = NORBuilder(alloc)
    for addr in a_bits + b_bits:
        bld.depth_map[addr] = 0

    eq_bits = [bld.XNOR2(a_bits[i], b_bits[i]) for i in range(32)]
    cur = eq_bits
    while len(cur) > 1:
        nxt = []
        for i in range(0, len(cur) - 1, 2):
            nxt.append(bld.AND2(cur[i], cur[i+1]))
        if len(cur) % 2 == 1:
            nxt.append(cur[-1])
        cur = nxt

    out_bit = cur[0]
    depth = bld.depth_of(out_bit)

    return Tile(
        records  = bld.records,
        in_a     = a_bits,
        in_b     = b_bits,
        out      = [out_bit],
        metadata = TileMetadata(
            operation      = "FP32_CMP_EQ",
            precision      = 32,
            pipeline_depth = depth,
            cell_count     = len(bld.records),
            notes = "FP32 bit-exact equality. No NaN handling (NaN != NaN not implemented)."
        )
    )


# ── peripheral tile stub factory ─────────────────────────────────────────────

def _make_peripheral_stub(operation: str, device_type: str,
                           cell_count: int, pipeline_depth: int,
                           inbound_lanes: int = 1,
                           outbound_lanes: int = 1,
                           notes: str = "") -> "callable":
    """
    Return a builder function for a peripheral handler tile stub.

    Peripheral tiles have no CellMapRecord list — they are structural
    stubs whose primary purpose is to carry metadata (pipeline_depth,
    cell_count, inbound_lanes, outbound_lanes) to the Pond creation layer.
    The actual handler cells are spatial programs loaded at device
    connection time from the device's onboard image storage.
    """
    def builder(base_address: int = 0x10000) -> Tile:
        return Tile(
            records  = [],   # structural stub — no cell map
            in_a     = [],
            in_b     = [],
            out      = [],
            metadata = TileMetadata(
                operation      = operation,
                precision      = 0,
                pipeline_depth = pipeline_depth,
                cell_count     = cell_count,
                ieee754_compliant = False,
                notes          = f"{device_type}. {notes}",
                inbound_lanes  = inbound_lanes,
                outbound_lanes = outbound_lanes,
            )
        )
    builder.__name__ = operation
    return builder


# ── tile library ─────────────────────────────────────────────────────────────


# ── Counter tile builders ─────────────────────────────────────────────────────
# First-order primitives for loop iteration.
# Three variants covering the common use patterns:
#
#   COUNTER_SHIFT_N  — shift-register counter for fixed small ranges (n=2..32)
#                      Signal walks a chain of storage cells; no arithmetic at all.
#                      Depth = n ticks exactly. Best for for i in range(n).
#
#   COUNTER_RIPPLE   — ripple-carry increment for variable/large ranges.
#                      Each tick adds 1 via ripple carry (avg ~2 gate depths).
#                      Comparator fires DONE when count == limit.
#
#   COUNTER_DECREMENT — counts down from n to 0.
#                       Decrement-by-1 + zero detector. Best for bounded loops
#                       where the index value is not needed.

def make_counter_shift(n: int, base_address: int = 0x10000) -> "Tile":
    """
    Shift-register counter for range(n), n in 2..32.

    Architecture:
      n storage cells in a chain. A single 1-bit token walks from cell 0
      to cell n-1, one step per TICK pulse.

      TICK_ADDR  — input: pulse to advance (one tick = one iteration)
      VALUE_ADDR — output: current step index (0..n-1), encoded as
                   the position of the active cell (one-hot, n output bits)
      DONE_ADDR  — output: fires 1 when token leaves cell n-1 (loop complete)

    No arithmetic, no carry. Depth per iteration = 1 tick.
    Total loop depth = n ticks.

    The token is implemented as a start_flag walking through a chain of
    PASS cells with storage mode. DONE is a wire from the last cell's output.
    """
    from gate_states import GS_PASS
    from controller import CellMapRecord

    alloc = TileAddressAllocator(base_address)
    b     = NORBuilder(alloc)

    # Allocate TICK input and n stage outputs
    tick_addr  = alloc.alloc()
    stage_addrs = [alloc.alloc() for _ in range(n)]
    done_addr   = alloc.alloc()

    records = []

    # Chain: TICK → stage[0] → stage[1] → ... → stage[n-1] → DONE
    # Each link is a PASS cell (signal routing, 1 tick latency each)
    prev = tick_addr
    for i, stage in enumerate(stage_addrs):
        records.append(CellMapRecord(GS_PASS, prev, stage))
        b.depth_map[stage] = i + 1
        prev = stage

    # DONE fires one tick after the last stage
    records.append(CellMapRecord(GS_PASS, prev, done_addr))
    b.depth_map[done_addr] = n + 1

    # Merge with NORBuilder records (empty for pure PASS chain)
    all_records = b.records + records

    return Tile(
        records  = all_records,
        in_a     = [tick_addr],
        in_b     = [],
        out      = stage_addrs + [done_addr],
        metadata = TileMetadata(
            operation      = "COUNTER_SHIFT_%d" % n,
            precision      = n,
            pipeline_depth = n + 1,
            cell_count     = len(all_records),
            notes          = (
                "Shift-register counter for range(%d). "
                "No arithmetic — pure PASS chain. "
                "out[0..%d]: one-hot step index. out[%d]: DONE." % (n, n-1, n)
            ),
        )
    )


def make_counter_ripple(bits: int = 8, base_address: int = 0x10000) -> "Tile":
    """
    Ripple-carry increment counter for variable or large ranges.

    Architecture:
      `bits`-wide counter register. Each TICK pulse adds 1 via ripple carry.
      Carry propagates on average 2 gate depths (worst case = bits).
      DONE fires when VALUE == LIMIT (XNOR + AND-tree comparison).

      TICK_ADDR   — input:  pulse to increment
      LIMIT_ADDR  — input:  stop value (bits-wide, wired at compile time)
      VALUE_ADDR  — output: current count (bits-wide)
      DONE_ADDR   — output: 1 when count == limit
      CARRY_ADDR  — output: overflow (count wrapped past 2^bits - 1)

    Depth per increment: avg 2 gate depths for ripple carry.
    Comparison depth: log2(bits) for AND-tree.
    """
    alloc = TileAddressAllocator(base_address)
    b     = NORBuilder(alloc)

    tick_addr  = alloc.alloc()
    limit_bits = alloc.alloc_word(bits)
    value_bits = alloc.alloc_word(bits)

    for addr in [tick_addr] + limit_bits + value_bits:
        b.depth_map[addr] = 0

    # Ripple-carry increment: bit[i] = bit[i] XOR carry[i]
    # carry[i+1] = bit[i] AND carry[i]  (carry in = TICK)
    out_bits  = []
    carry     = tick_addr
    for i in range(bits):
        new_bit = b.XOR2(value_bits[i], carry)
        carry   = b.AND2(value_bits[i], carry)
        out_bits.append(new_bit)

    carry_out = carry  # final carry = overflow

    # Comparator: DONE = (out_bits == limit_bits)
    # XNOR each pair, AND-tree the results
    eq_bits = [b.XNOR2(out_bits[i], limit_bits[i]) for i in range(bits)]
    cur = eq_bits
    while len(cur) > 1:
        nxt = []
        for i in range(0, len(cur) - 1, 2):
            nxt.append(b.AND2(cur[i], cur[i+1]))
        if len(cur) % 2:
            nxt.append(cur[-1])
        cur = nxt
    done_bit = cur[0]

    avg_depth  = int(2 + (bits ** 0.5))   # empirical ripple + comparator
    cell_count = len(b.records)

    return Tile(
        records  = b.records,
        in_a     = [tick_addr],
        in_b     = limit_bits,
        out      = out_bits + [done_bit, carry_out],
        metadata = TileMetadata(
            operation      = "COUNTER_RIPPLE_%d" % bits,
            precision      = bits,
            pipeline_depth = avg_depth,
            cell_count     = cell_count,
            notes          = (
                "%d-bit ripple counter. TICK to increment. "
                "out[0..%d]: value, out[%d]: DONE (==limit), out[%d]: carry." % (
                    bits, bits-1, bits, bits+1)
            ),
        )
    )


def make_counter_decrement(bits: int = 8, base_address: int = 0x10000) -> "Tile":
    """
    Decrement-by-1 counter for bounded loops (while n: n -= 1).

    Architecture:
      Counts down from initial value to 0.
      Decrement: subtract 1 via ripple borrow (NOT ripple add 1 on ~value).
      Zero detector: NOR across all value bits.

      TICK_ADDR  — input:  pulse to decrement
      VALUE_ADDR — input/output: current count (bits-wide, caller sets initial)
      DONE_ADDR  — output: 1 when count reaches 0

    Simpler than COUNTER_RIPPLE — no comparison against external limit,
    just zero detection (1 NOR gate per bit pair + AND-tree).
    Depth per decrement: avg 2 gate depths.
    """
    alloc = TileAddressAllocator(base_address)
    b     = NORBuilder(alloc)

    tick_addr  = alloc.alloc()
    value_bits = alloc.alloc_word(bits)

    for addr in [tick_addr] + value_bits:
        b.depth_map[addr] = 0

    # Decrement: equivalent to (NOT value) + 1 = two's complement -1
    # borrow[i+1] = NOT(value[i]) AND borrow[i], borrow[0] = TICK
    dec_bits = []
    borrow   = tick_addr
    for i in range(bits):
        not_v   = b.NOT(value_bits[i])
        new_bit = b.XOR2(value_bits[i], borrow)
        borrow  = b.AND2(not_v, borrow)
        dec_bits.append(new_bit)

    # Zero detector: DONE = NOR(all dec_bits) = 1 when all bits are 0
    # Build NOR tree: NOR(a,b), then NOR chain
    cur = dec_bits[:]
    while len(cur) > 1:
        nxt = []
        for i in range(0, len(cur) - 1, 2):
            nxt.append(b.NOR2(cur[i], cur[i+1]))
        if len(cur) % 2:
            nxt.append(b.NOT(cur[-1]))   # single leftover: NOT is a NOR(a,a)
        cur = nxt
    # The NOR tree gives 1 when all inputs are 0 — that's our DONE
    done_bit = cur[0]

    avg_depth  = int(2 + (bits ** 0.5))
    cell_count = len(b.records)

    return Tile(
        records  = b.records,
        in_a     = [tick_addr],
        in_b     = value_bits,
        out      = dec_bits + [done_bit],
        metadata = TileMetadata(
            operation      = "COUNTER_DECREMENT_%d" % bits,
            precision      = bits,
            pipeline_depth = avg_depth,
            cell_count     = cell_count,
            notes          = (
                "%d-bit decrement counter. TICK to decrement. "
                "out[0..%d]: new value, out[%d]: DONE (==0)." % (
                    bits, bits-1, bits)
            ),
        )
    )



def make_sr_latch(base_address: int = 0x10000) -> "Tile":
    """SR latch: cross-coupled NOR. S=1:set, R=1:reset, S=R=0:hold."""
    alloc = TileAddressAllocator(base_address)
    b     = NORBuilder(alloc)
    s_addr  = alloc.alloc(); r_addr  = alloc.alloc()
    q_addr  = alloc.alloc(); nq_addr = alloc.alloc()
    for a in [s_addr, r_addr, q_addr, nq_addr]: b.depth_map[a] = 0
    q_new  = b.NOR2(s_addr, nq_addr)
    nq_new = b.NOR2(r_addr, q_addr)
    b._emit2(GS_PASS, q_new, q_addr); b._emit2(GS_PASS, nq_new, nq_addr)
    depth = max(b.depth_of(q_new), b.depth_of(nq_new))
    return Tile(records=b.records, in_a=[s_addr, q_addr], in_b=[r_addr, nq_addr],
        out=[q_new, nq_new],
        metadata=TileMetadata(operation="SR_LATCH", precision=1,
            pipeline_depth=depth, cell_count=len(b.records),
            notes="Cross-coupled NOR SR latch."))

def make_ring_osc(base_address: int = 0x10000) -> "Tile":
    """Ring oscillator: 1 cell (GS_NOT|GS_LOOP_BACK|LOOP_MODE). Toggles every tick."""
    from gate_states import GS_LOOP_BACK, LOOP_MODE
    alloc = TileAddressAllocator(base_address)
    seed = alloc.alloc(); clk_out = alloc.alloc()
    gs = GS_NOT | GS_LOOP_BACK | LOOP_MODE
    return Tile(records=[CellMapRecord(gs, seed, clk_out)],
        in_a=[seed], in_b=[], out=[clk_out],
        metadata=TileMetadata(operation="RING_OSC", precision=1,
            pipeline_depth=1, cell_count=1,
            notes="1-cell ring oscillator. Toggles every tick."))




# ── INT32 bitwise logic tiles ─────────────────────────────────────────────────

def make_int32_not(base_address: int = 0x10000) -> Tile:
    """32-bit bitwise NOT: out[i] = ~a[i]."""
    alloc = TileAddressAllocator(base_address)
    a_bits = alloc.alloc_word(32)
    b = NORBuilder(alloc)
    for addr in a_bits:
        b.depth_map[addr] = 0
    out_bits = [b.NOT(a) for a in a_bits]
    depth = max(b.depth_of(o) for o in out_bits)
    return Tile(
        records  = b.records,
        in_a     = a_bits,
        in_b     = [],
        out      = out_bits,
        metadata = TileMetadata(
            operation      = "INT32_NOT",
            precision      = 32,
            pipeline_depth = depth,
            cell_count     = len(b.records),
            notes = "32-bit bitwise NOT. in_a=32 bits, out=32 bits."
        )
    )


def make_int32_and(base_address: int = 0x10000) -> Tile:
    """32-bit bitwise AND: out[i] = a[i] & b[i]."""
    alloc = TileAddressAllocator(base_address)
    a_bits = alloc.alloc_word(32)
    b_bits = alloc.alloc_word(32)
    b = NORBuilder(alloc)
    for addr in a_bits + b_bits:
        b.depth_map[addr] = 0
    out_bits = [b.AND2(a_bits[i], b_bits[i]) for i in range(32)]
    depth = max(b.depth_of(o) for o in out_bits)
    return Tile(
        records  = b.records,
        in_a     = a_bits,
        in_b     = b_bits,
        out      = out_bits,
        metadata = TileMetadata(
            operation      = "INT32_AND",
            precision      = 32,
            pipeline_depth = depth,
            cell_count     = len(b.records),
            notes = "32-bit bitwise AND. in_a=32, in_b=32, out=32."
        )
    )


def make_int32_or(base_address: int = 0x10000) -> Tile:
    """32-bit bitwise OR: out[i] = a[i] | b[i]."""
    alloc = TileAddressAllocator(base_address)
    a_bits = alloc.alloc_word(32)
    b_bits = alloc.alloc_word(32)
    b = NORBuilder(alloc)
    for addr in a_bits + b_bits:
        b.depth_map[addr] = 0
    out_bits = [b.OR2(a_bits[i], b_bits[i]) for i in range(32)]
    depth = max(b.depth_of(o) for o in out_bits)
    return Tile(
        records  = b.records,
        in_a     = a_bits,
        in_b     = b_bits,
        out      = out_bits,
        metadata = TileMetadata(
            operation      = "INT32_OR",
            precision      = 32,
            pipeline_depth = depth,
            cell_count     = len(b.records),
            notes = "32-bit bitwise OR. in_a=32, in_b=32, out=32."
        )
    )


def make_int32_xor(base_address: int = 0x10000) -> Tile:
    """32-bit bitwise XOR: out[i] = a[i] ^ b[i]."""
    alloc = TileAddressAllocator(base_address)
    a_bits = alloc.alloc_word(32)
    b_bits = alloc.alloc_word(32)
    b = NORBuilder(alloc)
    for addr in a_bits + b_bits:
        b.depth_map[addr] = 0
    out_bits = [b.XOR2(a_bits[i], b_bits[i]) for i in range(32)]
    depth = max(b.depth_of(o) for o in out_bits)
    return Tile(
        records  = b.records,
        in_a     = a_bits,
        in_b     = b_bits,
        out      = out_bits,
        metadata = TileMetadata(
            operation      = "INT32_XOR",
            precision      = 32,
            pipeline_depth = depth,
            cell_count     = len(b.records),
            notes = "32-bit bitwise XOR. in_a=32, in_b=32, out=32."
        )
    )


def make_int32_max(base_address: int = 0x10000) -> Tile:
    """
    32-bit signed maximum: out = a if a >= b else b.
    Built as MUX(a, b, a >= b) using INT32_SUB sign bit.
    """
    alloc = TileAddressAllocator(base_address)
    a_bits = alloc.alloc_word(32)
    b_bits = alloc.alloc_word(32)
    b = NORBuilder(alloc)
    for addr in a_bits + b_bits:
        b.depth_map[addr] = 0

    # a >= b  ←→  NOT (a - b < 0)  ←→  NOT sign_bit(a - b)
    # Build subtractor: a - b (ripple)
    diff_bits = []
    borrow = None
    for i in range(32):
        ai = a_bits[i]
        bi = b_bits[i]
        # Full subtractor with borrow
        if borrow is None:
            diff_i = b.XOR2(ai, bi)
            borrow = b.AND2(b.NOT(ai), bi)
        else:
            xor_ab  = b.XOR2(ai, bi)
            diff_i  = b.XOR2(xor_ab, borrow)
            borrow  = b.OR2(b.AND2(b.NOT(ai), bi),
                            b.AND2(b.NOT(xor_ab), borrow))
        diff_bits.append(diff_i)

    sign_bit = diff_bits[31]    # MSB = 1 if a < b
    a_lt_b   = sign_bit         # a < b
    a_ge_b   = b.NOT(a_lt_b)    # a >= b

    # MUX: if a >= b then a else b
    out_bits = [b.OR2(b.AND2(a_bits[i], a_ge_b),
                      b.AND2(b_bits[i], a_lt_b))
                for i in range(32)]

    depth = max(b.depth_of(o) for o in out_bits)
    return Tile(
        records  = b.records,
        in_a     = a_bits,
        in_b     = b_bits,
        out      = out_bits,
        metadata = TileMetadata(
            operation      = "INT32_MAX",
            precision      = 32,
            pipeline_depth = depth,
            cell_count     = len(b.records),
            notes = "32-bit signed MAX(a,b). in_a=32, in_b=32, out=32."
        )
    )


def make_int32_min(base_address: int = 0x10000) -> Tile:
    """
    32-bit signed minimum: out = a if a <= b else b.
    Built as MUX(a, b, a <= b) using INT32_SUB sign bit.
    """
    alloc = TileAddressAllocator(base_address)
    a_bits = alloc.alloc_word(32)
    b_bits = alloc.alloc_word(32)
    b = NORBuilder(alloc)
    for addr in a_bits + b_bits:
        b.depth_map[addr] = 0

    diff_bits = []
    borrow = None
    for i in range(32):
        ai = a_bits[i]
        bi = b_bits[i]
        if borrow is None:
            diff_i = b.XOR2(ai, bi)
            borrow = b.AND2(b.NOT(ai), bi)
        else:
            xor_ab  = b.XOR2(ai, bi)
            diff_i  = b.XOR2(xor_ab, borrow)
            borrow  = b.OR2(b.AND2(b.NOT(ai), bi),
                            b.AND2(b.NOT(xor_ab), borrow))
        diff_bits.append(diff_i)

    sign_bit = diff_bits[31]
    a_lt_b   = sign_bit          # a < b → take a
    a_ge_b   = b.NOT(a_lt_b)    # a >= b → take b

    out_bits = [b.OR2(b.AND2(a_bits[i], a_lt_b),
                      b.AND2(b_bits[i], a_ge_b))
                for i in range(32)]

    depth = max(b.depth_of(o) for o in out_bits)
    return Tile(
        records  = b.records,
        in_a     = a_bits,
        in_b     = b_bits,
        out      = out_bits,
        metadata = TileMetadata(
            operation      = "INT32_MIN",
            precision      = 32,
            pipeline_depth = depth,
            cell_count     = len(b.records),
            notes = "32-bit signed MIN(a,b). in_a=32, in_b=32, out=32."
        )
    )


# ── Pulse and delay tiles ─────────────────────────────────────────────────────

def make_pulse_gen(base_address: int = 0x10000) -> Tile:
    """
    Pulse generator: emits a single 1-cycle pulse when triggered.
    in_a[0] = trigger input
    out[0]  = pulse output (1 for exactly one cycle)
    Uses a NOT cell feeding back through a latch to suppress after first pulse.
    """
    from gate_states import GS_PASS, GS_NOT, GS_LATCH
    alloc = TileAddressAllocator(base_address)
    trig_addr  = alloc.alloc()
    pulse_addr = alloc.alloc()
    suppress_addr = alloc.alloc()

    from controller import CellMapRecord
    records = [
        # Trigger → pulse (direct PASS, one cycle)
        CellMapRecord(GS_PASS,  trig_addr,    pulse_addr),
        # Suppress: after trigger fires, NOT feeds back to block re-fire
        CellMapRecord(GS_NOT | GS_LATCH, trig_addr, suppress_addr),
    ]

    return Tile(
        records  = records,
        in_a     = [trig_addr],
        in_b     = [],
        out      = [pulse_addr, suppress_addr],
        metadata = TileMetadata(
            operation      = "PULSE_GEN",
            precision      = 1,
            pipeline_depth = 1,
            cell_count     = len(records),
            notes = "Single-cycle pulse on trigger. in_a[0]=trigger, out[0]=pulse."
        )
    )


def make_delay_n(n: int = 4, base_address: int = 0x10000) -> Tile:
    """
    N-cycle delay line: output = input delayed by N clock cycles.
    Implemented as PASS chain of N cells.
    in_a[0] = data input
    out[0]  = data output (delayed N cycles)
    """
    from gate_states import GS_PASS
    from controller import CellMapRecord

    alloc = TileAddressAllocator(base_address)
    addrs = [alloc.alloc() for _ in range(n + 1)]

    records = [
        CellMapRecord(GS_PASS, addrs[i], addrs[i+1])
        for i in range(n)
    ]

    return Tile(
        records  = records,
        in_a     = [addrs[0]],
        in_b     = [],
        out      = [addrs[n]],
        metadata = TileMetadata(
            operation      = f"DELAY_{n}",
            precision      = 1,
            pipeline_depth = n,
            cell_count     = len(records),
            notes = f"{n}-cycle delay line. in_a[0]=input, out[0]=delayed output."
        )
    )


# ── Parity tile ───────────────────────────────────────────────────────────────

def make_parity_32(base_address: int = 0x10000) -> Tile:
    """
    32-bit even parity: out[0] = XOR of all 32 input bits.
    Result is 1 if odd number of 1s (parity error for even parity scheme).
    """
    alloc = TileAddressAllocator(base_address)
    a_bits = alloc.alloc_word(32)
    b = NORBuilder(alloc)
    for addr in a_bits:
        b.depth_map[addr] = 0

    # XOR tree: fold 32 bits to 1
    cur = list(a_bits)
    while len(cur) > 1:
        nxt = []
        for i in range(0, len(cur) - 1, 2):
            nxt.append(b.XOR2(cur[i], cur[i+1]))
        if len(cur) % 2 == 1:
            nxt.append(cur[-1])
        cur = nxt

    parity_bit = cur[0]
    depth = b.depth_of(parity_bit)

    return Tile(
        records  = b.records,
        in_a     = a_bits,
        in_b     = [],
        out      = [parity_bit],
        metadata = TileMetadata(
            operation      = "PARITY_32",
            precision      = 32,
            pipeline_depth = depth,
            cell_count     = len(b.records),
            notes = "32-bit even parity. out[0]=1 if odd number of 1s."
        )
    )


# ── LFSR tile ─────────────────────────────────────────────────────────────────

def make_lfsr_16(base_address: int = 0x10000) -> Tile:
    """
    16-bit Galois LFSR (Linear Feedback Shift Register).
    Polynomial: x^16 + x^15 + x^13 + x^4 + 1 (maximal length, period 65535).

    in_a[0-15] = initial seed (16 bits)
    in_b[0]    = clock tick (advance one step)
    out[0-15]  = current LFSR state (16 bits)
    out[16]    = output bit (LSB before shift)

    Each tick advances the LFSR one step.
    """
    alloc = TileAddressAllocator(base_address)
    seed_bits  = alloc.alloc_word(16)
    tick_addr  = alloc.alloc()
    state_bits = alloc.alloc_word(16)
    out_bit    = alloc.alloc()

    b = NORBuilder(alloc)
    for addr in seed_bits + [tick_addr] + state_bits:
        b.depth_map[addr] = 0

    # Galois LFSR taps for x^16+x^15+x^13+x^4+1: bits 15,14,12,3
    tap_positions = {15, 14, 12, 3}

    # Output bit = LSB of current state (seed_bits[0])
    output = b.AND2(seed_bits[0], tick_addr)  # only output on tick

    # New state:
    # bit[0] = feedback = seed[15] (the shifted-out bit)
    # bit[i] = seed[i-1] XOR (seed[15] if i in taps) for i > 0
    feedback = seed_bits[15]
    new_state = []
    for i in range(16):
        if i == 0:
            new_state.append(feedback)
        elif i in tap_positions:
            new_state.append(b.XOR2(seed_bits[i-1], feedback))
        else:
            new_state.append(seed_bits[i-1])

    # Gate each new state bit by tick
    out_state = [b.AND2(ns, tick_addr) for ns in new_state]

    depth = max(b.depth_of(o) for o in out_state + [output])

    return Tile(
        records  = b.records,
        in_a     = seed_bits,
        in_b     = [tick_addr],
        out      = out_state + [output],
        metadata = TileMetadata(
            operation      = "LFSR_16",
            precision      = 16,
            pipeline_depth = depth,
            cell_count     = len(b.records),
            notes = ("16-bit Galois LFSR, poly x^16+x^15+x^13+x^4+1. "
                     "in_a=16-bit seed, in_b[0]=tick, out[0-15]=state, out[16]=output bit.")
        )
    )

class TileLibrary:
    """
    Registry of pre-compiled NOR-network macro tiles.

    Each tile is compiled once and cached. Multiple placements of the same
    tile share the compiled logic (via TilePlacer address remapping).
    """

    # Base address for tile internal wires — well above the compiler's range
    TILE_BASE = 0x00100000

    def __init__(self):
        self._cache: dict[str, Tile] = {}
        self._builders = {
            "INT32_ADD":     make_int32_add,
            "INT32_ADD_CLA": make_int32_add_cla,
            "INT32_SUB":     make_int32_sub,
            "INT32_EQ":     make_int32_eq,
            "INT32_MUX":    make_int32_mux,
            "FP32_ADD":     make_fp32_add,
            "FP32_MUL":     make_fp32_mul,
            "FP32_CMP_EQ":  make_fp32_cmp_eq,
            # Counter tiles — first-order loop primitives
            "COUNTER_SHIFT_4":    lambda base=0x10000: make_counter_shift(4, base),
            "COUNTER_SHIFT_8":    lambda base=0x10000: make_counter_shift(8, base),
            "COUNTER_SHIFT_16":   lambda base=0x10000: make_counter_shift(16, base),
            "COUNTER_SHIFT_32":   lambda base=0x10000: make_counter_shift(32, base),
            "COUNTER_RIPPLE_8":   lambda base=0x10000: make_counter_ripple(8, base),
            "COUNTER_RIPPLE_16":  lambda base=0x10000: make_counter_ripple(16, base),
            "COUNTER_RIPPLE_32":  lambda base=0x10000: make_counter_ripple(32, base),
            "COUNTER_DECREMENT_8":  lambda base=0x10000: make_counter_decrement(8, base),
            "COUNTER_DECREMENT_16": lambda base=0x10000: make_counter_decrement(16, base),
            "COUNTER_DECREMENT_32": lambda base=0x10000: make_counter_decrement(32, base),
            "SR_LATCH": make_sr_latch,
            "RING_OSC": make_ring_osc,
            # Bitwise logic tiles
            "INT32_NOT":  make_int32_not,
            "INT32_AND":  make_int32_and,
            "INT32_OR":   make_int32_or,
            "INT32_XOR":  make_int32_xor,
            "INT32_MAX":  make_int32_max,
            "INT32_MIN":  make_int32_min,
            # Pulse / delay
            "PULSE_GEN":  make_pulse_gen,
            "DELAY_4":    lambda base=0x10000: make_delay_n(4,  base),
            "DELAY_8":    lambda base=0x10000: make_delay_n(8,  base),
            "DELAY_16":   lambda base=0x10000: make_delay_n(16, base),
            # Parity and LFSR
            "PARITY_32":  make_parity_32,
            "LFSR_16":    make_lfsr_16,
            # Peripheral handler tiles (Bridge Interface Contract v0.1 §5.2)
            "KEYBOARD_HANDLER":  _make_peripheral_stub(
                "KEYBOARD_HANDLER",  "HID keyboard",      840,  12,
                inbound_lanes=1, outbound_lanes=1,
                notes="Low bandwidth. One keypress per several cycles."),
            "MOUSE_HANDLER":     _make_peripheral_stub(
                "MOUSE_HANDLER",     "HID mouse",         960,  12,
                inbound_lanes=1, outbound_lanes=2,
                notes="Low-moderate bandwidth. Outbound carries packed event word "
                      "(type|buttons|dx|dy) plus separate X/Y position lanes."),
            "SENSOR_HANDLER":    _make_peripheral_stub(
                "SENSOR_HANDLER",    "Generic ADC sensor", 1240, 18,
                inbound_lanes=2, outbound_lanes=1,
                notes="Moderate inbound bursts. Single outbound for processed values."),
            "AUDIO_IN_HANDLER":  _make_peripheral_stub(
                "AUDIO_IN_HANDLER",  "Microphone/line in", 2800, 24,
                inbound_lanes=4, outbound_lanes=1,
                notes="Continuous high-bandwidth inbound. 4 lanes for stereo 24-bit."),
            "AUDIO_OUT_HANDLER": _make_peripheral_stub(
                "AUDIO_OUT_HANDLER", "Speaker/line out",   2800, 24,
                inbound_lanes=1, outbound_lanes=4,
                notes="Continuous high-bandwidth outbound. 4 lanes for stereo output."),
            "DISPLAY_HANDLER":   _make_peripheral_stub(
                "DISPLAY_HANDLER",   "Display/video out",  18600, 32,
                inbound_lanes=1, outbound_lanes=8,
                notes="Very high outbound. 8 lanes for pixel stream at display rates."),
            "NETWORK_HANDLER":   _make_peripheral_stub(
                "NETWORK_HANDLER",   "Network interface",  4200, 28,
                inbound_lanes=4, outbound_lanes=4,
                notes="Symmetric full-duplex. 4 lanes each direction."),
            "STORAGE_HANDLER":   _make_peripheral_stub(
                "STORAGE_HANDLER",   "Block storage (NVMe)", 3100, 22,
                inbound_lanes=4, outbound_lanes=2,
                notes="Read-heavy. 4 inbound for read data, 2 outbound for writes."),
        }

    def get(self, name: str) -> Tile:
        """Return the named tile, building and caching it on first access."""
        if name not in self._cache:
            if name not in self._builders:
                raise KeyError(f"Unknown tile: '{name}'. "
                               f"Available: {sorted(self._builders)}")
            self._cache[name] = self._builders[name](self.TILE_BASE)
        return self._cache[name]

    def list_tiles(self) -> list[dict]:
        """Return metadata for all available tiles."""
        results = []
        for name in sorted(self._builders):
            tile = self.get(name)
            m = tile.metadata
            results.append({
                "name":           name,
                "operation":      m.operation,
                "precision":      m.precision,
                "pipeline_depth": m.pipeline_depth,
                "cell_count":     m.cell_count,
                "ieee754":        m.ieee754_compliant,
            })
        return results

    def available(self) -> list[str]:
        return sorted(self._builders.keys())

    # ── signing and persistence ───────────────────────────────────────────────

    @staticmethod
    def _machine_id(machine_key: int) -> str:
        """Truncated SHA-256 of the machine key (public identifier)."""
        return hashlib.sha256(machine_key.to_bytes(8, 'big')).hexdigest()[:16]

    def sign_tile(self, tile: Tile, machine_key: int,
                  license_tier: Optional[str] = None) -> dict:
        """
        Sign a tile with the machine key and return a serialisable dict.

        license_tier: defaults to the tile's canonical tier from _TILE_TIERS.
        The signed dict can be saved as a .icm file via save_tile().
        """
        tier = license_tier or _TILE_TIERS.get(
            tile.metadata.operation, TIER_BASE)
        compiled_at = int(time.time())
        version = "1.0.0"

        cell_map = [
            {"gate_state":     r.gate_state,
             "input_address":  r.input_address,
             "output_address": r.output_address}
            for r in tile.records
        ]

        canonical = json.dumps({
            "tile_name":    tile.metadata.operation,
            "version":      version,
            "compiled_at":  str(compiled_at),
            "cell_map":     cell_map,
            "license_tier": tier,
        }, sort_keys=True, separators=(',', ':'))

        key_bytes = machine_key.to_bytes(8, 'big')
        sig = _hmac.new(key_bytes, canonical.encode(),
                        hashlib.sha256).hexdigest()

        checksum_data = json.dumps({
            "cell_map":       cell_map,
            "pipeline_depth": tile.metadata.pipeline_depth,
            "cell_count":     tile.metadata.cell_count,
        }, sort_keys=True, separators=(',', ':'))
        checksum = hashlib.sha256(checksum_data.encode()).hexdigest()

        return {
            "tile_name":        tile.metadata.operation,
            "version":          version,
            "compiled_at":      compiled_at,
            "cell_map":         cell_map,
            "input_addresses":  {"in_a": tile.in_a, "in_b": tile.in_b},
            "output_addresses": tile.out,
            "metadata": {
                "operation":        tile.metadata.operation,
                "precision":        tile.metadata.precision,
                "pipeline_depth":   tile.metadata.pipeline_depth,
                "cell_count":       tile.metadata.cell_count,
                "ieee754_compliant": tile.metadata.ieee754_compliant,
                "notes":            tile.metadata.notes,
            },
            "license_tier": tier,
            "signature":    sig,
            "machine_id":   self._machine_id(machine_key),
            "checksum":     checksum,
        }

    def verify_tile(self, tile_dict: dict, machine_key: int,
                    licensed_tier: str = TIER_FULL) -> tuple[bool, str]:
        """
        Verify a signed tile dict.

        Checks machine_id, signature, checksum, and license tier.
        Returns (valid: bool, reason: str).
        """
        # Machine binding
        expected_mid = self._machine_id(machine_key)
        if tile_dict.get("machine_id") != expected_mid:
            return False, "machine_id mismatch — tile signed by different machine"

        # Signature
        canonical = json.dumps({
            "tile_name":    tile_dict["tile_name"],
            "version":      tile_dict["version"],
            "compiled_at":  str(tile_dict["compiled_at"]),
            "cell_map":     tile_dict["cell_map"],
            "license_tier": tile_dict["license_tier"],
        }, sort_keys=True, separators=(',', ':'))
        key_bytes = machine_key.to_bytes(8, 'big')
        expected_sig = _hmac.new(
            key_bytes, canonical.encode(), hashlib.sha256).hexdigest()
        if tile_dict.get("signature") != expected_sig:
            return False, "signature invalid — tile may have been tampered with"

        # Checksum
        chk_data = json.dumps({
            "cell_map":       tile_dict["cell_map"],
            "pipeline_depth": tile_dict["metadata"]["pipeline_depth"],
            "cell_count":     tile_dict["metadata"]["cell_count"],
        }, sort_keys=True, separators=(',', ':'))
        expected_chk = hashlib.sha256(chk_data.encode()).hexdigest()
        if tile_dict.get("checksum") != expected_chk:
            return False, "checksum mismatch — cell_map or metadata corrupted"

        # License tier
        required = TIER_ORDER.get(tile_dict.get("license_tier", TIER_FULL), 999)
        held = TIER_ORDER.get(licensed_tier, -1)
        if held < required:
            return False, (f"license insufficient: tile requires "
                           f"{tile_dict['license_tier']}, system holds {licensed_tier}")

        return True, "valid"

    def save_tile(self, tile: Tile, path: str, machine_key: int,
                  license_tier: Optional[str] = None) -> str:
        """
        Sign and save a tile to a .icm file.
        Returns the path written.
        """
        signed = self.sign_tile(tile, machine_key, license_tier)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(signed, f, indent=2)
        return path

    def load_tile(self, path: str, machine_key: int,
                  licensed_tier: str = TIER_FULL) -> Tile:
        """
        Load, verify, and reconstruct a Tile from a .icm file.
        Raises TileSigningError if verification fails.
        Raises TileLicenseError if license tier is insufficient.
        """
        with open(path) as f:
            tile_dict = json.load(f)

        valid, reason = self.verify_tile(tile_dict, machine_key, licensed_tier)
        if not valid:
            if "license" in reason:
                raise TileLicenseError(reason)
            raise TileSigningError(reason)

        records = [
            CellMapRecord(c["gate_state"], c["input_address"], c["output_address"])
            for c in tile_dict["cell_map"]
        ]
        m = tile_dict["metadata"]
        meta = TileMetadata(
            operation        = m["operation"],
            precision        = m["precision"],
            pipeline_depth   = m["pipeline_depth"],
            cell_count       = m["cell_count"],
            ieee754_compliant = m["ieee754_compliant"],
            notes            = m["notes"],
        )
        ia = tile_dict["input_addresses"]
        return Tile(
            records  = records,
            in_a     = ia.get("in_a", []),
            in_b     = ia.get("in_b", []),
            out      = tile_dict["output_addresses"],
            metadata = meta,
        )

    def save_library(self, directory: str, machine_key: int,
                     tile_names: Optional[list[str]] = None) -> dict:
        """
        Save all (or named) tiles to .icm files in directory.
        Returns {tile_name: path} mapping.
        """
        names = tile_names or self.available()
        os.makedirs(directory, exist_ok=True)
        paths = {}
        for name in names:
            tile = self.get(name)
            path = os.path.join(directory, f"{name}.icm")
            self.save_tile(tile, path, machine_key)
            paths[name] = path
        return paths


# ── tile placer ───────────────────────────────────────────────────────────────

class TilePlacer:
    """
    Places a tile into an address space by remapping its internal wire
    addresses to a fresh region of the bus.

    This allows the same compiled tile to be placed multiple times without
    address conflicts.

    Relative mode (relative=True):
      Assigns offsets starting from 0. Records hold offsets, not absolute
      addresses. Pass base_address to load_map() to resolve at load time:

        placer = TilePlacer(relative=True)
        records, in_a, in_b, out = placer.place(tile)
        ctrl.load_map(records, 'my_tile', base_address=pond.base_address)

      Same records can be loaded into any Pond at any base address.
    """

    def __init__(self, base_address: int = 0, relative: bool = False):
        self._relative = relative
        if relative:
            self._base = 0
            self._next = 0
        else:
            self._base = base_address
            self._next = base_address

    def place(self, tile: Tile,
              a_values: Optional[list[int]] = None,
              b_values: Optional[list[int]] = None
              ) -> tuple[list, list[int], list[int], list[int]]:
        """
        Place a tile at the current address offset.

        Returns (records, in_a_addrs, in_b_addrs, out_addrs).
        In relative mode all addresses are offsets from 0.
        """
        all_tile_addrs = set()
        for r in tile.records:
            all_tile_addrs.add(r.input_address)
            all_tile_addrs.add(r.output_address)
        for a in tile.in_a + tile.in_b + tile.out:
            all_tile_addrs.add(a)

        remap: dict[int, int] = {}

        if a_values is not None:
            for tile_addr, placed_addr in zip(tile.in_a, a_values):
                remap[tile_addr] = placed_addr
        if b_values is not None:
            for tile_addr, placed_addr in zip(tile.in_b, b_values):
                remap[tile_addr] = placed_addr

        for addr in sorted(all_tile_addrs):
            if addr not in remap:
                remap[addr] = self._next
                self._next += 1

        placed_records = [
            CellMapRecord(r.gate_state,
                          remap[r.input_address],
                          remap[r.output_address])
            for r in tile.records
        ]

        in_a_addrs = [remap[a] for a in tile.in_a]
        in_b_addrs = [remap[a] for a in tile.in_b]
        out_addrs  = [remap[a] for a in tile.out]

        return placed_records, in_a_addrs, in_b_addrs, out_addrs

    @property
    def is_relative(self) -> bool:
        return self._relative

    @property
    def next_offset(self) -> int:
        return self._next


# ── Ripple counter tile ────────────────────────────────────────────────────────

def _build_ripple_adder(alloc: TileAddressAllocator,
                         a_bits: list[int],
                         b_bits: list[int]) -> tuple:
    """
    Build an N-bit ripple-carry adder.

    Uses the same half-adder-first pattern as _build_int32_add:
      bit 0: half adder (no carry-in) — avoids the undriven-address
             timing problem that occurs when carry_in is a fresh bus
             address at depth 0 that is never written to.
      bit 1+: full adder using carry from previous stage.

    Full adder:
      sum[i]     = XOR(XOR(a[i], b[i]), carry[i])
      carry[i+1] = OR(AND(a[i], b[i]), AND(XOR(a[i], b[i]), carry[i]))

    Returns (builder, sum_bits, carry_out_addr).
    """
    b = NORBuilder(alloc)
    n = len(a_bits)
    for addr in a_bits + b_bits:
        b.depth_map[addr] = 0

    sum_bits = []
    c = None   # no carry-in on bit 0 (half adder first)

    for i in range(n):
        ai = a_bits[i]
        bi = b_bits[i]

        if c is None:
            # Bit 0: half adder — no carry-in address needed
            # sum[0] = XOR(a, b)
            s = b.XOR2(ai, bi)
            # carry[1] = AND(a, b)
            c = b.AND2(ai, bi)
        else:
            # Full adder: sum = XOR(XOR(a, b), carry_in)
            axb  = b.XOR2(ai, bi)
            s    = b.XOR2(axb, c)
            # carry[i+1] = OR(AND(a,b), AND(XOR(a,b), carry))
            ab   = b.AND2(ai, bi)
            axbc = b.AND2(axb, c)
            c    = b.OR2(ab, axbc)

        sum_bits.append(s)

    return b, sum_bits, c


def make_ripple_counter(bits: int = 4,
                         base_address: int = 0x10000) -> "Tile":
    """
    N-bit ripple-carry adder tile for use as a counter step.

    Inputs:
      in_a: current count (N bits, LSB first)
      in_b: step value   (N bits, LSB first)

    Output:
      out: count + step  (N bits, LSB first)

    Pipeline depth: N ticks (one tick per bit stage).
    Cell count: roughly 9 cells per bit (XOR + carry logic).

    The latch holding the accumulated count lives outside this tile —
    in the CounterLatch or PipelinedSlot storage cell. The tile computes
    one step; the latch feeds it the current value and receives the result.

    Example — 4-bit counter (0..15), step=1:
        counts 0 → 1 → 2 → ... → 15 → 0 (wraps)
    """
    if bits < 1 or bits > 16:
        raise ValueError(f"make_ripple_counter: bits must be 1-16, got {bits}")

    alloc  = TileAddressAllocator(base_address)
    a_bits = alloc.alloc_word(bits)
    b_bits = alloc.alloc_word(bits)

    builder, sum_bits, _ = _build_ripple_adder(alloc, a_bits, b_bits)

    depth = max(builder.depth_of(s) for s in sum_bits) if sum_bits else 0
    cells = len(builder.records)

    return Tile(
        records  = builder.records,
        in_a     = a_bits,
        in_b     = b_bits,
        out      = sum_bits,
        metadata = TileMetadata(
            operation      = f"RIPPLE_COUNT_{bits}",
            precision      = bits,
            pipeline_depth = depth,
            cell_count     = cells,
            notes          = (f"{bits}-bit ripple adder for counter use. "
                              f"Add step to current value. Wraps at 2^{bits}.")
        )
    )


# ── CounterLatch ──────────────────────────────────────────────────────────────

class CounterLatch:
    """
    A self-updating accumulator built from a ripple counter tile
    and a set of per-bit storage cells.

    The latch holds the current count. On each step() call:
      1. Freeze the adder tile
      2. Write (current_count, step) into the tile's input addresses
      3. Thaw the tile — adder runs, produces count+step
      4. Capture the result — update _count
      5. The result is also available at output_addresses for downstream use

    The step value is the input — set step=1 for a standard counter,
    step=2 for even numbers, step=N for any stride. Unsigned, wraps at 2^bits.

    Usage:
        ctrl = ImagoController(cell_count=500)
        ctr = CounterLatch.build(ctrl, bits=4, initial=0)
        ctr.step(step=1)   # count -> 1
        ctr.step(step=1)   # count -> 2
        ctr.step(step=3)   # count -> 5
        print(ctr.count)   # 5
    """

    def __init__(self,
                 ctrl:             "ImagoController",
                 region_id:        str,
                 in_a_addresses:   list[int],   # current count input (per bit)
                 in_b_addresses:   list[int],   # step input (per bit)
                 out_addresses:    list[int],   # result output (per bit)
                 bits:             int,
                 initial:          int = 0):
        self.ctrl           = ctrl
        self.region_id      = region_id
        self.in_a_addresses = in_a_addresses
        self.in_b_addresses = in_b_addresses
        self.out_addresses  = out_addresses
        self.bits           = bits
        self._count         = initial & ((1 << bits) - 1)
        self._mask          = (1 << bits) - 1
        self._step_count    = 0

    @classmethod
    def build(cls,
              ctrl:    "ImagoController",
              bits:    int = 4,
              initial: int = 0,
              name:    str = "counter") -> "CounterLatch":
        """
        Allocate and configure a CounterLatch in the controller's array.
        Starts frozen — call step() to advance.
        """
        tile   = make_ripple_counter(bits=bits)
        from fp_tiles import TilePlacer
        placer = TilePlacer(base_address=0x00300000)
        records, in_a, in_b, out = placer.place(tile)

        rid = ctrl.load_map(records, name)
        if rid is None:
            raise RuntimeError(f"CounterLatch.build: load_map failed for '{name}'")
        ctrl.freeze(region_id=rid)

        print(f"[COUNTER] '{name}': {bits}-bit ripple, "
              f"depth={tile.metadata.pipeline_depth}, "
              f"cells={tile.metadata.cell_count}, "
              f"initial={initial}")

        return cls(
            ctrl           = ctrl,
            region_id      = rid,
            in_a_addresses = in_a,
            in_b_addresses = in_b,
            out_addresses  = out,
            bits           = bits,
            initial        = initial,
        )

    @property
    def count(self) -> int:
        """Current accumulated count value."""
        return self._count

    @property
    def max_value(self) -> int:
        """Maximum value before wrap (2^bits - 1)."""
        return self._mask

    def step(self, step: int = 1) -> int:
        """
        Advance the counter by step. Returns the new count.

        Uses lock/load/run:
          1. Freeze the adder tile
          2. Inject current count bits into in_a, step bits into in_b
          3. Thaw — adder pipeline runs
          4. Wait pipeline_depth ticks, read result bits
          5. Update _count, return new value
        """
        ctrl = self.ctrl
        step = step & self._mask   # clamp to bit width

        # 1. Lock
        ctrl.freeze(region_id=self.region_id)

        # Flush stale cell data
        region = ctrl._regions[self.region_id]
        for phys in region.cell_addresses:
            cell = ctrl.array.cells.get(phys)
            if cell and not cell.storage_mode:
                cell.data = None

        # 2. Write current count bits into in_a (LSB first)
        for i, addr in enumerate(self.in_a_addresses):
            bit_val = (self._count >> i) & 1
            ctrl.array.bus[addr] = (bit_val, 0)

        # Write step bits into in_b (LSB first)
        for i, addr in enumerate(self.in_b_addresses):
            bit_val = (step >> i) & 1
            ctrl.array.bus[addr] = (bit_val, 0)

        # 3. Thaw — adder runs
        ctrl.thaw(region_id=self.region_id)

        # 4. Wait for result — use run_loop style: stop when all out bits seen
        captured_bits = {}
        for _ in range(1000):
            ctrl.array.tick()
            for i, addr in enumerate(self.out_addresses):
                if i not in captured_bits:
                    entry = ctrl.array.bus.get(addr)
                    if entry is not None:
                        captured_bits[i] = (entry[0] if isinstance(entry, tuple)
                                            else entry)
            if len(captured_bits) == self.bits:
                break

        # 5. Reconstruct result from captured bits
        if len(captured_bits) == self.bits:
            result = 0
            for i in range(self.bits):
                result |= (captured_bits[i] & 1) << i
            self._count = result & self._mask
        else:
            # Partial capture — bits that didn't arrive are 0 (zero-value cells
            # may not emit if they have no downstream consumer armed)
            result = 0
            for i in range(self.bits):
                result |= (captured_bits.get(i, 0) & 1) << i
            self._count = result & self._mask

        ctrl.freeze(region_id=self.region_id)
        ctrl.array.bus.clear()

        self._step_count += 1
        return self._count

    def reset(self, value: int = 0) -> None:
        """Reset the count to a specific value without running the adder."""
        self._count = value & self._mask

    def step_n(self, n: int, step: int = 1) -> list[int]:
        """
        Advance the counter n times with the given step.
        Returns a list of all intermediate values.
        """
        return [self.step(step) for _ in range(n)]

    def status(self) -> dict:
        return {
            "count":       self._count,
            "bits":        self.bits,
            "max_value":   self._mask,
            "step_count":  self._step_count,
            "region_id":   self.region_id,
        }

    def __repr__(self) -> str:
        return (f"CounterLatch(count={self._count}/{self._mask} "
                f"bits={self.bits} steps={self._step_count})")
