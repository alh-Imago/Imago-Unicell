#!/usr/bin/env python3
"""kintex_carrier_scale_report_v1.py -- read the build logs of the size/speed folders made by tools/kintex_carrier_scale_v1.py (ledger #1319) and print one table.

  python3 tools/kintex_carrier_scale_report_v1.py ~/openFPGALoader/build/demo-projects [--csv out.csv]

For every folder named k7_scale_vixen_nNNN that has a build.log it reports: the LUT and flip-flop sites nextpnr says were used, the Fmax lines of the LAST timing report
in the log (the final one, after routing), and whether nextpnr routed it (post-routing legalisation and a normal finish) and, separately, whether the log shows the bitstream step (`fpga-as ... .bit`). Nothing here is measured
on the card. A log that stops early (placer or router failed, out of memory) is reported as "NOT ROUTED" with the last "Info:" or "ERROR" line.
The utilisation line format of nextpnr-xilinx is read leniently (any "SLICE_LUTX ... used/total" or "SLICE_FFX ..." line); if none is found the cell says "?" and you
can read the log yourself.
"""
import argparse
import os
import re
import sys


def parse_log(text):
    r = {"lut": None, "lut_total": None, "ff": None, "ff_total": None, "fmax": [], "bit": False, "routed": False, "last": ""}
    for line in text.splitlines():
        m = re.search(r"(SLICE_LUTX|SLICE_LUT\w*)\S*:?\s+(\d+)\s*/\s*(\d+)", line)
        if m:
            r["lut"], r["lut_total"] = int(m.group(2)), int(m.group(3))
        m = re.search(r"(SLICE_FFX|SLICE_FF\w*)\S*:?\s+(\d+)\s*/\s*(\d+)", line)
        if m:
            r["ff"], r["ff_total"] = int(m.group(2)), int(m.group(3))
        if "fpga-as" in line and ".bit" in line:
            r["bit"] = True
        if line.startswith("Info:") or "ERROR" in line:
            r["last"] = line.strip()
    # nextpnr only gets to "post-routing legalisation" and "Program finished normally" after the router succeeded (ledger #1322: the log of a finished P&R need not
    # contain the later bitstream step, so "routed" and "bitstream written" are reported separately)
    r["routed"] = ("post-routing legalisation" in text) and ("Program finished normally" in text)
    # the last block of "Max frequency" lines is the final report
    allf = re.findall(r"Max frequency for clock\s+'([^']+)':\s*([\d.]+)\s*MHz\s*\((PASS|FAIL) at ([\d.]+) MHz\)", text)
    if allf:
        names = []
        for n, f, s, t in allf:
            if n not in names:
                names.append(n)
        final = {}
        for n, f, s, t in allf:
            final[n] = (float(f), s, float(t))
        r["fmax"] = [(n,) + final[n] for n in names]
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("demo")
    ap.add_argument("--csv", default=None)
    a = ap.parse_args()
    rows = []
    for d in sorted(os.listdir(a.demo)):
        m = re.fullmatch(r"k7_scale_vixen_n(\d+)", d)
        if not m:
            continue
        log = os.path.join(a.demo, d, "build.log")
        if not os.path.exists(log):
            rows.append((int(m.group(1)), None))
            continue
        rows.append((int(m.group(1)), parse_log(open(log, errors="replace").read())))
    if not rows:
        print("no k7_scale_vixen_nNNN folders in", a.demo)
        return 1
    out = ["N | LUT sites used (per cell) | FF sites used | Fmax (final timing report) | routed / bitstream"]
    csv = ["n,lut_used,lut_total,ff_used,ff_total,clock,fmax_mhz,target_mhz,timing,routed,bitstream_line"]
    for n, r in sorted(rows):
        if r is None:
            out.append("%d | (no build.log yet)" % n)
            continue
        lut = "?" if r["lut"] is None else "%d / %d (%.0f%%) (%.0f per cell)" % (r["lut"], r["lut_total"], 100.0 * r["lut"] / r["lut_total"], r["lut"] / float(n))
        ff = "?" if r["ff"] is None else "%d / %d" % (r["ff"], r["ff_total"])
        fm = "; ".join("%s %.2f MHz (%s at %.0f)" % (n_, f, s, t) for n_, f, s, t in r["fmax"]) or "none in the log"
        out.append("%d | %s | %s | %s | %s" % (n, lut, ff, fm, ("routed; bitstream line in log" if r["bit"] else "routed; no bitstream line in the log (check for the .bit file)") if r["routed"] else ("NOT ROUTED (last: %s)" % (r["last"][:90] or "empty log"))))
        for n_, f, s, t in (r["fmax"] or [("", 0, "", 0)]):
            csv.append("%d,%s,%s,%s,%s,%s,%.2f,%.0f,%s,%s,%s" % (n, r["lut"], r["lut_total"], r["ff"], r["ff_total"], n_, f, t, s, r["routed"], r["bit"]))
    print("\n".join(out))
    if a.csv:
        open(a.csv, "w").write("\n".join(csv) + "\n")
        print("wrote", a.csv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
