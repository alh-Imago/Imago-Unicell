#!/usr/bin/env python3
"""sizetable_v1.py - read the size-sweep build logs (build_sN.log) into one table and work out the cost per slice.

Reads nextpnr's "Device utilisation" block (every line "NAME: used/total pct%") and its "Max frequency" lines from each log.
Prints, per resource, the figure at each S, the cost per added slice between neighbouring sizes (the difference over the difference in S), and a straight-line
fit through all sizes: slope = cost per slice, intercept = what is left at S=0 (dispatcher + RAM side + host link).  If the per-slice cost differs between
neighbouring sizes the cost is not a straight line and the intercept must not be trusted.  Nothing is guessed: a size with no log is left out.
Usage:  python3 sizetable_v1.py [folder with the build_sN.log files, default .]
"""
import re, sys, os, glob
d = sys.argv[1] if len(sys.argv) > 1 else "."
rows = {}   # S -> {resource: used}
freq = {}   # S -> list of text
for f in glob.glob(os.path.join(d, "build_s*.log")):
    m = re.search(r"build_s(\d+)\.log$", f)
    if not m: continue
    s = int(m.group(1)); res = {}; inblock = False
    for line in open(f, errors="replace"):
        line = re.sub(r"^\s*(Info|Warning):\s*", "", line.rstrip())
        if "Device utilisation" in line or "Device utilization" in line:
            inblock = True; res = {}; continue          # keep the LAST block in the log (after placement)
        if inblock:
            mm = re.match(r"\s*([A-Za-z0-9_]+):\s*(\d+)\s*/\s*(\d+)\s+(\d+)%", line)
            if mm: res[mm.group(1)] = int(mm.group(2)); continue
            if line.strip() == "" : continue
            inblock = False
        if "Max frequency for clock" in line:
            freq.setdefault(s, []).append(line.strip())
    if res: rows[s] = res
if not rows:
    print("no build_sN.log with a Device utilisation block found in", d); sys.exit(1)
sizes = sorted(rows); names = sorted({n for r in rows.values() for n in r})
print("Resources used by size (nextpnr, last utilisation block of each log):")
print("%-18s" % "resource" + "".join("%10s" % ("S=%d" % s) for s in sizes) + "".join("%16s" % ("per slice %d-%d" % (a, b)) for a, b in zip(sizes, sizes[1:])) + "%12s%12s" % ("fit slope", "fit S=0"))
for n in names:
    ys = [rows[s].get(n) for s in sizes]
    if any(y is None for y in ys): 
        print("%-18s" % n + "".join("%10s" % ("-" if y is None else y) for y in ys)); continue
    steps = ["%16.1f" % ((ys[i+1]-ys[i]) / (sizes[i+1]-sizes[i])) for i in range(len(sizes)-1)]
    if len(sizes) >= 2:
        mx = sum(sizes)/len(sizes); my = sum(ys)/len(ys)
        sxx = sum((x-mx)**2 for x in sizes); slope = sum((x-mx)*(y-my) for x, y in zip(sizes, ys))/sxx; icpt = my - slope*mx
        tail = "%12.1f%12.0f" % (slope, icpt)
    else: tail = ""
    print("%-18s" % n + "".join("%10d" % y for y in ys) + "".join(steps) + tail)
print("\nTiming lines:")
for s in sizes:
    for t in freq.get(s, ["(no Max frequency line)"]): print("S=%-3d %s" % (s, t))
