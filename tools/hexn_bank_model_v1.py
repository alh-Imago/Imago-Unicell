"""Hex-N counted-detector bank, Python model as functions (same rules as tools/hexn_tally_v5.py; threshold = exact rational midpoint rounded half to even as in the RTL). Used by tools/hexn_tang_host_v1.py.
make(seed, K, NB, AW, S, q) -> dict(train=[(bits_list, label)], test=[...], T, wts, thr); classify(model, samples) -> [(pred, counts)] with pred -1 for a tie or silence; sample(rnd, template, q) makes a noisy copy."""
import os, random, importlib.util
from fractions import Fraction
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_sp = importlib.util.spec_from_file_location("t5", os.path.join(ROOT, "tools", "hexn_tally_v5.py")); t5 = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(t5)
def sample(rnd, tpl, q): return t5.v12.sample(rnd, tpl, q)
def make(seed, K, NB=12, AW=6, S=16, q=0.15, per_test=50, D=4):
    t5.mc.AW = AW; CAP = t5.CAP; rnd = random.Random(seed)
    while True:
        tpl = [[rnd.randint(0, 1) for _ in range(NB)] for _ in range(K)]
        if all(sum(a != c for a, c in zip(tpl[i], tpl[j])) >= D for i in range(K) for j in range(i)): break
    train = [(sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(S)]
    test = [(sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(per_test)]
    sh = random.Random(seed + 5); sh.shuffle(train); sh.shuffle(test)
    T = max(1, round(0.5 * S)); cnt = [[0] * NB for _ in range(K)]
    for bits, y in train:
        for k in range(K):
            for j in range(NB):
                if bits[j]: cnt[k][j] = max(-CAP, min(CAP, cnt[k][j] + ((K - 1) if y == k else -1)))
    wts = [[(1 if cnt[k][j] >= T else -1 if cnt[k][j] <= -T else 0) for j in range(NB)] for k in range(K)]
    thr = []; sump = []; sumn = []
    for k in range(K):
        fw = [(t5.run(t5.cfg_w(wts[k], 0, NB), bits, NB)[1], y == k) for bits, y in train]
        pos = [v for v, p in fw if p]; neg = [v for v, p in fw if not p]
        sump.append(sum(pos)); sumn.append(sum(neg))
        R = (Fraction(sum(pos), len(pos)) + Fraction(sum(neg), len(neg))) / 2
        thr.append(max(0, min((1 << AW) - 1, round(R))))
    return dict(K=K, NB=NB, AW=AW, S=S, q=q, tpl=tpl, cnt=cnt, train=train, test=test, T=T, wts=wts, thr=thr, sump=sump, sumn=sumn, seed=seed, D=D)
def classify(m, samples):
    t5.mc.AW = m["AW"]; K, NB = m["K"], m["NB"]; cf = [t5.cfg_w(m["wts"][k], m["thr"][k], NB) for k in range(K)]; out = []
    for bits, y in samples:
        g = [t5.run(c, bits, NB)[0] for c in cf]; mx = max(g); out.append((g.index(mx) if (mx > 0 and g.count(mx) == 1) else -1, g))
    return out
