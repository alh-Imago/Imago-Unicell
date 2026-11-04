#!/usr/bin/env python3
"""Build a multi-image flash file (a ring of Gowin bitstreams) from .fs files.

Each image goes in its own slot (default 1 MiB) starting at flash offset 0; image k
carries the multiboot header byte 0x25 = 0xcc and a jump address = slot k+1 (the last
jumps back to slot 0). A RECONFIG_N pulse then steps to the next image. Slot 0 is
what the chip loads at power-up.

Measured on the Tang Nano 20K (4 Nov 2026, ledger rows 09:35-10:20): byte 0x25 = 0xcc
plus the jump field makes a RECONFIG_N tap load the jump target; 0xae (what apycula
writes) does not. Which bit of 0x25 does it is NOT known; 0xcc is the value from the
hoglet67 multiboot builds and from our own A2 test. The first-row CRC is repaired
(tools/hexn_fs2bin_v2.py). Nothing here writes to a board.

usage: hexn_flashimg_v1.py out.bin a.fs b.fs [c.fs ...] [--slot 0x100000] [--flag 0xcc]
       then: openFPGALoader -b tangnano20k -f out.bin      (writes offset 0: replaces what is there)
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_fs2bin_v2 as T

FLAG_BYTE = 0x25


def build(fs_files, slot=0x100000, flag=0xcc):
    if slot % 0x1000 or slot <= 0:
        raise SystemExit('slot must be a positive multiple of 4 KiB')
    n = len(fs_files)
    out = bytearray(b'\xff' * (slot * n))
    info = []
    for k, f in enumerate(fs_files):
        nxt = ((k + 1) % n) * slot
        b, j, old, fixed = T.convert(f, nxt, [(FLAG_BYTE, flag)])
        if len(b) > slot:
            raise SystemExit(f'{f}: {len(b)} bytes does not fit a slot of {slot}')
        # verify: re-split the patched image into the source's rows and check the first-row CRC
        rows = T.read_lines(f); out_rows = []; p = 0
        for r in rows:
            out_rows.append(bytearray(b[p:p + len(r)])); p += len(r)
        _, c, s = T.crc_of_first_row(out_rows)
        if c != s:
            raise SystemExit(f'{f}: first-row CRC does not verify after patching')
        out[k * slot:k * slot + len(b)] = b
        info.append((f, k * slot, len(b), nxt))
    return out, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dst'); ap.add_argument('fs', nargs='+')
    ap.add_argument('--slot', type=lambda x: int(x, 0), default=0x100000)
    ap.add_argument('--flag', type=lambda x: int(x, 0), default=0xcc)
    a = ap.parse_args()
    img, info = build(a.fs, a.slot, a.flag)
    open(a.dst, 'wb').write(img)
    for f, base, ln, nxt in info:
        print(f'slot at 0x{base:07x}: {os.path.basename(f)} {ln} bytes, jump -> 0x{nxt:07x}, flag 0x{a.flag:02x}')
    print(f'{a.dst}: {len(img)} bytes')


if __name__ == '__main__':
    main()
