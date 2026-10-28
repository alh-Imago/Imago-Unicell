"""Check a report of the board test hexn_tang_cardtest_v5 (serial capture from the Tang Nano 20K, or the simulation) against the bit-true Python reference tools/hexn_tier_ref_v5.py.
Usage on the board:  stty -F /dev/ttyUSB1 115200 raw; timeout 5 cat /dev/ttyUSB1 > cap.txt; python3 tools/hexn_tang_cardtest_check_v5.py cap.txt
Board settings (the defaults of the top): KW 18, VW 18, FB 6, RAMB 8, LB 6, LOW 4, N 1500, M 500. Pass other values as --N etc. if the top was changed."""
import argparse, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tier_ref_v5 as R
def kof(i, KW): return ((i + 1) * 0x2545F491 & 0xFFFFFFFF) & ((1 << KW) - 1)
def vof(i, VW): return (((i + 1) * 0x85EBCA6B & 0xFFFFFFFF) >> 7) & ((1 << VW) - 1)
def uof(i, VW): return vof(i, VW) ^ (0x2AAAA & ((1 << VW) - 1))
def expected(KW=18, VW=18, FB=6, RAMB=8, LB=6, LOW=4, N=1500, M=500):
    """-> (counters after save, after restore, after final gets) as lists of 27, plus (pre-save errors, post-restore errors) as (wrong, lost, never-seen-found)."""
    t = R.Tier5(KW, FB, RAMB, LB, LOW)
    pre = [0, 0, 0]
    for i in range(N): t.put(kof(i, KW), vof(i, VW))
    for i in range(0, N, 7): t.put(kof(i, KW), uof(i, VW))
    for i in range(N):
        f, v = t.get(kof(i, KW)); want = uof(i, VW) if i % 7 == 0 else vof(i, VW)
        if not f: pre[1] += 1
        elif v != want: pre[0] += 1
    for i in range(M):
        f, v = t.get(kof(i + N, KW)); pre[2] += int(bool(f))
    assert t.save() >= 0
    c0 = [t.n[k] for k in R.NAMES]
    t.power_loss(); t.n = {k: 0 for k in R.NAMES}; t.restore(); c1 = [t.n[k] for k in R.NAMES]
    post = [0, 0, 0]
    for i in range(N):
        f, v = t.get(kof(i, KW)); want = uof(i, VW) if i % 7 == 0 else vof(i, VW)
        if not f: post[1] += 1
        elif v != want: post[0] += 1
    for i in range(M):
        f, v = t.get(kof(i + N, KW)); post[2] += int(bool(f))
    c2 = [t.n[k] for k in R.NAMES]
    return c0, c1, c2, pre, post
def parse(text):
    """Text from the serial port (or the simulation) -> (dict of H lines, list of 81 C values or None). Uses the last complete frame."""
    h = {}; c = {}
    for typ, a, v in re.findall(r"([HC])([0-9A-F]{2})=([0-9A-F]{8})", text):
        (h if typ == "H" else c)[int(a, 16)] = int(v, 16)
    return h, c
def judge(text, **kw):
    """-> (verdict, lines). verdict: 'PASS', 'REFUSED' (region not empty, nothing written), 'CARD ERROR', 'FAIL' or 'NO REPORT'."""
    h, c = parse(text); out = []
    if len(h) < 16: return "NO REPORT", ["no complete report in the capture (%d H lines)" % len(h)]
    names = {0: "running", 1: "REFUSED: region not empty", 2: "card error during probe", 3: "passed"}
    out.append("probe: %s; non-zero words %d; first non-empty block %s; SD_BASE %d" % (names.get(h[0], h[0]), h[1], "none" if h[2] == 0xFFFFFFFF else h[2], h[15]))
    if h[0] == 1: return "REFUSED", out + ["nothing was written to the card; choose another SD_BASE (rebuild with the new value)"]
    if h[0] == 2: return "CARD ERROR", out + ["card error word %08X" % h[3]]
    if h[3] and h[0] == 3: return "CARD ERROR", out + ["tier card error flag %08X" % h[3]]
    if not h[4]: return "FAIL", out + ["test not finished"]
    out.append("before the reset: wrong %d, known not found %d, never-seen found %d" % (h[10], h[11], h[12]))
    out.append("after save+reset+restore: wrong %d, known not found %d, never-seen found %d" % (h[6], h[7], h[8]))
    out.append("tier ready after %d clocks (%.2f s), whole test %d clocks (%.2f s) at 27 MHz" % (h[13], h[13] / 27e6, h[14], h[14] / 27e6))
    if len(c) < 81: return "FAIL", out + ["counter lines missing (%d of 81)" % len(c)]
    exp = expected(**kw); ok = (h[5] == 0 and h[9] == 0)
    for s, (name, e) in enumerate(zip(("after save", "after restore", "after final gets"), exp[:3])):
        got = [c[27 * s + k] for k in range(27)]
        diff = [(n, g, x) for n, g, x in zip(R.NAMES, got, e) if g != x]
        out.append("counters %-16s %s" % (name, "equal to the reference" if not diff else "DIFFERENT: " + ", ".join("%s board %d ref %d" % d for d in diff))); ok &= not diff
    out.append("reference errors before reset %s, after restore %s" % (exp[3], exp[4])); ok &= [h[10], h[11], h[12]] == exp[3] and [h[6], h[7], h[8]] == exp[4]
    return ("PASS" if ok else "FAIL"), out
def main():
    a = argparse.ArgumentParser(); a.add_argument("capture")
    for k, v in dict(KW=18, VW=18, FB=6, RAMB=8, LB=6, LOW=4, N=1500, M=500).items(): a.add_argument("--" + k, type=int, default=v)
    a = a.parse_args(); text = open(a.capture, errors="replace").read()
    v, lines = judge(text, **{k: getattr(a, k) for k in "KW VW FB RAMB LB LOW N M".split()})
    print("\n".join(lines)); print("CARD TEST " + v); return 0 if v == "PASS" else 1
if __name__ == "__main__": sys.exit(main())
