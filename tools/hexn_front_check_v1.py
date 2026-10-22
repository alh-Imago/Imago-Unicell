"""Interface test, detectors -> glue buffer -> one full cell (rtl/hexn_front_v1.v, rtl/hexn_glue_v1.v, rtl/tb_hexn_front_v1.v). Generates random trials, runs the simulation (iverilog), and compares per trial:
(1) the burst lengths the glue captured with the counting rules (clocks = min(forward total - threshold + 1, 7) once the total reaches the threshold; 0 otherwise),
(2) the cell's forward total with a clock-by-clock model written here from the cell's equations (a lane's burst of n clocks adds +-1 on clocks 1..n; the running total is clamped at 0 and at 2^AW-1 every clock),
(3) the cell's output burst count: min(total - threshold, 6) + 1 when the total reaches the cell threshold, else 0.
Usage: python3 tools/hexn_front_check_v1.py [trials] [seed]"""
import sys, os, random, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_tang_script_v1 as S1
K, NB, AW, PL = 19, 18, 7, 10
def cell_model(lens, cfg, cthr):
    acc = 0
    for t in range(PL):
        pos = sum(1 for g in range(K) if cfg[g] == 1 and 1 <= t <= lens[g]); neg = sum(1 for g in range(K) if cfg[g] == 2 and 1 <= t <= lens[g])
        acc = max(0, min((1 << AW) - 1, acc + pos - neg))
    cnt = (min(acc - cthr, 6) + 1) if acc >= cthr else 0
    return acc, cnt
def main():
    ntr = int(sys.argv[1]) if len(sys.argv) > 1 else 1500; rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 7); trials = []; exp = []
    for _ in range(ntr):
        bits = [rnd.randint(0, 1) for _ in range(NB)]; wp = []; wn = []; thr = []; lens = []; W = []
        for g in range(K):
            w = [1 if rnd.random() < 0.35 else -1 if rnd.random() < 0.25 else 0 for _ in range(NB)]; W.append(w)
            f = S1.fwd_of(S1.net_of(w, bits), AW); r = rnd.random()
            t = 0 if r < 0.05 else (1 << AW) - 1 if r < 0.1 else max(0, f - rnd.randint(-3, 9)); thr.append(t)
            lens.append(min(f - t + 1, 7) if f >= t else 0)
            wp.append(sum(1 << j for j in range(NB) if w[j] > 0)); wn.append(sum(1 << j for j in range(NB) if w[j] < 0))
        cfg = [rnd.choices([0, 1, 2], [0.3, 0.45, 0.25])[0] for _ in range(K)]; acc0, _ = cell_model(lens, cfg, 0)
        cthr = rnd.randint(0, 127) if rnd.random() < 0.1 else max(0, acc0 - rnd.randint(-4, 9))
        trials.append((bits, wp, wn, thr, cfg, cthr)); acc, cnt = cell_model(lens, cfg, cthr); exp.append((lens, acc, cnt))
    d = tempfile.mkdtemp(); fn = os.path.join(d, "stim.txt")
    with open(fn, "w") as f:
        f.write("%d\n" % ntr)
        for bits, wp, wn, thr, cfg, cthr in trials:
            f.write("%x %s %s %s %s %d\n" % (sum(b << j for j, b in enumerate(bits)), " ".join("%x" % x for x in wp), " ".join("%x" % x for x in wn), " ".join(map(str, thr)), " ".join(map(str, cfg)), cthr))
    src = ["rtl/tb_hexn_front_v1.v", "rtl/hexn_front_v1.v", "rtl/hexn_glue_v1.v", "rtl/hexn_det_v3.v", "rtl/hexn_cell_v2.v"]
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "s.vvp")] + [os.path.join(ROOT, s) for s in src], check=True)
    out = subprocess.run(["vvp", "-n", os.path.join(d, "s.vvp"), "+stim=" + fn], capture_output=True, text=True).stdout
    got = [l.split()[1:] for l in out.splitlines() if l.startswith("R ")]
    if len(got) != ntr: sys.exit("simulation gave %d results for %d trials" % (len(got), ntr))
    bad_cap = bad_fwd = bad_cnt = 0; shown = 0; fired = 0; mx = 0
    for i, (g, (lens, acc, cnt)) in enumerate(zip(got, exp)):
        gl = [int(x) for x in g[:K]]; gf = int(g[K]); gc = int(g[K + 1]); fired += cnt > 0; mx = max(mx, max(lens))
        a, b, c = gl != lens, gf != acc, gc != cnt; bad_cap += a; bad_fwd += b; bad_cnt += c
        if (a or b or c) and shown < 6: shown += 1; print("trial %d: captured %s expected %s | cell total %d expected %d | cell burst %d expected %d" % (i, gl, lens, gf, acc, gc, cnt))
    print("trials %d: captured burst lengths wrong %d, cell forward total wrong %d, cell output burst wrong %d (cell fired in %d trials; longest detector burst seen %d)" % (ntr, bad_cap, bad_fwd, bad_cnt, fired, mx))
    sys.exit(0 if not (bad_cap or bad_fwd or bad_cnt) else 1)
if __name__ == "__main__": main()
