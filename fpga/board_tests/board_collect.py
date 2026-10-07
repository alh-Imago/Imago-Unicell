#!/usr/bin/env python3
"""board_collect.py -- reads raw/<name>.bin (what the board printed) and raw/<name>.loader.txt written by run_all.sh and builds board_results.txt / .csv. Standard library only."""
import csv, glob, json, os, re, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
strip = lambda t: re.sub(r"last=[0-9A-F]+", "", t)
rows, out = [], [f"UniCell on-board test run  {datetime.datetime.now():%Y-%m-%d %H:%M:%S}", "=" * 100]
for fs in sorted(glob.glob(os.path.join(HERE, "*.fs"))):
    name = os.path.splitext(os.path.basename(fs))[0]
    meta = json.load(open(fs[:-3] + ".json")) if os.path.exists(fs[:-3] + ".json") else {}
    sim = meta.get("sim_line", "")
    raw = open(os.path.join(HERE, "raw", name + ".bin"), "rb").read() if os.path.exists(os.path.join(HERE, "raw", name + ".bin")) else b""
    text = raw.decode("ascii", "replace")
    mine = [m.group(0) for m in re.finditer(r"UCT " + re.escape(name) + r" res=[PF] n=[0-9A-F]{4} e=[0-9A-F]{4} bad=[0-9A-F]{4} to=\d last=[0-9A-F]{8} sig=[0-9A-F]{8} w=[0-9A-F,]*", text)]
    others = sorted(set(re.findall(r"UCT (\w+) res=", text)) - {name})
    rc = open(os.path.join(HERE, "raw", name + ".rc")).read().strip() if os.path.exists(os.path.join(HERE, "raw", name + ".rc")) else "?"
    loader = open(os.path.join(HERE, "raw", name + ".loader.txt"), errors="replace").read() if os.path.exists(os.path.join(HERE, "raw", name + ".loader.txt")) else ""
    if rc != "0":
        status, line = "NOLOAD", ""
    elif mine:
        # the most common complete line (a line cut by the start or end of the capture is ignored)
        full = [l for l in mine if sim and len(l) >= len(sim) - 1] or mine
        line = max(set(full), key=full.count)
        status = "PASS" if " res=P " in line + " " else "FAIL"
        if status == "PASS" and sim and strip(line) != strip(sim):
            status = "PASS(line differs from simulation)"
    else:
        status, line = ("OLDDESIGN" if others else "NOREPORT"), ""
    print(f"[{name}] {status}")
    out += [f"{name:<22} {status}", f"   what     : {meta.get('what', '')}", f"   board    : {line or '(nothing received)'}", f"   simulated: {sim}",
            f"   capture  : {len(raw)} bytes, {len(mine)} lines of this test, other tests seen: {others or 'none'}", f"   built    : {meta.get('lut4', '?')} LUT4, {meta.get('dff', '?')} flip-flops, Fmax {meta.get('fmax_mhz', '?')} MHz"]
    if not status.startswith("PASS"):
        out.append("   loader output: " + loader.replace("\n", " | ")[-600:])
    out.append("")
    rows.append([name, status, line, sim, meta.get("lut4", ""), meta.get("dff", ""), meta.get("fmax_mhz", "")])
n = sum(1 for r in rows if r[1].startswith("PASS"))
out += ["=" * 100, f"SUMMARY: {n} of {len(rows)} passed"]
open(os.path.join(HERE, "board_results.txt"), "w").write("\n".join(out) + "\n")
with open(os.path.join(HERE, "board_results.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["test", "status", "board_line", "simulated_line", "lut4", "dff", "fmax_mhz"]); w.writerows(rows)
print("\n".join(out[-2:]))
