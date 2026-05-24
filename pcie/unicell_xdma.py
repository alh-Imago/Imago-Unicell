#!/usr/bin/env python3
"""
unicell_xdma.py — UniCell PCIe tool via XDMA BAR0

Uses /dev/xdma0_user (Xilinx XDMA kernel driver) to talk to the
UniCell array over PCIe. No custom kernel driver needed — just the
standard xdma.ko from Xilinx/dma_ip_drivers.

BAR0 layout (CELL_STRIDE=32 bytes per cell):
  cell_base = cell_index * 32
  +0x00  [W]  CMD_WRITE   opcode[31:24] + payload[23:0]
               cell targeted via address bits [20:5]
  +0x04  [W]  DATA_WRITE  bus_addr[31:16] + data[15:0]
  +0x08  [R]  OUT_HI      out_addr[31:16] + out_data[15:0]
  +0x0C  [R]  OUT_LO      out_data[31:0]
  +0x10  [W]  STATUS_LO   armed_count[31:16] + out_valid[0]
  +0x14  [R]  STATUS_HI   cycle_count[31:0]
  +0x10  [W]  RESET       write any value

Install xdma driver:
  git clone https://github.com/Xilinx/dma_ip_drivers
  cd dma_ip_drivers/XDMA/linux-kernel
  make && sudo insmod xdma/xdma.ko poll_mode=0
  ls /dev/xdma0_user  # should appear when card enumerates

Usage:
  sudo python3 unicell_xdma.py info
  sudo python3 unicell_xdma.py configure --cell 0 --opcode 4 --payload 0xa5000800
  sudo python3 unicell_xdma.py inject --bus-addr 0 --data 42
  sudo python3 unicell_xdma.py read
  sudo python3 unicell_xdma.py reset
  sudo python3 unicell_xdma.py dump --cells 10
"""

import os
import sys
import mmap
import struct
import argparse

DEVICE      = "/dev/xdma0_user"
BAR0_SIZE   = 4096        # 4KB BAR0
CELL_STRIDE = 32          # bytes per cell

# Register offsets within BAR0 (not per-cell — global registers)
OFF_CMD     = 0x00
OFF_DATA    = 0x04
OFF_OUT_HI  = 0x08
OFF_OUT_LO  = 0x0C
OFF_STATUS  = 0x10
OFF_CYCLES  = 0x14
OFF_RESET   = 0x10

# Opcodes
CMD_NOP             = 0x00
CMD_DATA_WRITE      = 0x01
CMD_SET_INPUT_ADDR  = 0x02
CMD_SET_OUTPUT_ADDR = 0x03
CMD_RECONFIGURE     = 0x04
CMD_FREEZE          = 0x05
CMD_RELEASE         = 0x06
CMD_PING            = 0x09
CMD_LATCH_IN_ON     = 0x0A
CMD_LATCH_IN_OFF    = 0x0B
CMD_MEM_CALL        = 0x0C
CMD_REARM           = 0x0D
CMD_SET_LOGICAL     = 0x0E

CMD_NAMES = {
    0x00: 'NOP', 0x01: 'DATA_WRITE', 0x02: 'SET_INPUT_ADDR',
    0x03: 'SET_OUTPUT_ADDR', 0x04: 'RECONFIGURE', 0x05: 'FREEZE',
    0x06: 'RELEASE', 0x09: 'PING', 0x0A: 'LATCH_IN_ON',
    0x0B: 'LATCH_IN_OFF', 0x0C: 'MEM_CALL', 0x0D: 'REARM',
    0x0E: 'SET_LOGICAL',
}


class UniCellXDMA:
    def __init__(self, device=DEVICE):
        self.device = device
        self.fd = None
        self.mm = None

    def open(self):
        try:
            self.fd = os.open(self.device, os.O_RDWR | os.O_SYNC)
            self.mm = mmap.mmap(self.fd, BAR0_SIZE,
                                mmap.MAP_SHARED,
                                mmap.PROT_READ | mmap.PROT_WRITE)
        except PermissionError:
            print(f"Permission denied — try: sudo python3 {os.path.basename(__file__)}")
            raise
        except FileNotFoundError:
            print(f"Device {self.device} not found.")
            print("Is xdma.ko loaded? Is the PCIe card enumerated?")
            print("Check: lspci | grep Xilinx")
            print("       lsmod | grep xdma")
            raise

    def close(self):
        if self.mm:
            self.mm.close()
        if self.fd is not None:
            os.close(self.fd)

    def _read32(self, offset):
        self.mm.seek(offset)
        return struct.unpack('<I', self.mm.read(4))[0]

    def _write32(self, offset, value):
        self.mm.seek(offset)
        self.mm.write(struct.pack('<I', value & 0xFFFFFFFF))

    def cell_offset(self, cell_index):
        return cell_index * CELL_STRIDE

    def send_command(self, cell_index, opcode, payload=0):
        """Send a command to a cell.
        opcode:  8-bit command opcode
        payload: 24-bit payload (auth[23:16] + config[15:0])
        The cell is addressed via its position in BAR0.
        """
        # CMD_WRITE register: opcode in [31:24], payload in [23:0]
        cmd_word = ((opcode & 0xFF) << 24) | (payload & 0xFFFFFF)
        # Cell address is encoded in the AXI address bits [20:5]
        # Bridge extracts: cpu_addr = aw_addr[20:5] = cell_index
        # So we write to: cell_offset + OFF_CMD
        offset = self.cell_offset(cell_index) + OFF_CMD
        self._write32(offset, cmd_word)

    def inject_data(self, bus_addr, data):
        """Inject a data packet onto the UniCell bus.
        bus_addr: 16-bit logical address
        data:     16-bit data value
        """
        data_word = ((bus_addr & 0xFFFF) << 16) | (data & 0xFFFF)
        self._write32(OFF_DATA, data_word)

    def read_output(self):
        """Read the last cell output (addr + data)."""
        hi = self._read32(OFF_OUT_HI)
        lo = self._read32(OFF_OUT_LO)
        out_addr = (hi >> 16) & 0xFFFF
        out_data = lo
        return out_addr, out_data

    def read_status(self):
        """Read armed_count, out_valid, cycle_count."""
        st   = self._read32(OFF_STATUS)
        cyc  = self._read32(OFF_CYCLES)
        armed     = (st >> 16) & 0xFFFF
        out_valid = st & 0x1
        return armed, out_valid, cyc

    def reset(self):
        """Reset the UniCell array."""
        self._write32(OFF_RESET, 0x1)

    def configure_cell(self, cell_index, topology=0, auth=0,
                       start_flag=True, one_shot=False,
                       latch_in=False, loop_back=False):
        """Reconfigure a cell — sends CMD_RECONFIGURE."""
        cfg  = topology & 0x3FF
        cfg |= (1 if start_flag else 0) << 11
        cfg |= (1 if latch_in   else 0) << 15
        cfg |= (1 if one_shot   else 0) << 19
        cfg |= (1 if loop_back  else 0) << 20
        payload = ((auth & 0xFF) << 16) | (cfg & 0xFFFF)
        self.send_command(cell_index, CMD_RECONFIGURE, payload)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()


# ── CLI ──────────────────────────────────────────────────────────────────────

def cmd_info(args):
    with UniCellXDMA() as u:
        armed, out_valid, cycles = u.read_status()
        out_addr, out_data = u.read_output()
    print(f"UniCell XDMA Interface")
    print(f"  Device:      {DEVICE}")
    print(f"  BAR0 size:   {BAR0_SIZE} bytes")
    print(f"  Armed cells: {armed}")
    print(f"  Cycles:      {cycles}")
    print(f"  Last output: addr=0x{out_addr:04X} data=0x{out_data:08X}")
    print(f"  Out valid:   {bool(out_valid)}")


def cmd_configure(args):
    with UniCellXDMA() as u:
        u.configure_cell(args.cell,
                         topology=args.topology,
                         auth=args.auth)
    print(f"Cell {args.cell} configured: topo={args.topology:#05x} auth={args.auth:#04x}")


def cmd_inject(args):
    with UniCellXDMA() as u:
        u.inject_data(args.bus_addr, args.data)
    print(f"Injected: bus_addr=0x{args.bus_addr:04X} data=0x{args.data:08X}")


def cmd_read(args):
    with UniCellXDMA() as u:
        out_addr, out_data = u.read_output()
        armed, out_valid, cycles = u.read_status()
    print(f"Last output:")
    print(f"  addr  = 0x{out_addr:04X}")
    print(f"  data  = 0x{out_data:08X} ({out_data})")
    print(f"  valid = {bool(out_valid)}")
    print(f"  armed = {armed} cells")
    print(f"  cycles = {cycles}")


def cmd_reset(args):
    with UniCellXDMA() as u:
        u.reset()
    print("Array reset sent")


def cmd_dump(args):
    with UniCellXDMA() as u:
        armed, out_valid, cycles = u.read_status()
        out_addr, out_data = u.read_output()
    print(f"Armed cells: {armed}  Cycles: {cycles}")
    print(f"Last fire:   addr=0x{out_addr:04X}  data=0x{out_data:08X}  valid={bool(out_valid)}")


def main():
    parser = argparse.ArgumentParser(description="UniCell XDMA PCIe tool")
    parser.add_argument("--device", default=DEVICE)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("info",  help="Show device status")
    sub.add_parser("reset", help="Reset UniCell array")
    sub.add_parser("read",  help="Read last cell output")
    sub.add_parser("dump",  help="Dump status")

    p = sub.add_parser("configure", help="Configure a cell")
    p.add_argument("--cell",     type=lambda x: int(x,0), required=True)
    p.add_argument("--topology", type=lambda x: int(x,0), default=0)
    p.add_argument("--auth",     type=lambda x: int(x,0), default=0xA5)

    p = sub.add_parser("inject", help="Inject data onto bus")
    p.add_argument("--bus-addr", type=lambda x: int(x,0), required=True, dest="bus_addr")
    p.add_argument("--data",     type=lambda x: int(x,0), required=True)

    args = parser.parse_args()
    if hasattr(args, 'device'):
        DEVICE = args.device

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
