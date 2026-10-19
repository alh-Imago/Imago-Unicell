#!/usr/bin/env python3
"""decode_freeze.py LOG [CSV] -- decode "SNAP <T> <84 words>" lines (v2: visible AND hidden cell state). Layouts: k7_freeze_v2.v and tools/cell_debug_clone_v1.py."""
import json
import os
import re
import sys

here = os.path.dirname(os.path.abspath(__file__))
cells = json.load(open(os.path.join(here, "cells.json")))
text = open(sys.argv[1]).read()
csv = open(sys.argv[2], "w") if len(sys.argv) > 2 else None
if csv:
    csv.write("T_asked,t_held,frozen,cell,name,kind,word_hex,fire_nsew,data_valid,a_arrived,"
              "hid0_hex,hid1_hex,hid2_hex,hid3_hex,down_mask,up_mask,pending_ack,armed,flags_hex\n")
found = 0
for m in re.finditer(r"SNAP\s+(\S+)\s+((?:[0-9a-fA-F]{8}\s*){84})", text):
    found += 1
    T = m.group(1)
    w = [int(x, 16) for x in m.group(2).split()]
    magic, t, fl, sig, last, tl = w[:6]
    frozen = (fl >> 24) & 1
    print("T asked %s: magic %08X %s | run count t=%d | frozen=%d | results so far %d | run %d | signature %08X | last result %08X | T in force %08X"
          % (T, magic, "OK" if magic == 0x46525A32 else "WRONG", t, frozen, fl & 0xFFFF, (fl >> 16) & 0xFF, sig, last, tl))
    for c in cells:
        n = c["cell"]
        word, st = w[6 + 2 * n], w[7 + 2 * n]
        h0, h1, h2, h3 = w[32 + 4 * n: 36 + 4 * n]
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
        print("   C%-2d %-16s %-5s out %08X fire=%s dv=%d aa=%d | %s" % (n, c["name"], c["kind"], word, format((st >> 2) & 0xF, "04b"), dv, aa, hid))
        if csv:
            csv.write("%s,%d,%d,%d,%s,%s,%08X,%s,%d,%d,%08X,%08X,%08X,%08X,%d,%d,%s,%d,%s\n" % (
                T, t, frozen, n, c["name"], c["kind"], word, fire, dv, aa, h0, h1, h2, h3, down, up, format(pend, "04b"), armed, " ".join(flags)))
if not found:
    sys.exit("no SNAP lines with 84 words found in the log")
