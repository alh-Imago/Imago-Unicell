"""Hex-N detector bank v2 (new file; VM model only).  Alan, 21 Oct 2026: 'the multiple detectors seems to be the key'.
BANK = 4 independent cells, one per class; EVERY cell receives all 12 input wires (lanes 0..11 = faces 0,1,2) directly, with NO routing between cells; cell k's answer is the burst count on its own
output face (face 3, lanes 12..15) in the last window; the answer is the cell with strictly the most clocks (tie/silence wrong).  Same task, data, noise, search and reward as the 4-class cluster
(v21: best of 100 random starts, keep-or-undo, 1-3 changes per try, keep if >=, gated per-class reward + readout score), same seeds, so results compare with the cluster's 0.451 at 1,000 tries.
Arms: --cell sum (the v2 summing cell, hexn_cell_v2_model.MixCell) | table (the v3 decision-table cell, 64 rows).  W=2 windows (independent cells need no relay time).
NEW IN v2: --see limits which of the 12 input wires each detector receives (fan-out cost): all (v1) | faces2 (detector k gets the 8 wires of faces k%3 and (k+1)%3) | face1 (detector k gets the 4 wires of face k%3; detector 3 repeats face 0) | half (detector k gets 6 wires: k even = wires 0,2,4..; k odd = wires 1,3,5.. of 12 -> every other wire).
Usage: python3 tools/hexn_bank_v2.py --cell table [--first S] [--runs N] [--tries T] [--W w]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
c15, m3, tri, v21 = load("hexn_cluster_v15"), load("hexn_cell_v3_model"), load("hexn_tri_v1"), load("hexn_cluster_v21")
v6, v12, mc = c15.v6, c15.v12, c15.mc
K, N, P, PL, NB = 4, mc.N, mc.P, c15.PL, c15.NB
CELL = "table"; SEE = "all"


def wires(k):
    if SEE == "faces2": return [j for j in range(NB) if j // P in (k % 3, (k + 1) % 3)]
    if SEE == "face1": return [j for j in range(NB) if j // P == k % 3]
    if SEE == "half": return [j for j in range(NB) if j % 2 == k % 2]
    return list(range(NB))


def new_cfg(r):
    if CELL == "sum": return c15.easy(r)
    a, d, t = tri.new_cfg(tri.Net("hex"), r); return (a, d, t)


def mutate(cfg, r):
    if CELL == "sum": return c15.mutate(cfg, r)
    return tri.mutate(tri.Net("hex"), cfg, r)


def make(cfg): return mc.MixCell(*cfg) if CELL == "sum" else tri.Cell(6, *cfg)


def counts(cells, bits, W):
    cnt = [0] * K
    for w in range(W):
        for phase in (0, 1):
            for t in range(PL):
                tx = [c.tx(phase) for c in cells]
                if w == W - 1:
                    for k in range(K): cnt[k] += sum(tx[k][12 + p] for p in range(P))
                for k, c in enumerate(cells):
                    rx = [0] * N
                    for j in WIRES[k]: rx[j] = bits[j]
                    c.clock(rx, phase, int(t == 0), int(phase == 1 and t == PL - 1))
    return cnt


def run_all(cfgs, data, W): return [counts([make(c) for c in cfgs], bits, W) for bits, y in data]


def rewards(cfgs, data, W, bits=4):
    g = run_all(cfgs, data, W); top = (1 << bits) - 1; tot = 0
    for k in range(K):
        pos = [x for (_, y), x in zip(data, g) if y == k]; neg = [x for (_, y), x in zip(data, g) if y != k]
        tp = sum(x[k] > 0 for x in pos); tn = sum(not x[k] > 0 for x in neg); fired = tp + (len(neg) - tn)
        if fired in (0, len(data)): continue
        tot += round(top * (tp / len(pos) + tn / len(neg)) / 2)
    ok = sum((max(x) > 0 and x.count(max(x)) == 1 and x.index(max(x)) == y) for (_, y), x in zip(data, g))
    return tot + round(top * ok / len(data))


def accuracy(cfgs, data, W):
    g = run_all(cfgs, data, W)
    return sum((max(x) > 0 and x.count(max(x)) == 1 and x.index(max(x)) == y) for (_, y), x in zip(data, g)) / len(data)


def one(seed, q, tries, S, W, warm=100):
    rnd = random.Random(seed); tpl = v12.make_templates(rnd, K)
    train = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(S)]
    test = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(50)]
    sh = random.Random(seed + 5); sh.shuffle(train); sh.shuffle(test); lf = v6.Lfsr(seed + 77); best = None; br = -1
    for _ in range(warm):
        c = [new_cfg(lf) for _ in range(K)]; r = rewards(c, train, W)
        if r > br: best, br = c, r
    cur, cr = best, br
    for _ in range(tries - warm):
        nxt = list(cur)
        for _ in range(1 + lf.randrange(3)):
            j = lf.randrange(K); nxt[j] = mutate(nxt[j], lf)
        r = rewards(nxt, train, W)
        if r >= cr: cur, cr = nxt, r
    return accuracy(cur, test, W), v12.template_rule(tpl, test)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--cell", default="table"); ap.add_argument("--see", default="all"); ap.add_argument("--noise", type=float, default=0.15); ap.add_argument("--W", type=int, default=2)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); ap.add_argument("--tries", type=int, default=1000); ap.add_argument("--per-class", type=int, default=16)
    a = ap.parse_args(); CELL = a.cell; SEE = a.see; WIRES = [wires(k) for k in range(K)]
    print(f"hex-n detector bank v1: cell {a.cell}, sees {a.see}, 4 classes (chance 0.25), W {a.W}, noise {a.noise}, {a.tries} tries")
    print(f"{'seed':>4} {'learned':>8} {'template-rule':>13}"); tot = 0
    for s in range(a.first, a.first + a.runs):
        l, t = one(s, a.noise, a.tries, a.per_class, a.W); tot += l
        print(f"{s:>4} {l:>8.2f} {t:>13.2f}", flush=True)
    print(f"mean learned {tot / a.runs:.2f}")
