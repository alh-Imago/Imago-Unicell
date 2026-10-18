#!/usr/bin/env python3
"""board_collect_c1_v2.py -- ledger #1217 (clone of v1): read raw/<LABEL>_c1_*.bin (the Tang's result line) and, if present, raw/<LABEL>_c1_*.esp32 (the ESP32's status lines), and print the C1 table to board_results_<LABEL>.txt.
New in v2: rising and falling time-outs apart (tor/tof), events that could not be timed (inv), the number of timed edges (nr/nf) for correct averages, and the ESP32's cumulative interrupt counts compared with the edges the Tang sent.
Usage: python3 board_collect_c1_v2.py LABEL"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NS = 1000.0 / 27.0
LABEL = sys.argv[1] if len(sys.argv) > 1 else "run"
BUCK = ["< 2 us", "2-5 us", "5-10 us", "10-20 us", "20-50 us", ">= 50 us"]
X8 = "([0-9A-F]{8})"


def parse(line):
    m = re.match(r"UCC (\S+) res=(\w) n=%s tor=%s tof=%s inv=%s pre=%s" % ((X8,) * 5), line)
    if not m:
        return None
    d = dict(name=m.group(1), res=m.group(2), n=int(m.group(3), 16), tor=int(m.group(4), 16), tof=int(m.group(5), 16), inv=int(m.group(6), 16), pre=int(m.group(7), 16), line=line)
    for s in ("r", "f"):
        mm = re.search(r" %s=%s,%s,%s n%s=%s" % (s, X8, X8, X8, s, X8), line)
        if not mm:
            return None
        d[s] = tuple(int(mm.group(i), 16) for i in (1, 2, 3))
        d["n" + s] = int(mm.group(4), 16)
    mm = re.search(r" h=([0-9A-F,]+)", line)
    if not mm:
        return None
    d["h"] = [int(x, 16) for x in mm.group(1).split(",")]
    return d


def us(c):
    return c * NS / 1000.0


def esp32(path):
    """cumulative totals from the ESP32 status lines: (first evT, last evT, first stormT, last stormT, max storm per second, lines)"""
    if not os.path.exists(path):
        return None
    txt = open(path, "rb").read().decode("latin-1")
    rows = re.findall(r"C1 loop=(\d) .*?ev=(\d+) storm=(\d+) evT=(\d+) stormT=(\d+)", txt)
    if not rows:
        return "NOLINES"
    return dict(loop=rows[-1][0], ev0=int(rows[0][3]) - int(rows[0][1]), ev1=int(rows[-1][3]), st0=int(rows[0][4]) - int(rows[0][2]), st1=int(rows[-1][4]),
                peak_storm=max(int(r[2]) for r in rows), lines=len(rows))


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
        out.append(f"=== {name}: {d['res']}  timed events {d['nr'] + d['nf']} of {d['n'] * 2}  unanswered: rising {d['tor']}, falling {d['tof']}  not timeable after an unanswered edge: {d['inv']}  loop-back pre-check {d['pre']} of 16")
        if d['res'] == 'L':
            out.append("    ANSWER NOT SEEN: the ESP32 did not follow the slow test edges; nothing was measured. Check Tang 86 -> IO16, IO17 -> Tang 72, that the sketch is running, and that no T2/T3 jumper is still on 72.")
            continue
        out.append(f"    line: {d['line']}")
        for s, what in (("r", "rising edge -> answer"), ("f", "falling edge -> answer")):
            mn, mx, sm = d[s]
            cnt = d["n" + s]
            avg = sm / max(cnt, 1)
            out.append(f"    {what:24s} {cnt:5d} timed   min {mn:6d} clk ({us(mn):8.2f} us)   max {mx:6d} clk ({us(mx):8.2f} us)   avg {avg:8.1f} clk ({us(avg):7.2f} us)   spread {mx-mn:6d} clk ({us(mx-mn):8.2f} us)")
        tot = sum(d["h"])
        out.append("    all timed events by answer time:  " + "   ".join(f"{b}: {c} ({100.0*c/max(tot,1):.1f}%)" for b, c in zip(BUCK, d["h"])))
        e = esp32(os.path.join(HERE, "raw", f"{LABEL}_{name}.esp32"))
        if e is None:
            out.append("    (no ESP32 log for this build: run with ESPPORT=/dev/ttyUSBn to record the ESP32's interrupt counts)")
        elif e == "NOLINES":
            out.append("    ESP32 log present but no 'C1 ... evT=' lines in it: the sketch must be unicell_c1_interrupts_v2 and the Serial Monitor closed.")
        else:
            sent = d["n"] * 2 + 16
            seen = e["ev1"] - e["ev0"]
            out.append(f"    ESP32 counted {seen} edge interrupts on IO16 during the log ({e['lines']} lines); the Tang sent {sent} (= {d['n']*2} timed + 16 slow pre-check edges); difference {seen - sent:+d} (a few extra edges are normal while the Tang loads)")
            out.append(f"    ESP32 counted {e['st1'] - e['st0']} storm interrupts on IO21 (peak {e['peak_storm']} in one second; expected about 15,650 a second for the c1_storm build, 0 for c1_quiet)")
            if d['tor'] + d['tof'] > 0:
                out.append(f"    The Tang saw {d['tor'] + d['tof']} unanswered edge(s). If the ESP32 count above is short of the Tang's by about that many, the interrupts were MISSED; if it matches, they ran but the answer was late or wrong.")
        out.append("    (the 2-flip-flop input synchroniser in the Tang adds up to 2 clocks)")
        out.append("")
    open(os.path.join(HERE, f"board_results_{LABEL}.txt"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
