#!/usr/bin/env python3
"""Gowin .fs (text 0/1 lines) -> flash .bin, with header patches and CRC repair.
v2 (clone of v1, v1 kept): adds --set-byte OFFSET=VALUE and repairs the first
frame CRC, which covers the header lines (all but the 0xd2 SPI-address line).
CRC layout read from apycula/bslib.py: header lines after the 3 preamble lines
(ff.., ff.., a5c3) go into the CRC except 0xd2; each frame row ends with 8
bytes (crc lo, crc hi, 6 x ff); CRC of row 0 = crc16arc(header lines + row0[:-8]).

usage: hexn_fs2bin_v2.py in.fs out.bin [--jump 0x200000] [--set-byte 0x25=0xcc]
"""
import argparse
from apycula.crc16 import make_crc16_arc

SIG = bytes.fromhex('a5c3060000000000081b')
D2 = bytes.fromhex('d200ffff')


def read_lines(path):
    rows = []
    for line in open(path):
        s = line.strip()
        if not s or s.startswith('//'):
            continue
        if set(s) - set('01') or len(s) % 8:
            raise SystemExit(f'bad line: {s[:40]!r}')
        rows.append(bytearray(int(s, 2).to_bytes(len(s) // 8, 'big')))
    return rows


def crc_of_first_row(rows):
    """returns (index_of_first_frame_row, computed_crc, stored_crc)."""
    crcdat = bytearray()
    for i, ba in enumerate(rows):
        if i < 3:
            continue                               # preamble lines
        if ba[0] != 0xd2:
            crcdat.extend(ba)
        if ba[0] == 0x3b:
            row = rows[i + 1]
            crcdat.extend(row[:-8])
            calc = make_crc16_arc()
            return i + 1, calc(crcdat), (row[-7] << 8) + row[-8]
    raise SystemExit('frame count line (0x3b) not found')


def convert(src, jump=None, set_bytes=()):
    rows = read_lines(src)
    k, c, s = crc_of_first_row(rows)
    if c != s:
        raise SystemExit(f'input first-row CRC does not verify (computed {c:04x}, stored {s:04x}); my CRC model is wrong')
    flat = bytearray().join(rows)
    if flat.find(SIG) != 0x16:
        raise SystemExit('GW2A-18 header not at 0x16')
    j = flat.find(D2, 0, 0x80) + 4
    old = int.from_bytes(flat[j:j + 4], 'big')
    if jump is not None:
        flat[j:j + 4] = jump.to_bytes(4, 'big')
    for off, val in set_bytes:
        if off >= 0x60:
            raise SystemExit('refusing to patch beyond the header')
        flat[off] = val
    # rebuild rows from the patched flat image and repair CRC of row 0
    out = []; p = 0
    for ba in rows:
        out.append(bytearray(flat[p:p + len(ba)])); p += len(ba)
    k, c, s = crc_of_first_row(out)
    if c != s:
        out[k][-8] = c & 0xff; out[k][-7] = c >> 8
    return bytearray().join(out), j, old, (c != s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--jump', type=lambda x: int(x, 0))
    ap.add_argument('--set-byte', action='append', default=[])
    a = ap.parse_args()
    sb = [tuple(int(t, 0) for t in x.split('=')) for x in a.set_byte]
    b, j, old, fixed = convert(a.src, a.jump, sb)
    open(a.dst, 'wb').write(b)
    print(f'{a.src}: {len(b)} bytes, jump field 0x{j:x}: 0x{old:08x} -> 0x{int.from_bytes(b[j:j+4],"big"):08x}; '
          f'set-bytes {a.set_byte}; first-row CRC repaired: {fixed}')


if __name__ == '__main__':
    main()
