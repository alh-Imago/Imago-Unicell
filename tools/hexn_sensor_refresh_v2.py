"""hexn_sensor_refresh_v2: TWO WAYS TO IMPROVE THE TABLE REFRESH (Python; model only; SYNTHETIC; new file 31 Oct 2026). Alan, 16:05: 'both are good approaches, try one then the other see which comes out best'. Clone of tools/hexn_sensor_refresh_v1.py (v1 unchanged).
  refresh_t : labelled; the loaded table is trusted as 3 pseudo-passings until the neural's own wrong guesses reach 8 of the last 20 (the 17:55 counter), then the pseudo-counts drop to 1 (the loaded table is nearly forgotten) - fixes the early lag.
  unl       : UNLABELLED; the neural's own guess is used as the label (hard EM); every passing updates the guessed animal's mean and variance.
  unl_gate  : unlabelled, only passings whose best score beats the second by at least GATE (2 nats = 512 in Q8 weight units) update.
  refresh (v1 labelled, reference) and simple. Forgetting step never below 1/100 in the SHIFT scenario arms. World D corrected-height arm, 4 cm bins, RIGHT / WRONG (x1.25) / SHIFT (animals 25 per cent taller from passing 1500). 6 seeds. Usage: python3 tools/hexn_sensor_refresh_v2.py [SEEDS]"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_multiout_int_v1 as MO, hexn_sensor_sun_v1 as D, hexn_sensor_switch_v1 as S, hexn_sensor_refresh_v1 as R
def run(seeds=6, every=10, gate=512):
    D.BW = 4.0; D.NB = 48; ns = (0, 10, 30, 100, 300, 1000, 1500, 1600, 1800, 2200, 3000); arms = ["refresh", "refresh_t", "unl", "unl_gate", "simple"]
    for sc, scale in (("RIGHT", 1.0), ("WRONG", 1.25), ("SHIFT", 1.0)):
        acc = {a: np.zeros(len(ns)) for a in arms}
        for sd in range(seeds):
            rng = np.random.default_rng(9000 + sd); test = [(a, *D.observe(rng, a)) for a in rng.integers(0, D.K, 300)]; stream = [(a, *D.observe(rng, a)) for a in rng.integers(0, D.K, max(ns))]
            if sc == "SHIFT": stream = [(a, r * (1.25 if i >= 1500 else 1.0), b) for i, (a, r, b) in enumerate(stream)]; test2 = [(a, r * 1.25, b) for a, r, b in test]
            for arm in arms:
                if arm == "simple": m = D.MU * scale; nn = np.ones(D.K)
                else: st = R.Stats(scale, 0.01 if sc == "SHIFT" else 0.0); mo = MO.MultiOutInt(st.weights(), 0); hist = []; trusted = True; seen = 0
                done = 0
                for j, n in enumerate(ns):
                    for i in range(done, n):
                        a, r, band = stream[i]; y = r.mean() / D.FB[band]
                        if arm == "simple": nn[a] += 1; m[a] += (y - m[a]) / nn[a]; continue
                        x = D.feats("corr", r, band)
                        if arm.startswith("unl"):
                            sc_ = mo.scores(x); o = sorted(sc_, reverse=True); g = sc_.index(o[0])
                            if arm == "unl" or o[0] - o[1] >= gate: st.add(g, y)
                        else:
                            if arm == "refresh_t":
                                hist.append(mo.predict(x) != a); hist = hist[-20:]
                                if trusted and sum(hist) >= 8: trusted = False; st.n = np.minimum(st.n, 1.0)
                            st.add(a, y)
                        if (i + 1) % every == 0: mo.W = st.weights()
                    done = n; T = test2 if (sc == "SHIFT" and n > 1500) else test
                    if arm == "simple": ok = np.mean([int(np.argmin(np.abs(m - r.mean() / D.FB[b]))) == a for a, r, b in T])
                    else:
                        if n % every: mo.W = st.weights()
                        ok = np.mean([mo.predict(D.feats("corr", r, b)) == a for a, r, b in T])
                    acc[arm][j] += ok
        print("%s, 4 cm bins; passings:" % sc, "  ".join("%5d" % n for n in ns), flush=True)
        for a in arms: print("  %-9s" % a, "  ".join("%.3f" % (v / seeds) for v in acc[a]), flush=True)
if __name__ == "__main__": run(*[int(v) for v in sys.argv[1:]])
