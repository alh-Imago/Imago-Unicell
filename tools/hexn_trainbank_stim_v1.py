"""Hex-N training bank check, Python side. Usage: hexn_trainbank_stim_v1.py SEED K NB STIMFILE [aw] [S] [noise].
Runs exactly the counted-detector training of tools/hexn_tally_v5.py (same templates, samples, shuffle, counting, weights, midpoint threshold using the cell model's own run()), writes the training samples to STIMFILE for the RTL
testbench (first line 'K NB S T', then one line 'label bits' per sample, bit j = input lane j, in training order) and prints the expected result: one line per detector 'k wpos wneg thr' (wpos/wneg as decimal lane masks).
The threshold is printed as the exact rational rule rounded half to even (what the RTL does); a trailing note says if the float expression the Python model uses gave a different number."""
import sys, os, random, importlib.util
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("t5", os.path.join(ROOT, "tools", "hexn_tally_v5.py")); t5 = importlib.util.module_from_spec(sp); sp.loader.exec_module(t5)
from fractions import Fraction
seed, K, NB, stim = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
AW = int(sys.argv[5]) if len(sys.argv) > 5 else 6; S = int(sys.argv[6]) if len(sys.argv) > 6 else 16; q = float(sys.argv[7]) if len(sys.argv) > 7 else 0.15
t5.mc.AW = AW; v12 = t5.v12; CAP = t5.CAP; D = 4
rnd = random.Random(seed)
while True:
    tpl = [[rnd.randint(0, 1) for _ in range(NB)] for _ in range(K)]
    if all(sum(a != c for a, c in zip(tpl[i], tpl[j])) >= D for i in range(K) for j in range(i)): break
train = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(S)]
test = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(50)]
sh = random.Random(seed + 5); sh.shuffle(train); sh.shuffle(test)
T = max(1, round(0.5 * S)); cnt = [[0] * NB for _ in range(K)]
for bits, y in train:
    for k in range(K):
        for j in range(NB):
            if bits[j]: cnt[k][j] = max(-CAP, min(CAP, cnt[k][j] + ((K - 1) if y == k else -1)))
wts = [[(1 if cnt[k][j] >= T else -1 if cnt[k][j] <= -T else 0) for j in range(NB)] for k in range(K)]
with open(stim, "w") as f:
    f.write(f"{K} {NB} {S} {T}\n")
    for bits, y in train: f.write("%d %d\n" % (y, sum(1 << j for j in range(NB) if bits[j])))
note = []
for k in range(K):
    fw = [(t5.run(t5.cfg_w(wts[k], 0, NB), bits, NB)[1], y == k) for bits, y in train]
    pos = [v for v, p in fw if p]; neg = [v for v, p in fw if not p]
    R = (Fraction(sum(pos), len(pos)) + Fraction(sum(neg), len(neg))) / 2
    fl = max(0, min(1 << AW, round((sum(pos) / len(pos) + sum(neg) / len(neg)) / 2)))
    th = max(0, min((1 << AW) - 1, round(R)))          # Fraction round() is half to even
    if th != fl: note.append(f"detector {k}: rational {th}, float {fl}")
    wp = sum(1 << j for j in range(NB) if wts[k][j] > 0); wn = sum(1 << j for j in range(NB) if wts[k][j] < 0)
    print(k, wp, wn, th)
if note: print("NOTE float expression differs:", "; ".join(note), file=sys.stderr)
