"""
test_cla.py — Carry-Lookahead Adder Tile Tests

Validates INT32_ADD_CLA against the architecture specification:
  - NOR-network pipeline depth << ripple-carry (target: < 100)
  - Cell count < ripple-carry (INT32_ADD uses 12,931)
  - Per-depth bus emission count <= 256 (fits existing segment)
  - Bit-exact correctness against INT32_ADD reference
  - Carry-in, boundary values, overflow wrapping

Run with: python3 test_cla.py
"""

import struct, collections
from fp_tiles import (
    TileLibrary, Tile, TileMetadata,
    TileAddressAllocator, NORBuilder,
    _build_int32_add, _build_int32_add_cla,
    make_int32_add_cla,
)
from controller import ImagoController, CellMapRecord
from gate_states import GS_PASS, GS_NOT
from unicell import VAR_TRUE, VAR_FALSE

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def check_eq(name, got, expected):
    ok = got == expected
    if not ok:
        print(f"    got {got!r}, expected {expected!r}")
    check(name, ok)

# ── helpers ──────────────────────────────────────────────────────────────────

def to_bits(v, w=32):
    v = v & 0xFFFFFFFF
    return [(v >> i) & 1 for i in range(w)]

def from_bits(bits):
    r = sum(b << i for i, b in enumerate(bits))
    return r if r < 2**31 else r - 2**32

def run_tile_cla(tile: Tile, a_val: int, b_val: int, cin: int = 0) -> int:
    """Run INT32_ADD_CLA with given operands, return signed 32-bit sum."""
    ctrl = ImagoController(cell_count=len(tile.records) + 200)
    rid  = ctrl.load_map(tile.records, "INT32_ADD_CLA")
    inputs = {}
    for addr, bit in zip(tile.in_a, to_bits(a_val)):
        inputs[addr] = bit
    # in_b = x_bits[0..31] + [cin0]
    for addr, bit in zip(tile.in_b[:32], to_bits(b_val)):
        inputs[addr] = bit
    inputs[tile.in_b[32]] = cin
    result = ctrl.run(rid, inputs=inputs, capture_addresses=tile.out)
    return from_bits([result.get(addr, 0) for addr in tile.out])

INT32_MAX =  2**31 - 1
INT32_MIN = -(2**31)

lib = TileLibrary()

# =============================================================================
print("\n=== INT32_ADD_CLA — tile metadata ===\n")

tile_cla = lib.get("INT32_ADD_CLA")
tile_rip = lib.get("INT32_ADD")

check("INT32_ADD_CLA: operation name",
      tile_cla.metadata.operation == "INT32_ADD_CLA")
check("INT32_ADD_CLA: precision is 32-bit",
      tile_cla.metadata.precision == 32)
check("INT32_ADD_CLA: 32 A input addresses",  len(tile_cla.in_a) == 32)
check("INT32_ADD_CLA: 33 B input addresses (32 data + 1 carry-in)",
      len(tile_cla.in_b) == 33)
check("INT32_ADD_CLA: 32 output (sum) addresses", len(tile_cla.out) == 32)
check("INT32_ADD_CLA: pipeline_depth > 0",
      tile_cla.metadata.pipeline_depth > 0)
check("INT32_ADD_CLA: cell_count > 0",
      tile_cla.metadata.cell_count > 0)

print(f"    CLA  depth={tile_cla.metadata.pipeline_depth}  "
      f"cells={tile_cla.metadata.cell_count}")
print(f"    Ripple depth={tile_rip.metadata.pipeline_depth}  "
      f"cells={len(tile_rip.records)}")

# =============================================================================
print("\n=== INT32_ADD_CLA — pipeline depth vs ripple-carry ===\n")

cla_depth    = tile_cla.metadata.pipeline_depth
ripple_depth = tile_rip.metadata.pipeline_depth

check("CLA pipeline_depth < ripple pipeline_depth",
      cla_depth < ripple_depth)
check("CLA pipeline_depth < 100 (meaningful improvement)",
      cla_depth < 100)
check("CLA pipeline_depth > 0", cla_depth > 0)

speedup = ripple_depth / cla_depth
print(f"    Speedup: {speedup:.1f}x  (ripple {ripple_depth} -> CLA {cla_depth})")
check(f"CLA speedup >= 2x over ripple", speedup >= 2.0)

# =============================================================================
print("\n=== INT32_ADD_CLA — cell count ===\n")

cla_cells    = tile_cla.metadata.cell_count
ripple_cells = len(tile_rip.records)

check("CLA cell_count < ripple cell_count",
      cla_cells < ripple_cells)
print(f"    CLA {cla_cells} cells vs ripple {ripple_cells} "
      f"(saving {ripple_cells - cla_cells}, "
      f"{100*(ripple_cells-cla_cells)/ripple_cells:.0f}%)")

# =============================================================================
print("\n=== INT32_ADD_CLA — bus lane compliance ===\n")

# Rebuild the CLA NOR network and measure per-depth emission counts.
# Every depth must stay <= 256 to fit the default bus segment.
alloc_m = TileAddressAllocator(0x10000)
a_m = alloc_m.alloc_word(32); b_m = alloc_m.alloc_word(32); cin_m = alloc_m.alloc()
bld_m, sums_m = _build_int32_add_cla(alloc_m, a_m, b_m, cin_m)

depth_count = collections.Counter(
    bld_m.depth_map.get(r.output_address, 0) for r in bld_m.records
)
max_per_depth = max(depth_count.values())
over_256 = [(d, c) for d, c in sorted(depth_count.items()) if c > 256]

check("No depth exceeds 256 lane limit", len(over_256) == 0)
print(f"    Peak emissions at any single depth: {max_per_depth}")
if over_256:
    for d, c in over_256:
        print(f"    VIOLATION: depth {d} has {c} cells")

# =============================================================================
print("\n=== INT32_ADD_CLA — correctness (basic) ===\n")

tile = lib.get("INT32_ADD_CLA")

basic_cases = [
    (0,          0,          0,  0),
    (1,          1,          0,  2),
    (100,        200,        0,  300),
    (-1,         1,          0,  0),
    (-1,         -1,         0,  -2),
    (1_000_000,  2_000_000,  0,  3_000_000),
    (42,         58,         0,  100),
    (0x12345678, 0x11111111, 0,  0x23456789),
]
for av, bv, cinv, expected in basic_cases:
    got = run_tile_cla(tile, av, bv, cinv)
    check_eq(f"CLA: {av} + {bv} = {expected}", got, expected)

# =============================================================================
print("\n=== INT32_ADD_CLA — carry-in ===\n")

check_eq("CLA: 0 + 0 + cin=1 = 1",  run_tile_cla(tile, 0, 0, 1), 1)
check_eq("CLA: 1 + 1 + cin=1 = 3",  run_tile_cla(tile, 1, 1, 1), 3)
check_eq("CLA: 10 + 20 + cin=1 = 31", run_tile_cla(tile, 10, 20, 1), 31)
check_eq("CLA: -1 + 0 + cin=1 = 0",  run_tile_cla(tile, -1, 0, 1), 0)

# =============================================================================
print("\n=== INT32_ADD_CLA — boundary and overflow ===\n")

check_eq("CLA: INT32_MAX + 0 = INT32_MAX",
         run_tile_cla(tile, INT32_MAX, 0), INT32_MAX)
check_eq("CLA: INT32_MIN + 0 = INT32_MIN",
         run_tile_cla(tile, INT32_MIN, 0), INT32_MIN)
check_eq("CLA: INT32_MAX + 1 wraps to INT32_MIN",
         run_tile_cla(tile, INT32_MAX, 1), INT32_MIN)
check_eq("CLA: INT32_MIN + (-1) wraps to INT32_MAX",
         run_tile_cla(tile, INT32_MIN, -1), INT32_MAX)
check_eq("CLA: INT32_MIN + INT32_MIN = 0 (mod 2^32)",
         run_tile_cla(tile, INT32_MIN, INT32_MIN), 0)
check_eq("CLA: -1 + 0 = -1",
         run_tile_cla(tile, -1, 0), -1)
check_eq("CLA: 0xFFFF + 0xFFFF = 0x1FFFE",
         run_tile_cla(tile, 0xFFFF, 0xFFFF), 0x1FFFE)
check_eq("CLA: 2^15 + 2^15 = 2^16",
         run_tile_cla(tile, 32768, 32768), 65536)

# =============================================================================
print("\n=== INT32_ADD_CLA — bit-exact match vs INT32_ADD (50 cases) ===\n")

# Deterministic pseudo-random sequence (LCG, 32-bit)
def lcg_seq(n, seed=0xDEADBEEF):
    vals = []
    s = seed
    for _ in range(n):
        s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
        # signed
        vals.append(s if s < 2**31 else s - 2**32)
    return vals

ripple_tile = lib.get("INT32_ADD")
vals = lcg_seq(100)
pairs = list(zip(vals[:50], vals[50:]))

def run_ripple(tile, av, bv):
    ctrl = ImagoController(cell_count=len(tile.records)+200)
    rid  = ctrl.load_map(tile.records, "INT32_ADD")
    inputs = {}
    for addr, bit in zip(tile.in_a, to_bits(av)): inputs[addr] = bit
    for addr, bit in zip(tile.in_b, to_bits(bv)): inputs[addr] = bit
    result = ctrl.run(rid, inputs=inputs, capture_addresses=tile.out)
    return from_bits([result.get(addr, 0) for addr in tile.out])

mismatches = 0
for av, bv in pairs:
    cla_result    = run_tile_cla(tile, av, bv)
    ripple_result = run_ripple(ripple_tile, av, bv)
    if cla_result != ripple_result:
        mismatches += 1
        print(f"    MISMATCH: {av} + {bv}: CLA={cla_result} ripple={ripple_result}")

check(f"CLA matches INT32_ADD on 50 pseudo-random pairs (mismatches={mismatches})",
      mismatches == 0)

# =============================================================================
print("\n=== INT32_ADD_CLA — commutativity and associativity ===\n")

sample_pairs = [(100, 200), (-300, 150), (INT32_MAX, 0), (0x1234, 0x5678)]
for av, bv in sample_pairs:
    r1 = run_tile_cla(tile, av, bv)
    r2 = run_tile_cla(tile, bv, av)
    check(f"CLA commutative: {av} + {bv} == {bv} + {av}", r1 == r2)

a, b2, c2 = 100, 200, 300
ab  = run_tile_cla(tile, a,  b2)
abc = run_tile_cla(tile, ab, c2)
bc  = run_tile_cla(tile, b2, c2)
abc2 = run_tile_cla(tile, a, bc)
check("CLA associative: (100+200)+300 == 100+(200+300)", abc == abc2)

# =============================================================================
print("\n=== INT32_ADD_CLA — TileLibrary integration ===\n")

available = lib.available()
check("INT32_ADD_CLA in TileLibrary.available()", "INT32_ADD_CLA" in available)

tiles_info = lib.list_tiles()
cla_row = next((r for r in tiles_info if r["name"] == "INT32_ADD_CLA"), None)
check("INT32_ADD_CLA appears in list_tiles()", cla_row is not None)
if cla_row:
    check("list_tiles row: pipeline_depth > 0",   cla_row["pipeline_depth"] > 0)
    check("list_tiles row: cell_count > 0",        cla_row["cell_count"] > 0)

# Cache: second get() returns same object
tile_a = lib.get("INT32_ADD_CLA")
tile_b = lib.get("INT32_ADD_CLA")
check("TileLibrary caches INT32_ADD_CLA (same object on repeat get)", tile_a is tile_b)

# =============================================================================
print("\n=== Results ===\n")

passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
total  = len(results)
print(f"Results: {passed} passed, {failed} failed out of {total} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("\nFailed tests:")
    for status, name in results:
        if status == "FAIL":
            print(f"  [FAIL] {name}")
