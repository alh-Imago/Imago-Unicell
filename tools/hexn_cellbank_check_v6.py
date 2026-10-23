"""Check of the bank with NC LEAKY cells (rtl/hexn_bank_v17.v + hexn_cell_v5.v in hexn_lattice_<shape>_v16, rtl/tb_hexn_cellbank_v3.v). New file (v3 of the checker untouched). Like v3, but each mode-1 trial also gets a leak setting and each cell KEEPS its forward total from run to run: before the new window its total a becomes a - (a >> s) (s = 7: unchanged; s = 0: cleared). Mode-0 trials do not touch the cells.
Expected values: counting rules + a clock-by-clock cell model that starts from the carried total. Usage: python3 tools/hexn_cellbank_check_v4.py SHAPE NC TRIALS SEED LEAKMODE [top]   (top = through the board top v10 and its serial commands, rtl/tb_hexn_cell_top_v2.v; v4 of this checker was extended with it)   (LEAKMODE: 0 = leak setting always 0 (must equal the old cell), r = random 0..7 per trial)"""
import sys, os, random, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_tang_script_v1 as S1, hexn_bist_sets_v1 as BS
NB, AW, PL = 18, 7, 10
def leaked(a, s): return a if s == 7 else a - (a >> s)
def cell_run(K, lens, cfg, cthr, a0):
    acc = a0
    for t in range(PL):
        pos = sum(1 for g in range(K) if cfg[g] == 1 and 1 <= t <= lens[g]); neg = sum(1 for g in range(K) if cfg[g] == 2 and 1 <= t <= lens[g])
        acc = max(0, min((1 << AW) - 1, acc + pos - neg))
    return acc, ((min(acc - cthr, 6) + 1) if acc >= cthr else 0)
def main():
    shape, NC, ntr, seed, lm = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]; top = len(sys.argv) > 6 and sys.argv[6] == "top"; rnd = random.Random(seed); K = {"hex7": 7, "hex19": 19}[shape]
    d = BS.make_set(K, NB, AW, (1, 0.5, 0.2, 8)); m = S1.make_model(d, 16); trials = []; exp = []; state = [0] * NC
    for n in range(ntr):
        bits = [b ^ (1 if rnd.random() < rnd.choice([0.05, 0.2, 0.4]) else 0) for b in d["train"][rnd.randrange(len(d["train"]))][0]]
        mode = n % 2 if n >= 2 else 1 - n % 2; pred, lens = S1.classify(m, bits); lk = 0 if lm == "0" else rnd.randrange(8); cells = []; res = []
        for c in range(NC):
            cfg = [rnd.choices([0, 1, 2], [0.3, 0.45, 0.25])[0] for _ in range(K)]; a0 = leaked(state[c], lk); acc0, _ = cell_run(K, lens, cfg, 0, a0)
            cthr = rnd.randint(0, 127) if rnd.random() < 0.1 else max(0, acc0 - rnd.randint(-4, 9)); cells.append((cthr, cfg)); r = cell_run(K, lens, cfg, cthr, a0); res.append(r)
            if mode == 1: state[c] = r[0]
        trials.append((mode, bits, lk, cells)); exp.append((pred, lens, res))
    dd = tempfile.mkdtemp(); fn = os.path.join(dd, "stim.txt")
    with open(fn, "w") as f:
        f.write("%d %d\n" % (d["T"], ntr))
        for bits, y in d["train"]: f.write("%d %x\n" % (y, sum(b << j for j, b in enumerate(bits))))
        for mode, bits, lk, cells in trials: f.write("%d %x %d %s\n" % (mode, sum(b << j for j, b in enumerate(bits)), lk, " ".join("%d %s" % (t, " ".join(map(str, cfg))) for t, cfg in cells)))
    core = ["rtl/gen/hexn_lattice_%s_w18_v16.v" % shape, "rtl/hexn_bank_v17.v", "rtl/hexn_det_v3.v", "rtl/hexn_glue_v1.v", "rtl/hexn_cell_v5.v", "rtl/hexn_trainbank_v9.v", "rtl/hexn_cfgbank_v2.v", "rtl/hexn_sdiv_v1.v"]
    if top: src = ["rtl/tb_hexn_cell_top_v2.v", "rtl/hexn_tang_top_v10.v", "rtl/hexn_uart_v1.v"] + core; defs = ["-DLATMOD=hexn_lattice_%s_v16" % shape, "-DNCLS=%d" % K, "-DNCELL=%d" % NC, "-DCLKDIV=8"]
    else: src = ["rtl/tb_hexn_cellbank_v3.v"] + core; defs = ["-DLAT=hexn_lattice_%s_v16" % shape, "-Ptb_hexn_cellbank_v3.K=%d" % K, "-Ptb_hexn_cellbank_v3.NC=%d" % NC]
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(dd, "s.vvp")] + defs + [os.path.join(ROOT, x) for x in src], check=True)
    out = subprocess.run(["vvp", "-n", os.path.join(dd, "s.vvp"), "+stim=" + fn], capture_output=True, text=True).stdout
    got = [l.split()[1:] for l in out.splitlines() if l.startswith("R ")]
    if len(got) != ntr: sys.exit("simulation gave %d results for %d trials" % (len(got), ntr))
    b0 = b1 = bf = bo = n0 = n1 = fired = shown = carried = 0
    # through the top the detector part of a mode-1 trial is not returned (only the cell data and captured lengths), so it is not compared there
    for i, (g, (pred, lens, res)) in enumerate(zip(got, exp)):
        g = [int(x) if x.isdigit() else -1 for x in g]; mode, av, ac = g[0], g[1], g[2]; cnt = g[3:3 + K]; cells = g[3 + 2 * K:]
        bad0 = (cnt != lens) or (av != (1 if pred >= 0 else 0)) or (av and ac != pred)
        if mode == 0: n0 += 1; b0 += bad0; continue
        n1 += 1; b1 += (0 if top else bad0)
        for c in range(NC):
            fwd, cc = cells[2 * c], cells[2 * c + 1]; e_acc, e_cnt = res[c]; bf += fwd != e_acc; bo += cc != e_cnt; fired += e_cnt > 0; carried += trials[i][2] != 0 and e_acc > 0
            if (fwd != e_acc or cc != e_cnt) and shown < 5: shown += 1; print("trial %d cell %d leak %d: total %d (exp %d) burst %d (exp %d)" % (i, c, trials[i][2], fwd, e_acc, cc, e_cnt))
    print("%s, %d leaky cells, leak mode %s: mode 0 trials %d wrong %d | mode 1 trials %d: detector part wrong %d, cell totals wrong %d of %d, cell outputs wrong %d (firings %d, totals carried with a nonzero leak setting %d)" % (shape, NC, lm, n0, b0, n1, b1, bf, n1 * NC, bo, fired, carried))
    sys.exit(0 if not (b0 or b1 or bf or bo) else 1)
if __name__ == "__main__": main()
