"""hexn_proto_v1: WIRE THE FIRST LAYER DIRECTLY FROM EXAMPLES instead of searching for its settings (Python model only; new file; imports hexn_depth_v1 / hexn_layer_v2, untouched).
Prototype rule (no search, no reward needed for the weights): for each class, take k noisy examples from the teacher, and for every input lane count the 1s: more than half = ADD, otherwise = SUBTRACT.
The cell's threshold = frac x PULSE x (number of ADD lanes), the same form as the hand-wired network; frac is picked from a short list by the reward (graded) on a small training batch (the only thing the reward chooses).
Compared with the numbers of hexn_depth_v1 (one layer, learned by search, 1,500 tries) and HAND (clean templates). Same patterns per seed (seed -> patterns as in hexn_depth_v1), same test (60 per class at noise 0.1 and 0.2).
ASSUMPTIONS: the teacher can supply k examples with their class (labels), each seen through the training noise q; examples are independent. Usage: python3 tools/hexn_proto_v1.py seeds"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer_v2 as L
import hexn_layer_learn_v2 as LL
import hexn_depth_v1 as D
def proto_net(examples, frac):
    l1 = []
    for ex in examples:
        w = [1 if sum(e[i] for e in ex) * 2 > len(ex) else 2 for i in range(L.NIN)]
        l1.append((w, max(1, round(frac * L.PULSE * sum(1 for s in w if s == 1)))))
    return {"l1": l1, "l2": []}
def run(seed, M, k, qtrain):
    rnd = random.Random(seed); pats = [[int(rnd.random() < 0.5) for _ in range(L.NIN)] for _ in range(M)]
    tr = random.Random(seed + 500); ex = [[L.noisy(tr, p, qtrain) for _ in range(k)] for p in pats]
    def rew(net, batch):
        s = 0.0
        for y, bits in batch:
            out = D.present1(net, bits); a = L.answer(out); oth = max([o for j, o in enumerate(out) if j != y] or [0])
            s += max(-1.0, min(1.0, (out[y] - oth) / 14.0)) + (1.0 if a == y else (-0.25 if a == -1 else -0.5))
        return s
    batch = LL.make_batch(tr, pats, 4, 0.1)
    net = max((proto_net(ex, f) for f in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8)), key=lambda n: rew(n, batch))
    res = []
    for qq in (0.1, 0.2):
        r2 = random.Random(seed + 55); ok = 0; n = 0
        for y, bits in LL.make_batch(r2, pats, 60, qq): ok += L.answer(D.present1(net, bits)) == y; n += 1
        res.append(ok / n)
    return res
if __name__ == "__main__":
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    print(f"prototype first layer from k labelled noisy examples per class (training noise 0.1); right at test noise 0.1 / 0.2; {seeds} seeds. For comparison, learned by search (1,500 tries, 6 seeds): M=3 0.83 / 0.69, M=6 0.42 / 0.31, M=10 0.23 / 0.18; hand-wired from clean templates: 0.89 / 0.53, 0.89 / 0.52, 0.90 / 0.54")
    print("patterns M | examples k | right 0.1  right 0.2")
    for M in (3, 6, 10):
        for k in (1, 3, 10):
            r = [run(s, M, k, 0.1) for s in range(seeds)]
            print(f"    {M:2d}     |    {k:2d}      |  {sum(x[0] for x in r) / seeds:.2f}      {sum(x[1] for x in r) / seeds:.2f}")
