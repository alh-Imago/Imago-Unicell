#!/usr/bin/env python3
"""Ring for finding which bit of header byte 0x25 makes a RECONFIG_N reload follow the jump (4 Nov 2026, Alan 21:23 'yes we can go there').

Known (measured 4 Nov): 0xcc + the jump field -> the reload goes to the jump target; 0xae (apycula's value) -> it reloads offset 0. 0xae = 1010 1110, 0xcc = 1100 1100;
they differ in bits 6, 5 and 1 (0x62). Which bit does it is NOT known.

One flash write tests up to three flag values in a chain. A reload from a slot whose flag does NOT enable the jump goes back to offset 0 (slot 0, the 7x7), so the chain tells you
the first variant that fails and cannot test the ones behind it. Slots (1 MiB each, 7 MiB for three variants):
  0: 7x7 (90894555)  flag 0xcc (known good) -> 1       1: 6x6 (8F532C4A)  flag V1 -> 2       2: 5x5 (3A7FD506) flag 0xcc -> 3
  3: 6x6             flag V2                -> 4       4: 5x5             flag 0xcc  -> 5       5: 6x6            flag V3 -> 6       6: 5x5 flag 0xcc -> 0
Hop with `openFPGALoader -b tangnano20k -r` (or a pin 9 tap) from a power-up. If every flag enables the jump the ids read 7x7, 6x6, 5x5, 6x6, 5x5, 6x6, 5x5, 7x7.
If V1 fails: 7x7, 6x6, 7x7 ...  If V2 fails: 7x7, 6x6, 5x5, 6x6, 7x7 ...  If V3 fails: 7x7, 6x6, 5x5, 6x6, 5x5, 6x6, 7x7 ...
(The variant is the flag of the 6x6 image just BEFORE the id that falls back to 7x7.)

usage: hexn_flagtest_ring_v1.py out.bin SEVEN.fs SIX.fs FIVE.fs --flags 0xee,0x8c,0xce
Writes nothing to a board. The first-row CRC is repaired per slot (tools/hexn_fs2bin_v2.py)."""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_fs2bin_v2 as T

FLAG_BYTE = 0x25; SLOT = 0x100000; GOOD = 0xcc


def plan(flags):
    """list of (image kind 7/6/5, flag, next slot) for len(flags) variants"""
    n = len(flags); sl = []
    sl.append((7, GOOD, 1))
    for i, f in enumerate(flags):
        t = 1 + 2 * i
        sl.append((6, f, t + 1))                                  # test slot (6x6, variant flag)
        sl.append((5, GOOD, (t + 2) % (2 * n + 1)))               # good slot after it (5x5)
    return sl


def build(seven, six, five, flags):
    src = {7: seven, 6: six, 5: five}; sl = plan(flags); out = bytearray(b'\xff' * (SLOT * len(sl))); info = []
    for k, (kind, flag, nxt) in enumerate(sl):
        b, j, old, fixed = T.convert(src[kind], nxt * SLOT, [(FLAG_BYTE, flag)])
        rows = T.read_lines(src[kind]); orows = []; p = 0
        for r in rows: orows.append(bytearray(b[p:p + len(r)])); p += len(r)
        _, c, s = T.crc_of_first_row(orows)
        if c != s: raise SystemExit('slot %d: first-row CRC does not verify after patching' % k)
        if len(b) > SLOT: raise SystemExit('slot %d too big' % k)
        out[k * SLOT:k * SLOT + len(b)] = b; info.append((k, kind, flag, nxt, len(b)))
    return out, info


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('dst'); ap.add_argument('seven'); ap.add_argument('six'); ap.add_argument('five')
    ap.add_argument('--flags', default='0xee,0x8c,0xce'); a = ap.parse_args()
    flags = [int(x, 0) for x in a.flags.split(',')]
    if not 1 <= len(flags) <= 3: raise SystemExit('1 to 3 flags (8 MiB flash, 1 MiB slots)')
    img, info = build(a.seven, a.six, a.five, flags); open(a.dst, 'wb').write(img)
    for k, kind, flag, nxt, ln in info: print('slot %d at 0x%07x: %dx%d  flag 0x%02x  jump -> slot %d  (%d bytes)' % (k, k * SLOT, kind, kind, flag, nxt, ln))
    print('%s: %d bytes (dump this many to verify)' % (a.dst, len(img)))


if __name__ == '__main__':
    main()
