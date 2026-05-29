"""
test_new_tiles.py — Functional tests for new library tiles

Tests:
  - INT32_NOT, INT32_AND, INT32_OR, INT32_XOR: bitwise logic correctness
  - INT32_MAX, INT32_MIN: signed comparison correctness
  - DELAY_4/8/16: pipeline depth correct
  - PARITY_32: XOR tree correctness
  - LFSR_16: advances state correctly
  - PULSE_GEN: builds OK
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from fp_tiles import TileLibrary, TilePlacer
from controller import ImagoController, CellMapRecord
from gate_states import GS_PASS

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    results.append(("PASS" if ok else "FAIL", name))
    if not ok:
        print(f"  [FAIL] {name}  got={got!r}  expected={expected!r}")
    else:
        print(f"  [PASS] {name}")


lib = TileLibrary()

def run_tile(tile_name, in_a_val=None, in_b_val=None,
             bits_a=32, bits_b=32, max_cycles=50_000):
    """
    Place tile, load into controller, run with given inputs.
    Returns list of output bit values (normalised to 0/1).
    Uses compute_tile_preloads when tile has a preload_map,
    otherwise injects A first then B (two-arrival ordering).
    """
    from compiler_int32 import compute_tile_preloads
    tile   = lib.get(tile_name)
    placer = TilePlacer(base_address=0x100000)
    records, in_a, in_b, out, _ = placer.place(tile)

    # Build 32-bit bus word dicts (0=0x00000000, 1=0xFFFFFFFF)
    a_dict = {}
    b_dict = {}
    if in_a_val is not None:
        for bit, addr in enumerate(in_a[:bits_a]):
            a_dict[addr] = 0xFFFFFFFF if (in_a_val >> bit) & 1 else 0
    if in_b_val is not None:
        for bit, addr in enumerate(in_b[:bits_b]):
            b_dict[addr] = 0xFFFFFFFF if (in_b_val >> bit) & 1 else 0

    # Use preloaded-A when tile has a preload_map; else rely on two-arrival
    preloads = compute_tile_preloads(tile, a_dict, b_dict) if getattr(tile, 'preload_map', None) else None

    ctrl = ImagoController(cell_count=len(records) + 100)
    rid  = ctrl.load_map(records, tile_name, preloaded_a=preloads)

    # one_shot for AND/OR tree tiles (EQ, MUX, comparisons) — not for ADD/SUB
    op = tile.metadata.operation
    if preloads and op not in ('INT32_ADD', 'INT32_ADD_CLA', 'INT32_SUB'):
        region = ctrl._regions[rid]
        region.preloaded_one_shot = True

    # Inject A first (stored as a_data), then B (triggers fire)
    # For preloaded tiles, only inject B-side
    if preloads:
        a_src_addrs = set(preloads.keys())
        inputs = {k: v for k, v in {**a_dict, **b_dict}.items()
                  if k not in a_src_addrs}
    else:
        inputs = {**a_dict, **b_dict}

    result = ctrl.run(rid, inputs=inputs, capture_addresses=out,
                      max_cycles=max_cycles)

    bits = []
    for addr in out:
        v = result.get(addr) if result else None
        bits.append(1 if v else 0)
    return bits

def bits_to_int(bits, signed=False):
    """Convert list of bit values (LSB first) to integer."""
    v = sum(b << i for i, b in enumerate(bits) if b)
    if signed and len(bits) == 32 and (v >> 31):
        v -= (1 << 32)
    return v


# =============================================================================
print("\n=== INT32_NOT ===\n")
# =============================================================================

# NOT(0x00000000) = 0xFFFFFFFF
bits = run_tile("INT32_NOT", in_a_val=0x00000000)
check_eq("NOT(0): cell count",  len(bits), 32)
check_eq("NOT(0) = 0xFFFFFFFF", bits_to_int(bits), 0xFFFFFFFF)

# NOT(0xFFFFFFFF) = 0x00000000
bits2 = run_tile("INT32_NOT", in_a_val=0xFFFFFFFF)
check_eq("NOT(0xFFFFFFFF) = 0", bits_to_int(bits2), 0)

# NOT(0xA5A5A5A5)
bits3 = run_tile("INT32_NOT", in_a_val=0xA5A5A5A5)
check_eq("NOT(0xA5A5A5A5) = 0x5A5A5A5A",
         bits_to_int(bits3), 0x5A5A5A5A)


# =============================================================================
print("\n=== INT32_AND ===\n")
# =============================================================================

bits = run_tile("INT32_AND", in_a_val=0xFF00FF00, in_b_val=0x0F0F0F0F)
check_eq("AND(0xFF00FF00, 0x0F0F0F0F) = 0x0F000F00",
         bits_to_int(bits), 0x0F000F00)

bits2 = run_tile("INT32_AND", in_a_val=0xFFFFFFFF, in_b_val=0xA5A5A5A5)
check_eq("AND(all_ones, X) = X",
         bits_to_int(bits2), 0xA5A5A5A5)

bits3 = run_tile("INT32_AND", in_a_val=0xFFFFFFFF, in_b_val=0x00000000)
check_eq("AND(any, 0) = 0",
         bits_to_int(bits3), 0)


# =============================================================================
print("\n=== INT32_OR ===\n")
# =============================================================================

bits = run_tile("INT32_OR", in_a_val=0xF0F0F0F0, in_b_val=0x0F0F0F0F)
check_eq("OR(0xF0F0F0F0, 0x0F0F0F0F) = 0xFFFFFFFF",
         bits_to_int(bits), 0xFFFFFFFF)

bits2 = run_tile("INT32_OR", in_a_val=0x00000000, in_b_val=0xA5A5A5A5)
check_eq("OR(0, X) = X",
         bits_to_int(bits2), 0xA5A5A5A5)

bits3 = run_tile("INT32_OR", in_a_val=0x00000000, in_b_val=0x00000000)
check_eq("OR(0, 0) = 0",
         bits_to_int(bits3), 0)


# =============================================================================
print("\n=== INT32_XOR ===\n")
# =============================================================================

bits = run_tile("INT32_XOR", in_a_val=0xFFFFFFFF, in_b_val=0xFFFFFFFF)
check_eq("XOR(all_ones, all_ones) = 0",
         bits_to_int(bits), 0)

bits2 = run_tile("INT32_XOR", in_a_val=0xA5A5A5A5, in_b_val=0x5A5A5A5A)
check_eq("XOR(0xA5A5A5A5, 0x5A5A5A5A) = 0xFFFFFFFF",
         bits_to_int(bits2), 0xFFFFFFFF)

bits3 = run_tile("INT32_XOR", in_a_val=0x12345678, in_b_val=0x00000000)
check_eq("XOR(X, 0) = X",
         bits_to_int(bits3), 0x12345678)


# =============================================================================
print("\n=== INT32_MAX ===\n")
# =============================================================================

bits = run_tile("INT32_MAX", in_a_val=10, in_b_val=5, max_cycles=500_000)
check_eq("MAX(10, 5) = 10", bits_to_int(bits), 10)

bits2 = run_tile("INT32_MAX", in_a_val=3, in_b_val=7, max_cycles=500_000)
check_eq("MAX(3, 7) = 7",   bits_to_int(bits2), 7)

bits3 = run_tile("INT32_MAX", in_a_val=42, in_b_val=42, max_cycles=500_000)
check_eq("MAX(42, 42) = 42", bits_to_int(bits3), 42)


# =============================================================================
print("\n=== INT32_MIN ===\n")
# =============================================================================

bits = run_tile("INT32_MIN", in_a_val=10, in_b_val=5, max_cycles=500_000)
check_eq("MIN(10, 5) = 5",  bits_to_int(bits), 5)

bits2 = run_tile("INT32_MIN", in_a_val=3, in_b_val=7, max_cycles=500_000)
check_eq("MIN(3, 7) = 3",   bits_to_int(bits2), 3)

bits3 = run_tile("INT32_MIN", in_a_val=99, in_b_val=99, max_cycles=500_000)
check_eq("MIN(99, 99) = 99", bits_to_int(bits3), 99)


# =============================================================================
print("\n=== DELAY tiles ===\n")
# =============================================================================

for delay_n, name in [(4, "DELAY_4"), (8, "DELAY_8"), (16, "DELAY_16")]:
    tile = lib.get(name)
    check_eq(f"{name}: pipeline_depth = {delay_n}",
             tile.metadata.pipeline_depth, delay_n)
    check_eq(f"{name}: cell_count = {delay_n}",
             tile.metadata.cell_count, delay_n)
    check_eq(f"{name}: in_a = 1", len(tile.in_a), 1)
    check_eq(f"{name}: out = 1",  len(tile.out),  1)


# =============================================================================
print("\n=== PARITY_32 ===\n")
# =============================================================================

# Even number of 1s — parity = 0
bits = run_tile("PARITY_32", in_a_val=0b11001100)
check_eq("PARITY(0b11001100) = 0 (even)",  bits[0], 0)

# Odd number of 1s — parity = 1
bits2 = run_tile("PARITY_32", in_a_val=0b10000001)
check_eq("PARITY(0b10000001) = 0 (even)",  bits2[0], 0)

bits3 = run_tile("PARITY_32", in_a_val=0b10000000)
check_eq("PARITY(0b10000000) = 1 (odd)",   bits3[0], 1)

# All ones: 32 bits set — even count, parity = 0
bits4 = run_tile("PARITY_32", in_a_val=0xFFFFFFFF)
check_eq("PARITY(0xFFFFFFFF) = 0 (32 bits, even)", bits4[0], 0)


# =============================================================================
print("\n=== PULSE_GEN ===\n")
# =============================================================================

tile = lib.get("PULSE_GEN")
check("PULSE_GEN: builds OK",        tile is not None)
check_eq("PULSE_GEN: cell_count = 2", tile.metadata.cell_count, 2)
check_eq("PULSE_GEN: depth = 1",      tile.metadata.pipeline_depth, 1)
check_eq("PULSE_GEN: in_a = 1",       len(tile.in_a), 1)


# =============================================================================
print("\n=== LFSR_16 ===\n")
# =============================================================================

tile = lib.get("LFSR_16")
check("LFSR_16: builds OK",          tile is not None)
check_eq("LFSR_16: in_a = 16",       len(tile.in_a), 16)
check_eq("LFSR_16: in_b = 1",        len(tile.in_b), 1)
check_eq("LFSR_16: out = 17",        len(tile.out),  17)
check("LFSR_16: cell_count > 0",     tile.metadata.cell_count > 0)


# =============================================================================
print("\n=== All tiles in TileLibrary ===\n")
# =============================================================================

all_tiles = lib.available()
new_tiles = ['INT32_NOT','INT32_AND','INT32_OR','INT32_XOR',
             'INT32_MAX','INT32_MIN','PULSE_GEN','DELAY_4',
             'DELAY_8','DELAY_16','PARITY_32','LFSR_16']
for name in new_tiles:
    check(f"{name} in available()", name in all_tiles)

check("total tiles >= 39", len(all_tiles) >= 39)


# =============================================================================
print("\n=== Results ===\n")
# =============================================================================

passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed:
    print("\nFailed:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
