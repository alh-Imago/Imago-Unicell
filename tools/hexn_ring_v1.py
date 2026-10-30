"""Hex-N ring design vs single bank, PYTHON MODEL ONLY (new file, 30 Oct 2026; nothing built, no RTL, no card).
Question (Alan, 30 Oct 21:49): does a 'network' (ring 1 = small counted detectors, each hearing only part of the wires;
ring 2 = counted detectors hearing ring 1's bursts) make any real difference to accuracy or size against the single bank
(one counted detector per class, each hearing all wires)?
Detector model (simplified, validated against the recorded 12-wire figure 0.824, see --validate): lane weights +1/-1/0 counted
(up by K-1 when the lane is on in the own class, down by 1 otherwise, saturating +-31; weight +1 if count >= T, -1 if <= -T);
total = sum of weight * lane value, clamped to 0..(2^AW - 1); threshold = rounded midpoint of the mean own-class and other-class
training totals; burst = 0 if total < max(thr,1) else 1 + min(6, total - thr); the answer is the unique highest burst (>0).
Ring 2 lanes carry ring 1's burst lengths (graded) or only whether they fired (token). Training counts use 'lane on' (burst >= 1).
Size: detector logic from the recorded synthesis (Gowin LUT4 + ALU cells counted as logic: about 185 / 263 / 307 for 12 / 18 / 20
lanes), interpolated as 29 + 13 per lane; lane settings and the training side are NOT included. Lane connections = sum over
detectors of the lanes each one hears (a measure of the fan-out wiring)."""
import argparse, random, statistics as st
CAP = 31; AW = 7; TMAX = 16


def sample(rnd, tpl, q): return [b ^ (rnd.random() < q) for b in tpl]


def templates(rnd, n, nb, d):
    while True:
        t = [[rnd.randint(0, 1) for _ in range(nb)] for _ in range(n)]
        if all(sum(a != c for a, c in zip(t[i], t[j])) >= d for i in range(n) for j in range(i)): return t


def train_bank(X, y, K, aw, S):
    nb = len(X[0]); T = max(1, min(TMAX, round(0.5 * S))); cap = (1 << aw) - 1
    cnt = [[0] * nb for _ in range(K)]
    for x, c in zip(X, y):
        for k in range(K):
            d = (K - 1) if c == k else -1
            for j in range(nb):
                if x[j]: cnt[k][j] = max(-CAP, min(CAP, cnt[k][j] + d))
    w = [[(1 if v >= T else -1 if v <= -T else 0) for v in row] for row in cnt]
    thr = []
    for k in range(K):
        pos = [tot(w[k], x, cap) for x, c in zip(X, y) if c == k]; neg = [tot(w[k], x, cap) for x, c in zip(X, y) if c != k]
        mp = sum(pos) / max(1, len(pos)); mn = sum(neg) / max(1, len(neg)); thr.append(max(0, min(cap, round((mp + mn) / 2))))
    return dict(w=w, thr=thr, K=K, cap=cap)


def tot(w, x, cap): return max(0, min(cap, sum(a * b for a, b in zip(w, x))))
def burst(t, thr): return 1 + min(6, t - thr) if (t > 0 and t >= thr) else 0
def bursts(m, x): return [burst(tot(m["w"][k], x, m["cap"]), m["thr"][k]) for k in range(m["K"])]
def answer(g):
    mx = max(g); return g.index(mx) if (mx > 0 and g.count(mx) == 1) else -1


def one_plain(seed, K, nb, q, S, D, parts, mode):
    rnd = random.Random(seed); tpl = templates(rnd, K, nb, D)
    tr = [(sample(rnd, tpl[c], q), c) for c in range(K) for _ in range(S)]; te = [(sample(rnd, tpl[c], q), c) for c in range(K) for _ in range(50)]
    return evaluate(tr, te, K, [(c,) for c in range(K)], nb, parts, S, mode, single_lab=lambda c: [c], sides_k=[K] * parts)


def one_comp(seed, P, ppart, wpart, q, S, mode):
    """Compositional task: P parts, each a pattern of wpart wires chosen from ppart patterns; class = tuple of choices."""
    rnd = random.Random(seed); pt = []
    for _ in range(P): pt.append(templates(rnd, ppart, wpart, max(2, wpart // 3)))
    combos = [()]
    for _ in range(P): combos = [c + (i,) for c in combos for i in range(ppart)]
    K = len(combos); nb = P * wpart
    def mk(c): return sum((pt[p][c[p]] for p in range(P)), [])
    tr = []; te = []
    for ci, c in enumerate(combos):
        for _ in range(S): tr.append((sample(rnd, mk(c), q), ci))
        for _ in range(50): te.append((sample(rnd, mk(c), q), ci))
    return evaluate(tr, te, K, combos, nb, P, S, mode, single_lab=None, sides_k=[ppart] * P)


def evaluate(tr, te, K, combos, nb, parts, S, mode, single_lab, sides_k):
    random.Random(7).shuffle(tr)  # counters saturate, so the training order must be mixed (as in the recorded model)
    X = [x for x, _ in tr]; y = [c for _, c in tr]; wp = nb // parts; res = {}
    # arm 1: single bank, K detectors, all wires
    m = train_bank(X, y, K, AW, S); res["single"] = sum(answer(bursts(m, x)) == c for x, c in te) / len(te)
    # ring 1: one bank per side on its own wires; labels per side
    sides = []
    for p in range(parts):
        lab = [(combos[c][p] if len(combos[0]) == parts else c) for c in y]
        sides.append(train_bank([x[p * wp:(p + 1) * wp] for x in X], lab, sides_k[p], AW, max(1, S * K // sides_k[p])))
    def feat(x, graded):
        f = []
        for p in range(parts):
            b = bursts(sides[p], x[p * wp:(p + 1) * wp]); f += b if graded else [1 if v else 0 for v in b]
        return f
    for graded in (True, False):
        F = [feat(x, graded) for x in X]; on = [[1 if v else 0 for v in f] for f in F]
        # counted training uses 'lane on'; run uses the graded value or the token
        m2 = train_bank(on, y, K, AW, S)
        # threshold from the totals actually seen at run time (graded or token)
        cap = m2["cap"]; thr = []
        for k in range(K):
            pos = [tot(m2["w"][k], f, cap) for f, c in zip(F, y) if c == k]; neg = [tot(m2["w"][k], f, cap) for f, c in zip(F, y) if c != k]
            thr.append(max(0, min(cap, round((sum(pos) / len(pos) + sum(neg) / len(neg)) / 2))))
        m2["thr"] = thr
        ok = sum(answer(bursts(m2, feat(x, graded))) == c for x, c in te); res["ring_graded" if graded else "ring_token"] = ok / len(te)
    # side winners only (no ring 2), for compositional tasks
    if single_lab is None:
        ok = 0
        for x, c in te:
            wn = tuple(answer(bursts(sides[p], x[p * wp:(p + 1) * wp])) for p in range(parts)); ok += (wn == combos[c])
        res["sides_only"] = ok / len(te)
    return res


def lanes_size(nlanes): return 29 + 13 * nlanes


def sizes(K, nb, parts, sides_k):
    wp = nb // parts
    single = dict(det=K, lanes=K * nb, logic=K * lanes_size(nb))
    r1 = sum(sides_k); r1lanes = sum(sides_k[p] * wp for p in range(parts)); r1logic = sum(sides_k[p] * lanes_size(wp) for p in range(parts))
    r2lanes = K * r1; r2logic = K * lanes_size(r1)
    ring = dict(det=r1 + K, lanes=r1lanes + r2lanes, logic=r1logic + r2logic, r1=r1, r2lanes_each=r1)
    return single, ring


def report(name, f, seeds, K, nb, parts, sides_k):
    rs = [f(s) for s in range(seeds)]; keys = list(rs[0])
    line = {k: (st.mean(r[k] for r in rs), st.pstdev(r[k] for r in rs)) for k in keys}
    s, r = sizes(K, nb, parts, sides_k)
    print(f"{name}: K={K} wires={nb} parts={parts}")
    for k in keys: print(f"   {k:12s} {line[k][0]:.3f} (sd {line[k][1]:.3f})")
    print(f"   size single: {s['det']} detectors, {s['lanes']} lane connections, ~{s['logic']} logic cells | ring: {r['det']} detectors, {r['lanes']} lane connections, ~{r['logic']} logic cells (ring 2 detectors hear {r['r2lanes_each']} lanes each)", flush=True)
    return line


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=25); ap.add_argument("--validate", action="store_true"); a = ap.parse_args()
    if a.validate:
        AW = 6
        r = [one_plain(s, 4, 12, 0.15, 16, 4, 1, True)["single"] for s in range(a.seeds)]
        print(f"VALIDATE single bank 12 wires K=4 D=4 noise 0.15 AW 6, {a.seeds} seeds: {st.mean(r):.3f} (recorded real-cell figure 0.824)")
    else:
        for q in (0.15, 0.25):
            print(f"\n===== noise {q} =====")
            for parts in (2, 3):
                report(f"PLAIN 8 classes, {parts} sides", lambda s: one_plain(s, 8, 18, q, 16, 4, parts, True), a.seeds, 8, 18, parts, [8] * parts)
            report("COMPOSITIONAL 2 parts x 4 patterns x 9 wires", lambda s: one_comp(s, 2, 4, 9, q, 16, True), a.seeds, 16, 18, 2, [4, 4])
            report("COMPOSITIONAL 3 parts x 3 patterns x 6 wires", lambda s: one_comp(s, 3, 3, 6, q, 16, True), a.seeds, 27, 18, 3, [3, 3, 3])
