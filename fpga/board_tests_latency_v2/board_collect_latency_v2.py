#!/usr/bin/env python3
"""board_collect_latency_v2.py -- ledger #1207 (clone of v1; reads pre=, res=L means the pin 86 -> pin 72 jumper was not seen and nothing was measured): read raw/lat_*.bin, print the T2 latency table (clocks of the 27 MHz clock; 1 clock = 37.04 ns) to board_results.txt and the screen."""
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
NS = 1000.0 / 27.0
SER = [("rA", "rising edge -> result (includes the wait for the next 1 ms sample)"), ("rB", "rising: last sample tick -> result (the design's own part)"),
       ("fA", "falling edge -> result (includes the wait for the next 1 ms sample)"), ("fB", "falling: last sample tick -> result (the design's own part)")]


def parse(line):
    m = re.match(r"UCT (\S+) res=(\w) n=([0-9A-F]{8}) to=([0-9A-F]{8}) pre=([0-9A-F]{8})", line)
    if not m:
        return None
    d = dict(name=m.group(1), res=m.group(2), n=int(m.group(3), 16), to=int(m.group(4), 16), pre=int(m.group(5), 16), line=line)
    for s, _ in SER:
        mm = re.search(s + r"=([0-9A-F]{8}),([0-9A-F]{8}),([0-9A-F]{8})", line)
        if not mm:
            return None
        d[s] = tuple(int(x, 16) for x in mm.groups())
    mm = re.search(r"chk=([0-9A-F]{8})", line)
    d["chk"] = int(mm.group(1), 16) if mm else None
    return d


def main():
    out = []
    res = {}
    for f in sorted(glob.glob(os.path.join(HERE, "raw", "lat_*.bin"))):
        name = os.path.basename(f)[:-4]
        txt = open(f, "rb").read().decode("latin-1")
        lines = [ln.strip() for ln in re.split(r"[\r\n]+", txt) if ln.startswith("UCT ")]
        d = None
        for ln in reversed(lines):
            d = parse(ln)
            if d:
                break
        if not d:
            out.append(f"{name}: NO RESULT LINE ({len(txt)} bytes read). Check the jumper pin 86 -> pin 72, the load, and the serial port.")
            continue
        res[name] = d
        out.append(f"=== {name}: {d['res']}  events {d['n']}  time-outs {d['to']}  load checksum {d['chk']:08X}  loop-back pre-check {d['pre']} of 16")
        if d['res'] == 'L':
            out.append("    LOOP-BACK NOT SEEN: pin 72 did not follow pin 86; no measurement was made. Check the jumper (pin 86 -> pin 72) and that nothing else is on pin 72.")
            res[name] = d
            continue
        out.append(f"    line: {d['line']}")
        for s, what in SER:
            mn, mx, sm = d[s]
            avg = sm / max(d['n'], 1)
            out.append(f"    {s}  min {mn:6d} clk ({mn*NS/1000:8.3f} us)   max {mx:6d} clk ({mx*NS/1000:8.3f} us)   avg {avg:9.1f} clk   spread {mx-mn:6d} clk   {what}")
        for s in ("rB", "fB"):
            out.append(f"    {s} {'CONSTANT: min = max' if d[s][0] == d[s][1] else 'NOT constant'}")
        out.append("")
    if len(res) == 2 and "lat_idle" in res and "lat_busy" in res:
        i, b = res["lat_idle"], res["lat_busy"]
        same = all(i[s][0] == b[s][0] and i[s][1] == b[s][1] for s in ("rB", "fB"))
        out.append("idle against busy, the design's own part (B): " + ("min and max are the SAME in both" if same else "DIFFERENT: idle %s / busy %s (rB), idle %s / busy %s (fB)" % (i["rB"][:2], b["rB"][:2], i["fB"][:2], b["fB"][:2])))
        out.append("load running in the busy build (checksum not zero): " + ("yes" if b["chk"] else "NO: the load did not run"))
    open(os.path.join(HERE, "board_results.txt"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
