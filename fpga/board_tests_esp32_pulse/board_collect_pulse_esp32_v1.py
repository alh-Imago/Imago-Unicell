#!/usr/bin/env python3
"""board_collect_pulse_esp32_v1.py -- ledger #1227: turns the P1 result lines in raw/<label>_pe_*.bin into board_results_<label>.txt (pulse width -> how many pulses the ESP32 handler noticed), with the ESP32's own run count from raw/<label>_pe_*.esp32.
Usage: python3 board_collect_pulse_esp32_v1.py [label]"""
import os
import re
import sys

WIDTHS = [2700, 1350, 540, 270, 135, 54, 27, 16, 8, 4, 2, 1]
CLK_NS = 1000.0 / 27.0
here = os.path.dirname(os.path.abspath(__file__))
label = sys.argv[1] if len(sys.argv) > 1 else "run"
out = []
for name in ("pe_quiet", "pe_storm"):
    p = os.path.join(here, "raw", f"{label}_{name}.bin")
    txt = open(p, "rb").read().decode("latin-1") if os.path.exists(p) else ""
    line = next((l for l in txt.splitlines() if l.startswith("UCW " + name)), None)
    if not line:
        out.append(f"=== {name}: NO RESULT LINE ({len(txt)} bytes read)\n")
        continue
    m = re.match(r"UCW (\S+) res=(\w) np=([0-9A-F]{8}) pre=([0-9A-F]{8})", line)
    np_, pre = int(m.group(3), 16), int(m.group(4), 16)
    out.append(f"=== {name}: {m.group(2)}  pulses per width {np_}  slow pre-check pulses answered {pre} of 8")
    out.append(f"    line: {line}")
    out.append(f"    {'width':>9} {'clocks':>7} {'caught':>7} {'of':>5} {'caught %':>9}")
    for i, w in enumerate(WIDTHS):
        c = int(re.search(r" w%d=([0-9A-F]{8})" % i, line).group(1), 16)
        out.append(f"    {w * CLK_NS:7.0f} ns {w:7d} {c:7d} {np_:5d} {100.0 * c / np_:8.1f}%")
    ep = os.path.join(here, "raw", f"{label}_{name}.esp32")
    if os.path.exists(ep):
        et = open(ep, "rb").read().decode("latin-1")
        rt = [int(x) for x in re.findall(r"rT=(\d+)", et)]
        st = [int(x) for x in re.findall(r"stormT=(\d+)", et)]
        loops = sorted(set(re.findall(r"loop=([01])", et)))
        sw = sorted(set(re.findall(r"storm_work_us=(\d+)", et)))
        if rt:
            sent = 8 + 12 * np_
            out.append(f"    ESP32 counted {rt[-1] - rt[0]} handler runs during the log ({len(rt)} lines); the Tang sent {sent} pulses (8 pre-check + 12 x {np_}); difference {rt[-1] - rt[0] - sent:+d}")
            out.append(f"    ESP32 counted {st[-1] - st[0]} storm interrupts (loop={','.join(loops)}, storm_work_us={','.join(sw)})")
        else:
            out.append("    (the ESP32 log has no rT= lines)")
    else:
        out.append("    (no ESP32 log: run with ESPPORT=auto)")
    out.append("")
txt = "\n".join(out)
open(os.path.join(here, f"board_results_{label}.txt"), "w").write(f"label: {label}\n" + txt)
print(txt)
