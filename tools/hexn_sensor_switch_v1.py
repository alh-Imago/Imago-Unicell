"""hexn_sensor_switch_v1: THE LEARNING SWITCH (Python; model only; SYNTHETIC; new file 31 Oct 2026). Alan, 15:49: 'yes apply the learning switch, this would be similar to the switch to opponent type during play'.
Same world D as tools/hexn_sensor_sun_v1.py (sun angle, corrected-height arm, 24 inputs, whole-number learning). Three arms:
  never : table as loaded, no learning;      always: learns from every labelled passing (the old behaviour);
  switch: learning OFF while the loaded table keeps predicting well. A window of the last WIN labelled passings counts the neural's own wrong guesses (made BEFORE learning from that passing). When wrong guesses in the window reach LIMIT, learning turns ON; once ON it stays on (no switch back; tried below as HOLD variants).
Two loaded tables: RIGHT (the true animal table) and WRONG (all animals 25 per cent taller than loaded). Simple design cent_corr (running mean of corrected height, prior = loaded mean, weight 1) for the lower limit.
Usage: python3 tools/hexn_sensor_switch_v1.py [RATE] [WIN] [LIMIT]  (defaults 64 20 6)"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_multiout_int_v1 as MO, hexn_sensor_sun_v1 as D
def table(scale):
    W = D.score_rows(D.MU * scale, D.SD * scale); return np.round(W * 256).astype(int).tolist()
def run(rate=64, win=20, limit=6, seeds=30, ns=(0, 10, 30, 100, 300, 1000)):
    arms = ["never", "always", "switch", "cent_corr"]; out = {}
    for tname, scale in (("RIGHT", 1.0), ("WRONG", 1.25)):
        acc = {a: np.zeros(len(ns)) for a in arms}; on_at = []; fired = 0
        for sd in range(seeds):
            rng = np.random.default_rng(3000 + sd); test = [(a, *D.observe(rng, a)) for a in rng.integers(0, D.K, 300)]; stream = [(a, *D.observe(rng, a)) for a in rng.integers(0, D.K, max(ns))]
            for arm in arms:
                if arm == "cent_corr": m = D.MU * scale; nn = np.ones(D.K)
                else: mo = MO.MultiOutInt(table(scale), rate)
                learn = arm == "always"; hist = []; done = 0
                for j, n in enumerate(ns):
                    for i in range(done, n):
                        a, r, band = stream[i]
                        if arm == "cent_corr": nn[a] += 1; m[a] += (r.mean() / D.FB[band] - m[a]) / nn[a]; continue
                        x = D.feats("corr", r, band)
                        if arm == "switch" and not learn:
                            hist.append(mo.predict(x) != a); hist = hist[-win:]
                            if sum(hist) >= limit: learn = True; on_at.append(i + 1)
                        if learn: mo.learn(x, a)
                    done = n
                    if arm == "cent_corr": ok = np.mean([int(np.argmin(np.abs(m - r.mean() / D.FB[b]))) == a for a, r, b in test])
                    else: ok = np.mean([mo.predict(D.feats("corr", r, b)) == a for a, r, b in test])
                    acc[arm][j] += ok
        out[tname] = (acc, on_at)
        print("table %s, rate %d/128, window %d limit %d; labelled passings seen:" % (tname, rate, win, limit), "  ".join("%5d" % n for n in ns))
        for a in arms: print("  %-10s" % a, "  ".join("%.2f " % (v / seeds) for v in acc[a]))
        print("  switch turned learning on in %d of %d runs; median passing %s" % (len(on_at), seeds, int(np.median(on_at)) if on_at else "-"))
if __name__ == "__main__":
    a = [int(v) for v in sys.argv[1:]]; run(*a)
