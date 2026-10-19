#!/usr/bin/env python3
"""check_saveload.py LOG -- checks the S / D / L / F snapshots written by freeze_saveload_test.sh and prints PASS or FAIL for each statement.
S = saved (frozen at the first count), D = after the disturbance (a different run), L = after loading S back (still frozen), F = after the release."""
import re
import sys

text = open(sys.argv[1]).read()
snap = {}
for m in re.finditer(r"SNAP\s+(\S+)\s+((?:[0-9a-fA-F]{8}\s*){86})", text):
    snap[m.group(1)] = [int(x, 16) for x in m.group(2).split()]
need = ["S", "D", "L", "F"]
if not all(k in snap for k in need):
    sys.exit("missing snapshots: %s" % [k for k in need if k not in snap])
S, D, L, F = (snap[k] for k in need)
ok_all = True


def check(cond, what):
    global ok_all
    ok_all = ok_all and cond
    print("%s  %s" % ("PASS" if cond else "FAIL", what))


check(all(x[0] == 0x46525A33 for x in (S, D, L, F)), "magic FRZ3 in all four reads (the right bitstream is loaded)")
check(((S[2] >> 24) & 1) == 1 and ((D[2] >> 24) & 1) == 1, "S and D were taken frozen")
check(S[34:] != D[34:], "the disturbance changed the cells' hidden state (D differs from S)")
check(L[8:] == S[8:], "after the load, all 78 cell words (visible and hidden) equal the saved ones")
check(L[1] == S[1] and (L[2] & 0xFFFF) == (S[2] & 0xFFFF) and L[3] == S[3] and L[4] == S[4] and L[6] == S[6],
      "after the load, the driver state (count %d, k and results so far, signature, last word, last clock) equals the saved one" % S[1])
check(((L[2] >> 24) & 1) == 1, "frozen after the load")
check((F[2] & 0xFF) == 6 and F[3] == 0x7FEF5298 and F[4] == 0x7FFFFEAA,
      "after the release: 6 results, signature %08X (Tang 7FEF5298), last word %08X (Tang 7FFFFEAA)" % (F[3], F[4]))
check(F[6] == 1562, "the last result arrived at count %d (the Tang's line says 0x61A = 1562)" % F[6])
print("\nOVERALL: %s" % ("PASS" if ok_all else "FAIL"))
