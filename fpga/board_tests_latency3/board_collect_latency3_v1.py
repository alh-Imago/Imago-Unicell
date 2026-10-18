#!/usr/bin/env python3
"""board_collect_latency3_v1.py -- ledger #1209 (clone of the T2 v2 collector): read raw/lt3_*.bin, print the T3 two-input latency table (clocks of the 27 MHz clock; 1 clock = 37.04 ns) to board_results.txt and the screen."""
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
NS = 1000.0 / 27.0
SER = [("sA", "ONE input changes: edge -> result (includes the wait for the next 1 ms sample)"), ("sB", "ONE input changes: last sample tick -> result (the design's own part)"),
       ("dA", "BOTH inputs change, 0..2.4 ms apart: FIRST edge -> final result (includes the gap between the edges)"), ("dB", "BOTH change: last sample tick -> final result (the design's own part)")]


def parse(line):
    m = re.match(r"UCT (\S+) res=(\w) n=([0-9A-F]{8}) to=([0-9A-F]{8}) pre=([0-9A-F]{8}) p1=([0-9A-F]{8}) bad=([0-9A-F]{8}) nd=([0-9A-F]{8})", line)
    if not m:
        return None
    d = dict(name=m.group(1), res=m.group(2), n=int(m.group(3), 16), to=int(m.group(4), 16), pre=int(m.group(5), 16), p1=int(m.group(6), 16), bad=int(m.group(7), 16), nd=int(m.group(8), 16), line=line)
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
    for f in sorted(glob.glob(os.path.join(HERE, "raw", "lt3_*.bin"))):
        name = os.path.basename(f)[:-4]
        txt = open(f, "rb").read().decode("latin-1")
        lines = [ln.strip() for ln in re.split(r"[\r\n]+", txt) if ln.startswith("UCT ")]
        d = None
        for ln in reversed(lines):
            d = parse(ln)
            if d:
                break
        if not d:
            out.append(f"{name}: NO RESULT LINE ({len(txt)} bytes read). Check the jumpers pin 86 -> pin 72 and pin 53 -> pin 71, the load, and the serial port.")
            continue
        res[name] = d
        out.append(f"=== {name}: {d['res']}  events {d['n']}  time-outs {d['to']}  load checksum {d['chk']:08X}  loop-back pre-check pin 72: {d['pre']} of 16, pin 71: {d['p1']} of 16  wrong-result-after-hold {d['bad']}  both-input events {d['nd']} (one-input events {d['n']-d['nd']-d['to']})")
        if d['res'] == 'L':
            out.append("    LOOP-BACK NOT SEEN on at least one input (a count other than 16 above): no measurement was made. Check the jumpers pin 86 -> pin 72 and pin 53 -> pin 71 and that nothing else is on pins 72 or 71.")
            res[name] = d
            continue
        out.append(f"    line: {d['line']}")
        for s, what in SER:
            mn, mx, sm = d[s]
            cnt = d['nd'] if s.startswith('d') else d['n'] - d['nd'] - d['to']
            avg = sm / max(cnt, 1)
            out.append(f"    {s}  min {mn:6d} clk ({mn*NS/1000:8.3f} us)   max {mx:6d} clk ({mx*NS/1000:8.3f} us)   avg {avg:9.1f} clk   spread {mx-mn:6d} clk   {what}")
        for s in ("sB", "dB"):
            out.append(f"    {s} {'CONSTANT: min = max' if d[s][0] == d[s][1] else 'NOT constant'}")
        out.append("")
    if len(res) == 2 and "lt3_idle" in res and "lt3_busy" in res:
        i, b = res["lt3_idle"], res["lt3_busy"]
        same = all(i[s][0] == b[s][0] and i[s][1] == b[s][1] for s in ("sB", "dB"))
        out.append("idle against busy, the design's own part (B): " + ("min and max are the SAME in both" if same else "DIFFERENT: idle %s / busy %s (sB), idle %s / busy %s (dB)" % (i["sB"][:2], b["sB"][:2], i["dB"][:2], b["dB"][:2])))
        out.append("load running in the busy build (checksum not zero): " + ("yes" if b["chk"] else "NO: the load did not run"))
    open(os.path.join(HERE, "board_results.txt"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
