#!/usr/bin/env python3
"""Gowin .fs (text of 0/1 lines) -> flash .bin, with optional jump-address patch.

The jump address is the 4 bytes after the 'd2 00 ff ff' command in the header
(measured on the hoglet67 multiboot release, 4 Nov). apycula's bslib excludes the
0xd2 line from its CRC, so patching it does not need a checksum fix (read from
apycula source; still to be proven on the board).

usage: hexn_fs2bin_v1.py in.fs out.bin [--jump 0x200000] [--info]
"""
import sys, argparse

SIG = bytes.fromhex('a5c3060000000000081b')      # sync + GW2A-18 id, header offset 0x16
D2 = bytes.fromhex('d200ffff')


def fs_to_bin(path):
    out = bytearray()
    with open(path) as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith('//'):
                continue
            if set(s) - set('01') or len(s) % 8:
                raise SystemExit(f'bad line in {path}: {s[:40]!r}')
            out += int(s, 2).to_bytes(len(s) // 8, 'big')
    return bytearray(out)


def find_jump(b):
    i = b.find(SIG)
    if i != 0x16:
        raise SystemExit(f'GW2A-18 header not at 0x16 (found {i})')
    j = b.find(D2, 0, 0x80)
    if j < 0:
        raise SystemExit('d2 00 ff ff command not found in header')
    return j + 4


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--jump', type=lambda x: int(x, 0), default=None)
    a = ap.parse_args()
    b = fs_to_bin(a.src)
    k = find_jump(b)
    old = int.from_bytes(b[k:k + 4], 'big')
    if a.jump is not None:
        if a.jump % 0x1000:
            raise SystemExit('jump address must be 4 KiB aligned')
        b[k:k + 4] = a.jump.to_bytes(4, 'big')
    open(a.dst, 'wb').write(b)
    new = int.from_bytes(b[k:k + 4], 'big')
    print(f'{a.src}: {len(b)} bytes, jump field at 0x{k:x}: 0x{old:08x} -> 0x{new:08x}')


if __name__ == '__main__':
    main()
