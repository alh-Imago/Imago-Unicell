#!/usr/bin/env python3
"""board_collect_c1_v1.py -- ledger #1211: read raw/<LABEL>_c1_*.bin and print the C1 table (ESP32 interrupt answer time, counted by the Tang in 27 MHz clocks; 1 clock = 37.04 ns) to board_results_<LABEL>.txt.
Usage: python3 board_collect_c1_v1.py LABEL"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NS = 1000.0 / 27.0
LABEL = sys.argv[1] if len(sys.argv) > 1 else "run"
BUCK = ["< 2 us", "2-5 us", "5-10 us", "10-20 us", "20-50 us", ">= 50 us"]


def parse(line):
    m = re.match(r"UCC (\S+) res=(\w) n=([0-9A-F]{8}) to=([0-9A-F]{8}) pre=([0-9A-F]{8})", line)
    if not m:
        return None
    d = dict(name=m.group(1), res=m.group(2), n=int(m.group(3), 16), to=int(m.group(4), 16), pre=int(m.group(5), 16), line=line)
    for s in ("r", "f"):
        mm = re.search(r" %s=([0-9A-F]{8}),([0-9A-F]{8}),([0-9A-F]{8})" % s, line)
        if not mm:
            return None
        d[s] = tuple(int(x, 16) for x in mm.groups())
    mm = re.search(r" h=([0-9A-F,]+)", line)
    if not mm:
        return None
    d["h"] = [int(x, 16) for x in mm.group(1).split(",")]
    return d


def us(c):
    return c * NS / 1000.0


def main():
    out = [f"ESP32 state label: {LABEL}"]
    for f in sorted(glob.glob(os.path.join(HERE, "raw", f"{LABEL}_c1_*.bin"))):
        name = os.path.basename(f)[len(LABEL) + 1:-4]
        txt = open(f, "rb").read().decode("latin-1")
        lines = [ln.strip() for ln in re.split(r"[\r\n]+", txt) if ln.startswith("UCC ")]
        d = None
        for ln in reversed(lines):
            d = parse(ln)
            if d:
                break
        if not d:
            out.append(f"{name}: NO RESULT LINE ({len(txt)} bytes read). Check the three wires, that the ESP32 sketch is running, and the serial port.")
            continue
        out.append(f"=== {name}: {d['res']}  events {d['n'] * 2} (rising + falling)  time-outs {d['to']}  loop-back pre-check {d['pre']} of 16")
        if d['res'] == 'L':
            out.append("    ANSWER NOT SEEN: the ESP32 did not follow the slow test edges; nothing was measured. Check Tang 86 -> IO16, IO17 -> Tang 72, that the sketch is running, and that no T2/T3 jumper is still on 72.")
            continue
        out.append(f"    line: {d['line']}")
        for s, what in (("r", "rising edge -> answer"), ("f", "falling edge -> answer")):
            mn, mx, sm = d[s]
            avg = sm / max(d['n'] - 0, 1)
            out.append(f"    {what:24s} min {mn:6d} clk ({us(mn):8.2f} us)   max {mx:6d} clk ({us(mx):8.2f} us)   avg {avg:8.1f} clk ({us(avg):7.2f} us)   spread {mx-mn:6d} clk ({us(mx-mn):8.2f} us)")
        tot = sum(d["h"])
        out.append("    all events by answer time:  " + "   ".join(f"{b}: {c} ({100.0*c/max(tot,1):.1f}%)" for b, c in zip(BUCK, d["h"])))
        out.append("    (the 2-flip-flop input synchroniser in the Tang adds up to 2 clocks; time-outs are not in the table above)")
        out.append("")
    open(os.path.join(HERE, f"board_results_{LABEL}.txt"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
