"""The leak model of tools/hexn_leak_model_v2.py run THROUGH THE RTL (simulation): hex7 bank (trained on a script), K leaky cells (hexn_cell_v4 via hexn_bank_v15, hexn_lattice_hex7_v14), cell g one-hot positive on detector g, so its forward total is class g's accumulator. Episodes of scene A (L windows) then scene B (L windows); each window is a fresh noisy copy; the first window of an episode uses leak setting 0 (cleared), the others the tested setting s (total becomes a - (a >> s); 7 = keep). Per frame the RTL totals are compared with the Python chain (must be identical) and the unique-highest-total answer is scored.
Usage: python3 tools/hexn_leak_rtl_v1.py SCRIPT [NOISE] [SCENES_PER_CLASS] """
import sys, os, random, subprocess, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_tang_script_v1 as S1, hexn_cellbank_check_v4 as C4
d = S1.parse_script(open(sys.argv[1]).read()); noise = float(sys.argv[2]) if len(sys.argv) > 2 else 0.15; per = int(sys.argv[3]) if len(sys.argv) > 3 else 12
K, NB, AW = d["classes"], d["wires"], d["aw"]; assert K == 7 and NB == 18 and AW == 7 and len(d["train"]) == K * 16
m = S1.make_model(d, 16); tpl = {}
for bits, y in d["train"] + d["test"]: tpl.setdefault(y, []).append(bits)
L = 8; SETTINGS = [("clear", 0), ("half", 1), ("a-a>>2", 2), ("a-a>>3", 3), ("none", 7)]; r = random.Random(11); episodes = []
for ya in range(K):
    for _ in range(per):
        yb = r.choice([c for c in range(K) if c != ya]); ba = r.choice(tpl[ya]); bb = r.choice(tpl[yb])
        fr = [[b ^ (1 if r.random() < noise else 0) for b in (ba if w < L else bb)] for w in range(2 * L)]; episodes.append((ya, yb, fr))
onehot = [[1 if j == g else 0 for j in range(K)] for g in range(K)]
trials = []
for name, s in SETTINGS:
    for ya, yb, fr in episodes:
        for w, bits in enumerate(fr): trials.append((1, bits, 0 if w == 0 else s))
dd = tempfile.mkdtemp(); fn = os.path.join(dd, "stim.txt")
with open(fn, "w") as f:
    f.write("%d %d\n" % (d["T"], len(trials)))
    for bits, y in d["train"]: f.write("%d %x\n" % (y, sum(b << j for j, b in enumerate(bits))))
    for mode, bits, lk in trials: f.write("%d %x %d %s\n" % (mode, sum(b << j for j, b in enumerate(bits)), lk, " ".join("0 " + " ".join(map(str, onehot[g])) for g in range(K))))
src = ["rtl/tb_hexn_cellbank_v3.v", "rtl/gen/hexn_lattice_hex7_w18_v14.v", "rtl/hexn_bank_v15.v", "rtl/hexn_det_v3.v", "rtl/hexn_glue_v1.v", "rtl/hexn_cell_v4.v", "rtl/hexn_trainbank_v9.v", "rtl/hexn_cfgbank_v2.v", "rtl/hexn_sdiv_v1.v"]
subprocess.run(["iverilog", "-g2012", "-o", os.path.join(dd, "s.vvp"), "-DLAT=hexn_lattice_hex7_v14", "-Ptb_hexn_cellbank_v3.K=7", "-Ptb_hexn_cellbank_v3.NC=7"] + [os.path.join(ROOT, x) for x in src], check=True)
out = subprocess.run(["vvp", "-n", os.path.join(dd, "s.vvp"), "+stim=" + fn], capture_output=True, text=True).stdout
got = [l.split()[1:] for l in out.splitlines() if l.startswith("R ")]
assert len(got) == len(trials), (len(got), len(trials))
KS = (0, 1, 2, 3, 4, 6, 8); print("RTL, noise %.2f, %d episodes per setting (scene A %d windows then B %d); share of episodes where the unique highest class total is the scene's true class, k windows after the switch (k=0: last window of A)" % (noise, len(episodes), L, L))
print("%-8s" % "leak" + "".join("  k=%d  " % k for k in KS)); mism = 0; idx = 0
for name, s in SETTINGS:
    hit = [0] * len(KS)
    for ya, yb, fr in episodes:
        state = [0] * K
        for w in range(2 * L):
            lens = S1.classify(m, fr[w])[1]; lk = 0 if w == 0 else s; state = [C4.cell_run(K, lens, onehot[g], 0, C4.leaked(state[g], lk))[0] for g in range(K)]
            g = [int(x) for x in got[idx][3 + 2 * K:]]; tot = g[0::2]; idx += 1; mism += tot != state
            k = w + 1 - L
            if k in KS: truth = ya if k == 0 else yb; mx = max(tot); hit[KS.index(k)] += (tot.count(mx) == 1 and tot[truth] == mx and mx > 0)
    print("%-8s" % name + "".join(" %.3f " % (h / len(episodes)) for h in hit))
print("frames where the RTL class totals differ from the Python chain: %d of %d" % (mism, len(trials)))
