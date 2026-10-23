#!/usr/bin/env python3
"""Simulation check of fpga/ypcb/hexn_ram/memlat.v (the RAM latency probe) against a stand-in Wishbone slave.
Checks: single reads measure exactly the slave latency (min = max = LAT), extra latency on one address in eight shows in max and sum,
stalls show in stall_sum, pipelined reads overlap (total about COUNT + LAT, not COUNT x LAT), no write is ever issued.
Usage: python3 tools/hexn_memlat_sim_v1.py"""
import os, re, subprocess, sys
d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fpga", "ypcb", "hexn_ram")
out = "/tmp/hexn_memlat_tb.vvp"
def run(mode, lat, extra, count, stall, wrap=False):
    subprocess.run(["iverilog", "-g2012"] + (["-DWRAP", "-P", f"tb_memlat.LEN={count.bit_length() - 1}"] if wrap else []) + ["-o", out, "-P", f"tb_memlat.MODE={mode}", "-P", f"tb_memlat.LAT={lat}", "-P", f"tb_memlat.EXTRA={extra}",
                    "-P", f"tb_memlat.COUNT={count}", "-P", f"tb_memlat.STALLCYC={stall}", os.path.join(d, "sim", "tb_memlat.v"), os.path.join(d, "memlat.v")] + ([os.path.join(d, "memtest.v")] if wrap else []), check=True)
    t = subprocess.run(["vvp", out], capture_output=True, text=True, timeout=300).stdout
    m = re.search(r"RESULT .*: (.*)", t)
    if not m: sys.exit("no RESULT line: " + t[-300:])
    return {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", m.group(1))}
bad = 0
def chk(name, ok, r):
    global bad
    print(("ok   " if ok else "FAIL ") + name + "  " + str(r)); bad += 0 if ok else 1
r = run(0, 20, 0, 50, 0);  chk("single, fixed latency 20", r["n_done"] == 50 and r["lat_min"] == 20 and r["lat_max"] == 20 and r["lat_sum"] == 1000 and r["writes_seen"] == 0, r)
r = run(0, 20, 10, 200, 0); chk("single, extra 10 on one address in eight", r["lat_min"] == 20 and r["lat_max"] == 30 and 200 * 20 < r["lat_sum"] < 200 * 20 + 200 * 10 // 4, r)
r = run(0, 20, 0, 50, 3);  chk("single, stalls give stall_sum", r["lat_min"] == 20 and r["lat_max"] == 20 and r["stall_sum"] > 0, r)
r = run(1, 20, 0, 100, 0); chk("pipelined random overlaps: total about count + latency", r["n_done"] == 100 and 100 + 20 <= r["total"] <= 100 + 20 + 6, r)
r = run(2, 20, 0, 100, 0); chk("pipelined sequential overlaps", r["n_done"] == 100 and 100 + 20 <= r["total"] <= 100 + 20 + 6, r)
r = run(2, 40, 0, 100, 4); chk("pipelined with stalls 4 of 16 cycles, latency 40", r["n_done"] == 100 and r["stall_sum"] > 0 and 100 + 40 < r["total"] < 100 * 16 // 12 + 40 + 8, r)
r = run(0, 20, 0, 32, 0, wrap=True); chk("drop-in memtest wrapper, single, 2^5 reads at latency 20", r["n_done"] == 32 and r["lat_min"] == 20 and r["lat_max"] == 20 and r["lat_sum"] == 640, r)
r = run(1, 20, 0, 64, 0, wrap=True); chk("drop-in memtest wrapper, pipelined random, 2^6 reads", r["n_done"] == 64 and 64 + 20 <= r["total"] <= 64 + 20 + 6, r)
r = run(2, 30, 0, 64, 3, wrap=True); chk("drop-in memtest wrapper, pipelined sequential with stalls", r["n_done"] == 64 and r["stall_sum"] > 0, r)
print("MEMLAT SIM PASS" if bad == 0 else "MEMLAT SIM FAIL"); sys.exit(1 if bad else 0)
