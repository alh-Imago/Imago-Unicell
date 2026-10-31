"""hexn_sensor_why_v1: WHY does the learned corrected-height neural stop at .87-.88 against .91 for the running mean? (Python; model only; SYNTHETIC; new file 31 Oct 2026). Alan, 15:52: 'examine the where first then the why'.
Hypothesis from the where-run (tools/hexn_sensor_where_v1.py): the neural has 144 free numbers (6 animals x 24 bins) learned from a few thousand noisy readings, the simple design 6 means; a shortage of data per bin, not the learning rule, would show as accuracy rising toward .91 with many more passings, and a smoothed (shared-shape) table would help early. Arms: neural WRONG table, neural blank, simple; passings 1000 / 4000 / 16000; rates 64 and 16; 8 seeds."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_multiout_int_v1 as MO, hexn_sensor_sun_v1 as D, hexn_sensor_switch_v1 as S
def run(seeds=8, ns=(1000, 4000, 16000), rates=(64, 16)):
    for rate in rates:
        acc = {k: np.zeros(len(ns)) for k in ("wrong", "blank")}; sim = np.zeros(len(ns))
        for sd in range(seeds):
            rng = np.random.default_rng(5000 + sd); test = [(a, *D.observe(rng, a)) for a in rng.integers(0, D.K, 300)]; stream = [(a, *D.observe(rng, a)) for a in rng.integers(0, D.K, max(ns))]
            ms = {k: MO.MultiOutInt(S.table(1.25) if k == "wrong" else D.prior("corr", True), rate) for k in acc}; m = D.MU * 1.25; nn = np.ones(D.K); done = 0
            for j, n in enumerate(ns):
                for a, r, band in stream[done:n]:
                    for mo in ms.values(): mo.learn(D.feats("corr", r, band), a)
                    nn[a] += 1; m[a] += (r.mean() / D.FB[band] - m[a]) / nn[a]
                done = n
                for k, mo in ms.items(): acc[k][j] += np.mean([mo.predict(D.feats("corr", r, b)) == a for a, r, b in test])
                sim[j] += np.mean([int(np.argmin(np.abs(m - r.mean() / D.FB[b]))) == a for a, r, b in test])
        print("rate %d/128; passings:" % rate, "  ".join("%6d" % n for n in ns))
        for k in acc: print("  neural %-6s" % k, "  ".join("%.3f " % (v / seeds) for v in acc[k]))
        print("  simple       ", "  ".join("%.3f " % (v / seeds) for v in sim))
run()
