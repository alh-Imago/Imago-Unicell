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
  - Max 4 cells (iCEBreaker iCE40UP5K, 32-bit gate tree, 12 MHz)
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
        init = r.get('init')
        print(f"  Cell {i}: gs=0x{gs:08X}  in=0x{inp:04X}  out=0x{out:04X}"
              + (f"  init=0x{init:08X}" if init is not None else ""))


def load_onto_fpga(bridge: FPGABridge, icm: dict, max_cells: int = 8) -> bool:
    records = icm.get('records', [])

    if len(records) > max_cells:
        print(f"[ICM] ERROR: ICM has {len(records)} cells, "
              f"hardware supports {max_cells}")
        return False

    # address_width: VM uses 32-bit, iCEBreaker truncates to 16-bit.
    # Read from ICM header; default 32 (VM) or 16 (iCEBreaker target).
    addr_width = icm.get('address_width', 32)
    addr_mask  = 0xFFFF if addr_width == 16 else 0xFFFFFFFF

    # Warn on retired fields from format_version < 2
    if any(r.get('inB') for r in records):
        print("[ICM] WARNING: inB field found — retired in format_version=2. Ignored.")
    if any(r.get('alt') for r in records):
        print("[ICM] WARNING: alt field found — SELECT cells retired. Ignored.")

    print(f"[ICM] Loading {len(records)} cell(s) onto FPGA...")

    # Reset array first
    bridge.reset()
    time.sleep(0.1)

    for cell_idx, record in enumerate(records):
        cell_addr  = cell_idx          # physical cell address
        gate_state = record.get('gs', 0x00000001)
        input_addr = record.get('in',  0x1000)
        output_addr= record.get('out', 0x2000)
        init_val   = record.get('init')   # preloaded a_data (None = no preload)

        bridge.configure_cell(cell_addr, gate_state,
                              input_addr  & addr_mask,
                              output_addr & addr_mask)
        time.sleep(0.02)

        # Preload a_data if init is specified (e.g. NOT cells: 0xFFFFFFFF)
        # This implements the preloaded-A pattern on silicon:
        # cell fires immediately on first B arrival since a_arrived=True.
        if init_val is not None:
            bridge.preload_cell(cell_addr, init_val & 0xFFFFFFFF)
            time.sleep(0.02)
            print(f"  Cell {cell_idx} (0x{cell_addr:04X}): "
                  f"gs=0x{gate_state:08X}  "
                  f"in=0x{input_addr:04X}  "
                  f"out=0x{output_addr:04X}  "
                  f"init=0x{init_val:08X}")
        else:
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
    parser.add_argument('--max-cells', type=int, default=4,
                        help='Maximum cells available (default: 4)')
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
