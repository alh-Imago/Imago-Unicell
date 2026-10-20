"""Hex-N cluster v17 (new file): GROW FROM MINIMAL cells plus STUCK PRUNING (Alan's proposal, 20 Oct 2026).
Same cluster, layout, classes, noise, samples, learner and local per-group rewards as v16.  Two changes:
1. Every cell starts with just ONE receiving lane and ONE sending lane (random lanes; all other lanes inactive).  Growth = the normal mutation that switches a lane on.
2. Stuck pruning: every --every tries the current cluster is run on the training samples and each ACTIVE lane whose received signal is the same for every sample ('stuck')
   gets a counter; a lane stuck for --k checks in a row is switched OFF (zeroed).  --prune off|high|both: 'high' = only lanes stuck at a non-zero level, 'both' = stuck at any level.
Arms: --start minimal|easy (easy = the v16 start).
Usage: python3 tools/hexn_cluster_v17.py [--start minimal|easy] [--prune off|high|both] [--every E] [--k K] [--runs N] [--first S] [--tries T] [--noise Q] [--diag]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
v16 = load("hexn_cluster_v16"); c15 = v16.c15; mc = c15.mc; N, P, PL = c15.N, c15.P, c15.PL


def minimal(r):
    a = [0] * N; d = [r.choice([0, 1, 1, 2, 3]) for _ in range(N)]; c = [r.choice([1, 1, 2, 0]) for _ in range(N)]
    i = r.randrange(N); o = r.randrange(N)
    while o == i: o = r.randrange(N)
    a[i] = a[o] = 1; d[i] = 0; d[o] = 1
    return (a, d, c, [r.randint(0, 1)], 0)


def rx_profile(topo, cfgs, bits):
    """Run one sample; return for each cell and lane the number of clocks the lane received a 1 (same wiring as c15.respond)."""
    cells = [mc.MixCell(*c) for c in cfgs]; seen = [[0] * N for _ in cells]; ins = {}
    for j, (i, lane) in enumerate(topo.inputs): ins[(i, lane)] = j
    for w in range(topo.W):
        for phase in (0, 1):
            for t in range(PL):
                tx = [c.tx(phase) for c in cells]
                for i, c in enumerate(cells):
                    rx = [0] * N
                    for f in range(6):
                        nb = topo.nbr[i][f]
                        if nb is not None:
                            src = tx[nb]; o = ((f + 3) % 6) * P
                            for p in range(P): rx[f * P + p] = src[o + p]
                    for (ii, lane), j in ins.items():
                        if ii == i: rx[lane] = bits[j]
                    for l in range(N): seen[i][l] += rx[l]
                    c.clock(rx, phase, int(t == 0), int(phase == 1 and t == PL - 1))
    return seen


def stuck_lanes(topo, cfgs, data, mode):
    prof = [rx_profile(topo, cfgs, b) for b, _ in data]; out = set()
    for i in range(len(cfgs)):
        for l in range(N):
            if not cfgs[i][0][l]: continue
            vals = {p[i][l] for p in prof}
            if len(vals) == 1 and (mode == "both" or next(iter(vals)) > 0): out.add((i, l))
    return out


def one(seed, R, q, tries, S, start, prune, every, kk, warm=100, diag=False):
    topo = c15.Topo(R); rnd = random.Random(seed); tpl = c15.v12.make_templates(rnd, 4)
    train = [(c15.v12.sample(rnd, tpl[y], q), y) for y in range(4) for _ in range(S)]
    test = [(c15.v12.sample(rnd, tpl[y], q), y) for y in range(4) for _ in range(50)]
    lf = c15.v6.Lfsr(seed + 77); n = len(topo.cells); mk = minimal if start == "minimal" else c15.easy
    best = None; br = -1
    for _ in range(warm):
        c = [mk(lf) for _ in range(n)]; r = v16.local_rewards(topo, c, train)
        if r > br: best, br = c, r
    cur, cr = best, br; cnt = {}; pruned = 0; hist = [cr]
    for t in range(tries - warm):
        nxt = list(cur)
        for _ in range(1 + lf.randrange(3)):
            j = lf.randrange(n); nxt[j] = c15.mutate(nxt[j], lf)
        r = v16.local_rewards(topo, nxt, train)
        if r >= cr: cur, cr = nxt, r
        if prune != "off" and (t + 1) % every == 0:
            st = stuck_lanes(topo, cur, train, prune)
            for key in list(cnt):
                if key not in st: del cnt[key]
            for key in st: cnt[key] = cnt.get(key, 0) + 1
            kill = [key for key, v in cnt.items() if v >= kk]
            if kill:
                cur = list(cur)
                for i, l in kill:
                    a = list(cur[i][0]); a[l] = 0; cur[i] = (a,) + tuple(cur[i][1:]); cnt.pop((i, l)); pruned += 1
                cr = v16.local_rewards(topo, cur, train)
        if (t + 1) % 100 == 0: hist.append(cr)
    active = sum(sum(c[0]) for c in cur)
    if diag: print("   reward history", hist, "active lanes", active, "pruned", pruned)
    return c15.accuracy(topo, cur, test), c15.v12.template_rule(tpl, test), active, pruned


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--radius", type=int, default=1); ap.add_argument("--noise", type=float, default=0.15)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); ap.add_argument("--tries", type=int, default=600)
    ap.add_argument("--per-class", type=int, default=16); ap.add_argument("--start", default="minimal"); ap.add_argument("--prune", default="off")
    ap.add_argument("--every", type=int, default=50); ap.add_argument("--k", type=int, default=3); ap.add_argument("--diag", action="store_true"); a = ap.parse_args()
    print(f"hex cluster radius {a.radius}, start {a.start}, prune {a.prune} (every {a.every} tries, k={a.k}), local rewards, noise {a.noise}, {a.tries} tries")
    print(f"{'seed':>4} {'learned':>8} {'template-rule':>13} {'active':>7} {'pruned':>7}")
    tot = 0
    for s in range(a.first, a.first + a.runs):
        l, t, ac, pr = one(s, a.radius, a.noise, a.tries, a.per_class, a.start, a.prune, a.every, a.k, diag=a.diag); tot += l
        print(f"{s:>4} {l:>8.2f} {t:>13.2f} {ac:>7} {pr:>7}", flush=True)
    print(f"mean learned {tot / a.runs:.2f}")
