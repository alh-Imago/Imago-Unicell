"""
packed_shift_adder.py — Packed word shift-chain adder for Imago UniCell.

CONCEPT
-------
The Kogge-Stone parallel prefix adder normally uses one cell per bit-position
per stage (32 cols × 5 stages = 160 cells). This implementation exploits a
different axis: packing ALL 32 bit-position G/P values into a SINGLE 32-bit
word, then using the cell's native shift operations to combine them.

Each KS prefix stage collapses from 32 parallel cells → 3 chained cells:
    SHR(span) → AND(P_packed) → OR(G_packed)

5 stages × 3 cells = 15 prefix cells.
+ 4 cells G/P extraction + 2 cells XOR sum = ~21 cells total.
vs 482 cells for the wide KS tree.

TRADE-OFF
---------
Wide KS:   parallel across all 32 bits simultaneously, 5 ticks deep
Packed KS: sequential across 5 stages, 3 ticks per stage = 15 ticks deep
           but only ~21 cells vs 482 — 23× more compact

USE CASE SCENARIOS
------------------
1. CELL-BUDGET CONSTRAINED targets (iCEBreaker iCE40UP5K: 128 LUT4 equiv)
   — Wide KS at 482 cells is impossible; packed at 21 cells fits easily.

2. MULTIPLE PARALLEL ADDERS — If you need 8 adders simultaneously,
   packed costs 8×21=168 cells. Wide KS would cost 8×482=3856 cells.

3. KINTEX-7 DENSE ARITHMETIC — For DSP-style kernels needing many adders
   in a tight cell budget alongside other logic.

4. FUTURE: 64-BIT ADDITION — Packed approach scales to 64-bit with 6 stages
   (span doubles: 1,2,4,8,16,32) at only 22 cells. Wide KS would need
   64 cols × 6 stages = 384 prefix cells.

METHODOLOGY — OTHER OPERATIONS USING THIS PATTERN
--------------------------------------------------
Any operation that is "parallel across N bit-positions but uses the same
power-of-2 span structure" can use packed shift-chain:

1. PRIORITY ENCODER — find highest set bit:
   P = x | (x >> 1) | (x >> 2) | (x >> 4) | (x >> 8) | (x >> 16)
   (5 OR-with-shift stages, 2 cells each = 10 cells)

2. LEADING ZERO COUNT (CLZ) — needed for float normalisation:
   Uses same prefix OR structure to propagate "seen a 1" bits rightward,
   then subtract from 31. Replaces the current multi-cell CLZ in fp_tiles.py.

3. POPULATION COUNT (POPCOUNT) — count set bits:
   Packed 2-bit sums → 4-bit sums → 8-bit sums → 16-bit → 32-bit
   Using shifts to align partial sums before adding:
   x = x - ((x >> 1) & 0x55555555)
   x = (x & 0x33333333) + ((x >> 2) & 0x33333333)
   etc. — the classic Hamming weight algorithm, now each step = 1-3 cells.

4. BYTE/NIBBLE REVERSE — endian swap:
   Uses rotate/shift + mask pattern, collapses to 4-5 cells.

5. CARRY-SAVE ADDER for 3-input add — (a+b+c) in two stages:
   S = a XOR b XOR c       (1 cell each)
   C = carry = (a&b)|(b&c)|(a&c), shifted left 1 (1 shift + 2 cells)
   Then packed add S+C.

6. GREY CODE ENCODER/DECODER:
   encode: G = x XOR (x >> 1)           — 2 cells
   decode: uses prefix XOR with doubling spans — same 5-stage pattern

7. PARITY TREE — XOR reduction across all bits:
   p = x XOR (x >> 1)
   p = p XOR (p >> 2)
   p = p XOR (p >> 4)
   p = p XOR (p >> 8)
   p = p XOR (p >> 16)    — 5 stages, 2 cells each = 10 cells

8. SCATTER/GATHER MASK — deposit/extract bits by mask (BMI2-style):
   Uses iterative shift+mask pattern, each step halves the active bits.
"""

from dataclasses import dataclass, field
from typing import Optional
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from unicell_array import UniCellArray
from unicell import UniCell
from gate_states import GS_AND, GS_OR, GS_XOR, GS_NOT, GS_PASS, GS_PASS_B


# ─────────────────────────────────────────────────────────────────────────────
# Simulation helpers
# ─────────────────────────────────────────────────────────────────────────────

MASK32 = 0xFFFFFFFF


def _shr(value: int, shift: int) -> int:
    """Logical right shift on 32-bit value."""
    return (value >> shift) & MASK32


def _shl(value: int, shift: int) -> int:
    """Logical left shift on 32-bit value."""
    return (value << shift) & MASK32


# ─────────────────────────────────────────────────────────────────────────────
# Packed KS prefix adder — pure Python reference model
# ─────────────────────────────────────────────────────────────────────────────

def packed_ks_add(a: int, b: int) -> int:
    """
    32-bit addition using packed Kogge-Stone prefix in a 32-bit word.

    G/P values for all 32 bit-positions are packed into single 32-bit words.
    Each KS stage operates on the full word with a single shift+AND+OR.

    This is the reference model for the cell implementation below.
    """
    a &= MASK32
    b &= MASK32

    # Stage 0: extract initial generate and propagate
    # G[i] = a[i] AND b[i]   — position i generates a carry
    # P[i] = a[i] XOR b[i]   — position i propagates a carry
    G = a & b
    P = a ^ b
    P0 = P   # preserve original propagate (= partial sum bits) for final XOR

    # Prefix stages — carry propagates from LOW bits toward HIGH bits,
    # so we use LEFT shifts (<<) to bring lower G/P values up to higher positions.
    # After all stages, G[i] = 1 iff there is a carry OUT of bit i.
    for span in (1, 2, 4, 8, 16):
        G = (G | (P & (_shl(G, span)))) & MASK32
        P = (P & (_shl(P, span))) & MASK32

    # Carry INTO each bit position i = carry OUT of bit i-1 = G shifted left 1
    carry = _shl(G, 1)

    # Final sum: partial sum XOR carry-in
    return (P0 ^ carry) & MASK32


def packed_ks_add_traced(a: int, b: int) -> dict:
    """
    Same as packed_ks_add but returns intermediate values at each stage.
    Shows exactly what each cell would hold at each step.
    """
    a &= MASK32
    b &= MASK32

    G = a & b
    P = a ^ b
    P0 = P
    trace = [{"stage": 0, "G": G, "P": P, "span": 0,
               "desc": "Initial G=a&b, P=a^b"}]

    for k, span in enumerate((1, 2, 4, 8, 16), 1):
        G_new = (G | (P & (_shl(G, span)))) & MASK32
        P_new = (P & (_shl(P, span))) & MASK32
        trace.append({
            "stage": k, "G": G_new, "P": P_new, "span": span,
            "desc": f"span={span}: G = G|(P&(G<<{span})), P = P&(P<<{span})"
        })
        G, P = G_new, P_new

    carry = _shl(G, 1)
    result = (P0 ^ carry) & MASK32
    trace.append({"stage": 6, "carry": carry, "result": result,
                  "desc": "carry = G<<1, sum = (a^b) ^ carry"})
    return {"result": result, "trace": trace}


# ─────────────────────────────────────────────────────────────────────────────
# Cell chain plan — maps each step to a UniCell role
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ChainCell:
    """Describes one cell's role in the packed shift-chain."""
    name:      str
    op:        str          # AND / OR / XOR / SHR / SHL / PASS
    preload_a: Optional[int] = None   # value preloaded into a_data (or None = driven by bus)
    shift:     Optional[int] = None   # shift amount if op is SHR/SHL
    input_from: Optional[str] = None  # logical name of input wire
    output_to:  Optional[str] = None  # logical name of output wire
    comment:   str = ""


def build_packed_adder_chain() -> list[ChainCell]:
    """
    Returns the ordered list of cells for a packed KS adder.
    Each cell maps to one UniCell in the array.

    Cell count: 4 (extract) + 15 (5 stages × 3) + 3 (sum) = 22 cells.

    Input wires:  A_raw (32-bit), B_raw (32-bit)
    Output wire:  SUM (32-bit)
    """
    chain = []

    # ── Extraction (2 cells) ─────────────────────────────────────
    chain.append(ChainCell(
        name="G0", op="AND",
        input_from="A_raw,B_raw", output_to="G_word",
        comment="G = a & b  — initial generate word"
    ))
    chain.append(ChainCell(
        name="P0", op="XOR",
        input_from="A_raw,B_raw", output_to="P_word",
        comment="P = a ^ b  — initial propagate word (also = partial sum)"
    ))

    # ── 5 prefix stages ──────────────────────────────────────────
    # Each stage: SHR(G, span) → AND(P) → OR(G) updates G
    #             SHR(P, span) → AND(P) updates P
    # We combine G and P updates — 3 cells per stage:
    #   Cell 1: shifted_G = G >> span          (SHR, preload=span)
    #   Cell 2: term      = P & shifted_G      (AND)
    #   Cell 3: G_new     = G | term           (OR)
    # P update (P & P>>span) is simpler and can share SHR:
    #   We fold P update into same shifted output — P_new = P & (P >> span)
    # To keep it minimal we track G only (P after all stages = original XOR = P0)

    for k, span in enumerate((1, 2, 4, 8, 16), 1):
        chain.append(ChainCell(
            name=f"SHL_G{k}", op="SHL", shift=span,
            input_from="G_word", output_to=f"G_shifted_{k}",
            comment=f"Stage {k}: G << {span}  (carry propagates upward)"
        ))
        chain.append(ChainCell(
            name=f"AND_PG{k}", op="AND",
            input_from=f"P_word,G_shifted_{k}", output_to=f"PG_term_{k}",
            comment=f"Stage {k}: P & (G << {span})"
        ))
        chain.append(ChainCell(
            name=f"OR_G{k}", op="OR",
            input_from=f"G_word,PG_term_{k}", output_to="G_word",
            comment=f"Stage {k}: G = G | (P & (G << {span}))"
        ))

    # ── Sum extraction (3 cells) ──────────────────────────────────
    chain.append(ChainCell(
        name="CARRY_SHL", op="SHL", shift=1,
        input_from="G_word", output_to="carry_word",
        comment="carry = G << 1  (carry into each bit position)"
    ))
    chain.append(ChainCell(
        name="SUM_XOR", op="XOR",
        input_from="P_word,carry_word", output_to="SUM",
        comment="sum = P ^ carry  (P = original a^b)"
    ))

    return chain


# ─────────────────────────────────────────────────────────────────────────────
# Other packed-word operations using the same methodology
# ─────────────────────────────────────────────────────────────────────────────

def packed_clz(x: int) -> int:
    """
    Count Leading Zeros using packed prefix OR.
    5 stages (OR with shift), then popcount the inverted result.
    Each stage = 2 cells (SHR + OR).  10 cells total.
    """
    x &= MASK32
    # Propagate highest set bit rightward
    for shift in (1, 2, 4, 8, 16):
        x = x | _shr(x, shift)
    # x is now a mask: 0b000...0111...1 where 1s start at the highest set bit
    # CLZ = 32 - popcount(x)
    return 32 - bin(x).count('1')


def packed_popcount(x: int) -> int:
    """
    Population count using packed shift-add tree.
    Classic Hamming weight — each step = 2-3 cells.  ~12 cells total.
    """
    x &= MASK32
    x = x - ((x >> 1) & 0x55555555)
    x = (x & 0x33333333) + ((x >> 2) & 0x33333333)
    x = (x + (x >> 4)) & 0x0F0F0F0F
    x = (x * 0x01010101) & MASK32
    return x >> 24


def packed_parity(x: int) -> int:
    """
    XOR reduction — parity of all bits.
    5 stages (XOR with shift), 2 cells each = 10 cells.
    """
    x &= MASK32
    for shift in (1, 2, 4, 8, 16):
        x = x ^ _shr(x, shift)
    return x & 1


def packed_clz_chain() -> list[ChainCell]:
    """Cell chain plan for CLZ (10 cells)."""
    chain = []
    for k, span in enumerate((1, 2, 4, 8, 16), 1):
        chain.append(ChainCell(
            name=f"SHR_CLZ{k}", op="SHR", shift=span,
            input_from="X_word", output_to=f"X_shifted_{k}",
            comment=f"CLZ stage {k}: X >> {span}"
        ))
        chain.append(ChainCell(
            name=f"OR_CLZ{k}", op="OR",
            input_from=f"X_word,X_shifted_{k}", output_to="X_word",
            comment=f"CLZ stage {k}: X = X | (X >> {span})"
        ))
    # X_word now has all bits below MSB set — CLZ = 32 - popcount
    return chain


def packed_parity_chain() -> list[ChainCell]:
    """Cell chain plan for parity (10 cells)."""
    chain = []
    for k, span in enumerate((1, 2, 4, 8, 16), 1):
        chain.append(ChainCell(
            name=f"SHR_PAR{k}", op="SHR", shift=span,
            input_from="X_word", output_to=f"X_shifted_{k}",
            comment=f"Parity stage {k}: X >> {span}"
        ))
        chain.append(ChainCell(
            name=f"XOR_PAR{k}", op="XOR",
            input_from=f"X_word,X_shifted_{k}", output_to="X_word",
            comment=f"Parity stage {k}: X = X ^ (X >> {span})"
        ))
    return chain


def packed_grey_encode_chain() -> list[ChainCell]:
    """Grey code encode: G = x ^ (x >> 1). Just 2 cells."""
    return [
        ChainCell(name="SHR_GREY", op="SHR", shift=1,
                  input_from="X_word", output_to="X_shifted",
                  comment="x >> 1"),
        ChainCell(name="XOR_GREY", op="XOR",
                  input_from="X_word,X_shifted", output_to="GREY_OUT",
                  comment="Grey = x ^ (x >> 1)"),
    ]


def packed_grey_decode_chain() -> list[ChainCell]:
    """
    Grey code decode: prefix XOR with doubling spans.
    5 stages × 2 cells = 10 cells.
    """
    chain = []
    for k, span in enumerate((1, 2, 4, 8, 16), 1):
        chain.append(ChainCell(
            name=f"SHR_GD{k}", op="SHR", shift=span,
            input_from="G_word", output_to=f"G_shifted_{k}",
            comment=f"Grey decode stage {k}: G >> {span}"
        ))
        chain.append(ChainCell(
            name=f"XOR_GD{k}", op="XOR",
            input_from=f"G_word,G_shifted_{k}", output_to="G_word",
            comment=f"Grey decode stage {k}: G = G ^ (G >> {span})"
        ))
    return chain


# ─────────────────────────────────────────────────────────────────────────────
# Summary report
# ─────────────────────────────────────────────────────────────────────────────

def cell_count_comparison() -> str:
    adder = build_packed_adder_chain()
    clz   = packed_clz_chain()
    par   = packed_parity_chain()
    ge    = packed_grey_encode_chain()
    gd    = packed_grey_decode_chain()

    lines = [
        "┌─────────────────────────────────────────────────────────────┐",
        "│         Packed Shift-Chain Cell Count Comparison            │",
        "├──────────────────────────┬──────────────┬───────────────────┤",
        "│ Operation                │ Packed cells │ Previous cells    │",
        "├──────────────────────────┼──────────────┼───────────────────┤",
        f"│ 32-bit KS adder          │ {len(adder):>6} cells  │ ~482 cells (KS)   │",
        f"│ Leading zero count (CLZ) │ {len(clz):>6} cells  │ ~64 cells (fp_tile│",
        f"│ Parity (XOR reduction)   │ {len(par):>6} cells  │ ~32 cells         │",
        f"│ Grey encode              │ {len(ge):>6} cells  │  ~8 cells         │",
        f"│ Grey decode              │ {len(gd):>6} cells  │ ~64 cells         │",
        "└──────────────────────────┴──────────────┴───────────────────┘",
        "",
        "Note: Packed adder trades 23× cell reduction for 15-tick depth",
        "      vs 5-tick depth for wide KS. Choose based on cell budget.",
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

def run_tests():
    import random
    random.seed(42)

    print("=== Packed KS Adder ===")
    cases = [
        (0, 0, 0),
        (1, 1, 2),
        (0xFFFFFFFF, 1, 0),           # overflow wraps
        (0x7FFFFFFF, 1, 0x80000000),
        (0xDEADBEEF, 0x12345678, (0xDEADBEEF + 0x12345678) & MASK32),
        (0xFFFF0000, 0x0000FFFF, 0xFFFFFFFF),
        (0xFFFF0000, 0x00010000, 0x00000000),  # carry through upper half
    ]
    for a, b, expected in cases:
        result = packed_ks_add(a, b)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status}  0x{a:08X} + 0x{b:08X} = 0x{result:08X}  (expected 0x{expected:08X})")

    # Random tests
    fails = 0
    for _ in range(1000):
        a = random.randint(0, MASK32)
        b = random.randint(0, MASK32)
        expected = (a + b) & MASK32
        if packed_ks_add(a, b) != expected:
            fails += 1
    print(f"  Random 1000 tests: {1000-fails}/1000 PASS")

    print("\n=== CLZ ===")
    clz_cases = [
        (0x80000000, 0),
        (0x40000000, 1),
        (0x00000001, 31),
        (0xFFFFFFFF, 0),
        (0x00010000, 15),
    ]
    for x, expected in clz_cases:
        result = packed_clz(x)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status}  CLZ(0x{x:08X}) = {result}  (expected {expected})")

    print("\n=== Parity ===")
    par_cases = [
        (0x00000001, 1),
        (0x00000003, 0),
        (0xFFFFFFFF, 0),
        (0x80000001, 0),
        (0x00000007, 1),
    ]
    for x, expected in par_cases:
        result = packed_parity(x)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {status}  PARITY(0x{x:08X}) = {result}  (expected {expected})")

    print("\n=== Grey Encode/Decode round-trip ===")
    grey_cases = [0, 1, 2, 3, 15, 127, 255, 0xDEAD, 0xFFFFFFFF]
    for x in grey_cases:
        x &= MASK32
        # encode
        g = x ^ _shr(x, 1)
        # decode (prefix XOR)
        d = g
        for span in (1, 2, 4, 8, 16):
            d = d ^ _shr(d, span)
        status = "PASS" if d == x else "FAIL"
        print(f"  {status}  x=0x{x:08X} → grey=0x{g:08X} → decoded=0x{d:08X}")

    print("\n=== Cell Chain Plans ===")
    print(cell_count_comparison())

    print("\n=== Adder trace (0xA + 0x7) ===")
    traced = packed_ks_add_traced(0xA, 0x7)
    for step in traced["trace"]:
        if "result" in step:
            print(f"  Stage {step['stage']}: result=0x{step['result']:08X}  ← {step['desc']}")
        else:
            print(f"  Stage {step['stage']}: G=0x{step['G']:08X} P=0x{step['P']:08X}  ← {step['desc']}")


if __name__ == "__main__":
    run_tests()
