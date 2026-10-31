"""hexn_sensor_where_v1: WHERE does the learned neural lose to the simple running mean? (Python; model only; SYNTHETIC; new file 31 Oct 2026). Alan, 15:52: 'examine the where first then the why'.
World D, corrected-height arm, WRONG table (x1.25), learn from all labelled passings (rate 64), 1000 passings, 30 seeds, 300 test passings each. Reports per-animal and per-sun-band accuracy for neural and simple design, the main confusions, and the Bayes ceiling (true model, known tables) for the same test passings."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_multiout_int_v1 as MO, hexn_sensor_sun_v1 as D, hexn_sensor_switch_v1 as S
def bayes(r, band):
    # true generative model: per-passing factor f uniform in band, height ~N(mu,sd), readings noise 3 per cent; use mean reading with variance-matched gaussian over the band centre factor
    f = D.FB[band]; m = r.mean(); best = None
    sc = []
    for a in range(D.K):
        mu = D.MU[a] * f; sd = np.sqrt((D.SD[a] * f) ** 2 + (D.MU[a] * 0.17 / np.sqrt(3) * 0.5) ** 2 + (mu * 0.03) ** 2 / 5)
        sc.append(-0.5 * ((m - mu) / sd) ** 2 - np.log(sd))
    return int(np.argmax(sc))
def run(rate=64, seeds=30, n=1000):
    K, NA = D.K, D.NA; cn = np.zeros((K, K)); cs = np.zeros((K, K)); cb = np.zeros((K, K)); tot = np.zeros(K)
    bn = np.zeros(NA); bs = np.zeros(NA); bb = np.zeros(NA); bt = np.zeros(NA); W0 = None; dW = np.zeros(NB := D.NB); occ = np.zeros(NB)
    for sd in range(seeds):
        rng = np.random.default_rng(3000 + sd); test = [(a, *D.observe(rng, a)) for a in rng.integers(0, K, 300)]; stream = [(a, *D.observe(rng, a)) for a in rng.integers(0, K, n)]
        mo = MO.MultiOutInt(S.table(1.25), rate); w0 = np.array(mo.W, float); m = D.MU * 1.25; nn = np.ones(K)
        for a, r, band in stream:
            mo.learn(D.feats("corr", r, band), a); nn[a] += 1; m[a] += (r.mean() / D.FB[band] - m[a]) / nn[a]
            c = D.counts(r / D.FB[band]); occ += np.array(c)
        dW += np.abs(np.array(mo.W, float) - w0).sum(0)
        for a, r, band in test:
            pn = mo.predict(D.feats("corr", r, band)); ps = int(np.argmin(np.abs(m - r.mean() / D.FB[band]))); pb = bayes(r, band)
            tot[a] += 1; cn[a, pn] += 1; cs[a, ps] += 1; cb[a, pb] += 1; bt[band] += 1; bn[band] += pn == a; bs[band] += ps == a; bb[band] += pb == a
    names = ["rat", "cat", "dog", "sheep", "deer", "horse"]
    print("per animal accuracy (neural / simple / true-model ceiling):")
    for a in range(K): print("  %-6s %.2f  %.2f  %.2f" % (names[a], cn[a, a] / tot[a], cs[a, a] / tot[a], cb[a, a] / tot[a]))
    print("overall: neural %.3f simple %.3f ceiling %.3f" % (np.trace(cn) / tot.sum(), np.trace(cs) / tot.sum(), np.trace(cb) / tot.sum()))
    print("per sun band 0..5 (neural / simple / ceiling):")
    for b in range(NA): print("  band %d  %.2f  %.2f  %.2f" % (b, bn[b] / bt[b], bs[b] / bt[b], bb[b] / bt[b]))
    print("biggest neural errors (true -> guessed, share of all test passings), simple design in brackets:")
    e = [(cn[a, p] / tot.sum(), cs[a, p] / tot.sum(), names[a], names[p]) for a in range(K) for p in range(K) if a != p]
    for v, s, a, p in sorted(e, reverse=True)[:6]: print("  %s -> %s  %.3f  (%.3f)" % (a, p, v, s))
    print("height bins (8 cm): total |weight change| per bin (all animals, mean per seed) and passings landing in the bin per seed:")
    print("  bin  " + " ".join("%5d" % i for i in range(NB))); print("  dW   " + " ".join("%5.0f" % (v / seeds) for v in dW)); print("  seen " + " ".join("%5.0f" % (v / seeds) for v in occ))
run()
