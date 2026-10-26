"""hexn_layer_learn_v1: can FEEDBACK find the settings of a two-layer network of v2 cells (hexn_layer_v1.py) that tells M noisy patterns apart? (Python model only; new file.)
The learner sees ONLY the teacher's reward for a batch of noisy presentations (right = +1, wrong = -0.5, no answer = 0); it never sees the pattern bits or the network's inner state. One try = change 1-3 things (a lane off/add/subtract, or a threshold by 1-3) in randomly chosen cells;
keep the change when the reward is NOT WORSE, otherwise undo. Start = the best of WARM random networks. Modes: LEARN, RANDOM (the best of the same number of random networks), HAND (the hand-wired network, an upper reference).
Test = fresh presentations at noise 0.1 and 0.2 (60 per class). Pattern bits are random with density 0.5."""
import sys, random, importlib.util, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer_v1 as L
def rand_net(rnd, N1, N2):
    return {"l1": [([rnd.choice((0, 1, 2)) for _ in range(L.NIN)], rnd.randint(1, 20)) for _ in range(N1)], "l2": [([rnd.choice((0, 1, 2)) for _ in range(N1)], rnd.randint(1, 8)) for _ in range(N2)]}
def mutate(net, rnd):
    l1 = [(list(w), t) for w, t in net["l1"]]; l2 = [(list(w), t) for w, t in net["l2"]]
    for _ in range(rnd.randint(1, 3)):
        layer = l1 if rnd.random() < 0.7 else l2; i = rnd.randrange(len(layer)); w, t = layer[i]
        if rnd.random() < 0.75: k = rnd.randrange(len(w)); w[k] = rnd.choice([s for s in (0, 1, 2) if s != w[k]])
        else: t = max(1, t + rnd.choice((-3, -2, -1, 1, 2, 3)))
        layer[i] = (w, t)
    return {"l1": l1, "l2": l2}
REWARD = "plain"      # plain: right +1, wrong -0.5, none 0 (silence is free: the learner settles on silent networks, see the design doc) | nonecost: none -0.25 | graded: (right output - strongest other) / 14 clipped to -1..1, plus the plain terms with none -0.25
def reward(net, batch):
    s = 0.0
    for y, bits in batch:
        out = L.present(net, bits); a = L.answer(out)
        if REWARD == "plain": s += 1.0 if a == y else (0.0 if a == -1 else -0.5)
        elif REWARD == "nonecost": s += 1.0 if a == y else (-0.25 if a == -1 else -0.5)
        else:
            oth = max([o for j, o in enumerate(out) if j != y] or [0]); s += max(-1.0, min(1.0, (out[y] - oth) / 14.0)) + (1.0 if a == y else (-0.25 if a == -1 else -0.5))
    return s
def make_batch(rnd, pats, per, q): return [(y, L.noisy(rnd, p, q)) for y, p in enumerate(pats) for _ in range(per)]
def test(net, pats, q, rnd, per=60):
    r = w = n = 0
    for y, bits in make_batch(rnd, pats, per, q):
        a = L.answer(L.present(net, bits)); r += a == y; w += a not in (y, -1); n += a == -1
    t = r + w + n; return r / t, w / t, n / t
def hand(pats, frac=0.6):
    l1 = [([1 if b else 2 for b in p], max(1, round(frac * L.PULSE * sum(p)))) for p in pats]; n = len(pats)
    return {"l1": l1, "l2": [([1 if i == j else 0 for i in range(n)], 1) for j in range(n)]}
def run(seed, M, N1, tries, warm, per=4, q=0.1):
    rnd = random.Random(seed); pats = [[int(rnd.random() < 0.5) for _ in range(L.NIN)] for _ in range(M)]
    out = {}; tr = random.Random(seed + 100)
    batch = lambda: make_batch(tr, pats, per, q)          # a fresh noisy batch for every try, so a lucky batch does not get kept
    # LEARN
    lr = random.Random(seed + 7); best = max((rand_net(lr, N1, M) for _ in range(warm)), key=lambda n: reward(n, batch())); bs = reward(best, batch())
    for _ in range(tries - warm):
        c = mutate(best, lr); b = batch(); sc = reward(c, b)
        if sc >= reward(best, b): best = c
    out["LEARN"] = best
    # RANDOM
    rr = random.Random(seed + 9); rb = None; rs = -1e9
    for _ in range(tries):
        c = rand_net(rr, N1, M); s = reward(c, batch())
        if s > rs: rb, rs = c, s
    out["RANDOM"] = rb; out["HAND"] = hand(pats)
    res = {}
    for name, net in out.items(): res[name] = [test(net, pats, qq, random.Random(seed + 55)) for qq in (0.1, 0.2)]
    return res
if __name__ == "__main__":
    if len(sys.argv) > 5: REWARD = sys.argv[5]
    M = int(sys.argv[1]) if len(sys.argv) > 1 else 3; N1 = int(sys.argv[2]) if len(sys.argv) > 2 else 6; seeds = int(sys.argv[3]) if len(sys.argv) > 3 else 5; tries = int(sys.argv[4]) if len(sys.argv) > 4 else 1200
    print(f"reward = {REWARD}; M={M} patterns, hidden layer {N1} cells, {seeds} seeds, {tries} tries (warm start 30); test right/wrong/none at noise 0.1 and 0.2")
    agg = {}
    for s in range(seeds):
        r = run(s, M, N1, tries, 30)
        for k, v in r.items(): agg.setdefault(k, []).append(v)
    for k in ("HAND", "RANDOM", "LEARN"):
        for j, q in enumerate((0.1, 0.2)):
            xs = [v[j] for v in agg[k]]; print(f"{k:6s} noise {q}: " + "/".join(f"{sum(x[i] for x in xs)/len(xs):.2f}" for i in range(3)) + "   per seed right: " + " ".join(f"{x[0]:.2f}" for x in xs))
