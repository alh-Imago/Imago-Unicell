"""hexn_sensor_bins_v1: IS IT THE 8 cm BINS? (Python; model only; SYNTHETIC; new file 31 Oct 2026). Alan, 15:52: 'examine the where first then the why'. tools/hexn_sensor_why_v1.py showed that 16 times more passings did not lift the neural (.86 against .90): not a shortage of data. Test: the corrected-height arm with the layer 1 bin width 8, 4, 2 cm (24, 48, 96 inputs; the simple design uses the exact mean). WRONG table (x1.25) and blank start, rate 64 and 16, 1000 passings, 8 seeds."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_multiout_int_v1 as MO, hexn_sensor_sun_v1 as D, hexn_sensor_switch_v1 as S
def run(seeds=8, n=1000):
    for rate in (64, 16):
        print("rate %d/128, %d passings:" % (rate, n))
        for bw in (8, 4, 2):
            D.BW = float(bw); D.NB = int(192 // bw); res = {"wrong": 0.0, "blank": 0.0, "simple": 0.0}
            for sd in range(seeds):
                rng = np.random.default_rng(5000 + sd); test = [(a, *D.observe(rng, a)) for a in rng.integers(0, D.K, 300)]; stream = [(a, *D.observe(rng, a)) for a in rng.integers(0, D.K, n)]
                ms = {k: MO.MultiOutInt(S.table(1.25) if k == "wrong" else D.prior("corr", True), rate) for k in ("wrong", "blank")}; m = D.MU * 1.25; nn = np.ones(D.K)
                for a, r, band in stream:
                    for mo in ms.values(): mo.learn(D.feats("corr", r, band), a)
                    nn[a] += 1; m[a] += (r.mean() / D.FB[band] - m[a]) / nn[a]
                for k, mo in ms.items(): res[k] += np.mean([mo.predict(D.feats("corr", r, b)) == a for a, r, b in test])
                res["simple"] += np.mean([int(np.argmin(np.abs(m - r.mean() / D.FB[b]))) == a for a, r, b in test])
            print("  bin %d cm (%2d inputs): neural wrong-start %.3f  blank-start %.3f   simple %.3f" % (bw, D.NB, res["wrong"] / seeds, res["blank"] / seeds, res["simple"] / seeds))
run()
