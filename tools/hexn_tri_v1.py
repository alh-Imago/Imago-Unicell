"""Hex-N triangle test v1 (new file; VM model only).  Alan, 21 Oct 2026: build the hexagon from SIX TRIANGLE cells (3 faces, in and out on each) instead of one 6-faced cell.
A triangle has 3 faces, so its decision table has 2^3 = 8 rows x 3 levels x 2 bits = 48 bits (a 6-faced hex cell: 64 x 6 x 2 = 768 bits).  Six triangles = 288 bits.
Ring of six: triangle k has face 0 = the OUTER edge of the hexagon, face 1 = joined to triangle k+1 (its face 2), face 2 = joined to triangle k-1 (its face 1); lane for lane, as in the cluster.
Same ports in both arms (the hexagon's six outer edges, 4 lanes each): inputs = 12 wires on edges 0,1,2; outputs = 3 groups, one per edge 3,4,5 (3 classes, chance 0.33; the pattern is 12 bits, noise 0.15 per wire).
Cell behaviour is exactly hexn_cell_v3_model's TableCell with the number of faces made a parameter.  Search: as v21 (best of 100 random tables, then keep-or-undo, 1 to 3 changes per try, keep if >=), same gated reward + readout score.
Arms: --arm hex (ONE 6-faced table cell) | tri (ring of six triangles).  Usage: python3 tools/hexn_tri_v1.py --arm tri [--first S] [--runs N] [--tries T] [--W w]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
v6, v12 = load("hexn_learner_v6"), load("hexn_patterns_v12")
P, PL, LEN, K = 4, 10, (0, 2, 4, 6), 3


class Cell:
    def __init__(self, F, active, dr, table):
        self.F, self.a, self.d, self.t = F, active, dr, table; N = F * P
        self.snd = [[bool(active[i] and dr[i] in (1, 3)) for i in range(N)], [bool(active[i] and dr[i] == 2) for i in range(N)]]
        self.rcv = [[i for i in range(N) if active[i] and dr[i] in (0, 2)], [i for i in range(N) if active[i] and dr[i] == 3]]
        self.fin = [0] * F; self.out = [0] * F; self.bc = 0; self.N = N

    def tx(self, phase):
        snd = self.snd[phase]; return [int(snd[i] and self.bc < LEN[self.out[i // P]]) for i in range(self.N)]

    def clock(self, rx, phase, ph_start, win_end):
        if ph_start and not phase: self.fin = [0] * self.F
        if not phase:
            for i in self.rcv[0]:
                if rx[i]: self.fin[i // P] = 1
        self.bc = 0 if ph_start else min(self.bc + 1, 7)
        if win_end and phase: self.out = list(self.t[sum(b << f for f, b in enumerate(self.fin))])


class Net:
    def __init__(self, arm):
        if arm == "hex":
            self.F, self.n = 6, 1; self.nbr = [[None] * 6]
            self.inputs = {(0, f * P + p): f * P + p for f in range(3) for p in range(P)}
            self.outputs = [[(0, (3 + g) * P + p) for p in range(P)] for g in range(K)]
        else:
            self.F, self.n = 3, 6; self.nbr = [[None, ((k + 1) % 6, 2), ((k - 1) % 6, 1)] for k in range(6)]
            self.inputs = {(k, p): k * P + p for k in range(3) for p in range(P)}
            self.outputs = [[(3 + g, p) for p in range(P)] for g in range(K)]
        self.rows = 1 << self.F


def counts(net, cells, bits, W):
    cnt = [0] * K; N = net.F * P
    for w in range(W):
        for phase in (0, 1):
            for t in range(PL):
                tx = [c.tx(phase) for c in cells]
                if w == W - 1:
                    for g in range(K): cnt[g] += sum(tx[i][l] for (i, l) in net.outputs[g])
                for i, c in enumerate(cells):
                    rx = [0] * N
                    for f in range(net.F):
                        nb = net.nbr[i][f]
                        if nb is not None:
                            j, g = nb
                            for p in range(P): rx[f * P + p] = tx[j][g * P + p]
                    for (ii, lane), j in net.inputs.items():
                        if ii == i: rx[lane] = bits[j]
                    c.clock(rx, phase, int(t == 0), int(phase == 1 and t == PL - 1))
    return cnt


def new_cfg(net, r):
    N = net.F * P
    return ([int(r.random() < 0.95) for _ in range(N)], [r.choice([0, 1, 1, 2, 3]) for _ in range(N)], [[r.randint(0, 3) for _ in range(net.F)] for _ in range(net.rows)])


def mutate(net, cfg, r):
    a, d, t = list(cfg[0]), list(cfg[1]), [list(x) for x in cfg[2]]; k = r.randrange(5); N = net.F * P
    if k < 3: t[r.randrange(net.rows)][r.randrange(net.F)] = r.randint(0, 3)
    elif k == 3: a[r.randrange(N)] ^= 1
    else: d[r.randrange(N)] = r.randint(0, 3)
    return (a, d, t)


def run_all(net, cfgs, data, W): return [counts(net, [Cell(net.F, *c) for c in cfgs], bits, W) for bits, y in data]


def rewards(net, cfgs, data, W, bits=4):
    g = run_all(net, cfgs, data, W); top = (1 << bits) - 1; tot = 0
    for k in range(K):
        pos = [x for (_, y), x in zip(data, g) if y == k]; neg = [x for (_, y), x in zip(data, g) if y != k]
        tp = sum(x[k] > 0 for x in pos); tn = sum(not x[k] > 0 for x in neg); fired = tp + (len(neg) - tn)
        if fired in (0, len(data)): continue
        tot += round(top * (tp / len(pos) + tn / len(neg)) / 2)
    ok = sum((max(x) > 0 and x.count(max(x)) == 1 and x.index(max(x)) == y) for (_, y), x in zip(data, g))
    return tot + round(top * ok / len(data))


def accuracy(net, cfgs, data, W):
    g = run_all(net, cfgs, data, W)
    return sum((max(x) > 0 and x.count(max(x)) == 1 and x.index(max(x)) == y) for (_, y), x in zip(data, g)) / len(data)


def one(arm, seed, q, tries, S, W, warm=100):
    net = Net(arm); rnd = random.Random(seed); tpl = v12.make_templates(rnd, K)
    train = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(S)]
    test = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(50)]
    sh = random.Random(seed + 5); sh.shuffle(train); sh.shuffle(test); lf = v6.Lfsr(seed + 77); best = None; br = -1
    for _ in range(warm):
        c = [new_cfg(net, lf) for _ in range(net.n)]; r = rewards(net, c, train, W)
        if r > br: best, br = c, r
    cur, cr = best, br
    for _ in range(tries - warm):
        nxt = list(cur)
        for _ in range(1 + lf.randrange(3)):
            j = lf.randrange(net.n); nxt[j] = mutate(net, nxt[j], lf)
        r = rewards(net, nxt, train, W)
        if r >= cr: cur, cr = nxt, r
    return accuracy(net, cur, test, W), v12.template_rule(tpl, test)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--arm", default="tri"); ap.add_argument("--noise", type=float, default=0.15); ap.add_argument("--W", type=int, default=7)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); ap.add_argument("--tries", type=int, default=1000); ap.add_argument("--per-class", type=int, default=16)
    a = ap.parse_args()
    print(f"hex-n triangle test v1: arm {a.arm} (3 classes, chance 0.33), W {a.W}, noise {a.noise}, {a.tries} tries")
    print(f"{'seed':>4} {'learned':>8} {'template-rule':>13}"); tot = 0
    for s in range(a.first, a.first + a.runs):
        l, t = one(a.arm, s, a.noise, a.tries, a.per_class, a.W); tot += l
        print(f"{s:>4} {l:>8.2f} {t:>13.2f}", flush=True)
    print(f"mean learned {tot / a.runs:.2f}")
