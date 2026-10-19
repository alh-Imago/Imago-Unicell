#!/usr/bin/env python3
"""decode_freeze.py LOG [CSV] -- decode "SNAP <label> <86 words>" lines (v3). Layout: tools/kintex_freeze_pack_v3.py."""
import json
import os
import re
import sys

here = os.path.dirname(os.path.abspath(__file__))
cells = json.load(open(os.path.join(here, "cells.json")))
text = open(sys.argv[1]).read()
csv = open(sys.argv[2], "w") if len(sys.argv) > 2 else None
if csv:
    csv.write("T_asked,t_held,frozen,cell,name,kind,word_hex,fire_nsew,data_valid,a_arrived,hid0_hex,hid1_hex,hid2_hex,hid3_hex,down_mask,up_mask,pending_ack,armed,flags\n")
found = 0
for m in re.finditer(r"SNAP\s+(\S+)\s+((?:[0-9a-fA-F]{8}\s*){86})", text):
    found += 1
    T = m.group(1)
    w = [int(x, 16) for x in m.group(2).split()]
    magic, t, fl, sig, last, tl, lastt = w[:7]
    frozen = (fl >> 24) & 1
    print("%s: magic %08X %s | count t=%d | frozen=%d | results so far %d | k=%d | run %d | signature %08X | last result %08X at count %d | T in force %08X"
          % (T, magic, "OK" if magic == 0x46525A33 else "WRONG", t, frozen, fl & 0xFF, (fl >> 8) & 0xFF, (fl >> 16) & 0xFF, sig, last, lastt, tl))
    for c in cells:
        n = c["cell"]
        word, st = w[8 + 2 * n], w[9 + 2 * n]
        h0, h1, h2, h3 = w[34 + 4 * n: 38 + 4 * n]
        fire = format((st >> 2) & 0xF, "04b")
        dv, aa = (st >> 1) & 1, st & 1
        if c["kind"] == "adder":
            down, up, sdown, pend = h2 & 63, (h2 >> 6) & 63, (h2 >> 12) & 63, (h2 >> 18) & 15
            flags = [x for x, b in (("a_arrived", 0), ("data_valid", 1), ("subtract", 2), ("join", 3), ("second_output", 4), ("carry_held", 5),
                                      ("delivering_carry", 6), ("phase1_offered", 7), ("armed", 8), ("prog_done", 9)) if (h3 >> b) & 1]
            armed = (h3 >> 8) & 1
            hid = "a_reg %08X  out_buffer %08X  down %02d up %02d 2nd_down %02d pend %s  [%s]" % (h0, h1, down, up, sdown, format(pend, "04b"), " ".join(flags))
        else:
            down, up, pend = h3 & 63, (h3 >> 6) & 63, (h3 >> 12) & 15
            flags = [x for x, b in (("data_valid", 16), ("fixed", 17), ("armed", 18), ("prog_done", 19)) if (h3 >> b) & 1]
            armed = (h3 >> 18) & 1
            hid = "data_reg %08X  init %08X  addon %05X  down %02d up %02d pend %s  [%s]" % (h0, h1, h2 & 0xFFFFF, down, up, format(pend, "04b"), " ".join(flags))
        print("   C%-2d %-16s %-5s out %08X fire=%s dv=%d aa=%d | %s" % (n, c["name"], c["kind"], word, fire, dv, aa, hid))
        if csv:
            csv.write("%s,%d,%d,%d,%s,%s,%08X,%s,%d,%d,%08X,%08X,%08X,%08X,%d,%d,%s,%d,%s\n" % (
                T, t, frozen, n, c["name"], c["kind"], word, fire, dv, aa, h0, h1, h2, h3, down, up, format(pend, "04b"), armed, " ".join(flags)))
if not found:
    sys.exit("no SNAP lines with 86 words found in the log")
