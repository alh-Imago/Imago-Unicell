"""Hex-N fully counted detector bank v5 (new file): WIDER INPUT.  Alan, 21 Oct 2026: widen the wires to at least 18 (a multiple of 6).  Clone of hexn_tally_v4 (rule MID, counted lane weights, counted threshold) but self-contained and with --wires NB input lanes (lanes 0..NB-1, receive-only) and the output on lane 20 (face 5), so NB can be 12, 18 or 20 of the cell's 24 lanes.
--aw sets the accumulator width of the cell (default 6 = the cell as built: the forward total saturates at 63, about 6 agreeing lanes; 8 gives 255) because wider patterns may saturate it.  NB=12 and aw=6 reproduce hexn_tally_v4 exactly.
Counting, threshold and answer rule exactly as in hexn_tally_v4 (up by K-1 / down by 1, T = half the samples per class, midpoint threshold, strictly most clocks wins).  Files: --out FILE lines 'seed accuracy template-rule'.
Usage: python3 tools/hexn_tally_v5.py --out FILE --classes 8 --mindist 4 --wires 18 [--aw 6] [--per-class 16] [--noise 0.15] [--first S] [--runs N]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
t4 = load("hexn_tally_v4"); b = t4.b; mc = b.mc; v12 = t4.v12; CAP = t4.CAP; N = mc.N; PL = b.PL; OUT = 20


def cfg_w(weights, thr, NB):
    a = [0] * N; d = [0] * N; c = [0] * N
    for j in range(NB):
        if weights[j]: a[j] = 1; d[j] = 0; c[j] = 1 if weights[j] > 0 else 3
    a[OUT] = 1; d[OUT] = 1; c[OUT] = 1
    return (a, d, c, [thr], 0)


def run(cfg, bits, NB, W=2):
    c = mc.MixCell(*cfg); n = 0
    for w in range(W):
        for phase in (0, 1):
            for t in range(PL):
                tx = c.tx(phase)
                if w == W - 1: n += sum(tx[OUT:OUT + 4])
                rx = [0] * N
                for j in range(NB): rx[j] = bits[j]
                c.clock(rx, phase, int(t == 0), int(phase == 1 and t == PL - 1))
    return n, c.fwd


def one(seed, K, D, NB, q, S, Tfrac=0.5):
    rnd = random.Random(seed)
    while True:
        tpl = [[rnd.randint(0, 1) for _ in range(NB)] for _ in range(K)]
        if all(sum(a != c for a, c in zip(tpl[i], tpl[j])) >= D for i in range(K) for j in range(i)): break
    train = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(S)]
    test = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(50)]
    sh = random.Random(seed + 5); sh.shuffle(train); sh.shuffle(test)
    T = max(1, round(Tfrac * S)); cnt = [[0] * NB for _ in range(K)]
    for bits, y in train:
        for k in range(K):
            for j in range(NB):
                if bits[j]: cnt[k][j] = max(-CAP, min(CAP, cnt[k][j] + ((K - 1) if y == k else -1)))
    wts = [[(1 if cnt[k][j] >= T else -1 if cnt[k][j] <= -T else 0) for j in range(NB)] for k in range(K)]
    thr = []
    for k in range(K):
        f = [(run(cfg_w(wts[k], 0, NB), bits, NB)[1], y == k) for bits, y in train]
        pos = [v for v, p in f if p]; neg = [v for v, p in f if not p]
        thr.append(max(0, min(1 << mc.AW, round((sum(pos) / len(pos) + sum(neg) / len(neg)) / 2))))
    cfgs = [cfg_w(wts[k], thr[k], NB) for k in range(K)]; ok = 0
    for bits, y in test:
        g = [run(c, bits, NB)[0] for c in cfgs]; ok += (max(g) > 0 and g.count(max(g)) == 1 and g.index(max(g)) == y)
    rule = 0
    for bits, y in test:
        dd = [sum(x != z for x, z in zip(bits, tp)) for tp in tpl]; m = min(dd); rule += dd.index(m) == y and dd.count(m) == 1
    right = sum(wts[k][j] == (1 if tpl[k][j] else -1) for k in range(K) for j in range(NB)); off = sum(w == 0 for ws in wts for w in ws)
    return ok / len(test), rule / len(test), right, off, K * NB


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--classes", type=int, default=4); ap.add_argument("--mindist", type=int, default=4); ap.add_argument("--wires", type=int, default=12); ap.add_argument("--aw", type=int, default=6)
    ap.add_argument("--per-class", type=int, default=16); ap.add_argument("--noise", type=float, default=0.15); ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); a = ap.parse_args()
    mc.AW = a.aw
    for s in range(a.first, a.first + a.runs):
        acc, rule, right, off, n = one(s, a.classes, a.mindist, a.wires, a.noise, a.per_class)
        with open(a.out, "a") as f: f.write(f"{s:>4} {acc:>8.2f} {rule:>13.2f}\n")
        print(f"seed {s}: K={a.classes} D={a.mindist} wires {a.wires} aw {a.aw}: counted {acc:.2f}, template rule {rule:.2f}; lanes right {right}/{n}, off {off}, wrong {n - right - off}", flush=True)
