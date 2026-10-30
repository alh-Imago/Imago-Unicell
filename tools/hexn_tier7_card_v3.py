"""(v3, 30 Oct 2026: clone of hexn_tier7_card_v2.py, which is left untouched; adds --mixkeys, keys spread by a mixing function, because the stepped keys of v2 cluster in the tier's hash and fill only about a twentieth of the lines. v2 text follows.)
(v2, 29 Oct 2026: clone of hexn_tier7_card_v1.py, which is left untouched; sends CLEAR (0x47) after INFO so the model and the card start from the same empty store without reloading the bitstream; needs the hexn_tier2 bitstream.)
Run the Kintex memory tier on the card over JTAG (USER3): INFO, a self-test against the Python model (tools/hexn_tier_ref_v3.py, Tier3 with SPS = 8) and, if asked, a dump of every level to a JSON file.
Usage (from ~/ypcb-00338-1p1, in the nix shell with openocd, right after loading the bitstream of fpga/ypcb/hexn_tier):
    nix shell nixpkgs#openocd --command env OPENOCD=openocd python3 ~/hexn-wt/tools/hexn_tier7_card_v2.py --steps 2000 --dump tier_dump.json
Options: --steps N (random PUT/GET steps, default 1000), --keys N (distinct keys, default 500), --dump FILE, --info (only INFO). Exit 0 = PASS. First run on the card 29 Oct 2026 (see HEXN_DESIGN.md). 29 Oct: refuses to start when the tier already holds data from an earlier run (the model starts empty); reload the bitstream first, or use --force."""
import argparse, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_jtag_host_v1 as J, hexn_tier7_host_v2 as H
from hexn_tier_ref_v3 import Tier3
def h32(x):
    m = (x * 0x9E3779B1) & 0xFFFFFFFF; m ^= m >> 15; m = (m * 0x85EBCA6B) & 0xFFFFFFFF; return m ^ (m >> 13)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--steps", type=int, default=1000); ap.add_argument("--keys", type=int, default=500)
    ap.add_argument("--dump"); ap.add_argument("--info", action="store_true"); ap.add_argument("--mixkeys", action="store_true", help="spread the keys with a mixing function instead of the stepped keys of v2 (the stepped keys cluster in the tier's hash, see HEXN_DESIGN.md 30 Oct)"); ap.add_argument("--keep", action="store_true", help="do not CLEAR first (the model starts empty, so only for a tier you know is empty)"); a = ap.parse_args()
    cands = [os.environ.get("OPENOCD_CFG", ""), os.path.join(os.getcwd(), "board/ypcb-00338-1p1/openocd.cfg"), os.path.expanduser("~/ypcb-00338-1p1/board/ypcb-00338-1p1/openocd.cfg")]
    cfg = next((c for c in cands if c and os.path.isfile(c)), None)
    if cfg is None: sys.exit("openocd.cfg not found; set OPENOCD_CFG or run from ~/ypcb-00338-1p1")
    os.environ["HEXN_CHAIN"] = "3"      # the tier's bridge is on USER3
    ex = J.OpenOCDExec(cfg); dev = H.Tier7Dev(J.JtagLink(ex.scan))
    try:
        inf = dev.info(); print("INFO", inf)
        if not inf["ready"]: sys.exit("FAIL: the tier is not ready (DDR3 calibration not complete?)")
        if a.info: return
        if not a.keep:
            st = dev.clear(); print("CLEAR ->", st)
            if not (st["ready"] and not st["ddr_err"]): sys.exit("FAIL: the tier is not ready after CLEAR")
            c0 = dev.counters()
            if any(c0.values()): sys.exit("FAIL: counters not zero after CLEAR: %s" % c0)
        KW, VW = inf["KW"], inf["VW"]; MK, MV = (1 << KW) - 1, (1 << VW) - 1
        t = Tier3(KW=KW, FB=inf["FB"], BMB=inf["BMB"], RAMB=inf["RAMB"], SB=inf["SB"], SPS=inf["bucket"]); bad = 0; t0 = time.time()
        for n in range(a.steps):
            r = h32(n + 0x1111); ki = (r >> 4) % a.keys; kk = (h32(ki + 0x777) if a.mixkeys else ((ki + 1) * 0x2545F491 & 0xFFFFFFFF)) & MK
            if ((r >> 20) % 10) < 4:
                v = h32(n + 0x5151) & MV; t.put(kk, v); dev.put(kk, v)
            else:
                f, v = t.get(kk); g = dev.get(kk)
                if (g["found"], g["value"]) != (int(f), v if f else 0):
                    bad += 1
                    if bad < 10: print("step %d key %x: card found %d value %x, model found %d value %x" % (n, kk, g["found"], g["value"], int(f), v if f else 0))
        c = dev.counters(); cb = sum(1 for k in t.n if c[k] != t.n[k])
        print("%d steps in %.1f s; wrong answers %d; counters different from the model %d of 17" % (a.steps, time.time() - t0, bad, cb))
        for k in t.n:
            if c[k] != t.n[k]: print("  counter %s: card %d model %d" % (k, c[k], t.n[k]))
        if a.dump:
            d = dev.dump_all(a.dump, progress=lambda w, i: print("dump", w, i)); t.flush()
            want0 = {i: [(1 << 31) | e[0], e[1]] for i, e in t.fast.items()}; want1 = {i: [(1 << 31) | e[0], e[1]] for i, e in t.sdram.items()}
            ok = d["level0"] == want0 and d["level1"] == want1 and len(d["lines"]) == len(t.written)
            print("dump saved to %s: level0 %d entries, level1 %d, lines %d; equal to the model: %s" % (a.dump, len(d["level0"]), len(d["level1"]), len(d["lines"]), ok)); bad += (not ok)
        print("TIER ON CARD PASS" if bad == 0 and cb == 0 else "TIER ON CARD FAIL"); sys.exit(0 if bad == 0 and cb == 0 else 1)
    finally: ex.close()
if __name__ == "__main__": main()
