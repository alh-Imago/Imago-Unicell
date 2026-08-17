"""
test_mif_mux.py — MIF_MUX (64-bit MIF-pair 2:1 multiplexer) tests

MIF_MUX selects between two MIF pairs (ctrl+mant = 64 bits) on a selector bit.
It is the correct primitive for conditional select on MIF data (LIF reset,
LBM boundary selects, masked updates) — INT32_MUX only covers 32 of the 64
bits. Uses a shared NOT(sel) (193 cells vs 256 naive).

Run with: python3 test_mif_mux.py
"""

import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_fp_tiles import run_tile, int_to_bits, bits_to_int
from fp_tiles import TileLibrary

lib = TileLibrary()
mux = lib.get("MIF_MUX")

results = []
def check(label, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, label))
    print(f"  [{status}] {label}")


print("Structure")
check("operation metadata is MIF_MUX", mux.metadata.operation == "MIF_MUX")
check("in_a = sel + 64 pair bits (65)", len(mux.in_a) == 65)
check("in_b = 64 pair bits", len(mux.in_b) == 64)
check("out = 64 pair bits", len(mux.out) == 64)
check("cell count 193 (shared NOT, not 256 naive)", mux.metadata.cell_count == 193)
check("shallow pipeline (depth 3)", mux.metadata.pipeline_depth == 3)

print("\nSelection correctness")
def sel_pair(sel, a_ctrl, a_mant, b_ctrl, b_mant):
    A = int_to_bits(a_ctrl) + int_to_bits(a_mant)
    B = int_to_bits(b_ctrl) + int_to_bits(b_mant)
    out = run_tile(mux, [sel] + A, B)
    return bits_to_int(out[:32]), bits_to_int(out[32:])

c, m = sel_pair(1, 0xAAAAAAAA, 0x12345678, 0x55555555, 0x9ABCDEF0)
check("sel=1 selects full A pair (ctrl)", c == 0xAAAAAAAA)
check("sel=1 selects full A pair (mant)", m == 0x12345678)
c, m = sel_pair(0, 0xAAAAAAAA, 0x12345678, 0x55555555, 0x9ABCDEF0)
check("sel=0 selects full B pair (ctrl)", c == 0x55555555)
check("sel=0 selects full B pair (mant)", m == 0x9ABCDEF0)

# Both halves selected together — the failure mode of using INT32_MUX (which
# would only mux one of the two cells) is excluded.
c, m = sel_pair(1, 0xFFFFFFFF, 0x00000000, 0x00000000, 0xFFFFFFFF)
check("ctrl and mant selected as one unit (not independently)",
      c == 0xFFFFFFFF and m == 0x00000000)

print("\nRandomised")
random.seed(42)
ok = True
for _ in range(200):
    ac, am, bc, bm = (random.getrandbits(32) for _ in range(4))
    c1, m1 = sel_pair(1, ac, am, bc, bm)
    c0, m0 = sel_pair(0, ac, am, bc, bm)
    if (c1, m1) != (ac, am) or (c0, m0) != (bc, bm):
        ok = False
        break
check("200 random pairs correct in both selector positions", ok)

# A==B: selector must not matter.
c1, m1 = sel_pair(1, 0xDEADBEEF, 0xCAFEBABE, 0xDEADBEEF, 0xCAFEBABE)
c0, m0 = sel_pair(0, 0xDEADBEEF, 0xCAFEBABE, 0xDEADBEEF, 0xCAFEBABE)
check("A==B gives same result for either selector",
      (c1, m1) == (c0, m0) == (0xDEADBEEF, 0xCAFEBABE))

print("\nRegistration")
check("MIF_MUX in TileLibrary builders", "MIF_MUX" in lib._builders)

# ---- Results ----------------------------------------------------------------
print(f"\n{'='*55}")
passed = sum(1 for s, _ in results if s == "PASS")
failed = sum(1 for s, _ in results if s == "FAIL")
print(f"Results: {passed} passed, {failed} failed out of {len(results)} tests")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("\nFailed tests:")
    for s, n in results:
        if s == "FAIL":
            print(f"  {n}")
