#!/usr/bin/env python3
"""
unicell_xdma.py — UniCell PCIe tool using XDMA BAR0 MMIO

Talks directly to /dev/xdma0_user via read/write/seek.
No kernel module needed beyond the standard xdma driver.

Register map (AXI-Lite, 32-bit registers, CELL_STRIDE=32 bytes/cell):
  0x000000: Bridge control/status
  0x000004: Armed cell count
  0x000008: Cycle count
  0x00000C: Output addr (last fired)
  0x000010: Output data (last fired)
  0x000014: Output valid flag
  0x000018: Reset (write 1 to reset)

  Per-cell registers at base + (cell_index * CELL_STRIDE):
  +0x00: cmd_latch  (command/gate-state word)
  +0x04: input_addr
  +0x08: output_addr
  +0x0C: a_data
  +0x10: data_reg (current cell value)
  +0x14: status/armed flag

Usage:
    sudo python3 unicell_xdma.py info
    sudo python3 unicell_xdma.py reset
    sudo python3 unicell_xdma.py dump --cells 8
    sudo python3 unicell_xdma.py poke --offset 0x100 --value 0xDEADBEEF
    sudo python3 unicell_xdma.py peek --offset 0x100
"""

import os
import struct
import argparse

DEVICE      = "/dev/xdma0_user"
CELL_STRIDE = 32
BAR0_SIZE   = 4 * 1024 * 1024  # 4MB

# Bridge status register offsets
REG_ARMED_COUNT  = 0x04
REG_CYCLE_COUNT  = 0x08
REG_OUT_ADDR     = 0x0C
REG_OUT_DATA     = 0x10
REG_OUT_VALID    = 0x14
REG_RESET        = 0x18

def read32(fd, offset):
    fd.seek(offset)
    data = fd.read(4)
    if len(data) < 4:
        raise IOError(f"Short read at offset 0x{offset:08X}")
    return struct.unpack("<I", data)[0]

def write32(fd, offset, value):
    fd.seek(offset)
    fd.write(struct.pack("<I", value))

def cmd_info(args):
    with open(DEVICE, "rb+", buffering=0) as fd:
        armed  = read32(fd, REG_ARMED_COUNT)
        cycles = read32(fd, REG_CYCLE_COUNT)
        ov     = read32(fd, REG_OUT_VALID)
        oa     = read32(fd, REG_OUT_ADDR)
        od     = read32(fd, REG_OUT_DATA)

    print("UniCell XDMA Fabric")
    print(f"  Device:       {DEVICE}")
    print(f"  Armed cells:  {armed}")
    print(f"  Cycle count:  {cycles}")
    print(f"  Output valid: {bool(ov)}")
    if ov:
        print(f"  Output addr:  0x{oa:04X}")
        print(f"  Output data:  0x{od:08X}")

def cmd_reset(args):
    with open(DEVICE, "rb+", buffering=0) as fd:
        write32(fd, REG_RESET, 1)
    print("Reset sent.")

def cmd_dump(args):
    n = args.cells
    with open(DEVICE, "rb+", buffering=0) as fd:
        print(f"Dumping {n} cells (stride={CELL_STRIDE} bytes):")
        print(f"{'Cell':>4}  {'cmd_latch':>10}  {'in_addr':>8}  {'out_addr':>9}  {'a_data':>10}  {'data_reg':>10}")
        print("-" * 65)
        for i in range(n):
            base = 0x1000 + i * CELL_STRIDE  # cells start at 0x1000 in bridge map
            try:
                cmd  = read32(fd, base + 0x00)
                ia   = read32(fd, base + 0x04)
                oa   = read32(fd, base + 0x08)
                ad   = read32(fd, base + 0x0C)
                dr   = read32(fd, base + 0x10)
                print(f"{i:>4}  0x{cmd:08X}  0x{ia:04X}    0x{oa:04X}     0x{ad:08X}  0x{dr:08X}")
            except IOError as e:
                print(f"{i:>4}  READ ERROR: {e}")

def cmd_peek(args):
    with open(DEVICE, "rb+", buffering=0) as fd:
        val = read32(fd, args.offset)
    print(f"[0x{args.offset:08X}] = 0x{val:08X}")

def cmd_poke(args):
    with open(DEVICE, "rb+", buffering=0) as fd:
        write32(fd, args.offset, args.value)
    print(f"[0x{args.offset:08X}] <- 0x{args.value:08X}")

def main():
    p = argparse.ArgumentParser(description="UniCell XDMA tool")
    sub = p.add_subparsers(dest="command")
    sub.required = True

    sub.add_parser("info",  help="Show fabric status")
    sub.add_parser("reset", help="Reset fabric")

    dp = sub.add_parser("dump", help="Dump cell registers")
    dp.add_argument("--cells", type=int, default=8)

    pp = sub.add_parser("peek", help="Read a BAR0 register")
    pp.add_argument("--offset", type=lambda x: int(x,0), required=True)

    pk = sub.add_parser("poke", help="Write a BAR0 register")
    pk.add_argument("--offset", type=lambda x: int(x,0), required=True)
    pk.add_argument("--value",  type=lambda x: int(x,0), required=True)

    args = p.parse_args()
    {"info": cmd_info, "reset": cmd_reset, "dump": cmd_dump,
     "peek": cmd_peek, "poke": cmd_poke}[args.command](args)

if __name__ == "__main__":
    main()
