#!/usr/bin/env python3
"""ram_scaling_v1.py - table of the memories of the S-Core pool per size, from the files ram_scaling_v1.sh wrote to /tmp (Yosys, no place-and-route).
Part 1: the RAM primitives Yosys mapped (block RAM and LUT RAM) per size, and the difference per added slice.
Part 2: every memory the design describes (Yosys '$mem_v2' cells), with the slice index collapsed (slot[3] -> slot[*]), so you see which are per slice and which are one for the whole pool:
        instances, width x depth, bits each, read/write ports, and the total bits per size.
LUT sites for LUT RAM (rough, from the primitive types): RAM32M and RAM64M 4 LUTs, RAM64X1D and RAM32X1D 2 LUTs, RAM128X1D 4 LUTs (written from knowledge of the 7-series library, not measured here)."""
import re, sys, collections
sizes = [int(a) for a in sys.argv[1:]] or [4, 8, 16]
LUTS = {"RAM32M": 4, "RAM64M": 4, "RAM64X1D": 2, "RAM32X1D": 2, "RAM128X1D": 4, "RAM256X1S": 4, "RAM64X1S": 1, "RAM32X1S": 1}
stat = {}
for s in sizes:
    d = {}
    for line in open("/tmp/ramsc_stat_%d.txt" % s):
        m = re.match(r"\s+(RAM\w+|CARRY4|DSP48E1)\s+(\d+)\s*$", line)
        if m: d[m.group(1)] = int(m.group(2))
    stat[s] = d
names = sorted({n for d in stat.values() for n in d})
print("Mapped RAM primitives (Yosys synth_xilinx before LUT mapping):")
print("%-12s" % "primitive" + "".join("%9s" % ("S=%d" % s) for s in sizes) + "".join("%16s" % ("per slice %d-%d" % (a, b)) for a, b in zip(sizes, sizes[1:])))
for n in names:
    ys = [stat[s].get(n, 0) for s in sizes]
    print("%-12s" % n + "".join("%9d" % y for y in ys) + "".join("%16.2f" % ((ys[i+1]-ys[i])/(sizes[i+1]-sizes[i])) for i in range(len(ys)-1)))
lut = [sum(LUTS.get(n, 0) * stat[s].get(n, 0) for n in names) for s in sizes]
print("%-12s" % "LUT RAM sites (rough)" + "".join("%9d" % y for y in lut) + "".join("%16.1f" % ((lut[i+1]-lut[i])/(sizes[i+1]-sizes[i])) for i in range(len(lut)-1)))
def intp(v):
    v = v.strip()
    m = re.match(r"\d+'([01]+)$", v)
    return int(m.group(1), 2) if m else int(v)
mems = {}
for s in sizes:
    cells = []; cur = None
    for line in open("/tmp/ramsc_dump_%d.txt" % s):
        line = line.strip()
        if line.startswith("cell $mem_v2"): cur = {}; cells.append(cur)
        elif line.startswith("parameter") and cur is not None:
            mm = re.match(r'parameter \\(\w+) (.*)$', line)
            if mm: cur[mm.group(1)] = mm.group(2).strip()
    grp = collections.OrderedDict()
    for c in cells:
        name = c.get("MEMID", "?").strip('"').lstrip("\\")
        name = re.sub(r"\[\d+\]", "[*]", name)
        w = intp(c["WIDTH"]); n = intp(c["SIZE"]); rp = intp(c["RD_PORTS"]); wp = intp(c["WR_PORTS"])
        key = (name, w, n, rp, wp)
        grp[key] = grp.get(key, 0) + 1
    mems[s] = grp
keys = sorted({k for g in mems.values() for k in g}, key=lambda k: (-k[1]*k[2], k[0]))
print("\nEvery memory in the design ('x' = instances at each size; bits = width x depth each; r/w = read and write ports):")
print("%-62s %6s %6s %7s %3s %3s" % ("name (slice index collapsed)", "width", "depth", "bits", "r", "w") + "".join("%9s" % ("x S=%d" % s) for s in sizes))
for k in keys:
    print("%-62s %6d %6d %7d %3d %3d" % (k[0][:62], k[1], k[2], k[1]*k[2], k[3], k[4]) + "".join("%9d" % mems[s].get(k, 0) for s in sizes))
print("%-62s %6s %6s %7s %3s %3s" % ("TOTAL bits", "", "", "", "", "") + "".join("%9d" % sum(k[1]*k[2]*v for k, v in mems[s].items()) for s in sizes))
