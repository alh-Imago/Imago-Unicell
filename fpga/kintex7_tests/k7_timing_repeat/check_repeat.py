#!/usr/bin/env python3
"""check_repeat.py LOG -- summarise tests A and B of the k7_timing_repeat kit (layout of the k7_freeze_load v3 scan: see ../k7_freeze_load/decode_freeze.py).

Word 0 magic 46525A33 | 1 count t | 2 flags (results so far [7:0], k [15:8], run number [23:16], frozen bit 24) | 3 signature | 4 last result word | 5 T in force | 6 clock of the last result.
It checks that
  * every scan carries the magic (the right bitstream is loaded);
  * the run number goes up by exactly one at every restart (so each read is a NEW run, not the same one read again);
  * all free runs give one identical (results, signature, last word, clock of the last result) tuple; it is compared with the Tang tree's figures (#1251) but a different value there is reported, not hidden;
  * (test B) after freeze + release the tuple equals the free run's.
Exit status 0 only if everything holds."""
import re
import sys
from collections import Counter

TANG = (6, 0x7FEF5298, 0x7FFFFEAA, 1562)          # results, signature, last word, clock of the last result: ledger #1251 (Tang figures, measured on this card in #1251)
text = open(sys.argv[1]).read()
rows = []
for m in re.finditer(r"SNAP\s+(\S+)\s+((?:[0-9a-fA-F]{8}\s*){86})", text):
    w = [int(x, 16) for x in m.group(2).split()]
    rows.append((m.group(1), w))
if not rows:
    sys.exit("no 86-word SNAP lines in the log: is the k7_freeze_load v3 bitstream loaded, and did openocd run? (see the log)")


def tup(w):
    return (w[2] & 0xFF, w[3], w[4], w[6])


def show(t):
    return "results %d  signature %08X  last word %08X  last result at clock %d" % t


bad = 0
magic_bad = [l for l, w in rows if w[0] != 0x46525A33]
print("scans read: %d; wrong magic: %d" % (len(rows), len(magic_bad)))
if magic_bad:
    print("  FAIL: the right bitstream is not loaded (expected 46525A33). First bad label: %s" % magic_bad[0])
    sys.exit(1)

free = [(l, w) for l, w in rows if l.startswith("free_")]
if free:
    runs = [(w[2] >> 16) & 0xFF for _, w in free]
    steps = Counter(((b - a) & 0xFF) for a, b in zip(runs, runs[1:]))
    print("\nTEST A  %d free runs" % len(free))
    print("  run number goes up by 1 each time: %s (steps seen: %s)" % ("yes" if set(steps) <= {1} else "NO", dict(steps)))
    bad += not set(steps) <= {1}
    c = Counter(tup(w) for _, w in free)
    for t, n in c.most_common():
        print("  %5d x  %s" % (n, show(t)))
    one = len(c) == 1
    print("  all identical: %s" % ("YES" if one else "NO (%d different outcomes)" % len(c)))
    bad += not one
    top = c.most_common(1)[0][0]
    print("  equals the Tang figures of #1251 (%s): %s" % (show(TANG), "YES" if top == TANG else "NO -- differs; report it as it stands"))
    base = top
else:
    b = [w for l, w in rows if l == "base"]
    base = tup(b[0]) if b else None

frz = [(l, w) for l, w in rows if l.startswith("frz")]
rel = [(l, w) for l, w in rows if l.startswith("rel")]
if rel:
    print("\nTEST B  %d freeze-and-release cycles (baseline = %s)" % (len(rel), show(base) if base else "none read"))
    by = {}
    for l, w in rel:
        T = re.match(r"rel(\d+)_", l).group(1)
        by.setdefault(T, []).append(tup(w))
    for T, v in by.items():
        c = Counter(v)
        same = len(c) == 1 and (base is None or list(c)[0] == base)
        print("  freeze at %-5s x%-3d: %s%s" % (T, len(v), "all equal the free run" if same else "DIFFERENT: ", "" if same else "; ".join("%d x %s" % (n, show(t)) for t, n in c.most_common())))
        bad += not same
    notfrozen = [l for l, w in frz if not ((w[2] >> 24) & 1)]
    print("  scans taken at the freeze that were not frozen: %d (%s)" % (len(notfrozen), "expected 0 for counts below the run's end (about 1562); counts past the end finish before they freeze" if notfrozen else "ok"))
    held = Counter(((w[1]), re.match(r"frz(\d+)_", l).group(1)) for l, w in frz)
    tt = {}
    for (t, T), n in held.items():
        tt.setdefault(T, []).append(t)
    print("  count held at each freeze (must be one value per T): " + "; ".join("T=%s -> %s" % (T, sorted(set(v))) for T, v in tt.items()))
print("\nOVERALL: %s" % ("PASS" if not bad else "FAIL"))
sys.exit(1 if bad else 0)
