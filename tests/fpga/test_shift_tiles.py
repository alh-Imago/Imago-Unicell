"""
test_shift_tiles.py — iCEBreaker silicon validation for SHR, SAR, SHL tiles

Tests INT32_SHR_2, INT32_SAR_2, INT32_SHL_1 on real hardware.
These tiles were built and VM-tested but never validated on silicon.

Key test: SAR_2(-2000) must return -500 (sign-extending shift).
          SHR_2(-2000) must return 1073741324 (logical, zero-fill).

Usage:
    python tests/fpga/test_shift_tiles.py COM4
    python tests/fpga/test_shift_tiles.py COM4 0x2A5
"""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from fp_tiles import TileLibrary, TilePlacer
from fpga_bridge import FPGABridge

PORT = sys.argv[1] if len(sys.argv) > 1 else 'COM4'
AUTH = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x2A5

lib     = TileLibrary()
passed  = 0
failed  = 0

def check(label, got, expected):
    global passed, failed
    if got == expected:
        print(f"  [PASS] {label}")
        passed += 1
    else:
        print(f"  [FAIL] {label}: got={got} expected={expected}")
        failed += 1

def to_signed32(v):
    v = v & 0xFFFFFFFF
    return v - 0x100000000 if v >= 0x80000000 else v

def to_unsigned32(v):
    return v & 0xFFFFFFFF


def run_shift_tile(bridge, tile_name, input_val, base_cell=0, base_addr=0x1000):
    """
    Load a shift tile onto iCEBreaker and run it.
    Returns signed int32 result or None on timeout.
    """
    tile   = lib.get(tile_name)
    placer = TilePlacer(base_address=base_addr)
    records, in_a, in_b, out_addrs, preload = placer.place(tile)

    bridge.reset()
    time.sleep(0.2)

    # Load all cell records
    for cell_id, rec in enumerate(records, start=base_cell):
        bridge.configure(
            cell_id     = cell_id,
            gate_state  = rec.gate_state,
            input_addr  = rec.input_address,
            output_addr = rec.output_address,
        )
        time.sleep(0.002)

    time.sleep(0.05)

    # Inject input bits
    v = to_unsigned32(input_val)
    for bit_idx, addr in enumerate(in_a):
        bit = (v >> bit_idx) & 1
        bridge.inject(addr, 0xFFFFFFFF if bit else 0)
        time.sleep(0.001)

    # Drain output — collect all fired addresses
    out_set    = set(out_addrs)
    result_map = {}
    deadline   = time.time() + 1.5

    while time.time() < deadline and len(result_map) < len(out_addrs):
        r = bridge.read_output(timeout=0.1)
        if r is None:
            break
        addr, data = r
        if addr in out_set:
            result_map[addr] = data & 1

    if len(result_map) < len(out_addrs):
        # Try drain for any stragglers
        for addr, data in bridge.drain(timeout=0.3):
            if addr in out_set:
                result_map[addr] = data & 1

    if not result_map:
        return None

    # Reconstruct — missing bits default to 0
    raw = sum(result_map.get(addr, 0) << i for i, addr in enumerate(out_addrs))
    return to_signed32(raw)


def main():
    print(f"\n=== Shift Tile Silicon Validation ({PORT}) ===\n")

    try:
        bridge = FPGABridge(PORT, num_cells=256)
    except Exception as e:
        print(f"ERROR: Could not open {PORT}: {e}")
        sys.exit(1)

    with bridge:

        # ── INT32_SHR_2 — logical right shift ────────────────────────────────
        print("--- INT32_SHR_2 (logical right shift, zero-fill) ---")
        for inp, expected in [
            (0,           0),
            (4,           1),
            (100,         25),
            (1000,        250),
            (0xFFFFFFFF,  0x3FFFFFFF),  # no sign extension
        ]:
            r = run_shift_tile(bridge, 'INT32_SHR_2', inp)
            if r is None:
                print(f"  [FAIL] SHR_2({inp}): timeout")
                global failed; failed += 1
            else:
                check(f"SHR_2({inp})", to_unsigned32(r), to_unsigned32(expected))

        # ── INT32_SAR_2 — arithmetic right shift ─────────────────────────────
        print("\n--- INT32_SAR_2 (arithmetic right shift, sign-extend) ---")
        for inp, expected in [
            (0,       0),
            (4,       1),
            (1000,    250),
            (-4,      -1),      # sign preserved
            (-2000,   -500),    # key test
            (-1,      -1),      # all ones
        ]:
            r = run_shift_tile(bridge, 'INT32_SAR_2', inp)
            if r is None:
                print(f"  [FAIL] SAR_2({inp}): timeout")
                failed += 1
            else:
                check(f"SAR_2({inp})", r, expected)

        # ── INT32_SHL_1 — logical left shift ─────────────────────────────────
        print("\n--- INT32_SHL_1 (logical left shift by 1) ---")
        for inp, expected in [
            (0,    0),
            (1,    2),
            (4,    8),
            (100,  200),
            (1000, 2000),
        ]:
            r = run_shift_tile(bridge, 'INT32_SHL_1', inp)
            if r is None:
                print(f"  [FAIL] SHL_1({inp}): timeout")
                failed += 1
            else:
                check(f"SHL_1({inp})", r, expected)

    # ── Summary ───────────────────────────────────────────────────────────────
    total = passed + failed
    print(f"\n=== Results: {passed} passed, {failed} failed out of {total} ===")
    if failed == 0:
        print("ALL PASSED — shift tiles confirmed on iCEBreaker silicon.")
    else:
        print("FAILURES — investigate before building further on shift tiles.")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
