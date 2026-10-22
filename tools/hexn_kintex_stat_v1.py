"""Reads the yosys `stat` output (stat.txt) of a Hex-N Kintex build and prints LUT / FF / BRAM / DSP / CARRY4 counts. Handles both layouts of yosys stat ("<count> <cell>" and "<cell> <count>").
Usage: python3 tools/hexn_kintex_stat_v1.py build_hexn_kintex/*/stat.txt"""
import re, sys
def counts(text):
    d = {}
    for line in text.splitlines():
        m = re.match(r"^\s*(\d+)\s+(?:[\d.]+\s+)?([A-Z][A-Z0-9_]*)\s*$", line) or re.match(r"^\s*([A-Z][A-Z0-9_]*)\s+(\d+)\s*$", line)
        if m:
            a, b = m.groups()
            n, c = (int(a), b) if a.isdigit() else (int(b), a)
            d[c] = d.get(c, 0) + n
    return d
for f in sys.argv[1:]:
    d = counts(open(f).read()); g = lambda *ks: sum(d.get(k, 0) for k in ks)
    print("%s: LUT %d, FF %d, BRAM36 %d, BRAM18 %d, DSP %d, CARRY4 %d, LUTRAM %d" % (f, g("LUT1", "LUT2", "LUT3", "LUT4", "LUT5", "LUT6"), g("FDRE", "FDSE", "FDCE", "FDPE"), g("RAMB36E1"), g("RAMB18E1"), g("DSP48E1"), g("CARRY4"), g("RAM32M", "RAM64M", "RAM128X1D", "RAM32X1D", "RAM64X1D")))
