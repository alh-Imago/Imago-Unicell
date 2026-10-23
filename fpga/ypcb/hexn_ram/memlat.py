#!/usr/bin/env python3
"""Run the RAM latency probe (hexn_ram build) over JTAG and print the latency in controller cycles and nanoseconds.
Needs the hexn_ram bitstream loaded and the DDR3 calibrated (state 23, the same as designs/uberddr3/check.py).

    python3 memlat.py [--len 10] [--clk-mhz 83.333] [--channel 0|1]
Runs the three modes with 2^len reads each: single random reads (min, mean, max latency), pipelined random reads and pipelined
sequential reads (cycles per read when reads overlap). The register layout is the uberddr3 one; memtest.v's fields carry the results.
Needs ypcb's tools/jtagdr.py (YPCB, default ~/ypcb-00338-1p1)."""
import argparse, os, sys, time
YPCB = os.environ.get("YPCB", os.path.expanduser("~/ypcb-00338-1p1"))

def decode(w):
    """w = the register as 32-bit words. Returns the probe's fields."""
    return {"busy": w[22] & 1, "seq_done": (w[22] >> 1) & 0xFF, "lat_min": w[23], "lat_max": w[24], "lat_sum": w[25], "stall_sum": w[26],
            "fold": w[27] & 0xFF, "total": w[28], "n": w[29] & 0xFFFF}

def report(r, mode, n, clk_hz):
    ns = lambda c: c / clk_hz * 1e9
    if mode == 1:
        mean = r["lat_sum"] / n
        return (f"single random reads x{n}: latency min {r['lat_min']} / mean {mean:.1f} / max {r['lat_max']} cycles = "
                f"{ns(r['lat_min']):.0f} / {ns(mean):.0f} / {ns(r['lat_max']):.0f} ns; waited on stall {r['stall_sum']} cycles in total; "
                f"{r['total'] / n:.1f} cycles per read including the probe's own 2")
    name = "pipelined random" if mode == 2 else "pipelined sequential"
    per = r["total"] / n
    return (f"{name} reads x{n}: {r['total']} cycles in all = {per:.2f} cycles per read ({ns(per):.1f} ns, "
            f"{64 * clk_hz / per / 1e9:.2f} GB/s of 64-byte words); stall cycles {r['stall_sum']}")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--len", type=int, default=10); ap.add_argument("--clk-mhz", type=float, default=83.333)
    ap.add_argument("--channel", type=int, choices=(0, 1), default=0); a = ap.parse_args()
    sys.path.insert(0, os.path.join(YPCB, "tools"))
    from jtagdr import read_dr, xfer_dr, words
    BITS = 1024; n = 1 << min(a.len, 15)
    def status():
        w = words(read_dr(BITS)[0][1], 32)
        if w[0] != 0x55424433: sys.exit("magic %08x: is a uberddr3-based build loaded?" % w[0])
        return w
    w = status()
    dual = (w[3] >> 1) & 1
    if a.channel and not dual: sys.exit("this bitstream drives one channel")
    xfer_dr([(0x4D << 24) | (a.channel << 15) | ((w[22] >> 1) & 0xFF)], BITS); w = status()
    if not ((w[1] >> 1) & 1 and (w[1] >> 2) & 0x1F == 23): sys.exit("controller not calibrated (run check.py)")
    ok = True
    for mode in (1, 2, 3):
        seq = ((status()[22] >> 1) & 0xFF) % 255 + 1
        xfer_dr([(0x4D << 24) | (7 << 16) | (a.channel << 15) | (mode << 13) | (a.len << 8) | seq], BITS)
        t0 = time.time()
        while True:
            r = decode(status())
            if r["seq_done"] == seq and not r["busy"]: break
            if time.time() - t0 > 60: sys.exit("timed out in mode %d" % mode)
            time.sleep(0.2)
        if r["n"] != n: ok = False
        print(report(r, mode, n, a.clk_mhz * 1e6) + ("" if r["n"] == n else f"   [WARNING: only {r['n']} of {n} reads counted]"))
    print("RAM LATENCY PROBE DONE" if ok else "RAM LATENCY PROBE INCOMPLETE")
    sys.exit(0 if ok else 1)

if __name__ == "__main__": main()
