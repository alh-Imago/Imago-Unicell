#!/usr/bin/env python3
"""Show which 64 KiB blocks of a flash dump hold data (blank flash reads as 0xff).
usage: flash_map.py dump.bin"""
import sys
d = open(sys.argv[1], 'rb').read()
B = 65536; runs = []; s = None
for i in range(0, len(d), B):
    used = d[i:i + B] != b'\xff' * B
    if used and s is None: s = i
    if not used and s is not None: runs.append((s, i)); s = None
if s is not None: runs.append((s, len(d)))
print('size', len(d))
for a, b in runs: print(hex(a), '-', hex(b), (b - a) // 1024, 'KiB')
