"""Check of the lattice bank with NC full cells behind the glue buffer (rtl/hexn_bank_v14.v in hexn_lattice_<shape>_v13, rtl/tb_hexn_cellbank_v2.v). New file (v2 of the checker untouched).
Trains the bank in simulation, then runs random trials in mode 0 (detectors only) and mode 1 (detectors -> glue -> NC cells, each with its own random lane settings and threshold). Expected values: counting rules (tools/hexn_tang_script_v1.py) and the clock-by-clock cell model of tools/hexn_cellbank_check_v1.py.
Usage: python3 tools/hexn_cellbank_check_v3.py SHAPE NC TRIALS [SEED]"""
import sys, os, random, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_tang_script_v1 as S1, hexn_bist_sets_v1 as BS, hexn_cellbank_check_v1 as C1
NB, AW = 18, 7
def main():
    shape, NC, ntr = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); rnd = random.Random(int(sys.argv[4]) if len(sys.argv) > 4 else 3); K = {"hex7": 7, "hex19": 19}[shape]
    d = BS.make_set(K, NB, AW, (1, 0.5, 0.2, 8)); m = S1.make_model(d, 16); trials = []; exp = []
    for n in range(ntr):
        bits = [b ^ (1 if rnd.random() < rnd.choice([0.05, 0.2, 0.4]) else 0) for b in d["train"][rnd.randrange(len(d["train"]))][0]]
        mode = n % 2; pred, lens = S1.classify(m, bits); cells = []; res = []
        for c in range(NC):
            cfg = [rnd.choices([0, 1, 2], [0.3, 0.45, 0.25])[0] for _ in range(K)]; acc0, _ = C1.cell_model(K, lens, cfg, 0)
            cthr = rnd.randint(0, 127) if rnd.random() < 0.1 else max(0, acc0 - rnd.randint(-4, 9)); cells.append((cthr, cfg)); res.append(C1.cell_model(K, lens, cfg, cthr))
        trials.append((mode, bits, cells)); exp.append((pred, lens, res))
    dd = tempfile.mkdtemp(); fn = os.path.join(dd, "stim.txt")
    with open(fn, "w") as f:
        f.write("%d %d\n" % (d["T"], ntr))
        for bits, y in d["train"]: f.write("%d %x\n" % (y, sum(b << j for j, b in enumerate(bits))))
        for mode, bits, cells in trials: f.write("%d %x %s\n" % (mode, sum(b << j for j, b in enumerate(bits)), " ".join("%d %s" % (t, " ".join(map(str, cfg))) for t, cfg in cells)))
    src = ["rtl/tb_hexn_cellbank_v2.v", "rtl/gen/hexn_lattice_%s_w18_v13.v" % shape, "rtl/hexn_bank_v14.v", "rtl/hexn_det_v3.v", "rtl/hexn_glue_v1.v", "rtl/hexn_cell_v3.v", "rtl/hexn_trainbank_v9.v", "rtl/hexn_cfgbank_v2.v", "rtl/hexn_sdiv_v1.v"]
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(dd, "s.vvp"), "-DLAT=hexn_lattice_%s_v13" % shape, "-Ptb_hexn_cellbank_v2.K=%d" % K, "-Ptb_hexn_cellbank_v2.NC=%d" % NC] + [os.path.join(ROOT, s) for s in src], check=True)
    out = subprocess.run(["vvp", "-n", os.path.join(dd, "s.vvp"), "+stim=" + fn], capture_output=True, text=True).stdout
    got = [l.split()[1:] for l in out.splitlines() if l.startswith("R ")]
    if len(got) != ntr: sys.exit("simulation gave %d results for %d trials" % (len(got), ntr))
    b0 = b1 = bc = bf = bo = n0 = n1 = fired = shown = 0
    for i, (g, (pred, lens, res)) in enumerate(zip(got, exp)):
        g = [int(x) if x.isdigit() else -1 for x in g]; mode, av, ac = g[0], g[1], g[2]; cnt = g[3:3 + K]; cap = g[3 + K:3 + 2 * K]; cells = g[3 + 2 * K:]
        bad0 = (cnt != lens) or (av != (1 if pred >= 0 else 0)) or (av and ac != pred)
        if mode == 0: n0 += 1; b0 += bad0; continue
        n1 += 1; b1 += bad0; bc += cap != lens
        for c in range(NC):
            fwd, cc = cells[2 * c], cells[2 * c + 1]; e_acc, e_cnt = res[c]; bf += fwd != e_acc; bo += cc != e_cnt; fired += e_cnt > 0
            if (fwd != e_acc or cc != e_cnt) and shown < 5: shown += 1; print("trial %d cell %d: total %d (exp %d) burst %d (exp %d)" % (i, c, fwd, e_acc, cc, e_cnt))
    print("%s with %d cells: mode 0 trials %d: wrong %d | mode 1 trials %d: detector part wrong %d, captured lengths wrong %d, cell totals wrong %d of %d, cell outputs wrong %d (cell firings %d)" % (shape, NC, n0, b0, n1, b1, bc, bf, n1 * NC, bo, fired))
    sys.exit(0 if not (b0 or b1 or bc or bf or bo) else 1)
if __name__ == "__main__": main()
