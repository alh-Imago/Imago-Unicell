"""(v2, clone of hexn_grade_v1.py which is left untouched.) Adds: Q swept down to 0.125 (outcomes NOT shared across a family: 8 values, so a family guess is right 1 time in 8), the CLOSE vote floor 0.5 + VZ x 0.5 / sqrt(k) with VZ swept (4.2 as v1, 2.0 looser), and a sweep of the confidence LEVEL at which an answer is accepted (0.9, 0.7, 0.5, 0.3, 0): share of ALL queries answered, accuracy of those, and the share of RANDOM queries answered (always wrong).
Graded reply (EXACT / CLOSE / UNKNOWN) with a leap from the family, trained by the real outcome. Python model only; plain compare-all store, not the real block; the family structure of the OUTCOMES is an assumption built into the data (below), not something measured.
500 stored 64-wire patterns in 25 families (centre + SPREAD flipped wires), as hexn_noise_fb_v3.py. Each pattern has an OUTCOME, one of 8 values: the family's outcome with probability Q (default 0.8), otherwise a random value. A new family member (a SIBLING, never stored) gets its outcome by the same rule: so the family says something true about a sibling, but not always.
Looks and cue cleaning as C2 in hexn_noise_fb_v2.py: two looks, disagreeing wires unknown, noise estimate p_hat from the disagreement, third look (majority) if p_hat > 0.12.
BIN (today): one look, fixed threshold 0.75, best strictly ahead of second: answer the best match's outcome, else no answer.
GRADE: EXACT = best score >= max(0.60, 1 - p_hat - 3 sigma, chance level for k known wires) and strictly ahead: answer the best's outcome. CLOSE = not exact but some stored patterns score above the chance level: answer by a vote of those patterns weighted by (score - 0.5), the leap. UNKNOWN otherwise.
TRAINING FEEDBACK: after each answer the true outcome arrives; per (grade, score band) the system keeps hits and tries and reports confidence = (hits+1)/(tries+2), learned online (no stored pattern is added or changed; that is a separate step). Reported: share answered, accuracy when answered, share of ALL queries answered correctly, accuracy and share when the learned confidence >= 0.7, and calibration (mean |confidence - actual| per answer, second half of the stream).
Queries per stream: 1/3 known, 1/3 sibling, 1/3 random (a random pattern has no true outcome in this model, so an answer to it counts as wrong). Usage: python3 tools/hexn_grade_v1.py [SEEDS]"""
import sys, numpy as np
from hexn_noise_fb_v2 import estimate, chance, W
N, F, O = 500, 25, 8
def run(seed, spread, noise, q=0.8, n_q=6000, vz=4.2):
    rng = np.random.default_rng(seed); cen = rng.integers(0, 2, (F, W), dtype=np.uint8); fout = rng.integers(0, O, F)
    def member():
        f = int(rng.integers(0, F)); c = cen[f].copy(); c[rng.choice(W, spread, replace=False)] ^= 1
        return c, (int(fout[f]) if rng.random() < q else int(rng.integers(0, O)))
    ms = [member() for _ in range(N)]; pats = np.array([m[0] for m in ms]); outs = np.array([m[1] for m in ms])
    cells = {}; rec = []; st = {k: dict(ans=0, right=0, hi_n=0, hi_right=0, cal=0.0, cal_n=0, n=0, g={}) for k in ("BIN", "GRADE")}
    kinds = {k: {"BIN": [0, 0, 0], "GRADE": [0, 0, 0]} for k in ("known", "sibling", "random")}
    for k in range(n_q):
        kind = ("known", "sibling", "random")[k % 3]
        if kind == "known": i = int(rng.integers(0, N)); base = pats[i]; truth = int(outs[i])
        elif kind == "sibling": base, truth = member()
        else: base = rng.integers(0, 2, W, dtype=np.uint8); truth = -1
        looks = [base ^ (rng.random(W) < noise).astype(np.uint8) for _ in range(3)]
        s = ((pats == looks[0])).sum(1); o = np.argsort(-s); b = s[o[0]] / W
        ans_b = int(outs[o[0]]) if b >= 0.75 * 1 and s[o[0]] > s[o[1]] else None
        agree = looks[0] == looks[1]; ph = estimate(1 - agree.mean())
        if ph > 0.12: cue, known = (sum(looks) >= 2).astype(np.uint8), np.ones(W, bool)
        else: cue, known = looks[0], agree
        kk = max(1, int(known.sum())); sc = ((pats == cue) & known).sum(1) / kk; o2 = np.argsort(-sc); best, second = sc[o2[0]], sc[o2[1]]
        ch = chance(kk); thr = max(0.60, 1 - ph - 3 * np.sqrt(max(ph * (1 - ph), 1e-4) / kk), ch)
        cv = 0.5 + vz * 0.5 / np.sqrt(kk)
        if kk < 8: grade, ans = "UNKNOWN", None
        elif best >= thr and best > second: grade, ans = "EXACT", int(outs[o2[0]])
        elif best >= cv:
            w = np.clip(sc - 0.5, 0, None) * (sc >= cv); v = np.bincount(outs, weights=w, minlength=O)
            grade, ans = "CLOSE", int(v.argmax())
        else: grade, ans = "UNKNOWN", None
        for name, a in (("BIN", ans_b), ("GRADE", ans)):
            r = st[name]; r["n"] += 1; kinds[kind][name][0] += 1
            if a is None: continue
            r["ans"] += 1; ok = a == truth; r["right"] += ok; kinds[kind][name][1] += 1; kinds[kind][name][2] += ok
            if name == "GRADE":
                band = (grade, int(np.clip((best - cv) / max(1e-9, 1 - cv) * 4, 0, 3))); h, t = cells.get(band, (0, 0)); conf = (h + 1) / (t + 2)
                if k >= n_q // 2: r["cal"] += abs(conf - ok); r["cal_n"] += 1; r["hi_n"] += conf >= 0.7; r["hi_right"] += (conf >= 0.7) and ok
                cells[band] = (h + ok, t + 1)
                if k >= n_q // 2: rec.append((conf, bool(ok), kind))
                if k >= n_q // 2: gg = r["g"].setdefault(grade, [0, 0, 0.0]); gg[0] += 1; gg[1] += ok; gg[2] += conf
    return st, kinds, rec
LEVELS = (0.9, 0.7, 0.5, 0.3, 0.0)
if __name__ == "__main__":
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"{N} patterns in {F} families, noise p=0.08, {seeds} seeds, 6,000 queries per stream (1/3 known, 1/3 sibling, 1/3 random). Q = chance a pattern's outcome equals its family's (1/8 = no sharing). VZ = looseness of the CLOSE vote floor (4.2 strict, 2.0 loose)")
    print("spread | Q | VZ | level | answered (share of all) | right when answered | random queries answered | mean conf of accepted")
    for spread in (6, 12):
        for q, vz in ((0.8, 4.2), (0.8, 2.0), (0.5, 4.2), (0.5, 2.0), (0.125, 4.2), (0.125, 2.0)):
            rs = [run(s, spread, 0.08, q=q, vz=vz) for s in range(seeds)]
            for L in LEVELS:
                a = [[x for x in r[2] if x[0] >= L] for r in rs]; half = 3000
                sh = np.mean([len(x) / half for x in a]); ac = np.mean([np.mean([y[1] for y in x]) if x else float("nan") for x in a])
                rn = np.mean([sum(1 for y in x if y[2] == "random") / (half / 3) for x in a]); mc = np.mean([np.mean([y[0] for y in x]) if x else float("nan") for x in a])
                print(f"{spread:<6} | {q:<5} | {vz} | {L:<5} | {sh:.3f} | {ac:.3f} | {rn:.3f} | {mc:.3f}")
