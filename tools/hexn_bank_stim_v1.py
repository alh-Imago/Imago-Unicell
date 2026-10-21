"""Hex-N bank end-to-end check, Python side. Usage: hexn_bank_stim_v1.py SEED K NB STIMFILE [aw] [S] [noise].
Same training as tools/hexn_trainbank_stim_v1.py (counted detector, tally_v5 rule, threshold = exact rational midpoint rounded half to even), then classifies the 50 test samples per class with the cell MODEL (hexn_tally_v5.run) and writes,
after the training lines, one line per test sample 'label bits c0 .. c(K-1)' (bits as decimal lane mask, c = output clocks of each detector in the last window).  Prints the expected RTL output lines 'label bits pred c0 ..' (pred -1 = tie or silence)
and, on stderr, 'accuracy A  (tally_v5 float-threshold accuracy B)'."""
import sys, os, random, importlib.util
from fractions import Fraction
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("t5", os.path.join(ROOT, "tools", "hexn_tally_v5.py")); t5 = importlib.util.module_from_spec(sp); sp.loader.exec_module(t5)
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
thr = []; thr_f = []
for k in range(K):
    fw = [(t5.run(t5.cfg_w(wts[k], 0, NB), bits, NB)[1], y == k) for bits, y in train]
    pos = [v for v, p in fw if p]; neg = [v for v, p in fw if not p]
    R = (Fraction(sum(pos), len(pos)) + Fraction(sum(neg), len(neg))) / 2
    thr.append(max(0, min((1 << AW) - 1, round(R)))); thr_f.append(max(0, min(1 << AW, round((sum(pos) / len(pos) + sum(neg) / len(neg)) / 2))))
def classify(th):
    cf = [t5.cfg_w(wts[k], th[k], NB) for k in range(K)]; ok = 0; rows = []
    for bits, y in test:
        g = [t5.run(c, bits, NB)[0] for c in cf]; m = max(g); pred = g.index(m) if (m > 0 and g.count(m) == 1) else -1
        ok += (pred == y); rows.append((y, sum(1 << j for j in range(NB) if bits[j]), pred, g))
    return ok / len(test), rows
acc, rows = classify(thr); accf, _ = classify(thr_f)
with open(stim, "w") as f:
    f.write(f"{K} {NB} {S} {T}\n")
    for bits, y in train: f.write("%d %d\n" % (y, sum(1 << j for j in range(NB) if bits[j])))
    for y, b, pred, g in rows: f.write("%d %d %s\n" % (y, b, " ".join(map(str, g))))
for y, b, pred, g in rows: print(y, b, pred, *g)
print(f"accuracy {acc:.3f}  (tally_v5 float-threshold accuracy {accf:.3f})", file=sys.stderr)
