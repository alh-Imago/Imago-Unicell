#!/usr/bin/env python3
"""
icm_loader.py — Load an ICM file onto the iCEBreaker FPGA

Usage:
    python fpga\icm_loader.py --port COM4 --icm composer\examples\not_gate.icm
    python fpga\icm_loader.py --port COM4 --icm composer\examples\and_gate.icm
    python fpga\icm_loader.py --port COM4 --icm mydesign.icm --test

The loader:
  1. Reads the ICM file
  2. Assigns each record to a physical cell (0x0000 upward)
  3. Configures each cell via the UART bridge
  4. Reports armed cell count
  5. Optionally runs a simple input/output test

Limitations (bring-up hardware):
  - Max 8 cells (iCEBreaker iCE40UP5K)
  - gate_state values must match the NOR topology in unicell.v
  - Input addresses must be injected manually or via --test flag
"""

import json
import argparse
import sys
import time

sys.path.insert(0, '.')
from fpga_bridge import FPGABridge


def load_icm(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def print_icm_summary(icm: dict):
    print(f"\n[ICM] Program:  {icm.get('name', 'unknown')}")
    print(f"[ICM] Author:   {icm.get('author', 'unknown')}")
    print(f"[ICM] Desc:     {icm.get('description', '')}")
    records = icm.get('records', [])
    print(f"[ICM] Cells:    {len(records)}")
    print()
    for i, r in enumerate(records):
        gs   = r.get('gs', 0)
        inp  = r.get('in', 0)
        out  = r.get('out', 0)
        inB  = r.get('inB')
        print(f"  Cell {i}: gs=0x{gs:08X}  in=0x{inp:04X}  out=0x{out:04X}"
              + (f"  inB=0x{inB:04X}" if inB else ""))


def load_onto_fpga(bridge: FPGABridge, icm: dict, max_cells: int = 8) -> bool:
    records = icm.get('records', [])

    if len(records) > max_cells:
        print(f"[ICM] ERROR: ICM has {len(records)} cells, "
              f"hardware supports {max_cells}")
        return False

    # Warn about fields not yet supported in silicon
    inB_cells  = [i for i, r in enumerate(records) if r.get('inB') is not None]
    init_cells = [i for i, r in enumerate(records) if r.get('init') is not None]
    if inB_cells:
        print(f"[ICM] WARNING: {len(inB_cells)} cell(s) use inB (SYNC_WAIT) "
              f"— not yet implemented in Verilog. B-input will be ignored.")
        print(f"         Cells: {inB_cells}")
        print(f"         Use the Python VM for designs requiring SYNC_WAIT.")
    if init_cells:
        print(f"[ICM] WARNING: {len(init_cells)} cell(s) have init values "
              f"— pre-load not yet implemented in FPGA protocol. "
              f"Storage cells will start uninitialised.")
        print(f"         Cells: {init_cells}")

    print(f"[ICM] Loading {len(records)} cell(s) onto FPGA...")

    # Reset array first
    bridge.reset()
    time.sleep(0.1)

    for cell_idx, record in enumerate(records):
        cell_addr  = cell_idx          # physical cell address
        gate_state = record.get('gs', 0x00000001)
        input_addr = record.get('in',  0x1000)
        output_addr= record.get('out', 0x2000)

        bridge.configure_cell(cell_addr, gate_state, input_addr, output_addr)
        time.sleep(0.02)
        print(f"  Cell {cell_idx} (0x{cell_addr:04X}): "
              f"gs=0x{gate_state:08X}  "
              f"in=0x{input_addr:04X}  "
              f"out=0x{output_addr:04X}")

    time.sleep(0.1)
    status = bridge.get_status()
    if status:
        armed = status['armed']
        print(f"\n[ICM] Armed cells: {armed}/{len(records)}")
        if armed == len(records):
            print("[ICM] All cells armed. Ready.")
            return True
        else:
            print(f"[ICM] WARNING: only {armed} of {len(records)} cells armed")
            return False
    return False


def run_test(bridge: FPGABridge, icm: dict):
    """
    Simple test: inject 0 then 1 to each unique input address
    and collect any outputs.
    """
    records = icm.get('records', [])
    input_addrs = list(set(r.get('in', 0) for r in records))
    output_addrs = list(set(r.get('out', 0) for r in records))

    print(f"\n[TEST] Input addresses:  {[hex(a) for a in input_addrs]}")
    print(f"[TEST] Output addresses: {[hex(a) for a in output_addrs]}")
    print()

    for val in [0, 1]:
        print(f"[TEST] Injecting {val} to all inputs...")
        for addr in input_addrs:
            bridge.inject(addr, val)
            time.sleep(0.01)

        time.sleep(0.1)
        outputs = []
        while True:
            result = bridge.wait_for_fire(timeout=0.3)
            if result is None:
                break
            outputs.append(result)

        if outputs:
            for addr, data in outputs:
                print(f"  Output at 0x{addr:04X}: {data & 1}")
        else:
            print("  No output received")
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Load an ICM file onto the iCEBreaker FPGA'
    )
    parser.add_argument('--port', default='COM4',
                        help='Serial port (default: COM4)')
    parser.add_argument('--baud', type=int, default=115200,
                        help='Baud rate (default: 115200)')
    parser.add_argument('--icm', required=True,
                        help='Path to .icm file')
    parser.add_argument('--test', action='store_true',
                        help='Run simple input/output test after loading')
    parser.add_argument('--max-cells', type=int, default=8,
                        help='Maximum cells available (default: 8)')
    args = parser.parse_args()

    # Load ICM
    try:
        icm = load_icm(args.icm)
    except FileNotFoundError:
        print(f"ERROR: ICM file not found: {args.icm}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid ICM file: {e}")
        sys.exit(1)

    print_icm_summary(icm)

    # Connect
    bridge = FPGABridge(port=args.port, baud=args.baud)
    if not bridge.connect():
        sys.exit(1)

    # Load
    ok = load_onto_fpga(bridge, icm, max_cells=args.max_cells)

    # Test
    if ok and args.test:
        run_test(bridge, icm)

    bridge.disconnect()


if __name__ == '__main__':
    main()
