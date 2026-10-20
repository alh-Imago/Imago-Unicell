"""Hex-N pattern recognition v13 (new file; v12 had the inputs and outputs on faces that cannot talk to each other, see HEXN_DESIGN.md 2a).
Uses the v2 model (faces feed one decision).  K classes, each a template of 12 on/off wires, samples = template with each wire flipped with probability NOISE.
One DETECTOR cell per class: the 12 wires go to lanes 0-11, the cell answers on lanes 12-23 (its burst clocks in window 2).  Each detector is trained alone
by the v6 learner on 'is it my class or not' (reward = balanced accuracy, 4 bits).  The cell's answer for a sample = the class whose detector gave the most output
clocks (ties, or no output at all, count as wrong).  Test = fresh samples.  Baselines: chance, best-of-same-number random cells per detector, and a template rule
that knows the templates (ceiling).   Usage: python3 tools/hexn_patterns_v13.py [--classes K] [--noise Q] [--first S] [--runs N] [--tries T] [--per-class S]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
v6, v12, mc = load("hexn_learner_v6"), load("hexn_patterns_v12"), load("hexn_cell_v2_model")
N, F, PL, NB = mc.N, mc.F, mc.PL if hasattr(mc, "PL") else 10, 12


def rand_cfg(r): return ([int(r.random() < 0.85) for _ in range(N)], [r.randint(0, 3) for _ in range(N)], [r.randint(0, 3) for _ in range(N)], [r.randint(0, 5)], r.choice([0, 0, 0, 1, 2]))


def mutate(cfg, r):
    a, d, c, t, b = [list(x) if isinstance(x, list) else x for x in cfg]; k = r.randrange(5)
    if k == 0: i = r.randrange(N); a[i] ^= 1
    elif k == 1: i = r.randrange(N); d[i] = r.randint(0, 3)
    elif k == 2: i = r.randrange(N); c[i] = r.randint(0, 3)
    elif k == 3: t[0] = max(0, min(7, t[0] + r.choice([-1, 1])))
    else: b = max(0, min(3, b + r.choice([-1, 1])))
    return (a, d, c, t, b)


def clocks(cfg, bits):
    c = mc.MixCell(*cfg); n = 0
    for w in range(2):
        for phase in (0, 1):
            for t in range(PL):
                rx = [0] * N
                for i in range(NB): rx[i] = bits[i]
                tx = c.tx(phase)
                if w == 1: n += sum(tx[NB:])
                c.clock(rx, phase, int(t == 0), int(phase == 1 and t == PL - 1))
    return n


def bal(cfg, data, y):
    tp = tn = pos = neg = 0
    for bits, l in data:
        fire = clocks(cfg, bits) > 0
        if l == y: pos += 1; tp += fire
        else: neg += 1; tn += (not fire)
    return round(1000 * (tp / pos + tn / neg) / 2)


def train(data, y, tries, seed, warm=100, bits=4):
    Q = lambda c: bal(c, data, y) * ((1 << bits) - 1) // 1000
    lf = v6.Lfsr(seed); best = None; br = -1
    for _ in range(warm):
        c = rand_cfg(lf); r = Q(c)
        if r > br: best, br = c, r
    cur, cr = best, br
    for _ in range(tries - warm):
        nxt = cur
        for _ in range(1 + lf.randrange(3)): nxt = mutate(nxt, lf)
        r = Q(nxt)
        if r >= cr: cur, cr = nxt, r
    return cur


def acc(cfgs, data):
    ok = 0
    for bits, y in data:
        g = [clocks(c, bits) for c in cfgs]; m = max(g); ok += (m > 0 and g.count(m) == 1 and g.index(m) == y)
    return ok / len(data)


def one(seed, K, q, tries, S):
    rnd = random.Random(seed); tpl = v12.make_templates(rnd, K)
    train_d = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(S)]
    test = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(50)]
    learned = [train(train_d, y, tries, seed * 100 + y + 1) for y in range(K)]
    rr = random.Random(seed + 1)
    rb = [max((rand_cfg(rr) for _ in range(tries)), key=lambda c: bal(c, train_d, y)) for y in range(K)]
    return acc(learned, test), acc(rb, test), v12.template_rule(tpl, test)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--classes", type=int, default=4); ap.add_argument("--noise", type=float, default=0.0)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); ap.add_argument("--tries", type=int, default=600)
    ap.add_argument("--per-class", type=int, default=4); a = ap.parse_args()
    print(f"{a.classes} detector cells, 12 wires, noise {a.noise}, {a.tries} tries per detector, {a.per_class} training samples per class; accuracy on 50 fresh test samples per class")
    print(f"{'seed':>4} {'learned':>8} {'random-best':>11} {'template-rule':>13} {'chance':>7}")
    for s in range(a.first, a.first + a.runs):
        l, r, t = one(s, a.classes, a.noise, a.tries, a.per_class); print(f"{s:>4} {l:>8.2f} {r:>11.2f} {t:>13.2f} {1/a.classes:>7.2f}", flush=True)
