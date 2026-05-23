#!/usr/bin/env python3
"""
unicell_tool.py — userspace tool for Imago-UniCell PCIe accelerator

Talks to /dev/unicell0 via ioctl.
Mirrors the workbench PTT view but against live silicon.

Usage:
    python3 unicell_tool.py info
    python3 unicell_tool.py configure --cell 0 --command 0x10000001 --topology 0x001 --a-data 0
    python3 unicell_tool.py inject --cell 0 --b-data 1
    python3 unicell_tool.py read --cell 0
    python3 unicell_tool.py reset
    python3 unicell_tool.py dump --cells 64
"""

import os
import fcntl
import struct
import argparse

DEVICE = "/dev/unicell0"

# ioctl numbers — must match unicell.c
UNICELL_IOC_MAGIC = ord('U')

def _iow(nr, size):  return (0x40000000 | (size << 16) | (UNICELL_IOC_MAGIC << 8) | nr)
def _ior(nr, size):  return (0x80000000 | (size << 16) | (UNICELL_IOC_MAGIC << 8) | nr)
def _iowr(nr, size): return (0xC0000000 | (size << 16) | (UNICELL_IOC_MAGIC << 8) | nr)
def _io(nr):         return (               0x00000000 | (UNICELL_IOC_MAGIC << 8) | nr)

# struct unicell_cell_cmd  { u32 cell_index, command, topology, a_data }
CELL_CMD_FMT  = "IIII"
CELL_CMD_SIZE = struct.calcsize(CELL_CMD_FMT)

# struct unicell_inject    { u32 cell_index, b_data }
INJECT_FMT  = "II"
INJECT_SIZE = struct.calcsize(INJECT_FMT)

# struct unicell_read      { u32 cell_index, output, status }
READ_FMT  = "III"
READ_SIZE = struct.calcsize(READ_FMT)

# struct unicell_info      { u32 num_cells, bar0_size, vendor_id, device_id }
INFO_FMT  = "IIII"
INFO_SIZE = struct.calcsize(INFO_FMT)

IOCTL_CONFIGURE = _iow(1,  CELL_CMD_SIZE)
IOCTL_INJECT    = _iow(2,  INJECT_SIZE)
IOCTL_READ      = _iowr(3, READ_SIZE)
IOCTL_RESET     = _io(4)
IOCTL_INFO      = _ior(5,  INFO_SIZE)


def open_device():
    try:
        return open(DEVICE, "rb+", buffering=0)
    except PermissionError:
        print(f"Permission denied — try: sudo python3 {os.path.basename(__file__)}")
        raise
    except FileNotFoundError:
        print(f"Device {DEVICE} not found — is the unicell.ko module loaded?")
        print("Check: lsmod | grep unicell")
        raise


def cmd_info(args):
    with open_device() as fd:
        buf = bytearray(INFO_SIZE)
        fcntl.ioctl(fd, IOCTL_INFO, buf)
        num_cells, bar0_size, vendor_id, device_id = struct.unpack(INFO_FMT, buf)
    print(f"UniCell PCIe Accelerator")
    print(f"  Vendor ID:  0x{vendor_id:04X}")
    print(f"  Device ID:  0x{device_id:04X}")
    print(f"  BAR0 size:  0x{bar0_size:08X} ({bar0_size} bytes)")
    print(f"  Num cells:  {num_cells}")
    print(f"  Cell stride: 32 bytes")


def cmd_configure(args):
    with open_device() as fd:
        buf = struct.pack(CELL_CMD_FMT,
            args.cell, args.command, args.topology, args.a_data)
        fcntl.ioctl(fd, IOCTL_CONFIGURE, bytearray(buf))
    print(f"Cell {args.cell} configured:")
    print(f"  command  = 0x{args.command:08X}")
    print(f"  topology = 0x{args.topology:08X}")
    print(f"  a_data   = 0x{args.a_data:08X}")


def cmd_inject(args):
    with open_device() as fd:
        buf = struct.pack(INJECT_FMT, args.cell, args.b_data)
        fcntl.ioctl(fd, IOCTL_INJECT, bytearray(buf))
    print(f"Cell {args.cell}: injected B=0x{args.b_data:08X}")


def cmd_read(args):
    with open_device() as fd:
        buf = bytearray(struct.pack(READ_FMT, args.cell, 0, 0))
        fcntl.ioctl(fd, IOCTL_READ, buf)
        cell_idx, output, status = struct.unpack(READ_FMT, buf)
    a_arrived    = bool(status & 0x1)
    output_valid = bool(status & 0x2)
    print(f"Cell {cell_idx}:")
    print(f"  output       = 0x{output:08X} ({output})")
    print(f"  a_arrived    = {a_arrived}")
    print(f"  output_valid = {output_valid}")


def cmd_reset(args):
    with open_device() as fd:
        fcntl.ioctl(fd, IOCTL_RESET)
    print("All cells reset (command=0)")


def cmd_dump(args):
    n = args.cells
    print(f"{'Cell':>4}  {'Output':>10}  {'Status':>8}  {'a_arr':>5}  {'valid':>5}")
    print("-" * 45)
    with open_device() as fd:
        for i in range(n):
            buf = bytearray(struct.pack(READ_FMT, i, 0, 0))
            fcntl.ioctl(fd, IOCTL_READ, buf)
            _, output, status = struct.unpack(READ_FMT, buf)
            a_arr = bool(status & 0x1)
            valid = bool(status & 0x2)
            print(f"{i:>4}  0x{output:08X}  0x{status:06X}  {str(a_arr):>5}  {str(valid):>5}")


def main():
    parser = argparse.ArgumentParser(description="UniCell PCIe tool")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("info",  help="Show device info")
    sub.add_parser("reset", help="Reset all cells")

    p = sub.add_parser("configure", help="Configure a cell")
    p.add_argument("--cell",     type=lambda x: int(x,0), required=True)
    p.add_argument("--command",  type=lambda x: int(x,0), default=0)
    p.add_argument("--topology", type=lambda x: int(x,0), default=0)
    p.add_argument("--a-data",   type=lambda x: int(x,0), default=0, dest="a_data")

    p = sub.add_parser("inject", help="Inject B packet to a cell")
    p.add_argument("--cell",   type=lambda x: int(x,0), required=True)
    p.add_argument("--b-data", type=lambda x: int(x,0), default=1, dest="b_data")

    p = sub.add_parser("read", help="Read cell output and status")
    p.add_argument("--cell", type=lambda x: int(x,0), required=True)

    p = sub.add_parser("dump", help="Dump all cell outputs")
    p.add_argument("--cells", type=int, default=64)

    args = parser.parse_args()
    {
        "info":      cmd_info,
        "configure": cmd_configure,
        "inject":    cmd_inject,
        "read":      cmd_read,
        "reset":     cmd_reset,
        "dump":      cmd_dump,
    }[args.command](args)


if __name__ == "__main__":
    main()
