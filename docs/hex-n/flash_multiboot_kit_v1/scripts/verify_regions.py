#!/usr/bin/env python3
"""Check a flash dump against a backup after writing one file at an offset.
usage: verify_regions.py backup.bin after.bin written_file OFFSET
prints three True/False lines: before the file unchanged, file present, after unchanged."""
import sys
a = open(sys.argv[1], 'rb').read(); b = open(sys.argv[2], 'rb').read()
p = open(sys.argv[3], 'rb').read(); o = int(sys.argv[4], 0)
print('size', len(b))
print('before unchanged:', a[:o] == b[:o])
print('file present    :', b[o:o + len(p)] == p)
print('after unchanged :', a[o + len(p):] == b[o + len(p):])
