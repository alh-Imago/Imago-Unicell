#!/usr/bin/env python3
"""decode_freeze.py LOG [CSV] -- decode "SNAP <T> <32 words>" lines from the OpenOCD scripts of this kit.
Header and cell layout are in k7_freeze_v1.v. Prints a table; with CSV given, appends one row per cell per snapshot."""
import json
import os
import re
import sys

here = os.path.dirname(os.path.abspath(__file__))
cells = json.load(open(os.path.join(here, "cells.json")))
text = open(sys.argv[1]).read()
csv = open(sys.argv[2], "w") if len(sys.argv) > 2 else None
if csv:
    csv.write("T_asked,t_held,frozen,cell,name,kind,word_hex,word_dec,fire_nsew,data_valid,a_arrived\n")
found = 0
for m in re.finditer(r"SNAP\s+(\S+)\s+((?:[0-9a-fA-F]{8}\s*){32})", text):
    found += 1
    T = m.group(1)
    w = [int(x, 16) for x in m.group(2).split()]
    magic, t, fl, sig, last, tl = w[:6]
    frozen = (fl >> 24) & 1
    print("T asked %s: magic %08X %s | run count t=%d | frozen=%d | results so far %d | run %d | signature %08X | last result %08X | T in force %08X"
          % (T, magic, "OK" if magic == 0x46525A31 else "WRONG", t, frozen, fl & 0xFFFF, (fl >> 16) & 0xFF, sig, last, tl))
    for c in cells:
        n = c["cell"]
        word, st = w[6 + 2 * n], w[7 + 2 * n]
        fire = format((st >> 2) & 0xF, "04b")
        dv, aa = (st >> 1) & 1, st & 1
        sw = word - (1 << 32) if word & 0x80000000 else word
        print("   C%-2d %-18s %-5s word %08X (%d)  fire[nsew]=%s  data_valid=%d  a_arrived=%d" % (n, c["name"], c["kind"], word, sw, fire, dv, aa))
        if csv:
            csv.write("%s,%d,%d,%d,%s,%s,%08X,%d,%s,%d,%d\n" % (T, t, frozen, n, c["name"], c["kind"], word, sw, fire, dv, aa))
if not found:
    sys.exit("no SNAP lines with 32 words found in the log")
