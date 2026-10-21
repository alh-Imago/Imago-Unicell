"""Hex-N tally-trained bank v3 (new file).  Alan, 21 Oct 2026: set each detector's lane weights by COUNTING, not by trial and error; the counter's commit threshold is the dial.
Per detector k (one per class) and per input lane j there is one up/down counter.  One pass over the 64 shuffled training samples (--epochs for more): for every lane that is ON (bit 1) in a sample, the counter goes UP by 3 if the sample is of detector k's own class, DOWN by 1 if it is any other class (3 other classes, so the pushes balance).
Counters saturate at +-CAP (31).  After the pass: counter >= +T -> lane weight +1 (gate code 1), counter <= -T -> weight -1 (code 3), otherwise the lane stays OFF.  The four detector THRESHOLDS are then tuned exactly as in hexn_oracle_v2 (coordinate descent on the training samples, 3 passes, 0..63); nothing else is tuned and the true template is never used.
Reported per seed: test accuracy on the 200 fresh samples, and (diagnostic) how many lanes the tally got the right sign on / left off / got wrong, judged against the true template signs.  Same seeds, data, noise, W=2 and answer rule as the bank, the learning curve and the hand-set bank.
v2 (new file, clone of v1): --per-class S (training samples per class, default 16) and --Tfrac F: commit threshold T = max(1, round(F * S)) (default F 0.5, so S=16 gives T=8 = v1 exactly); the rule is fixed in advance so the counters scale with the amount of training data.
v3 (new file, clone of v2): --thr-rule says how each detector's THRESHOLD is set once the lane weights are counted. search = v2 (coordinate descent on the training samples scored by the final answer). hist = COUNTED: each detector is run alone on every training sample and its forward total at window end is noted (a score histogram for own-class samples and one for the other classes: two small count tables); the threshold is the value (0..63) that maximises own-class share firing + other-class share silent (balanced accuracy of that one detector), ties go to the higher value; no joint search, each detector on its own. mid = the threshold is the midpoint between the mean forward total of own-class samples and the mean of other-class samples (two running averages).
Usage: python3 tools/hexn_tally_v3.py --T 8 --out FILE [--epochs 1] [--first S] [--runs N] [--noise Q]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
o = load("hexn_oracle_v2"); b = o.b; v12 = o.v12; K, N, NB = 4, o.N, o.NB; CAP = 31


def cfg_w(weights, thr):
    a = [0] * N; d = [0] * N; c = [0] * N
    for j in range(NB):
        if weights[j]: a[j] = 1; d[j] = 0; c[j] = 1 if weights[j] > 0 else 3
    a[12] = 1; d[12] = 1; c[12] = 1
    return (a, d, c, [thr], 0)


def fwd_of(cfg, bits, W=2):
    c = b.mc.MixCell(*cfg)
    for w in range(W):
        for phase in (0, 1):
            for tt in range(b.PL):
                rx = [0] * N
                for j in range(NB): rx[j] = bits[j]
                c.clock(rx, phase, int(tt == 0), int(phase == 1 and tt == b.PL - 1))
    return c.fwd


def counted_thr(wk, k, train, rule):
    f = [(fwd_of(cfg_w(wk, 0), bits), y == k) for bits, y in train]
    pos = [v for v, p in f if p]; neg = [v for v, p in f if not p]
    if rule == "mid": return max(0, min(63, round((sum(pos) / len(pos) + sum(neg) / len(neg)) / 2)))
    best, bt = -1, 0
    for t in range(64):
        s = sum(v >= t for v in pos) / len(pos) + sum(v < t for v in neg) / len(neg)
        if s >= best: best, bt = s, t
    return bt


def one(seed, q, T, epochs, S=16, W=2, rule="search"):
    rnd = random.Random(seed); tpl = v12.make_templates(rnd, K)
    train = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(S)]
    test = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(50)]
    sh = random.Random(seed + 5); sh.shuffle(train); sh.shuffle(test)
    cnt = [[0] * NB for _ in range(K)]
    for _ in range(epochs):
        for bits, y in train:
            for k in range(K):
                for j in range(NB):
                    if bits[j]: cnt[k][j] = max(-CAP, min(CAP, cnt[k][j] + (3 if y == k else -1)))
    wts = [[(1 if cnt[k][j] >= T else -1 if cnt[k][j] <= -T else 0) for j in range(NB)] for k in range(K)]
    right = sum(wts[k][j] == (1 if tpl[k][j] else -1) for k in range(K) for j in range(NB)); off = sum(wts[k][j] == 0 for k in range(K) for j in range(NB))
    thr = [10 * max(1, sum(1 for x in wts[k] if x > 0) * 7 // 10) for k in range(K)]; thr = [min(63, x) for x in thr]
    if rule != "search": thr = [counted_thr(wts[k], k, train, rule) for k in range(K)]
    best = o.acc([cfg_w(wts[k], thr[k]) for k in range(K)], train)
    for _ in range(3 if rule == "search" else 0):
        for k in range(K):
            for t in range(64):
                trial = list(thr); trial[k] = t; r = o.acc([cfg_w(wts[i], trial[i]) for i in range(K)], train)
                if r > best: best, thr = r, trial
    return o.acc([cfg_w(wts[k], thr[k]) for k in range(K)], test), best, v12.template_rule(tpl, test), right, off, K * NB


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--T", type=int, default=0); ap.add_argument("--Tfrac", type=float, default=0.5); ap.add_argument("--per-class", type=int, default=16); ap.add_argument("--thr-rule", default="search"); ap.add_argument("--epochs", type=int, default=1); ap.add_argument("--noise", type=float, default=0.15)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); a = ap.parse_args()
    for s in range(a.first, a.first + a.runs):
        t, tr, rule, right, off, n = one(s, a.noise, a.T if a.T else max(1, round(a.Tfrac * a.per_class)), a.epochs, a.per_class, 2, a.thr_rule)
        with open(a.out, "a") as f: f.write(f"{s:>4} {t:>8.2f} {rule:>13.2f}\n")
        print(f"seed {s}: tally {a.thr_rule} T={a.T if a.T else max(1, round(a.Tfrac * a.per_class))} S={a.per_class} test {t:.2f} (train {tr:.2f}); lanes right sign {right}/{n}, off {off}, wrong sign {n - right - off}", flush=True)
