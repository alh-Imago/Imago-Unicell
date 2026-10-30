"""Check rtl/hexn_det_v4.v against an independent Python model (new file, 30 Oct 2026). Random weights/thresholds/lane bits for 400 windows of PL=10 clocks;
the model: total = running sum of (sum of w*rx) each clock, saturating at +-(2^AW - 1), restarted at the first clock of each window; margin = finished total - threshold.
Needs iverilog. Usage: python3 tools/hexn_det_v4_check_v1.py [NB AW ...]  (default: 12 7, 18 8, 20 8, 12 8)"""
import os, random, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def check(nb, aw, seed=1, nwin=400, pl=10):
    rnd = random.Random(seed); d = tempfile.mkdtemp(prefix="detv4_"); mx = (1 << aw) - 1
    rx, wp, wn, th, ex = [], [], [], [], []
    for w in range(nwin):
        pos = rnd.getrandbits(nb); neg = rnd.getrandbits(nb) & ~pos; t = rnd.randint(-mx, mx); dens = rnd.choice([0.2, 0.5, 0.8]); acc = 0; hold = rnd.random() < 0.5; x = 0
        for c in range(pl):
            if not hold or c == 0: x = sum(1 << j for j in range(nb) if rnd.random() < dens)
            rx.append(x); net = bin(x & pos).count("1") - bin(x & neg).count("1"); acc = max(-mx, min(mx, acc + net))
        wp.append(pos); wn.append(neg); th.append(t); ex.append(acc)
    # the margin of window w is latched at the first clock of window w+1 with the threshold present THEN (th[w+1]; the last one keeps th[nwin-1])
    ex = [ex[w] - th[min(w + 1, nwin - 1)] for w in range(nwin)]; th = [t & 0xFFFF for t in th]; ex = [v & 0xFFFF for v in ex]
    for name, arr in (("rx", rx), ("wp", wp), ("wn", wn), ("th", th), ("ex", ex)):
        open(os.path.join(d, name + ".hex"), "w").write("\n".join("%08x" % v for v in arr) + "\n")
    vvp = os.path.join(d, "t.vvp")
    subprocess.run(["iverilog", "-g2012", "-o", vvp, "-P", f"tb_hexn_det_v4.NB={nb}", "-P", f"tb_hexn_det_v4.AW={aw}", "-P", f"tb_hexn_det_v4.NWIN={nwin}",
                    os.path.join(ROOT, "rtl", "tb_hexn_det_v4.v"), os.path.join(ROOT, "rtl", "hexn_det_v4.v")], check=True)
    out = subprocess.run(["vvp", vvp], cwd=d, capture_output=True, text=True).stdout
    lines = out.strip().splitlines(); return next((l for l in lines if "TB DET V4" in l), lines[-1] if lines else "NO OUTPUT"), out
if __name__ == "__main__":
    args = [int(a) for a in sys.argv[1:]] or [12, 7, 18, 8, 20, 8, 12, 8]; ok = True
    for i in range(0, len(args), 2):
        last, out = check(args[i], args[i + 1]); print(last); ok &= "PASS" in last
        if "PASS" not in last: print(out)
    sys.exit(0 if ok else 1)
