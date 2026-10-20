"""Hex-N pattern recognition v12 (new file). VM only. Single cell. First application test, as agreed with Alan (20 Oct).

Task: K classes. Each class is a template of 12 on/off wires. A sample is a template with each wire flipped with probability NOISE.
The cell sees the 12 wires on the lanes of faces 0-2 (a wire that is on is held high for the whole window). The sample is shown for two
windows (the cell's result is ready one window after the input), with a fresh cell for every sample (a real card would flush or reset between samples).
The answer is read from the other 12 lanes (faces 3-5), split into K groups of 3 lanes: the group with the most clocks high in window 2 is the cell's answer
(a tie counts as wrong).
Training: the v6 learner (LFSR, 4-bit reward, warm start, keep-or-undo, 1-3 changes). The reward is 1000*(0.7*accuracy + 0.3*share of output clocks in the
right group) on a TRAINING set of S noisy samples per class. The result is scored on a fresh TEST set the learner never saw.
Baselines on the same test set: chance (1/K); the best of the same number of random cells (picked on the training set); and a template-matching rule that
KNOWS the templates (the best a plain method can do, a ceiling).
Usage: python3 tools/hexn_patterns_v12.py [--classes K] [--noise Q] [--first S] [--runs N] [--tries T] [--per-class S]"""
import argparse, importlib.util, os, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
v3, v6 = load("hexn_mutation_v3"), load("hexn_learner_v6")
v1, Cell, F, P, N, PL = v3.v1, v3.Cell, v3.v1.F, v3.v1.P, v3.N, v3.PL
NB = 12


def make_templates(rnd, K):
    while True:
        t = [[rnd.randint(0, 1) for _ in range(NB)] for _ in range(K)]
        if all(sum(a != b for a, b in zip(t[i], t[j])) >= 4 for i in range(K) for j in range(i)): return t


def sample(rnd, tpl, q): return [b ^ int(rnd.random() < q) for b in tpl]


def respond(cfg, bits, K):
    c = Cell(*cfg); counts = [0] * N
    for w in range(2):
        for phase in (0, 1):
            for t in range(PL):
                rx = [0] * N
                for i in range(NB): rx[i] = bits[i]
                tx = c.tx(phase)
                if w == 1: counts = [a + b for a, b in zip(counts, tx)]
                c.clock(rx, phase, int(t == 0), int(phase == 1 and t == PL - 1))
    return [sum(counts[NB + 3 * g: NB + 3 * g + 3]) for g in range(K)]


def predict(g):
    m = max(g); return g.index(m) if m > 0 and g.count(m) == 1 else -1


def reward(cfg, data, K):
    acc = share = 0
    for bits, y in data:
        g = respond(cfg, bits, K); acc += predict(g) == y; share += g[y] / sum(g) if sum(g) else 0
    return round(1000 * (0.7 * acc / len(data) + 0.3 * share / len(data)))


def accuracy(cfg, data, K): return sum(predict(respond(cfg, b, K)) == y for b, y in data) / len(data)


def template_rule(tpl, data):
    ok = 0
    for b, y in data:
        d = [sum(x != z for x, z in zip(b, t)) for t in tpl]; m = min(d); ok += d.index(m) == y and d.count(m) == 1
    return ok / len(data)


def one(seed, K, q, tries, S, warm=100, bits=4):
    rnd = random.Random(seed); tpl = make_templates(rnd, K)
    train = [(sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(S)]
    test = [(sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(50)]
    Q = lambda c: reward(c, train, K) * ((1 << bits) - 1) // 1000
    lf = v6.Lfsr(seed + 77); best = None; br = -1
    for _ in range(warm):
        c = v1.rand_cfg(lf); r = Q(c)
        if r > br: best, br = c, r
    cur, cr = best, br
    for _ in range(tries - warm):
        nxt = cur
        for _ in range(1 + lf.randrange(3)): nxt = v1.mutate(nxt, lf)
        r = Q(nxt)
        if r >= cr: cur, cr = nxt, r
    rr = random.Random(seed + 1); rb = max((v1.rand_cfg(rr) for _ in range(tries)), key=lambda c: reward(c, train, K))
    return accuracy(cur, test, K), accuracy(rb, test, K), template_rule(tpl, test)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--classes", type=int, default=4); ap.add_argument("--noise", type=float, default=0.0)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); ap.add_argument("--tries", type=int, default=1000)
    ap.add_argument("--per-class", type=int, default=4); a = ap.parse_args()
    print(f"{a.classes} classes, {NB} wires, noise {a.noise} (each wire flipped), {a.tries} tries, {a.per_class} training samples per class; accuracy on 50 fresh test samples per class")
    print(f"{'seed':>4} {'learned':>8} {'random-best':>11} {'template-rule':>13} {'chance':>7}")
    for s in range(a.first, a.first + a.runs):
        l, r, t = one(s, a.classes, a.noise, a.tries, a.per_class); print(f"{s:>4} {l:>8.2f} {r:>11.2f} {t:>13.2f} {1/a.classes:>7.2f}", flush=True)
