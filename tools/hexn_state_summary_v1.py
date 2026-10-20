"""Summarise the output files of hexn_state_sweep_v1.sh (or any dNmMliveL.txt files): one row per delay / memory / live setting."""
import glob, os, re, sys
d = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/hexn_sweep")
rows = []
for f in glob.glob(os.path.join(d, "d*_m*_live*.txt")):
    m = re.match(r"d(\d+)_m(\d+)_live(\d)", os.path.basename(f))
    v = [l.split() for l in open(f) if re.match(r"\s+\d+\s+\d+\s+\d+\s*$", l)]
    if not v: continue
    l = sum(int(x[1]) for x in v) / len(v); r = sum(int(x[2]) for x in v) / len(v)
    rows.append((int(m[1]), int(m[2]), int(m[3]), len(v), l, r, sum(int(x[1]) > int(x[2]) for x in v)))
print(f"{'delay':>5} {'mem bits':>8} {'live':>4} {'seeds':>5} {'learned':>8} {'random-best':>11} {'beat random':>11}")
for r in sorted(rows): print(f"{r[0]:>5} {r[1]:>8} {'yes' if r[2] else 'no':>4} {r[3]:>5} {r[4]:>8.0f} {r[5]:>11.0f} {r[6]:>8}/{r[3]}")
