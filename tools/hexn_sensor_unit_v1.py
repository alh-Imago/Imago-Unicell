"""hexn_sensor_unit_v1: THE SENSOR SIDE OF THE UNIT, ALL THE FIXES TOGETHER (Python; model only; SYNTHETIC; new file 31 Oct 2026). Alan, 15:56: 'add in the learning switch and the finer bins'.
World D (sun angle), corrected-height arm, whole-number learning at a LOW rate (16/128), layer 1 bins of 8 / 4 / 2 cm, learning switch (OFF until 8 of the last 20 labelled guesses are wrong, then ON for good). Loaded table RIGHT or WRONG (animals 25 per cent taller). Arms: never, always, switch, simple (running mean of corrected height). Passings run to 3000 so false alarms of the switch on the right table show. Usage: python3 tools/hexn_sensor_unit_v1.py [SEEDS] [RATE]"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_multiout_int_v1 as MO, hexn_sensor_sun_v1 as D, hexn_sensor_switch_v1 as S
def run(seeds=10, rate=16, win=20, limit=8, ns=(0, 10, 30, 100, 300, 1000, 3000)):
    arms = ["never", "always", "switch", "simple"]
    for bw in (8, 4, 2):
        D.BW = float(bw); D.NB = int(192 // bw)
        for tname, scale in (("RIGHT", 1.0), ("WRONG", 1.25)):
            acc = {a: np.zeros(len(ns)) for a in arms}; on_at = []
            for sd in range(seeds):
                rng = np.random.default_rng(7000 + sd); test = [(a, *D.observe(rng, a)) for a in rng.integers(0, D.K, 300)]; stream = [(a, *D.observe(rng, a)) for a in rng.integers(0, D.K, max(ns))]
                for arm in arms:
                    if arm == "simple": m = D.MU * scale; nn = np.ones(D.K)
                    else: mo = MO.MultiOutInt(S.table(scale), rate)
                    learn = arm == "always"; hist = []; done = 0
                    for j, n in enumerate(ns):
                        for i in range(done, n):
                            a, r, band = stream[i]
                            if arm == "simple": nn[a] += 1; m[a] += (r.mean() / D.FB[band] - m[a]) / nn[a]; continue
                            x = D.feats("corr", r, band)
                            if arm == "switch" and not learn:
                                hist.append(mo.predict(x) != a); hist = hist[-win:]
                                if sum(hist) >= limit: learn = True; on_at.append(i + 1)
                            if learn: mo.learn(x, a)
                        done = n
                        if arm == "simple": ok = np.mean([int(np.argmin(np.abs(m - r.mean() / D.FB[b]))) == a for a, r, b in test])
                        else: ok = np.mean([mo.predict(D.feats("corr", r, b)) == a for a, r, b in test])
                        acc[arm][j] += ok
            print("bin %d cm (%d inputs), table %s, rate %d/128; passings:" % (bw, D.NB, tname, rate), "  ".join("%5d" % n for n in ns), flush=True)
            for a in arms: print("  %-7s" % a, "  ".join("%.3f" % (v / seeds) for v in acc[a]))
            print("  switch on in %d of %d runs, median passing %s" % (len(on_at), seeds, int(np.median(on_at)) if on_at else "-"), flush=True)
if __name__ == "__main__":
    run(*[int(v) for v in sys.argv[1:]])
