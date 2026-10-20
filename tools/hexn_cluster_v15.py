"""Hex-N hex CLUSTER simulator and pattern test v15 (new file). VM only. Cells = the v2 model (faces feed one decision).

Layout: cells in a hexagonal patch of radius R (R=1: 7 cells, R=2: 19). Face f of a cell is wired to face (f+3)%6 of the neighbour in direction f, lane for lane, in the same clock;
faces with no neighbour are EXTERNAL.  The 12 input wires enter on the 12 lanes of 3 consecutive external faces; the answer is read from the other side of the patch (8 external
faces, 2 per class).  Each external lane can only carry what the cell on that face sends.  A sample is shown for 2R+3 windows (one window of delay per hop) to a fresh cluster.
Classes/templates/noise/baselines as in v13.  Training = the v6 learner on the WHOLE cluster with one reward (4 bits; accuracy plus the share of output in the right group):
warm start (best of 100 random clusters), then keep-or-undo with 1-3 settings changed per try in randomly chosen cells.  All cells and all random baselines come from the same
'signal-passing' family (95% lanes active, mostly forward lanes, gate codes OR/XOR/AND, threshold 0-1), because random cells rarely pass anything on.
--check prints, before any training, how often the output changes when the input changes (a cluster whose output ignores the input would teach nothing).
Usage: python3 tools/hexn_cluster_v15.py [--radius R] [--noise Q] [--first S] [--runs N] [--tries T] [--per-class S] [--check]"""
import argparse, importlib.util, math, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
v6, v12, mc = load("hexn_learner_v6"), load("hexn_patterns_v12"), load("hexn_cell_v2_model")
N, F, P, PL, NB = mc.N, mc.F, mc.P, 10, 12
DIRS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]


class Topo:
    def __init__(self, R):
        self.cells = [(q, r) for q in range(-R, R + 1) for r in range(-R, R + 1) if max(abs(q), abs(r), abs(q + r)) <= R]
        idx = {c: i for i, c in enumerate(self.cells)}
        self.nbr = [[idx.get((q + dq, r + dr)) for dq, dr in DIRS] for q, r in self.cells]
        ext = [(i, f) for i in range(len(self.cells)) for f in range(6) if self.nbr[i][f] is None]
        def ang(e):
            q, r = self.cells[e[0]]; dq, dr = DIRS[e[1]]
            x = (q + r / 2) + 0.5 * (dq + dr / 2); y = (r + 0.5 * dr) * math.sqrt(3) / 2
            return math.atan2(y, x)
        self.ext = sorted(ext, key=ang); n = len(self.ext)
        self.inputs = [(i, f * P + p) for (i, f) in self.ext[0:3] for p in range(P)][:NB]
        self.outputs = [[(i, f * P + p) for (i, f) in self.ext[n // 2 - 1 + 2 * g: n // 2 + 1 + 2 * g] for p in range(P)] for g in range(4)]
        self.W = 2 * R + 3


def easy(r):
    return ([int(r.random() < 0.95) for _ in range(N)], [r.choice([0, 1, 1, 2, 3]) for _ in range(N)], [r.choice([1, 1, 2, 0]) for _ in range(N)], [r.randint(0, 1)], 0)


def mutate(cfg, r):
    a, d, c, t, b = [list(x) if isinstance(x, list) else x for x in cfg]; k = r.randrange(5)
    if k == 0: i = r.randrange(N); a[i] ^= 1
    elif k == 1: i = r.randrange(N); d[i] = r.randint(0, 3)
    elif k == 2: i = r.randrange(N); c[i] = r.randint(0, 3)
    elif k == 3: t[0] = max(0, min(7, t[0] + r.choice([-1, 1])))
    else: b = max(0, min(3, b + r.choice([-1, 1])))
    return (a, d, c, t, b)


def respond(topo, cfgs, bits, K=4):
    cells = [mc.MixCell(*c) for c in cfgs]; nc = len(cells); counts = [0] * 4
    ins = {}
    for j, (i, lane) in enumerate(topo.inputs): ins[(i, lane)] = j
    for w in range(topo.W):
        for phase in (0, 1):
            for t in range(PL):
                tx = [c.tx(phase) for c in cells]
                if w == topo.W - 1:
                    for g in range(4): counts[g] += sum(tx[i][lane] for (i, lane) in topo.outputs[g])
                for i, c in enumerate(cells):
                    rx = [0] * N
                    for f in range(6):
                        nb = topo.nbr[i][f]
                        if nb is not None:
                            src = tx[nb]; o = ((f + 3) % 6) * P
                            for p in range(P): rx[f * P + p] = src[o + p]
                    for (ii, lane), j in ins.items():
                        if ii == i: rx[lane] = bits[j]
                    c.clock(rx, phase, int(t == 0), int(phase == 1 and t == PL - 1))
    return counts[:K]


def reward(topo, cfgs, data):
    acc = share = 0
    for bits, y in data:
        g = respond(topo, cfgs, bits); m = max(g)
        acc += (m > 0 and g.count(m) == 1 and g.index(m) == y); share += g[y] / sum(g) if sum(g) else 0
    return round(1000 * (0.7 * acc / len(data) + 0.3 * share / len(data)))


def accuracy(topo, cfgs, data):
    ok = 0
    for bits, y in data:
        g = respond(topo, cfgs, bits); m = max(g); ok += (m > 0 and g.count(m) == 1 and g.index(m) == y)
    return ok / len(data)


def one(seed, R, q, tries, S, warm=100, bits=4):
    topo = Topo(R); rnd = random.Random(seed); tpl = v12.make_templates(rnd, 4)
    train = [(v12.sample(rnd, tpl[y], q), y) for y in range(4) for _ in range(S)]
    test = [(v12.sample(rnd, tpl[y], q), y) for y in range(4) for _ in range(50)]
    Q = lambda c: reward(topo, c, train) * ((1 << bits) - 1) // 1000
    lf = v6.Lfsr(seed + 77); n = len(topo.cells); best = None; br = -1
    for _ in range(warm):
        c = [easy(lf) for _ in range(n)]; r = Q(c)
        if r > br: best, br = c, r
    cur, cr = best, br
    for _ in range(tries - warm):
        nxt = list(cur)
        for _ in range(1 + lf.randrange(3)):
            j = lf.randrange(n); nxt[j] = mutate(nxt[j], lf)
        r = Q(nxt)
        if r >= cr: cur, cr = nxt, r
    rr = random.Random(seed + 1)
    rb = max(([easy(rr) for _ in range(n)] for _ in range(tries)), key=lambda c: reward(topo, c, train))
    return accuracy(topo, cur, test), accuracy(topo, rb, test), v12.template_rule(tpl, test)


def check(R):
    topo = Topo(R); r = random.Random(3); dep = act = 0
    for k in range(40):
        cfgs = [easy(r) for _ in range(len(topo.cells))]
        outs = set()
        for t in range(6):
            bits = [r.randint(0, 1) for _ in range(NB)]; outs.add(tuple(respond(topo, cfgs, bits)))
        dep += len(outs) > 1; act += any(sum(o) for o in outs)
    print(f"radius {R}: {len(topo.cells)} cells, {len(topo.ext)} external faces, window count {topo.W}; of 40 random clusters the output changed with the input in {dep}, was not silent in {act}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--radius", type=int, default=1); ap.add_argument("--noise", type=float, default=0.15)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); ap.add_argument("--tries", type=int, default=600)
    ap.add_argument("--per-class", type=int, default=16); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    if a.check: check(a.radius); raise SystemExit
    print(f"hex cluster radius {a.radius}, noise {a.noise}, {a.tries} tries, {a.per_class} training samples per class; accuracy on 50 fresh test samples per class")
    print(f"{'seed':>4} {'learned':>8} {'random-best':>11} {'template-rule':>13} {'chance':>7}")
    for s in range(a.first, a.first + a.runs):
        l, rb, t = one(s, a.radius, a.noise, a.tries, a.per_class); print(f"{s:>4} {l:>8.2f} {rb:>11.2f} {t:>13.2f} {0.25:>7.2f}", flush=True)
