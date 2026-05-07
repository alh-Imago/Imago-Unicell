"""
test_stage6.py -- Stage 6: Scale to 8 cells
Tests all 8 cells working together in various configurations.

Tests:
  1. 4-cell NOT chain      -- cascaded inversions, depth 4
  2. 3-input NAND          -- 3 NOT cells wired-OR to shared address
  3. 8-cell parallel       -- all 8 cells fire simultaneously
  4. Mixed: chain + parallel

Usage: python fpga\test_stage6.py --port COM4
"""
import sys, time, argparse
sys.path.insert(0, 'fpga')
from fpga_bridge import FPGABridge

GS_NOT       = 0x00000001
LOAD_PATTERN = 0xA5A5A5A5

def configure(b, cell, gs, in_addr, out_addr):
    b.inject(cell, LOAD_PATTERN)
    time.sleep(0.01)
    b.inject(cell, gs)
    time.sleep(0.01)
    b.inject(cell, in_addr)
    time.sleep(0.01)
    b.inject(cell, out_addr)
    time.sleep(0.02)

def collect_fires(b, count, timeout=3.0):
    results = []
    deadline = time.time() + timeout
    while len(results) < count and time.time() < deadline:
        r = b.wait_for_fire(timeout=max(0.1, deadline - time.time()))
        if r:
            results.append(r)
    return results

def status(b):
    time.sleep(0.05)
    s = b.get_status()
    time.sleep(0.05)
    return s

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="COM4")
    args = parser.parse_args()

    b = FPGABridge(args.port)
    b.connect()

    try:
        # ── Test 1: 4-cell NOT chain ──────────────────────────────────────────
        print("\n=== Test 1: 4-cell NOT chain ===")
        print("0x1000->[NOT0]->0x1001->[NOT1]->0x1002->[NOT2]->0x1003->[NOT3]->0x1004")
        print("Even chain length = buffer (input == output)")

        for i in range(4):
            configure(b, i, GS_NOT, 0x1000 + i, 0x1000 + i + 1)

        s = status(b)
        print(f"Armed: {s['armed'] if s else '?'} (expected 4)")

        passes = 0
        for val in [0, 1]:
            b.inject(0x1000, val)
            fires = collect_fires(b, 4, timeout=3.0)
            final = fires[-1][1] & 1 if fires else '?'
            expected = val  # 4 inversions = buffer
            ok = '✓' if final == expected else '✗'
            print(f"  chain4({val}) = {final} expected={expected} {ok} ({len(fires)} fires)")
            if final == expected:
                passes += 1
        print(f"Test 1: {passes}/2 passed")

        # ── Test 2: 3-input NAND ──────────────────────────────────────────────
        print("\n=== Test 2: 3-input NAND via wired-OR ===")
        print("NOT(A)->0x3000, NOT(B)->0x3000, NOT(C)->0x3000")
        print("OR of three NOTs = NAND(A,B,C)")

        configure(b, 4, GS_NOT, 0x2000, 0x3000)
        configure(b, 5, GS_NOT, 0x2001, 0x3000)
        configure(b, 6, GS_NOT, 0x2002, 0x3000)

        s = status(b)
        print(f"Armed: {s['armed'] if s else '?'} (expected 7)")

        passes = 0
        tests = [
            (0,0,0,1), (0,0,1,1), (0,1,0,1), (0,1,1,1),
            (1,0,0,1), (1,0,1,1), (1,1,0,1), (1,1,1,0)
        ]
        for a, bv, c, exp in tests:
            b.inject(0x2000, a)
            b.inject(0x2001, bv)
            b.inject(0x2002, c)
            fires = collect_fires(b, 3, timeout=2.0)
            result = max(f[1] & 1 for f in fires) if fires else '?'
            ok = '✓' if result == exp else '✗'
            print(f"  NAND3({a},{bv},{c}) = {result} expected={exp} {ok}")
            if result == exp:
                passes += 1
        print(f"Test 2: {passes}/8 passed")

        # ── Test 3: All 8 cells parallel ──────────────────────────────────────
        print("\n=== Test 3: All 8 cells parallel ===")
        print("All 8 cells listen on unique addresses, fire simultaneously")

        for i in range(8):
            configure(b, i, GS_NOT, 0x4000 + i, 0x5000 + i)

        s = status(b)
        print(f"Armed: {s['armed'] if s else '?'} (expected 8)")

        # Inject to all 8 inputs
        for i in range(8):
            b.inject(0x4000 + i, i % 2)  # alternating 0,1,0,1...
            time.sleep(0.005)

        fires = collect_fires(b, 8, timeout=3.0)
        print(f"  Received {len(fires)}/8 fires")
        passes = 0
        for addr, data in sorted(fires, key=lambda x: x[0]):
            cell_i = addr - 0x5000
            expected = 1 - (cell_i % 2)  # NOT of alternating input
            ok = '✓' if (data & 1) == expected else '✗'
            print(f"  cell{cell_i}: addr=0x{addr:04X} data={data & 1} expected={expected} {ok}")
            if (data & 1) == expected:
                passes += 1
        print(f"Test 3: {passes}/{len(fires)} correct, {len(fires)}/8 fired")

        # ── Final status ──────────────────────────────────────────────────────
        s = status(b)
        if s:
            print(f"\n=== Final Status ===")
            print(f"Armed: {s['armed']}  Cycles: {s['cycles']}")

    finally:
        b.disconnect()

if __name__ == "__main__":
    main()
