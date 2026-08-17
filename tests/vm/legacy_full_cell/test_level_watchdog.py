"""
test_level_watchdog.py — Level-watchdog arithmetic core (BRAM buffer backpressure)

Prototype for Alan's backpressure design: a watch cell (comparator) + a level
set (threshold constant) + a command cell (FREEZE/RELEASE), one pair guarding
BRAM-in (freeze the writer on overflow) and one guarding BRAM-out (freeze the
stepper on starvation), each with independent high/low thresholds so the pair
has real hysteresis (no chatter right at a boundary) instead of one shared
level.

SCOPE OF THIS FILE (explicit, not hidden):
  Proves the ARITHMETIC CORE — level = write_count - read_count, then two
  independent threshold compares (freeze_raw = level >= HIGH, release_raw =
  level <= LOW) — using the REAL compiled NOR tiles (INT32_SUB, INT32_LT_U),
  each run and verified independently first, then composed by feeding one
  tile's bit-exact output as the next tile's input. This is Python-level
  composition (two separate tile runs, glued by feeding real output bits
  forward), not yet a single continuous hardware pipeline with matched
  pipeline depths across sub->compare in one pass — that wiring, plus the
  live free-running ripple counters (COUNTER_RIPPLE, already tested
  separately in test_counter_tiles.py) feeding this instead of injected
  values, plus the actual bistable hysteresis LATCH holding "frozen" state
  between ticks (a loop_back-based cell, or a 2-cell cross-coupled NOR latch)
  are the next concrete steps once this arithmetic core is confirmed correct.

Run with: python3 test_level_watchdog.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from fp_tiles import TileLibrary, Tile
from controller import ImagoController
from compiler_int32 import compute_tile_preloads

results = []

def check(name, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def int_to_bits(value: int, width: int = 32) -> list[int]:
    value = value & ((1 << width) - 1)
    return [(value >> i) & 1 for i in range(width)]

def bits_to_int(bit_values: list[int]) -> int:
    result = 0
    for i, b in enumerate(bit_values):
        if b:
            result |= (1 << i)
    return result

def run_tile(tile: Tile, a_vals: list[int], b_vals: list[int], cell_budget: int = None) -> list[int]:
    """Same pattern as test_fp_tiles.py's run_tile -- one real tile, one pass."""
    n_cells = len(tile.records)
    if cell_budget is None:
        cell_budget = n_cells + 100

    a_dict = {addr: (0xFFFFFFFF if val else 0) for addr, val in zip(tile.in_a, a_vals)}
    b_dict = {addr: (0xFFFFFFFF if val else 0) for addr, val in zip(tile.in_b, b_vals)}

    preloaded_a = compute_tile_preloads(tile, a_dict, b_dict) if getattr(tile, 'preload_map', None) else None

    ctrl = ImagoController(cell_count=cell_budget)
    rid = ctrl.load_map(tile.records, tile.metadata.operation, preloaded_a=preloaded_a)
    if rid is None:
        return []

    region = ctrl._regions[rid]
    op = tile.metadata.operation
    needs_one_shot = op not in ('INT32_ADD', 'INT32_ADD_CLA', 'INT32_SUB', 'INT32_MUL')
    if preloaded_a and needs_one_shot:
        region.preloaded_one_shot = True

    inputs = {**a_dict, **b_dict}
    result = ctrl.run(rid, inputs=inputs, capture_addresses=tile.out)
    if result is None:
        return []
    return [1 if result.get(addr) else 0 for addr in tile.out]


def sub_u32(a: int, b: int) -> int:
    """a - b (32-bit unsigned wraparound), via the real INT32_SUB tile."""
    tile = lib.get("INT32_SUB")
    a_bits = int_to_bits(a)
    b_bits = int_to_bits(b) + [1]  # carry_in = 1 (two's-complement +1)
    out = run_tile(tile, a_bits, b_bits)
    return bits_to_int(out)

def lt_u32(a: int, b: int) -> int:
    """1 iff a < b (unsigned), via the real INT32_LT_U tile."""
    tile = lib.get("INT32_LT_U")
    a_bits = int_to_bits(a)
    b_bits = int_to_bits(b) + [1]  # carry_in = 1
    out = run_tile(tile, a_bits, b_bits)
    return out[0] if out else -1


lib = TileLibrary()

# =============================================================================
print("\n=== Isolated tile correctness (must hold before composing) ===\n")
# =============================================================================

sub_cases = [(5, 2, 3), (2, 5, (2 - 5) & 0xFFFFFFFF), (0, 0, 0), (15, 15, 0), (12, 4, 8)]
all_sub_ok = True
for a, b, expected in sub_cases:
    got = sub_u32(a, b)
    if got != expected:
        all_sub_ok = False
        print(f"    FAIL: SUB({a},{b}) = {got}, expected {expected}")
check("INT32_SUB: level = write-read correct on representative cases", all_sub_ok)

lt_cases = [(3, 5, 1), (5, 3, 0), (5, 5, 0), (0, 1, 1), (0, 0, 0)]
all_lt_ok = True
for a, b, expected in lt_cases:
    got = lt_u32(a, b)
    if got != expected:
        all_lt_ok = False
        print(f"    FAIL: LT_U({a},{b}) = {got}, expected {expected}")
check("INT32_LT_U: threshold compare correct on representative cases", all_lt_ok)

# =============================================================================
print("\n=== Composed watchdog core: level -> dual-threshold hysteresis ===\n")
# =============================================================================
# Buffer depth 16 (ADDR_W=4, matching bram_dp_v3.v this session), HIGH=12, LOW=4.
# freeze_raw  = level >= HIGH  (NOT(level < HIGH))
# release_raw = level <= LOW   (level < LOW+1)
# These are LEVEL signals (recomputed from write/read counts each time), not
# yet the stateful "stay frozen until release" latch -- see scope note above.

HIGH = 12
LOW  = 4

def watchdog_core(write_count: int, read_count: int) -> tuple:
    level = sub_u32(write_count, read_count)
    freeze_raw  = 1 - lt_u32(level, HIGH)
    release_raw = lt_u32(level, LOW + 1)
    return level, freeze_raw, release_raw

# Reference (pure Python) -- what the composed real-tile pipeline must match.
def watchdog_reference(write_count: int, read_count: int) -> tuple:
    level = (write_count - read_count) & 0xFFFFFFFF
    freeze_raw  = 1 if level >= HIGH else 0
    release_raw = 1 if level <= LOW else 0
    return level, freeze_raw, release_raw

# Sweep write/read count pairs spanning: empty, deadband-low, deadband-mid,
# deadband-high, at-HIGH, above-HIGH, and a wraparound-adjacent case.
sweep = [
    (0, 0),    # empty
    (3, 0),    # below LOW (3 < 4)
    (4, 0),    # exactly LOW
    (5, 0),    # just above LOW, in the deadband
    (8, 0),    # mid deadband
    (11, 0),   # just below HIGH
    (12, 0),   # exactly HIGH
    (15, 0),   # above HIGH (max for a 4-bit depth)
    (10, 2),   # level=8, mid deadband, nonzero read_count
    (2, 10),   # read ahead of write (shouldn't happen in practice, but the
               # arithmetic must not crash -- wraps per 32-bit unsigned rules)
]

all_composed_ok = True
for wc, rc in sweep:
    got = watchdog_core(wc, rc)
    want = watchdog_reference(wc, rc)
    if got != want:
        all_composed_ok = False
        print(f"    FAIL: watchdog(write={wc},read={rc}) = {got}, expected {want}")
    else:
        print(f"    OK: write={wc:2d} read={rc:2d} -> level=0x{got[0]:08x} "
              f"freeze_raw={got[1]} release_raw={got[2]}")
check("Composed watchdog core: matches reference across the full sweep", all_composed_ok)

print(f"\n=== Results ===\n")
pass_count = sum(1 for s, _ in results if s == "PASS")
fail_count = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {pass_count} passed, {fail_count} failed out of {pass_count+fail_count} tests")
if fail_count == 0:
    print("ALL TESTS PASSED")
    sys.exit(0)
else:
    print("\nFailed tests:")
    for status, name in results:
        if status == "FAIL":
            print(f"  {name}")
    sys.exit(1)
