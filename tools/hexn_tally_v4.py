"""Hex-N fully counted detector bank v4 (new file): HARDER TASKS.  Alan, 21 Oct 2026: test under many conditions.  Clone of hexn_tally_v3 (rule --thr-rule mid) with --classes K (K detectors, chance 1/K) and --mindist D (class patterns must differ in at least D of the 12 wires; D=4 and K=4 reproduce the earlier task exactly).
Counting: per detector k and input lane j one up/down counter; a lane that is on while the detector's own class is shown goes UP by (K-1), while any other class goes DOWN by 1 (so the pushes balance), saturating at +-31; after ONE pass over the K*S shuffled training samples the weight is +1 at counter >= T, -1 at <= -T, else off; T = max(1, round(Tfrac * S)) with Tfrac 0.5 (fixed in advance).
Threshold = midpoint of the mean forward total of own-class and other-class training samples (counted).  No search anywhere, the true patterns are never used.  The answer is the detector with strictly the most output clocks, as in the bank.
Also reported: the template rule (nearest true pattern, Hamming distance; an upper reference) and chance.  Files: --out FILE lines 'seed accuracy template-rule'.  Usage: python3 tools/hexn_tally_v4.py --out FILE --classes 8 --mindist 4 [--per-class 16] [--noise 0.15] [--first S] [--runs N]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
t3 = load("hexn_tally_v3"); o = t3.o; b = o.b; v12 = o.v12; N, NB, CAP = o.N, o.NB, t3.CAP


def templates(rnd, K, D):
    while True:
        t = [[rnd.randint(0, 1) for _ in range(NB)] for _ in range(K)]
        if all(sum(a != c for a, c in zip(t[i], t[j])) >= D for i in range(K) for j in range(i)): return t


def one(seed, K, D, q, S, Tfrac=0.5, W=2):
    b.K = K; b.WIRES = [b.wires(k) for k in range(K)]; t3.K = K
    rnd = random.Random(seed); tpl = templates(rnd, K, D)
    train = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(S)]
    test = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(50)]
    sh = random.Random(seed + 5); sh.shuffle(train); sh.shuffle(test)
    T = max(1, round(Tfrac * S)); cnt = [[0] * NB for _ in range(K)]
    for bits, y in train:
        for k in range(K):
            for j in range(NB):
                if bits[j]: cnt[k][j] = max(-CAP, min(CAP, cnt[k][j] + ((K - 1) if y == k else -1)))
    wts = [[(1 if cnt[k][j] >= T else -1 if cnt[k][j] <= -T else 0) for j in range(NB)] for k in range(K)]
    thr = [t3.counted_thr(wts[k], k, train, "mid") for k in range(K)]
    cfgs = [t3.cfg_w(wts[k], thr[k]) for k in range(K)]
    g = b.run_all(cfgs, test, W); acc = sum((max(x) > 0 and x.count(max(x)) == 1 and x.index(max(x)) == y) for (_, y), x in zip(test, g)) / len(test)
    rule = 0
    for bits, y in test:
        d = [sum(x != z for x, z in zip(bits, tp)) for tp in tpl]; m = min(d); rule += d.index(m) == y and d.count(m) == 1
    off = sum(w == 0 for ws in wts for w in ws); right = sum(wts[k][j] == (1 if tpl[k][j] else -1) for k in range(K) for j in range(NB))
    return acc, rule / len(test), right, off, K * NB


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--classes", type=int, default=4); ap.add_argument("--mindist", type=int, default=4)
    ap.add_argument("--per-class", type=int, default=16); ap.add_argument("--noise", type=float, default=0.15); ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); a = ap.parse_args()
    for s in range(a.first, a.first + a.runs):
        acc, rule, right, off, n = one(s, a.classes, a.mindist, a.per_class, a.per_class) if False else one(s, a.classes, a.mindist, a.noise, a.per_class)
        with open(a.out, "a") as f: f.write(f"{s:>4} {acc:>8.2f} {rule:>13.2f}\n")
        print(f"seed {s}: K={a.classes} mindist {a.mindist}: counted {acc:.2f}, template rule {rule:.2f}, chance {1 / a.classes:.2f}; lanes right sign {right}/{n}, off {off}, wrong {n - right - off}", flush=True)
