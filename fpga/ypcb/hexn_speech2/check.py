#!/usr/bin/env python3
"""Read the exact counts of the speech kit v2 (hexn_speech2) from the card over JTAG (USER2) and compare them with data/EXPECTED.txt of the v1 kit folder.
Run from ~/ypcb-00338-1p1 after loading hexn_speech2.bit (the OpenOCD board file is found as in fpga/ypcb/hexn_u2/check.py), in the openOCD shell:
    nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_REPO=$HOME/hexn-wt python3 ~/hexn-wt/fpga/ypcb/hexn_speech2/check.py
It reads the 64-bit register up to --tries times (default 20, one second apart) until done = 1, then prints the counts. PASS = the magic word SPCH, done = 1, total = recordings and correct = the model's figure.
--decode HEX decodes a register value you already have (no card needed). Nothing is written to the card by this script; the register is read only."""
import os, sys, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); repo = os.path.expanduser(os.environ.get("HEXN_REPO", "~/Imago-Unicell"))
ap = argparse.ArgumentParser(); ap.add_argument("--tries", type=int, default=20); ap.add_argument("--decode"); a = ap.parse_args()


def decode(v): return dict(correct=v & 0x1FF, total=(v >> 9) & 0x1FF, rec=(v >> 18) & 0x1FF, done=(v >> 27) & 1, pas=(v >> 28) & 1, zero=(v >> 29) & 7, magic=v >> 32)


exp = dict(l.split() for l in open(os.path.join(HERE, "..", "hexn_speech", "data", "EXPECTED.txt")))
if a.decode: v = int(a.decode, 16); d = decode(v)
else:
    os.environ["HEXN_CHAIN"] = "2"; sys.path.insert(0, os.path.join(repo, "tools")); import hexn_jtag_host_v1 as J
    cands = [os.environ.get("OPENOCD_CFG", ""), os.path.join(os.getcwd(), "board/ypcb-00338-1p1/openocd.cfg"), os.path.expanduser("~/ypcb-00338-1p1/board/ypcb-00338-1p1/openocd.cfg")]
    cfg = next((c for c in cands if c and os.path.isfile(c)), None)
    if cfg is None: sys.exit("openocd.cfg not found; set OPENOCD_CFG=<path to board/ypcb-00338-1p1/openocd.cfg> or run from ~/ypcb-00338-1p1")
    ex = J.OpenOCDExec(cfg, bits=64)
    try:
        for t in range(a.tries):
            v = ex.scan(0); d = decode(v)
            print("  read %2d: %016x  magic %s done %d correct %d total %d" % (t + 1, v, "ok" if d["magic"] == 0x53504348 else "WRONG (%08x)" % d["magic"], d["done"], d["correct"], d["total"]))
            if d["magic"] == 0x53504348 and d["done"]: break
            time.sleep(1)
    finally: ex.close()
print("recordings started %d, total scored %d, correct %d (%.1f%%), pass LED %s; model: total %s correct %s" % (d["rec"], d["total"], d["correct"], 100.0 * d["correct"] / max(1, d["total"]), "on" if d["pas"] else "off", exp["recordings"], exp["correct"]))
ok = d["magic"] == 0x53504348 and d["done"] == 1 and d["total"] == int(exp["recordings"]) and d["correct"] == int(exp["correct"])
print("PASS" if ok else "FAIL (a count that differs from the model is a real finding: send me the numbers)"); sys.exit(0 if ok else 1)
