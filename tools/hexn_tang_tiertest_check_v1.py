"""Check a serial capture from the board test hexn_tang_tiertest_v1 against the bit-true Python reference.
Usage: stty -F /dev/ttyUSB1 115200 raw; timeout 3 cat /dev/ttyUSB1 > cap.txt; python3 tools/hexn_tang_tiertest_check_v1.py cap.txt
Board settings (the defaults of the top): KW 18, VW 18, FB 11, BMB 16, RAMB 18, P 8, N 6000, M 3000. Pass other values as --N etc. if the top was changed."""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tier_ref_v2 as R
def key(i, KW): return ((i + 1) * 0x2545F491 & 0xFFFFFFFF) & ((1 << KW) - 1)
def vof(i, VW): return (((i + 1) * 0x85EBCA6B & 0xFFFFFFFF) >> 7) & ((1 << VW) - 1)
def uof(i, VW): return vof(i, VW) ^ (0x2AAAA & ((1 << VW) - 1))
def expected(KW, VW, FB, BMB, RAMB, P, N, M):
    t = R.Tier(KW, FB, BMB, RAMB, P)
    for i in range(N): t.put(key(i, KW), vof(i, VW))
    for i in range(0, N, 7): t.put(key(i, KW), uof(i, VW))
    for i in range(N): t.get(key(i, KW))
    for i in range(M): t.get(key(i + N, KW))
    n = t.n; return [n["fast_put"], n["sd_put"], n["overflow"], n["fast_hit"], n["skip"], n["sd_get"], n["fp"], n["sd_rd"], n["sd_wr"], n["found"]]
def main():
    a = argparse.ArgumentParser(); a.add_argument("capture")
    for k, v in dict(KW=18, VW=18, FB=11, BMB=16, RAMB=18, P=8, N=6000, M=3000).items(): a.add_argument("--" + k, type=int, default=v)
    a = a.parse_args(); text = open(a.capture, errors="replace").read()
    lines = re.findall(r"R([0-9A-F])=([0-9A-F]{8})", text)
    if len(lines) < 16: print("NO COMPLETE REPORT in the capture (%d lines)" % len(lines)); return 2
    r = {int(x, 16): int(y, 16) for x, y in lines[-16:]}
    print("errors total %d (wrong value %d, known key not found %d, never-seen key found %d)" % (r[0], r[1], r[2], r[3]))
    print("clear sweep %d clocks = %.3f s, whole test %d clocks = %.1f ms (27 MHz)" % (r[4], r[4] / 27e6, r[5], r[5] / 27e3))
    exp = expected(a.KW, a.VW, a.FB, a.BMB, a.RAMB, a.P, a.N, a.M); got = [r[k] for k in range(6, 16)]
    names = "fast_put sd_put overflow fast_hit skip sd_get fp sd_rd sd_wr found".split()
    ok = True
    for n, g, e in zip(names, got, exp):
        print("  %-9s board %6d  reference %6d  %s" % (n, g, e, "ok" if g == e else "DIFFERENT")); ok &= (g == e)
    print("BOARD TEST PASS" if ok and r[0] == 0 else "BOARD TEST FAIL"); return 0 if ok and r[0] == 0 else 1
if __name__ == "__main__": sys.exit(main())
