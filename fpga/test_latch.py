"""
test_latch.py -- Direct test of unicell-latch on iCEBreaker
Tests the latch cell timing model with detailed diagnostics.

Usage: python fpga\test_latch.py --port COM4
"""
import sys, time, argparse
sys.path.insert(0, 'fpga')
from fpga_bridge import FPGABridge

GS_NOT = 0x00000001
LOAD_PATTERN = 0xA5A5A5A5

def status(b, label):
    time.sleep(0.05)
    s = b.get_status()
    if s:
        print(f"  [{label}] armed={s['armed']} cycles={s['cycles']}")
    else:
        print(f"  [{label}] no response")
    return s

def test_not_gate(b, cell=0, in_addr=0x1000, out_addr=0x2000):
    print(f"\n=== NOT gate test (cell={cell} in=0x{in_addr:04X} out=0x{out_addr:04X}) ===")

    print(f"\nStep 1: LOAD_PATTERN to cell {cell}")
    b.inject(cell, LOAD_PATTERN)
    status(b, "after LOAD_PATTERN")

    print(f"\nStep 2: GS_NOT to cell {cell}")
    b.inject(cell, GS_NOT)
    status(b, "after GS_NOT")

    print(f"\nStep 3: input_addr=0x{in_addr:04X} to cell {cell}")
    b.inject(cell, in_addr)
    status(b, "after input_addr")

    print(f"\nStep 4: output_addr=0x{out_addr:04X} to cell {cell}")
    b.inject(cell, out_addr)
    status(b, "after output_addr -- should be armed=1 now")

    print(f"\nInjecting 0 to 0x{in_addr:04X}...")
    time.sleep(0.05)
    b.inject(in_addr, 0)
    result = b.wait_for_fire(timeout=3.0)
    if result:
        print(f"  FIRED: addr=0x{result[0]:04X} data={result[1] & 1} expected=1 {'✓' if (result[1]&1)==1 else '✗'}")
    else:
        print(f"  NO FIRE")
        status(b, "after no-fire")

    print(f"\nInjecting 1 to 0x{in_addr:04X}...")
    time.sleep(0.05)
    b.inject(in_addr, 1)
    result = b.wait_for_fire(timeout=3.0)
    if result:
        print(f"  FIRED: addr=0x{result[0]:04X} data={result[1] & 1} expected=0 {'✓' if (result[1]&1)==0 else '✗'}")
    else:
        print(f"  NO FIRE")
        status(b, "after no-fire")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="COM4")
    args = parser.parse_args()

    b = FPGABridge(args.port)
    b.connect()

    try:
        test_not_gate(b, cell=0, in_addr=0x1000, out_addr=0x2000)
    finally:
        b.disconnect()

if __name__ == "__main__":
    main()
