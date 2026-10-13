#!/usr/bin/env python3
"""board_collect_v2.py -- ledger #1167: clone of board_collect.py for the GROUP bitstreams. v1 looked for ./*.fs and ./<name>.json next to itself, so in the grouped
layout (groups/group_A.fs, groups/group_A.json) it found nothing and printed "0 of 0 passed" although the board had answered (#1166 run). This one reads the test list and the
simulated lines from groups/group_*.json. A line is judged complete when it has the full simulated length; lines cut by the start/end of the capture or by the board's
rotating selector are ignored. Standard library only.  usage: python3 board_collect_v2.py [raw_dir] [out_prefix]"""
import csv, glob, json, os, re, sys, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "raw")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "board_results")
strip = lambda t: re.sub(r"last=[0-9A-F]+", "", t)       # 'last' is the cycle the last word arrived: depends on when the capture started
rows, out = [], [f"UniCell on-board group run  {datetime.datetime.now():%Y-%m-%d %H:%M:%S}", "=" * 100]
for js in sorted(glob.glob(os.path.join(HERE, "groups", "group_*.json"))):
    meta = json.load(open(js)); g = meta["group"]
    binp = os.path.join(RAW, f"group_{g}.bin")
    raw = open(binp, "rb").read() if os.path.exists(binp) else b""
    text = raw.decode("latin1")
    for name in meta["tests"]:
        sim = meta["sim_lines"][name]
        pat = r"UCT " + re.escape(name) + r" res=[PF] n=[0-9A-F]{4} e=[0-9A-F]{4} bad=[0-9A-F]{4} to=\d last=[0-9A-F]{8} sig=[0-9A-F]{8} w=[0-9A-F,]*"
        mine = re.findall(pat, text)
        full = [l for l in mine if len(l) == len(sim)]
        if not raw: status, line = "NOREPORT", ""
        elif not full: status, line = "NOREPORT", ""
        else:
            line = max(set(full), key=full.count)
            same = sum(1 for l in full if strip(l) == strip(sim))
            status = "PASS" if " res=P " in line + " " and strip(line) == strip(sim) else ("FAIL" if " res=F " in line else "PASS(line differs from simulation)")
        out += [f"{name:<22} {status}", f"   group    : {g}", f"   board    : {line or '(nothing complete received)'}", f"   simulated: {sim}",
                f"   capture  : {len(raw)} bytes, {len(full)} complete lines of this test ({sum(1 for l in full if strip(l) == strip(sim))} equal to the simulation apart from 'last')",
                f"   built    : group {g} {meta.get('lut4', '?')} LUT4, {meta.get('dff', '?')} flip-flops, Fmax est. {meta.get('fmax_mhz', '?')} MHz", ""]
        rows.append([name, status, line, sim, meta.get("lut4", ""), meta.get("dff", ""), meta.get("fmax_mhz", "")]); print(f"[{name}] {status}")
n = sum(1 for r in rows if r[1].startswith("PASS"))
out += ["=" * 100, f"SUMMARY: {n} of {len(rows)} passed"]
open(OUT + ".txt", "w").write("\n".join(out) + "\n")
with open(OUT + ".csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["test", "status", "board_line", "simulated_line", "lut4", "dff", "fmax_mhz"]); w.writerows(rows)
print(f"SUMMARY: {n} of {len(rows)} passed -> {OUT}.txt")
