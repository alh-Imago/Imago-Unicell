#!/usr/bin/env python3
"""check_runner_repeat.py FOLDER LOG [VECTORS] -- summarise test C (runner_repeat.sh): the same vector run N times on an ICM runner design.
Per exit it lists the distinct (word count, signature, clock of the last word) outcomes; all N must be identical. With VECTORS the words are also compared with the VM's answer (expected.json).
The run number must go up by one at every start, so each read is a new run."""
import json
import os
import re
import sys
from collections import Counter

folder, log = sys.argv[1], sys.argv[2]
vec = os.path.basename(sys.argv[3]) if len(sys.argv) > 3 else None
d = json.load(open(os.path.join(folder, "design.json")))
lay, depth, nw = d["layout"], d["depth"], d["nw"]
text = open(log).read()
snaps = [(m.group(1), [int(x, 16) for x in m.group(2).split()]) for m in re.finditer(r"SNAP\s+(\S+)\s+((?:[0-9a-fA-F]{8}\s*)+)", text)]
runs = [(l, w) for l, w in snaps if l.startswith("run_")]
if not runs:
    sys.exit("no run_ SNAP lines in the log (see %s)" % log)
bad = 0
if any(len(w) != nw for _, w in runs) or any(w[0] != 0x52554E31 for _, w in runs):
    sys.exit("wrong scan length or magic: the right runner bitstream is not loaded (expected RUN1, %d words)" % nw)
fpd = d.get("fingerprint")
if fpd:
    fps = Counter("%08x" % w[lay["ebuf"]] for _, w in runs)
    print("design fingerprint on the card %s; this folder's design_map.json %s -> %s" % (dict(fps), fpd, "SAME DESIGN" if set(fps) == {fpd} else "DIFFERENT"))
    bad += set(fps) != {fpd}
rn = [w[3] & 0xFF for _, w in runs]
steps = Counter((b - a) & 0xFF for a, b in zip(rn, rn[1:]))
print("%d runs; run number goes up by 1 each time: %s (steps: %s)" % (len(runs), "yes" if set(steps) <= {1} else "NO", dict(steps)))
bad += not set(steps) <= {1}
exp = None
ef = os.path.join(folder, "expected.json")
if vec and os.path.exists(ef):
    exp = json.load(open(ef)).get(vec)
for j, x in enumerate(d["exits"]):
    b = lay["xst"] + 3 * j
    c = Counter()
    wrong = 0
    for _, w in runs:
        cnt, sig, last = w[b], w[b + 1], w[b + 2]
        c[(cnt, sig, last)] += 1
        if exp is not None:
            want = [v & 0xFFFFFFFF for v in exp["exits"][x["name"]]["words"]]
            got = w[lay["xbuf"] + j * depth: lay["xbuf"] + j * depth + min(cnt, depth)]
            wrong += not (cnt == len(want) and got == want[:depth])
    one = len(c) == 1
    print("exit %-12s %s" % (x["name"], "IDENTICAL in all runs" if one else "%d different outcomes" % len(c)))
    for (cnt, sig, last), n in c.most_common():
        print("   %5d x  %d word(s), signature %08X, last word at clock %d" % (n, cnt, sig, last))
    if exp is not None:
        print("   words equal the VM's answer in %d of %d runs" % (len(runs) - wrong, len(runs)))
        bad += wrong > 0
    bad += not one
print("\nOVERALL: %s" % ("PASS" if not bad else "FAIL"))
sys.exit(1 if bad else 0)
