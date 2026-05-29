"""
test_standalone_preload.py — Validates the three-tier preload model.

Case 1 (static): NOT gate uses GS_NOT_B, no init= or preload needed.
Case 2 (direct): AND/OR/XOR build preloaded_a directly from input bits —
                 no Python forward sim, no intermediate computation.
Case 3 (hosted): ADD/SUB/EQ/MUX use Python forward sim (full KS tree).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from controller import ImagoController
from fp_tiles import TileLibrary, TilePlacer
from unicell import VAR_TRUE, VAR_FALSE

results = []
def check(name, cond):
    status = "PASS" if cond else "FAIL"
    results.append((status, name))
    print(f"  [{status}] {name}")

def to_bus(v): return VAR_TRUE if v else VAR_FALSE

lib = TileLibrary()

# ── Case 1: NOT gate ─────────────────────────────────────────────────────────
print("\n=== Case 1: NOT gate (GS_NOT_B, no preload needed) ===\n")

tile_not = lib.get('INT32_NOT')
placer   = TilePlacer(base_address=0x10000)
recs, in_a, _, out, _ = placer.place(tile_not)

check("NOT tile: no init= values",
      all(getattr(r, 'initial_value', None) is None for r in recs))
check("NOT tile: all cells use GS_NOT_B (0x002)",
      all((r.gate_state & 0x1FF) == 0x002 for r in recs))

for in_val, exp in [(0x00000000, 0xFFFFFFFF), (0xFFFFFFFF, 0x00000000),
                    (0xA5A5A5A5, 0x5A5A5A5A), (0x12345678, 0xEDCBA987)]:
    ctrl = ImagoController(cell_count=len(recs)+50)
    rid  = ctrl.load_map(recs, 'INT32_NOT')
    inputs = {addr: to_bus((in_val>>bit)&1) for bit,addr in enumerate(in_a)}
    result = ctrl.run(rid, inputs=inputs, capture_addresses=out)
    got = sum((1 if result and result.get(a) else 0)<<i for i,a in enumerate(out))
    check(f"NOT(0x{in_val:08X}) = 0x{exp:08X} (no Python sim)",
          got == exp)

# ── Case 2: AND/OR/XOR direct preload from input bits ────────────────────────
print("\n=== Case 2: AND/OR/XOR (direct preload from a_bits, no forward sim) ===\n")

from compiler_int32 import compute_tile_preloads

for tile_name, op_fn, test_cases in [
    ('INT32_AND', lambda a,b: a & b, [
        (0xFF00FF00, 0x0F0F0F0F), (0xFFFFFFFF, 0xFFFFFFFF),
        (0x00000000, 0xFFFFFFFF), (0xA5A5A5A5, 0x5A5A5A5A)]),
    ('INT32_OR',  lambda a,b: a | b, [
        (0xF0F0F0F0, 0x0F0F0F0F), (0x00000000, 0x00000000),
        (0xA5A5A5A5, 0x5A5A5A5A), (0xFFFFFFFF, 0x00000000)]),
    ('INT32_XOR', lambda a,b: a ^ b, [
        (0xA5A5A5A5, 0x5A5A5A5A), (0xFFFFFFFF, 0xFFFFFFFF),
        (0x12345678, 0x87654321), (0x00000000, 0xFFFFFFFF)]),
]:
    tile = lib.get(tile_name)
    pm   = tile.preload_map  # {out_addr → a_src_addr}
    in_a_set = set(tile.in_a)

    # Verify all A-sources are direct input bits (Case 2 property)
    check(f"{tile_name}: all A-sources are direct input bits",
          pm is not None and all(v in in_a_set for v in pm.values()))

    for a_val, b_val in test_cases:
        placer2 = TilePlacer(base_address=0x20000)
        recs2, in_a2, in_b2, out2, _ = placer2.place(tile)

        a_dict = {addr: to_bus((a_val>>bit)&1) for bit,addr in enumerate(in_a2)}
        b_dict = {addr: to_bus((b_val>>bit)&1) for bit,addr in enumerate(in_b2)}

        # Direct preload: a_data = a_bit (no forward sim, just look up in a_dict)
        # This is what a standalone system would do: read a_bits, write preloads
        placed_pm = tile.preload_map  # uses tile addresses, not placed addresses
        direct_preloads = {out_a: a_dict.get(a_src, 0)
                           for out_a, a_src in zip(out2, in_a2)}

        ctrl3 = ImagoController(cell_count=len(recs2)+50)
        rid3  = ctrl3.load_map(recs2, tile_name,
                               preloaded_a={int(k): int(v) & 0xFFFFFFFF
                                            for k,v in direct_preloads.items()})
        result3 = ctrl3.run(rid3, inputs=b_dict, capture_addresses=out2,
                            max_cycles=10)
        got = sum((1 if result3 and result3.get(a) else 0)<<i for i,a in enumerate(out2))
        exp = op_fn(a_val, b_val) & 0xFFFFFFFF
        op  = tile_name.split('_')[1]
        check(f"{op}(0x{a_val:08X}, 0x{b_val:08X}) = 0x{exp:08X} (direct preload)",
              got == exp)

# ── Case 3: ADD uses full Python forward sim ──────────────────────────────────
print("\n=== Case 3: ADD uses Python forward sim (full KS tree) ===\n")

from compiler_int32 import run_int32_function
add_src = 'def f(a: int32, b: int32) -> int32: return a + b'
for a, b, exp in [(100,200,300), (0,0,0), (-1,1,0), (-1,-1,-2),
                  (0x7FFFFFFF,0,0x7FFFFFFF)]:
    got = run_int32_function(add_src, 'f', {'a':a,'b':b}, tile_library=lib)
    check(f"ADD({a}, {b}) = {exp} (Python forward sim)", got == exp)

# ── Summary ──────────────────────────────────────────────────────────────────
passed = sum(1 for s,_ in results if s=="PASS")
failed = sum(1 for s,_ in results if s=="FAIL")
print(f"\nResults: {passed} passed, {failed} failed out of {len(results)} tests")
if failed:
    for s,n in results:
        if s=="FAIL": print(f"  [FAIL] {n}")
