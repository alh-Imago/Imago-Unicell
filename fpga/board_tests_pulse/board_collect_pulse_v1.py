#!/usr/bin/env python3
"""board_collect_pulse_v1.py -- ledger #1224: turns the T4 result lines in raw/<label>_pls_*.bin into board_results_<label>.txt (pulse width -> how many pulses the design caught).
Usage: python3 board_collect_pulse_v1.py [label]"""
import os
import re
import sys

WIDTHS = [54000, 27000, 20250, 13500, 6750, 2700, 1350, 540, 270, 135, 54, 27]
CLK_NS = 1000.0 / 27.0
here = os.path.dirname(os.path.abspath(__file__))
label = sys.argv[1] if len(sys.argv) > 1 else "run"
out = []
for name in ("pls_idle", "pls_busy"):
    p = os.path.join(here, "raw", f"{label}_{name}.bin")
    txt = open(p, "rb").read().decode("latin-1") if os.path.exists(p) else ""
    line = next((l for l in txt.splitlines() if l.startswith("UCP " + name)), None)
    if not line:
        out.append(f"=== {name}: NO RESULT LINE ({len(txt)} bytes read)\n")
        continue
    m = re.match(r"UCP (\S+) res=(\w) np=([0-9A-F]{8}) stale=([0-9A-F]{8}) pre=([0-9A-F]{8})", line)
    np_, stale, pre = int(m.group(3), 16), int(m.group(4), 16), int(m.group(5), 16)
    out.append(f"=== {name}: {m.group(2)}  pulses per width {np_}  stale (result not zero before a pulse) {stale}  loop-back pre-check {pre} of 16")
    out.append(f"    line: {line}")
    out.append(f"    {'width':>9} {'clocks':>7} {'caught':>7} {'of':>5} {'caught %':>9} {'expected % (W/27000)':>21}")
    for i, w in enumerate(WIDTHS):
        c = int(re.search(r" w%d=([0-9A-F]{8})" % i, line).group(1), 16)
        us = w * CLK_NS / 1000.0
        exp = min(100.0, 100.0 * w / 27000.0)
        out.append(f"    {us:7.2f} us {w:7d} {c:7d} {np_:5d} {100.0 * c / np_:8.1f}% {exp:20.1f}%")
    out.append("")
txt = "\n".join(out)
open(os.path.join(here, f"board_results_{label}.txt"), "w").write(f"label: {label}\n" + txt)
print(txt)
