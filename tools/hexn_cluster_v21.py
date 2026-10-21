"""Hex-N cluster v21 (new file): the cluster of DECISION-TABLE cells (hexn_cell_v3_model.py), judged the same way as the v19 ladder: gated local reward + readout score, one cell per output group (--ownout is always on here),
600 tries, 16 samples per class, noise 0.15, same seeds, same compare tool.  Start: lane settings as v2 'easy'; every table entry starts as straight-through (each face with input fires the opposite face at level 2), with
each entry replaced by random levels with chance --rand (default 0.2) so the 100 warm-start candidates differ.  Mutation: a table entry's level (3 in 5), a lane's active flag, a lane's direction.
Usage: python3 tools/hexn_cluster_v21.py [--first S] [--runs N] [--tries T] [--noise Q] [--rand R]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
v19 = load("hexn_cluster_v19"); m3 = load("hexn_cell_v3_model"); c15 = v19.c15; F, P, N = m3.F, m3.P, m3.N


def new_cfg(r, rand):
    a, d, _, _, _ = c15.easy(r)
    table = []
    for combo in range(64):
        if r.random() < rand: table.append([r.randint(0, 3) for _ in range(F)])
        else: table.append([2 if (combo >> ((f + 3) % F)) & 1 else 0 for f in range(F)])
    return (a, d, table)


def mutate(cfg, r):
    a, d, t = list(cfg[0]), list(cfg[1]), [list(x) for x in cfg[2]]; k = r.randrange(5)
    if k < 3: t[r.randrange(64)][r.randrange(F)] = r.randint(0, 3)
    elif k == 3: i = r.randrange(N); a[i] ^= 1
    else: i = r.randrange(N); d[i] = r.randint(0, 3)
    return (a, d, t)


def run_all(topo, cfgs, data):
    out = []
    for bits, y in data:
        out.append(v19.sample_counts(topo, [m3.TableCell(*c) for c in cfgs], bits))
    return out


def rewards(topo, cfgs, data, bits=4):
    g = run_all(topo, cfgs, data); top = (1 << bits) - 1; tot = 0; stuck = []
    for k in range(4):
        pos = [x for (_, y), x in zip(data, g) if y == k]; neg = [x for (_, y), x in zip(data, g) if y != k]
        tp = sum(x[k] > 0 for x in pos); tn = sum(not x[k] > 0 for x in neg); fired = tp + (len(neg) - tn)
        if fired in (0, len(data)): stuck.append(k); continue
        tot += round(top * (tp / len(pos) + tn / len(neg)) / 2)
    ok = sum((max(x) > 0 and x.count(max(x)) == 1 and x.index(max(x)) == y) for (_, y), x in zip(data, g))
    return tot + round(top * ok / len(data))


def accuracy(topo, cfgs, data):
    g = run_all(topo, cfgs, data)
    return sum((max(x) > 0 and x.count(max(x)) == 1 and x.index(max(x)) == y) for (_, y), x in zip(data, g)) / len(data)


def one(seed, R, q, tries, S, rand, warm=100):
    topo = c15.Topo(R); topo.outputs = v19.own_outputs(topo); rnd = random.Random(seed); tpl = c15.v12.make_templates(rnd, 4)
    train = [(c15.v12.sample(rnd, tpl[y], q), y) for y in range(4) for _ in range(S)]
    test = [(c15.v12.sample(rnd, tpl[y], q), y) for y in range(4) for _ in range(50)]
    sh = random.Random(seed + 5); sh.shuffle(train); sh.shuffle(test)
    lf = c15.v6.Lfsr(seed + 77); n = len(topo.cells); best = None; br = -1
    for _ in range(warm):
        c = [new_cfg(lf, rand) for _ in range(n)]; r = rewards(topo, c, train)
        if r > br: best, br = c, r
    cur, cr = best, br
    for _ in range(tries - warm):
        nxt = list(cur)
        for _ in range(1 + lf.randrange(3)):
            j = lf.randrange(n); nxt[j] = mutate(nxt[j], lf)
        r = rewards(topo, nxt, train)
        if r >= cr: cur, cr = nxt, r
    return accuracy(topo, cur, test), c15.v12.template_rule(tpl, test)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--radius", type=int, default=1); ap.add_argument("--noise", type=float, default=0.15)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); ap.add_argument("--tries", type=int, default=600)
    ap.add_argument("--per-class", type=int, default=16); ap.add_argument("--rand", type=float, default=0.2); a = ap.parse_args()
    print(f"hex cluster v21 (decision-table cells) radius {a.radius}, noise {a.noise}, {a.tries} tries, rand {a.rand}")
    print(f"{'seed':>4} {'learned':>8} {'template-rule':>13}")
    tot = 0
    for s in range(a.first, a.first + a.runs):
        l, t = one(s, a.radius, a.noise, a.tries, a.per_class, a.rand); tot += l
        print(f"{s:>4} {l:>8.2f} {t:>13.2f}", flush=True)
    print(f"mean learned {tot / a.runs:.2f}")
