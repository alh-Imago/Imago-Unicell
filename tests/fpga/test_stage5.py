"""
test_stage5.py -- Stage 5: Bridge pair test
Two cells chained: cell 0 output feeds cell 1 input automatically via bus.

Cell 0: NOT gate  -- input=0x1000, output=0x5000 (intermediate)
Cell 1: NOT gate  -- input=0x5000, output=0x2000 (final)

Chain: inject(0x1000, val) -> cell0 fires NOT -> 0x5000 -> cell1 fires NOT -> 0x2000
Double NOT = buffer: input should equal final output.

Also tests wired-OR on intermediate address:
Cell 0 + Cell 1 both output to 0x3000 = NAND via wired-OR (as before).

Usage: python fpga\test_stage5.py --port COM4
"""
import sys, time, argparse
sys.path.insert(0, 'fpga')
from fpga_bridge import FPGABridge

GS_NOT       = 0x00000001
LOAD_PATTERN = 0xA5A5A5A5

def configure(b, cell, gs, in_addr, out_addr, label=""):
    b.inject(cell, LOAD_PATTERN)
    time.sleep(0.01)
    b.inject(cell, gs)
    time.sleep(0.01)
    b.inject(cell, in_addr)
    time.sleep(0.01)
    b.inject(cell, out_addr)
    time.sleep(0.05)
    if label:
        s = b.get_status()
        time.sleep(0.05)
        print(f"  {label}: armed={s['armed'] if s else '?'}")

def collect_fires(b, count, timeout=3.0):
    results = []
    deadline = time.time() + timeout
    while len(results) < count and time.time() < deadline:
        r = b.wait_for_fire(timeout=max(0.1, deadline - time.time()))
        if r:
            results.append(r)
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="COM4")
    args = parser.parse_args()

    b = FPGABridge(args.port)
    b.connect()

    try:
        print("\n=== Stage 5: Bridge Pair Test ===")
        print("Chain: 0x1000 -> [NOT cell0] -> 0x5000 -> [NOT cell1] -> 0x2000")
        print("Expected: double NOT = buffer (input == output)")

        # Configure chain
        configure(b, cell=0, gs=GS_NOT, in_addr=0x1000, out_addr=0x5000, label="cell0 (NOT, 0x1000->0x5000)")
        configure(b, cell=1, gs=GS_NOT, in_addr=0x5000, out_addr=0x2000, label="cell1 (NOT, 0x5000->0x2000)")

        s = b.get_status()
        time.sleep(0.05)
        print(f"\nArmed cells: {s['armed'] if s else '?'} (expected 2)")

        print("\n--- Double NOT (buffer) test ---")
        for val in [0, 1]:
            print(f"\nInject {val} to 0x1000...")
            b.inject(0x1000, val)

            # Expect TWO fires: cell0 fires first, then cell1
            fires = collect_fires(b, 2, timeout=3.0)

            if len(fires) == 2:
                addr0, data0 = fires[0]
                addr1, data1 = fires[1]
                final = data1 & 1
                expected = val
                ok = '✓' if final == expected else '✗'
                print(f"  cell0 fired: addr=0x{addr0:04X} data={data0 & 1}")
                print(f"  cell1 fired: addr=0x{addr1:04X} data={data1 & 1}")
                print(f"  double_NOT({val}) = {final} expected={expected} {ok}")
            elif len(fires) == 1:
                print(f"  Only 1 fire received: addr=0x{fires[0][0]:04X} data={fires[0][1] & 1}")
                print(f"  Chain broken after cell0")
            else:
                print(f"  NO fires received")

        print("\n--- NAND via wired-OR ---")
        print("Reconfiguring both cells to output to 0x3000")
        configure(b, cell=0, gs=GS_NOT, in_addr=0x1100, out_addr=0x3000)
        configure(b, cell=1, gs=GS_NOT, in_addr=0x1200, out_addr=0x3000)
        time.sleep(0.05)

        for a, bv in [(0,0),(0,1),(1,0),(1,1)]:
            b.inject(0x1100, a)
            b.inject(0x1200, bv)
            fires = collect_fires(b, 2, timeout=2.0)
            result = max(f[1] & 1 for f in fires) if fires else '?'
            expected = 1 if not (a and bv) else 0
            ok = '✓' if result == expected else '✗'
            print(f"  NAND({a},{bv}) = {result} expected={expected} {ok}")

        s = b.get_status()
        if s:
            print(f"\nFinal status: armed={s['armed']} fired={s.get('fired','?')} errors={s.get('errors','?')}")

    finally:
        b.disconnect()

if __name__ == "__main__":
    main()
