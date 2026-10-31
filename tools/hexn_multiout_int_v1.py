"""hexn_multiout_int_v1: THE MULTI-OUTPUT LEARNING STEP IN WHOLE NUMBERS (Python; model only; new file 31 Oct 2026). Alan, 15:00: 'apply the whole number learning so the system is consistent' (the animal example's neural learned in decimals; the game's neural already learns in whole numbers, tools/hexn_layer1_int_v4.py).
Same neural as the shadow test: one score per animal over the layer 1 counts, softmax, delta rule. All integers:
  scores   s_k = sum_b W[k][b] * x[b]            (weights Q8: 8 fractional bits; counts x are small integers)
  softmax  d_k = max_s - s_k >= 0 ; e_k = EXP[d_k >> (wb-4)] (128 entries, step 1/16, Q16, zero beyond 8) ; p_k = (e_k << 8) // sum(e)   (Q8; ONE division per learning step)
  error    err_k = p_k - (256 if k == label else 0)
  update   W[k][b] -= (rate * err_k * x[b] + 64) >> 7      (rate in 1/128 units: 192 = 1.5)
The rule is the decimal rule with learning rate rate/128. Usage as a module: MultiOutInt(W_rows, rate) with predict(x) and learn(x, label); the script compares it with the decimal arm of tools/hexn_sensor_shadow_v1.py on worlds A, B, C (prior weights from the integer goals-to-weights step)."""
import math, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
EXP = [int(round(65536 * math.exp(-i / 16.0))) for i in range(128)]
class MultiOutInt:
    def __init__(s, W, rate=192, wb=8): s.W = [list(r) for r in W]; s.rate = rate; s.wb = wb; s.wmax = max(abs(v) for r in s.W for v in r)
    def scores(s, x): return [sum(w * v for w, v in zip(r, x)) for r in s.W]
    def predict(s, x): sc = s.scores(x); return sc.index(max(sc))
    def learn(s, x, label):
        sc = s.scores(x); m = max(sc); e = []
        for v in sc:
            d = m - v; i = d >> (s.wb - 4); e.append(EXP[i] if d < (8 << s.wb) and i < 128 else 0)
        S = sum(e); p = [(v << 8) // S for v in e]
        for k, row in enumerate(s.W):
            err = p[k] - (256 if k == label else 0)
            if err == 0: continue
            for b, xb in enumerate(x):
                if xb: row[b] -= (s.rate * err * int(xb) + 64) >> 7
        s.wmax = max(s.wmax, max(abs(v) for r in s.W for v in r))
def run(world, seeds=40, ns=(0, 3, 10, 30, 100, 300)):
    import hexn_sensor_shadow_v1 as S, hexn_item_v1 as I
    g = I.goals_payload([("rat", 10, 2), ("cat", 28, 4), ("dog", 50, 10), ("sheep", 75, 8), ("deer", 110, 12), ("horse", 150, 12)], 24, 80); Wq = I.goals_to_weights(g, 8)
    S.LR = 1.5; acc = {"decimal": np.zeros(len(ns)), "whole": np.zeros(len(ns))}; wm = 0
    for sd in range(seeds):
        rng = np.random.default_rng(1000 + sd); test = [(a, *S.observe(rng, a, world)) for a in rng.integers(0, S.K, 300)]; stream = [(a, *S.observe(rng, a, world)) for a in rng.integers(0, S.K, max(ns))]
        d = S.Arm("neural"); d.W = np.array(Wq, dtype=float) / 256.0; mi = MultiOutInt(Wq); done = 0
        for j, n in enumerate(ns):
            for a, x, mean in stream[done:n]: d.learn(x, mean, a); mi.learn([int(v) for v in x], a)
            done = n; acc["decimal"][j] += np.mean([d.predict(x, mean) == a for a, x, mean in test]); acc["whole"][j] += np.mean([mi.predict([int(v) for v in x]) == a for a, x, mean in test])
        wm = max(wm, mi.wmax)
    print("world %s   labelled passings seen:" % world, "  ".join("%4d" % n for n in ns))
    for k in acc: print("  %-8s accuracy:" % k, "  ".join("%.2f" % (v / seeds) for v in acc[k]))
    print("  largest |weight| seen in the whole-number arm: %d (fits 16 bits: %s)" % (wm, wm < 32768))
if __name__ == "__main__":
    for w in (sys.argv[1:] or ["A", "B", "C"]): run(w)
