"""hexn_depth_v1: does DEPTH (a hidden layer) and does hidden-layer SIZE help as the number of patterns M grows? (Python model only; new file; imports hexn_layer_v2 and hexn_layer_learn_v2, both untouched.)
kind 'one' = ONE layer: M cells, each hearing the 20 input lanes directly (off/add/subtract + threshold); the answer = the cell with the most output clocks in the last two windows.
kind 'two' = the two-layer network of hexn_layer_v2 with N1 hidden cells. Same learner for both (feedback only; graded reward; warm start 30; mutate 1-3 settings, keep if not worse), same patterns per seed, same number of tries.
Usage: python3 tools/hexn_depth_v1.py M kind N1 seeds tries   (N1 ignored for 'one'). Also reports HAND (template cells; two-layer hand-wired for 'two') and RANDOM (best of the same number of random nets)."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer_v2 as L
import hexn_layer_learn_v2 as LL
LL.REWARD = "graded"
def present1(net, bits):
    L1 = [L.l1_cell(w, t) for (w, t) in net["l1"]]; out = [0] * len(L1)
    for win in range(L.WIN):
        for phase in (0, 1):
            for t in range(L.PL):
                ps, we = int(t == 0), int(phase == 1 and t == L.PL - 1)
                tx = [c.tx(phase) for c in L1]
                for c in L1:
                    rx = [0] * L.N
                    if phase == 0 and t < L.PULSE:
                        for lane, b in zip(L.IN_LANES, bits): rx[lane] = b
                    c.clock(rx, phase, ps, we)
                if win >= L.WIN - 2:
                    for j in range(len(L1)): out[j] += tx[j][L.OUT1]
    return out
def rand1(rnd, M): return {"l1": [([rnd.choice((0, 1, 2)) for _ in range(L.NIN)], rnd.randint(1, 20)) for _ in range(M)], "l2": []}
def mutate1(net, rnd):
    l1 = [(list(w), t) for w, t in net["l1"]]
    for _ in range(rnd.randint(1, 3)):
        i = rnd.randrange(len(l1)); w, t = l1[i]
        if rnd.random() < 0.75: k = rnd.randrange(len(w)); w[k] = rnd.choice([s for s in (0, 1, 2) if s != w[k]])
        else: t = max(1, t + rnd.choice((-3, -2, -1, 1, 2, 3)))
        l1[i] = (w, t)
    return {"l1": l1, "l2": []}
def run(seed, M, kind, N1, tries, warm=30, per=4, q=0.1):
    rnd = random.Random(seed); pats = [[int(rnd.random() < 0.5) for _ in range(L.NIN)] for _ in range(M)]
    pres = present1 if kind == "one" else L.present
    mk = (lambda r: rand1(r, M)) if kind == "one" else (lambda r: LL.rand_net(r, N1, M))
    mu = mutate1 if kind == "one" else LL.mutate
    def rew(net, batch):
        s = 0.0
        for y, bits in batch:
            out = pres(net, bits); a = L.answer(out); oth = max([o for j, o in enumerate(out) if j != y] or [0])
            s += max(-1.0, min(1.0, (out[y] - oth) / 14.0)) + (1.0 if a == y else (-0.25 if a == -1 else -0.5))
        return s
    def tst(net, qq, per=60):
        r2 = random.Random(seed + 55); r = w = n = 0
        for y, bits in LL.make_batch(r2, pats, per, qq):
            a = L.answer(pres(net, bits)); r += a == y; w += a not in (y, -1); n += a == -1
        t = r + w + n; return r / t, w / t, n / t
    tr = random.Random(seed + 100); batch = lambda: LL.make_batch(tr, pats, per, q)
    lr = random.Random(seed + 7); best = max((mk(lr) for _ in range(warm)), key=lambda n: rew(n, batch()))
    for _ in range(tries - warm):
        c = mu(best, lr); b = batch()
        if rew(c, b) >= rew(best, b): best = c
    rr = random.Random(seed + 9); rb = None; rs = -1e9
    for _ in range(tries):
        c = mk(rr); s = rew(c, batch())
        if s > rs: rb, rs = c, s
    hand = {"l1": [([1 if b else 2 for b in p], max(1, round(0.6 * L.PULSE * sum(p)))) for p in pats], "l2": []} if kind == "one" else LL.hand(pats)
    return {k: [tst(n, qq) for qq in (0.1, 0.2)] for k, n in (("HAND", hand), ("RANDOM", rb), ("LEARN", best))}
if __name__ == "__main__":
    M, kind, N1, seeds, tries = int(sys.argv[1]), sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    print(f"M={M} patterns, kind={kind}, hidden={N1 if kind == 'two' else '-'}, {seeds} seeds, {tries} tries, graded reward; right/wrong/none", flush=True)
    agg = {}
    for s in range(seeds):
        for k, v in run(s, M, kind, N1, tries).items(): agg.setdefault(k, []).append(v)
        print("seed", s, "done", flush=True)
    for k in ("HAND", "RANDOM", "LEARN"):
        for j, q in enumerate((0.1, 0.2)):
            xs = [v[j] for v in agg[k]]; print(f"{k:6s} noise {q}: " + "/".join(f"{sum(x[i] for x in xs)/len(xs):.2f}" for i in range(3)) + "   per seed right: " + " ".join(f"{x[0]:.2f}" for x in xs))
