"""hexn_hum_v1: does look SPACING matter when the noise is a shared mains hum / lamp flicker instead of independent flips? (new file; hexn_twostage_v2.py untouched)
Model (an assumption, not a measurement): wire j reads bit = [ s_j*M + c_j*A*sin(2*pi*f*t + phi) + n > 0 ], s_j = +-1 the true bit, M = 1, n ~ Normal(0, sigma),
c_j = +-1 fixed per wire (hum couples either way), phi random per event. sigma is tuned so the single-look flip rate is 0.15 (same as the earlier models) for every A,
so a difference between rows comes from the spacing and the hum, not from more noise overall.  Stage 1 = the board-verified bank model (hexn_bank_model_v2),
summed burst counts over L looks, exactly as hexn_twostage_v2.  Metric: stage-1 both-right (two sensors, 7 classes each)."""
import sys, random, math, numpy as np
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import hexn_bank_model_v2 as B
K, NB, AW, N = 7, 18, 7, 1500
def flip_rate(A, sig, n=4000):
    ph = np.linspace(0, 2 * math.pi, n, endpoint=False); h = A * np.sin(ph)
    from math import erf, sqrt
    return float(np.mean([0.5 * (1 - erf((1 - x) / (sig * sqrt(2)))) for x in h] + [0.5 * (1 - erf((1 + x) / (sig * sqrt(2)))) for x in h]) / 1)  # c=+-1 symmetric: average of both signs
def tune(A, target=0.15):
    lo, hi = 0.05, 5.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if flip_rate(A, mid) < target: lo = mid
        else: hi = mid
    return (lo + hi) / 2
def looks(rnd, tpl, c, A, sig, f, dts, L):
    phi = rnd.uniform(0, 2 * math.pi); t = 0.0; out = []
    for i in range(L):
        h = A * math.sin(2 * math.pi * f * t + phi)
        out.append([int(((1 if b else -1) + cj * h + rnd.gauss(0, sig)) > 0) for b, cj in zip(tpl, c)])
        t += dts(i)
    return out
def winner(t): mx = max(t); return t.index(mx) if mx > 0 and t.count(mx) == 1 else -1
def run(seed, A, f, dts, L):
    rnd = random.Random(seed); sig = tune(A)
    mA = B.make(seed, K, NB, AW, 16, 0.15, 50, 4); mB = B.make(seed + 10, K, NB, AW, 16, 0.15, 50, 4)
    cA = [rnd.choice((-1, 1)) for _ in range(NB)]; cB = [rnd.choice((-1, 1)) for _ in range(NB)]
    both = tie = 0; flips = []
    for _ in range(N):
        a, b = rnd.randrange(K), rnd.randrange(K)
        la = looks(rnd, mA["tpl"][a], cA, A, sig, f, dts, L); lb = looks(rnd, mB["tpl"][b], cB, A, sig, f, dts, L)
        flips.append(np.mean([x != y for x, y in zip(la[0], mA["tpl"][a])]))
        ta = [sum(x) for x in zip(*[g for (_, g) in B.classify(mA, [(bits, a) for bits in la])])]; tb = [sum(x) for x in zip(*[g for (_, g) in B.classify(mB, [(bits, b) for bits in lb])])]
        pa, pb = winner(ta), winner(tb); both += (pa == a and pb == b); tie += (pa < 0 or pb < 0)
    return both / N, tie / N, float(np.mean(flips))
if __name__ == "__main__":
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"{N} events x {seeds} seeds. Single-look flip rate held at 0.15. Cells: both-right (ties) [measured single-look flip rate]")
    rj = random.Random(99)
    cases = [("independent (no hum)", 0.0, 50, lambda i: 0.01)]
    for A in (0.6, 1.0):
        for f in (50, 100):
            T = 1000.0 / f
            cases += [(f"hum A={A} f={f}: gap 1 cycle ({T:.0f} ms)", A, f, lambda i, T=T: T / 1000),
                      (f"hum A={A} f={f}: gap half cycle ({T/2:.0f} ms)", A, f, lambda i, T=T: T / 2000),
                      (f"hum A={A} f={f}: gap quarter cycle ({T/4:.1f} ms)", A, f, lambda i, T=T: T / 4000),
                      (f"hum A={A} f={f}: gap random 2-30 ms", A, f, lambda i: rj.uniform(0.002, 0.03))]
    for L in (2, 3):
        print(f"\n== L = {L} looks ==")
        for name, A, f, dts in cases:
            rs = [run(s, A, f, dts, L) for s in range(seeds)]
            print(f"{name:52s} {np.mean([r[0] for r in rs]):.3f} ({np.mean([r[1] for r in rs]):.2f}) [{np.mean([r[2] for r in rs]):.3f}]")
