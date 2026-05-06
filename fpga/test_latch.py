"""
test_latch.py -- Direct test of unicell-latch on iCEBreaker
Tests the latch cell timing model without the demo infrastructure.

Usage: python fpga\test_latch.py --port COM4
"""
import sys, time, argparse
sys.path.insert(0, 'fpga')
from fpga_bridge import FPGABridge

GS_NOT = 0x00000001

def test_not_gate(b, cell=0, in_addr=0x1000, out_addr=0x2000):
    print(f"\n=== NOT gate test (cell {cell}) ===")
    
    # Configure
    b.inject(cell, 0xA5A5A5A5)   # LOAD_PATTERN
    time.sleep(0.01)
    b.inject(cell, GS_NOT)        # gate_state
    time.sleep(0.01)
    b.inject(cell, in_addr)       # input_address
    time.sleep(0.01)
    b.inject(cell, out_addr)      # output_address
    time.sleep(0.05)              # wait for config to complete

    s = b.get_status()
    print(f"After config: armed={s['armed'] if s else '?'}, cycles={s['cycles'] if s else '?'}")
    time.sleep(0.05)              # wait for status TX to clear

    for val in [0, 1]:
        print(f"\nInjecting {val} to 0x{in_addr:04X}...")
        b.inject(in_addr, val)
        
        # Wait longer than normal -- latch model takes 2-3 cycles
        result = b.wait_for_fire(timeout=5.0)
        
        if result:
            addr, data = result[0], result[1]
            expected = 1 - val
            ok = '✓' if (data & 1) == expected else '✗'
            print(f"  FIRED: addr=0x{addr:04X} data={data} ({data & 1}) expected={expected} {ok}")
        else:
            print(f"  NO FIRE after 5 seconds")
            # Check status
            s = b.get_status()
            print(f"  Status: armed={s['armed'] if s else '?'} cycles={s['cycles'] if s else '?'} fired={s.get('fired','?') if s else '?'}")

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
