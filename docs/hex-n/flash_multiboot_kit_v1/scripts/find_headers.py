#!/usr/bin/env python3
"""List Gowin GW2A-18 bitstream headers in a flash image and show the header bytes that
differ between them (this is how the jump field at 0x38-0x3b was found).
usage: find_headers.py image.bin"""
import sys
d = open(sys.argv[1], 'rb').read()
pat = bytes.fromhex('a5c3060000000000081b')     # sync + GW2A-18 id, sits at header offset 0x16
at = []; i = -1
while True:
    i = d.find(pat, i + 1)
    if i < 0: break
    at.append(i - 0x16)
print('bitstreams start at', [hex(a) for a in at])
hdr = [d[a:a + 0x60] for a in at]
for a, h in zip(at, hdr): print(hex(a), h.hex())
for k in range(0x60):
    v = [h[k] for h in hdr]
    if len(set(v)) > 1: print('differs at header byte', hex(k), [hex(x) for x in v])
