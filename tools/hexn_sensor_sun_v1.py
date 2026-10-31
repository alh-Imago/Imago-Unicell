"""hexn_sensor_sun_v1: SECOND SENSOR CUE, THE SUN ANGLE (Python + numpy; model only; SYNTHETIC; new file 31 Oct 2026). Alan, 15:01: 'the sun angle ... is another input factor, which the layer 1 handles so well, so yes this can be added'.
World D = world C of the shadow test with the cause made visible: each passing has a sun position u in 0..1; the shadow is scaled by f = 0.7 + 0.6 u; a SECOND sensor reads u with noise 0.03 and layer 1 turns it into 6 bands (one counted detector per band, count 1). Same six animals, 5 height readings per passing, 24 height bins of 8 cm.
Ways to use the second cue, all learned with the WHOLE-NUMBER step of tools/hexn_multiout_int_v1.py (weights Q8, rate in 1/128):
  one   : height counts only (the old world-C arm; the angle is ignored) - 24 inputs;
  concat: height counts + the 6 band detectors side by side - 30 inputs (a linear score cannot multiply them);
  joint : one detector per (height bin, band) pair, 144 inputs: the combination of the two layer 1 feeds is itself a counted key (what layer 3 does with moments);
  corr  : layer 1 bins the height reading divided by the band's factor (the sun table is a loaded item) - 24 inputs.
Priors from the stated tables: the animal table (as before) and the sun table (factor at the band centre, within-band spread of the factor): joint prior = per band, mean x factor and spread widened for the factor spread; corr prior = the animal table as it stands; concat prior = the animal table on the height block, 0 on the angle block. 'blank' = no prior (learns from nothing) for joint and corr.
Simple designs for the lower limit: cent_band (running mean of the observed height per animal AND band, nearest mean wins, prior = table mean x band factor), cent_corr (running mean of the corrected height per animal).
Usage: python3 tools/hexn_sensor_sun_v1.py [RATE]  (rate in 1/128 units, default 192)"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_multiout_int_v1 as MO
MU = np.array([10, 28, 50, 75, 110, 150.0]); SD = np.array([2, 4, 10, 8, 12, 12.0]); K = 6; NB = 24; BW = 8.0; NA = 6
FB = 0.7 + 0.6 * (np.arange(NA) + 0.5) / NA      # factor at the centre of each band
def observe(rng, a):
    h = rng.normal(MU[a], SD[a]); u = rng.uniform(); f = 0.7 + 0.6 * u; r = h * f * (1 + 0.03 * rng.standard_normal(5)); ua = min(max(u + 0.03 * rng.standard_normal(), 0.0), 0.999); band = int(ua * NA)
    return r, band
def counts(r): return [int(v) for v in np.bincount(np.clip((r // BW).astype(int), 0, NB - 1), minlength=NB)]
def feats(kind, r, band):
    if kind == "one": return counts(r)
    if kind == "concat": return counts(r) + [1 if i == band else 0 for i in range(NA)]
    if kind == "joint": x = [0] * (NB * NA); x[band * NB:(band + 1) * NB] = counts(r); return x
    return list(counts(r / FB[band]))
def score_rows(mu, sd):
    c = (np.arange(NB) + 0.5) * BW; sd = np.maximum(sd, 3.0)[:, None]; return np.maximum(-0.5 * ((c[None, :] - mu[:, None]) / sd) ** 2, -8.0) - np.log(sd)
def prior(kind, blank):
    base = score_rows(MU, SD); n = {"one": NB, "concat": NB + NA, "joint": NB * NA, "corr": NB}[kind]; W = np.zeros((K, n))
    if blank: return W.astype(int).tolist()
    if kind in ("one", "corr"): W[:, :NB] = base
    elif kind == "concat": W[:, :NB] = base
    else:
        for c in range(NA): W[:, c * NB:(c + 1) * NB] = score_rows(MU * FB[c], np.sqrt((SD * FB[c]) ** 2 + (MU * 0.029) ** 2))
    return np.round(W * 256).astype(int).tolist()
def run(rate=192, seeds=30, ns=(0, 10, 30, 100, 300, 1000)):
    arms = [("one", False), ("concat", False), ("joint", False), ("corr", False), ("joint", True), ("corr", True), ("cent_band", False), ("cent_corr", False)]; acc = {a: np.zeros(len(ns)) for a in arms}; wm = 0
    for sd in range(seeds):
        rng = np.random.default_rng(2000 + sd); test = [(a, *observe(rng, a)) for a in rng.integers(0, K, 300)]; stream = [(a, *observe(rng, a)) for a in rng.integers(0, K, max(ns))]
        for arm in arms:
            kind, blank = arm; done = 0
            if kind.startswith("cent"):
                m = np.tile(MU[:, None], (1, NA)) * FB[None, :] if kind == "cent_band" else np.tile(MU[:, None], (1, 1)); nn = np.ones_like(m)
            else: mo = MO.MultiOutInt(prior(kind, blank), rate)
            for j, n in enumerate(ns):
                for a, r, band in stream[done:n]:
                    if kind == "cent_band": nn[a, band] += 1; m[a, band] += (r.mean() - m[a, band]) / nn[a, band]
                    elif kind == "cent_corr": nn[a, 0] += 1; m[a, 0] += (r.mean() / FB[band] - m[a, 0]) / nn[a, 0]
                    else: mo.learn(feats(kind, r, band), a)
                done = n
                if kind == "cent_band": ok = np.mean([int(np.argmin(np.abs(m[:, b] - r.mean()))) == a for a, r, b in test])
                elif kind == "cent_corr": ok = np.mean([int(np.argmin(np.abs(m[:, 0] - r.mean() / FB[b]))) == a for a, r, b in test])
                else: ok = np.mean([mo.predict(feats(kind, r, b)) == a for a, r, b in test])
                acc[arm][j] += ok
            if not kind.startswith("cent"): wm = max(wm, mo.wmax)
    print("rate %d/128; labelled passings seen:" % rate, "  ".join("%5d" % n for n in ns))
    for arm in arms: print("  %-10s %-6s accuracy:" % (arm[0], "blank" if arm[1] else ("" if arm[0].startswith("cent") else "prior")), "  ".join("%.2f " % (v / seeds) for v in acc[arm]))
    print("  largest |weight| in any whole-number arm: %d (16 bit limit 32767)" % wm)
if __name__ == "__main__": run(int(sys.argv[1]) if len(sys.argv) > 1 else 192)
