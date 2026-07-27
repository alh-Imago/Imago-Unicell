#!/usr/bin/env python3
"""
unicell_pcie_test.py -- drive the UniCell fabric over PCIe BAR0 from Linux.

Replays the known-good configure+inject sequence from icm64_readstate.tcl
(the silicon-proven JTAG baseline) over PCIe instead, then reads back the
fabric's output registers.

    sudo ./unicell_pcie_test.py              # full sequence
    sudo ./unicell_pcie_test.py --probe      # register readback check only
    sudo ./unicell_pcie_test.py --dump       # read all four registers
    sudo ./unicell_pcie_test.py -s 09:00.0   # different slot

WHY THIS EXISTS RATHER THAN THE WINDOWS TOOL
--------------------------------------------
Intel's Windows driver never enables memory decode (Command register bit 1),
so every BAR access returns 0xFFFFFFFF regardless of what the FPGA is doing.
That produced days of false negatives during the 2026-07 bring-up. Under
Linux nothing claims the device either, but we can set the bit ourselves --
which this script does automatically, and re-checks, because the Command
register resets on every boot.

WHY ctypes AND NOT mmap SLICING
------------------------------
Python's mmap slice assignment is a memcpy and may split a 4-byte store into
four single-byte writes. pcie_unicell_bridge.v ignores byte enables entirely
(it assigns the whole register unconditionally), so each byte write clobbers
the full register and only the last survives -- writing 0xDEADBEEF lands as
0xDE000000. ctypes on a c_uint32 array issues genuine 32-bit stores.
See the byteenable note at the bottom of this file.
"""

import argparse
import ctypes
import mmap
import os
import subprocess
import sys

# Register map -- pcie_unicell_bridge.v. Indices are WORDS (ctypes array),
# so index N is byte offset N*4.
CMD_DATA, CMD_BUS, STATUS_ADDR_VALID, STATUS_DATA = 0, 1, 2, 3

# The known-good sequence: (cmd_data, cmd_bus, label).
# Host convention is CMD_DATA first, then CMD_BUS -- the CMD_BUS write is
# what fires cpu_valid and consumes the staged data.
SEQUENCE = [
    (0x00000000, 0x05280008, "ARRAY_RESET"),
    (0x00A50000, 0x00000007, "BOOT_COMMIT"),
    (0x00000000, 0x00000018, "SET_TARGET->cell0"),
    (0x00000200, 0x05280003, "SET_OUTPUT_ADDR"),
    (0x5282082C, 0x05280004, "RECONFIGURE(PASS_B)"),
    (0x00000000, 0x00000018, "SET_TARGET->cell0"),
    (0x00000004, 0x05280022, "ROUTING(east)"),
    (0x00000000, 0x00000018, "SET_TARGET->cell0"),
    (0x00000001, 0x05280023, "TRANSIT(route-only)"),
    (0x00000000, 0x00000018, "SET_TARGET->cell0"),
    (0x00000000, 0x05280012, "SWAP_AB"),
    (0x000000AA, 0x00000001, "INJECT(addr0,val0xAA)"),
]

EXPECT_ADDR = 0x0200
EXPECT_DATA = 0x000000AA


def enable_decode(slot):
    """Set memory decode + bus master, and verify it stuck."""
    try:
        subprocess.run(["setpci", "-s", slot, "COMMAND=0x0006"],
                       check=True, capture_output=True)
        out = subprocess.run(["setpci", "-s", slot, "04.w"],
                             check=True, capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("setpci not found -- install pciutils")
    except subprocess.CalledProcessError as e:
        sys.exit("setpci failed: %s" % (e.stderr.decode().strip() or e))

    cmd = int(out.stdout.strip(), 16)
    if not (cmd & 0x2):
        sys.exit("memory decode did not stick (COMMAND=0x%04X) -- "
                 "reads would return 0xFFFFFFFF" % cmd)
    print("memory decode enabled (COMMAND=0x%04X)" % cmd)


def open_bar(slot):
    path = "/sys/bus/pci/devices/0000:%s/resource0" % slot
    if not os.path.exists(path):
        sys.exit("%s not found -- is the card present and configured?" % path)
    fd = os.open(path, os.O_RDWR | os.O_SYNC)
    m = mmap.mmap(fd, 4096)
    return (ctypes.c_uint32 * 1024).from_buffer(m)


def all_ones(*vals):
    return all(v == 0xFFFFFFFF for v in vals)


def probe(bar):
    """Write/readback both command registers. Proves the write path."""
    print("\n-- register readback --")
    ok = True
    for idx, name, val in ((CMD_DATA, "CMD_DATA", 0xDEADBEEF),
                           (CMD_BUS,  "CMD_BUS",  0xCAFEBABE)):
        bar[idx] = val
        got = bar[idx]
        flag = "ok" if got == val else "MISMATCH"
        if got != val:
            ok = False
        print("  %-9s wrote %08X  read %08X  %s" % (name, val, got, flag))

    if not ok:
        print("\n  If reads are FFFFFFFF: endpoint isn't answering -- check")
        print("  memory decode, and that the application interface is out of")
        print("  reset (pld_core_ready tie in pcie_hip_wrapper.v).")
        print("  If only the top byte survived (DEADBEEF -> DE000000): the")
        print("  write was split into byte writes; that's a host-side bug,")
        print("  not the FPGA.")
    return ok


def dump(bar):
    print("\n-- all registers --")
    for idx, name in ((CMD_DATA, "CMD_DATA"), (CMD_BUS, "CMD_BUS"),
                      (STATUS_ADDR_VALID, "STATUS_ADDR_VALID"),
                      (STATUS_DATA, "STATUS_DATA")):
        print("  0x%X  %-18s = %08X" % (idx * 4, name, bar[idx]))


def run_sequence(bar, verbose=True):
    # Clear any stale sticky result first -- a write to STATUS_ADDR_VALID
    # clears the latch (the STATUS registers are otherwise read-only), so we
    # know anything we read afterwards came from THIS run.
    bar[STATUS_ADDR_VALID] = 0

    print("\n-- replaying icm64_readstate.tcl sequence --")
    for data, bus, name in SEQUENCE:
        bar[CMD_DATA] = data
        bar[CMD_BUS] = bus
        if verbose:
            print("  %-22s data=%08X bus=%08X" % (name, data, bus))

    sav = bar[STATUS_ADDR_VALID]
    sd = bar[STATUS_DATA]

    print("\n-- result --")
    print("  STATUS_ADDR_VALID = %08X" % sav)
    print("  STATUS_DATA       = %08X" % sd)

    if all_ones(sav, sd):
        print("\n  FFFFFFFF on both -- the endpoint is not answering at all.")
        print("  This is NOT a fabric result. Check memory decode first, then")
        print("  whether the application interface is out of reset.")
        return False

    # STATUS_ADDR_VALID packs as {15'h0, out_valid, out_addr[15:0]}
    valid = (sav >> 16) & 1
    addr = sav & 0xFFFF

    print("    out_valid = %d" % valid)
    print("    out_addr  = %04X" % addr)
    print("    out_data  = %08X" % sd)

    if not valid:
        print("\n  Fabric did not fire, or the result was not latched.")
        print("  out_valid upstream is combinational and only one CLK cycle")
        print("  wide -- if the sticky capture in pcie_unicell_bridge.v is")
        print("  missing from this build, a polled read can never catch it.")
        return False

    ok = True
    if addr != EXPECT_ADDR:
        print("\n  out_addr %04X != expected %04X (from SET_OUTPUT_ADDR)"
              % (addr, EXPECT_ADDR))
        ok = False
    if (sd & 0xFF) != EXPECT_DATA:
        print("  out_data %08X does not carry expected %02X"
              % (sd, EXPECT_DATA))
        ok = False

    print("\n  %s" % ("PASS -- fabric fired and the result matches"
                      if ok else "fired, but values differ from expected"))
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-s", "--slot", default="08:00.0",
                    help="PCI slot (default 08:00.0)")
    ap.add_argument("--probe", action="store_true",
                    help="register readback check only")
    ap.add_argument("--dump", action="store_true",
                    help="read all four registers and exit")
    ap.add_argument("--no-enable", action="store_true",
                    help="skip the memory-decode enable step")
    ap.add_argument("-q", "--quiet", action="store_true",
                    help="don't print each sequence step")
    args = ap.parse_args()

    if os.geteuid() != 0:
        sys.exit("needs root -- run with sudo")

    if not args.no_enable:
        enable_decode(args.slot)

    bar = open_bar(args.slot)

    if args.dump:
        dump(bar)
        return

    if not probe(bar):
        sys.exit(1)

    if args.probe:
        return

    sys.exit(0 if run_sequence(bar, verbose=not args.quiet) else 1)


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# KNOWN LATENT ISSUE, not exercised by this script
#
# pcie_unicell_bridge.v ignores avs_byteenable -- it does
#   cmd_data_staged <= avs_writedata
# unconditionally. Harmless for the full-width 32-bit accesses used here, but
# any partial write silently clobbers the whole register instead of updating
# part of it. Worth fixing in RTL; until then, only issue aligned 32-bit
# accesses to this BAR.
# ---------------------------------------------------------------------------
