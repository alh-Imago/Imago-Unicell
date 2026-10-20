"""Hex-N ladder comparison (new file). Paired comparison of two arms on the SAME seeds: python3 tools/hexn_ladder_compare_v1.py BASE_FILES... -- NEW_FILES...
Each file holds lines 'seed learned template-rule'.  Accept rule, fixed in advance (20 Oct 2026): the new arm is REAL only if mean paired difference / standard error >= 2 AND wins > losses.
Ties (|difference| < 0.005) count as neither.  Anything else is reported as 'no difference shown'."""
import math, re, sys
def load(files):
    d = {}
    for f in files:
        for line in open(f):
            m = re.match(r"\s*(\d+)\s+([0-9.]+)\s+[0-9.]+\s*$", line)
            if m: d[int(m.group(1))] = float(m.group(2))
    return d
a = sys.argv[1:]; i = a.index("--"); base, new = load(a[:i]), load(a[i + 1:])
seeds = sorted(set(base) & set(new)); diff = [new[s] - base[s] for s in seeds]; n = len(diff)
mean = sum(diff) / n; sd = math.sqrt(sum((x - mean) ** 2 for x in diff) / (n - 1)) if n > 1 else float("nan"); se = sd / math.sqrt(n)
w = sum(x > 0.005 for x in diff); l = sum(x < -0.005 for x in diff)
bm = sum(base[s] for s in seeds) / n; nm = sum(new[s] for s in seeds) / n
print(f"seeds {n}: base mean {bm:.3f}, new mean {nm:.3f}, paired difference {mean:+.3f} (SE {se:.3f}, ratio {mean / se if se else float('nan'):+.2f}); new wins {w}, loses {l}, ties {n - w - l}")
print("VERDICT:", "REAL (accept)" if se and mean / se >= 2 and w > l else "no difference shown (do not accept)")
