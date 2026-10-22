"""Check of the lattice bank with CELL MODE (rtl/hexn_bank_v12.v in hexn_lattice_<shape>_v11, rtl/tb_hexn_cellbank_v1.v). Trains the bank in simulation on a fixed training set, then runs random trials back to back, half in mode 0 (detectors only) and half in
mode 1 (detectors -> glue buffer -> one full cell). Expected values come from the counting rules (tools/hexn_tang_script_v1.py) and a clock-by-clock model of the cell's forward total written from its equations:
mode 0: answer, validity and all K burst counts equal the rules; mode 1 additionally: captured burst lengths equal the detector burst lengths, cell forward total, cell output burst count.
Usage: python3 tools/hexn_cellbank_check_v1.py SHAPE TRIALS [SEED] [top]   ("top" = test through the board top v9 and its serial commands, rtl/tb_hexn_cell_top_v1.v: mode 0 = RUN, mode 1 = LOADCELL + RUNCELL, which does not return the detector counts)     (SHAPE hex7 or hex19; 18 wires, accumulator 7)"""
import sys, os, random, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_tang_script_v1 as S1, hexn_bist_sets_v1 as BS
NB, AW, PL = 18, 7, 10
def cell_model(K, lens, cfg, cthr):
    acc = 0
    for t in range(PL):
        pos = sum(1 for g in range(K) if cfg[g] == 1 and 1 <= t <= lens[g]); neg = sum(1 for g in range(K) if cfg[g] == 2 and 1 <= t <= lens[g])
        acc = max(0, min((1 << AW) - 1, acc + pos - neg))
    return acc, ((min(acc - cthr, 6) + 1) if acc >= cthr else 0)
def main():
    shape = sys.argv[1]; ntr = int(sys.argv[2]); rnd = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 3); top = len(sys.argv) > 4 and sys.argv[4] == "top"; K = {"hex7": 7, "hex19": 19}[shape]
    d = BS.make_set(K, NB, AW, (1, 0.5, 0.2, 8)); m = S1.make_model(d, 16); trials = []; exp = []
    for n in range(ntr):
        y = rnd.randrange(K); bits = [b ^ (1 if rnd.random() < rnd.choice([0.05, 0.2, 0.4]) else 0) for b in d["train"][rnd.randrange(len(d["train"]))][0]]
        mode = n % 2; pred, lens = S1.classify(m, bits); cfg = [rnd.choices([0, 1, 2], [0.3, 0.45, 0.25])[0] for _ in range(K)]; acc0, _ = cell_model(K, lens, cfg, 0)
        cthr = rnd.randint(0, 127) if rnd.random() < 0.1 else max(0, acc0 - rnd.randint(-4, 9)); trials.append((mode, bits, cthr, cfg)); exp.append((pred, lens, cell_model(K, lens, cfg, cthr)))
    dd = tempfile.mkdtemp(); fn = os.path.join(dd, "stim.txt")
    with open(fn, "w") as f:
        f.write("%d %d\n" % (d["T"], ntr))
        for bits, y in d["train"]: f.write("%d %x\n" % (y, sum(b << j for j, b in enumerate(bits))))
        for mode, bits, cthr, cfg in trials: f.write("%d %x %d %s\n" % (mode, sum(b << j for j, b in enumerate(bits)), cthr, " ".join(map(str, cfg))))
    src = ["rtl/tb_hexn_cell_top_v1.v" if top else "rtl/tb_hexn_cellbank_v1.v", "rtl/hexn_tang_top_v9.v", "rtl/hexn_uart_v1.v", "rtl/gen/hexn_lattice_%s_w18_v11.v" % shape, "rtl/hexn_bank_v12.v", "rtl/hexn_det_v3.v", "rtl/hexn_glue_v1.v", "rtl/hexn_cell_v2.v", "rtl/hexn_trainbank_v9.v", "rtl/hexn_cfgbank_v2.v", "rtl/hexn_sdiv_v1.v"]
    defs = ["-DLATMOD=hexn_lattice_%s_v11" % shape, "-DNCLS=%d" % K, "-DCLKDIV=8"] if top else ["-DLAT=hexn_lattice_%s_v11" % shape, "-Ptb_hexn_cellbank_v1.K=%d" % K]
    subprocess.run(["iverilog", "-g2012", "-o", os.path.join(dd, "s.vvp")] + defs + [os.path.join(ROOT, s) for s in src], check=True)
    out = subprocess.run(["vvp", "-n", os.path.join(dd, "s.vvp"), "+stim=" + fn], capture_output=True, text=True).stdout
    got = [l.split()[1:] for l in out.splitlines() if l.startswith("R ")]
    if len(got) != ntr: sys.exit("simulation gave %d results for %d trials" % (len(got), ntr))
    b0 = b1 = bc = bf = bo = 0; n0 = n1 = fired = 0; shown = 0
    for i, (g, (pred, lens, (acc, ccnt))) in enumerate(zip(got, exp)):
        g = [int(x) if x.isdigit() else -1 for x in g]; mode, av, ac = g[0], g[1], g[2]; cnt = g[3:3 + K]; cap = g[3 + K:3 + 2 * K]; fwd, cc = g[3 + 2 * K], g[4 + 2 * K]
        bad0 = (cnt != lens) or ((av and ac) != (pred if pred >= 0 else 0)) or (av != (1 if pred >= 0 else 0)) or (av and ac != pred)
        if mode == 0: n0 += 1; b0 += bad0
        else:
            n1 += 1; b1 += (0 if top else bad0); bc += cap != lens; bf += fwd != acc; bo += cc != ccnt; fired += ccnt > 0
        if (((bad0 and not (top and mode == 1))) or (mode == 1 and (cap != lens or fwd != acc or cc != ccnt))) and shown < 5: shown += 1; print("trial %d mode %d: answer %d/%d expected %d, counts %s expected %s | caps %s | cell total %d (exp %d) burst %d (exp %d)" % (i, mode, av, ac, pred, cnt, lens, cap, fwd, acc, cc, ccnt))
    print("%s: mode 0 trials %d: answer or burst counts wrong %d | mode 1 trials %d: answer/counts wrong %d, captured lengths wrong %d, cell total wrong %d, cell output wrong %d (cell fired in %d)" % (shape, n0, b0, n1, b1, bc, bf, bo, fired))
    sys.exit(0 if not (b0 or b1 or bc or bf or bo) else 1)
if __name__ == "__main__": main()
