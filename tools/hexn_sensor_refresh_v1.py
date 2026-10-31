"""hexn_sensor_refresh_v1: LEVERAGE THE RUNNING AVERAGE TO SET THE NEURAL'S WEIGHTS (Python; model only; SYNTHETIC; new file 31 Oct 2026). Alan, 16:02: 'the running average system ... could this be leveraged to give the cell a boost in its result calculations? training, weights etc'.
Idea: the running mean and spread per animal ARE the goals table (mean, spread) of the goals-to-weights step; rebuild the neural's weights from them every 10 labelled passings (no gradient step). Statistics per animal: count, mean, variance (Welford; the loaded table counts as 3 pseudo-passings). Arms: refresh (never forgets), refresh_f (forgets: step never below 1/100), simple (nearest running mean), always (gradient learning at 64/128, the old arm). World D corrected-height arm, 4 cm bins, scenarios RIGHT, WRONG (x1.25), SHIFT (right, then at passing 1500 every animal 25 per cent taller). 6 seeds. Usage: python3 tools/hexn_sensor_refresh_v1.py [SEEDS]"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_multiout_int_v1 as MO, hexn_sensor_sun_v1 as D, hexn_sensor_switch_v1 as S
class Stats:
    def __init__(s, scale, floor): s.n = np.full(D.K, 3.0); s.m = D.MU * scale; s.v = (D.SD * scale) ** 2 + (D.MU * scale * 0.03) ** 2; s.floor = floor
    def add(s, a, y):
        s.n[a] += 1; g = max(1.0 / s.n[a], s.floor); d = y - s.m[a]; s.m[a] += g * d; s.v[a] += g * (d * d - s.v[a])
    def weights(s): return np.round(D.score_rows(s.m, np.sqrt(s.v)) * 256).astype(int).tolist()
def run(seeds=6, every=10):
    D.BW = 4.0; D.NB = 48; ns = (0, 10, 30, 100, 300, 1000, 1500, 1600, 1800, 2200, 3000); arms = ["refresh", "refresh_f", "simple", "always"]
    for sc, scale in (("RIGHT", 1.0), ("WRONG", 1.25), ("SHIFT", 1.0)):
        acc = {a: np.zeros(len(ns)) for a in arms}
        for sd in range(seeds):
            rng = np.random.default_rng(9000 + sd); test = [(a, *D.observe(rng, a)) for a in rng.integers(0, D.K, 300)]; stream = [(a, *D.observe(rng, a)) for a in rng.integers(0, D.K, max(ns))]
            if sc == "SHIFT": stream = [(a, r * (1.25 if i >= 1500 else 1.0), b) for i, (a, r, b) in enumerate(stream)]; test2 = [(a, r * 1.25, b) for a, r, b in test]
            for arm in arms:
                if arm == "simple": m = D.MU * scale; nn = np.ones(D.K)
                elif arm == "always": mo = MO.MultiOutInt(S.table(scale), 64)
                else: st = Stats(scale, 0.0 if arm == "refresh" else 0.01); mo = MO.MultiOutInt(st.weights(), 0)
                done = 0
                for j, n in enumerate(ns):
                    for i in range(done, n):
                        a, r, band = stream[i]; y = r.mean() / D.FB[band]
                        if arm == "simple": nn[a] += 1; m[a] += (y - m[a]) / nn[a]
                        elif arm == "always": mo.learn(D.feats("corr", r, band), a)
                        else:
                            st.add(a, y)
                            if (i + 1) % every == 0: mo.W = st.weights()
                    done = n; T = test2 if (sc == "SHIFT" and n > 1500) else test
                    if arm != "simple" and arm != "always" and n % every: mo.W = st.weights()
                    if arm == "simple": ok = np.mean([int(np.argmin(np.abs(m - r.mean() / D.FB[b]))) == a for a, r, b in T])
                    else: ok = np.mean([mo.predict(D.feats("corr", r, b)) == a for a, r, b in T])
                    acc[arm][j] += ok
        print("%s, 4 cm bins; passings:" % sc, "  ".join("%5d" % n for n in ns), flush=True)
        for a in arms: print("  %-9s" % a, "  ".join("%.3f" % (v / seeds) for v in acc[a]), flush=True)
if __name__ == "__main__": run(*[int(v) for v in sys.argv[1:]])
