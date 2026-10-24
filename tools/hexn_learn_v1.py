"""Outcome feedback changes the STORED PATTERNS (online learning), Python model only; plain compare-all store with a size limit, not the real block; nothing here has run on a board.
World: 25 families of 64-wire patterns (centre + SPREAD flipped wires); a POOL of 600 objects (family members) each with an outcome (its family's value with probability Q, else random of 8); queries draw uniformly from the pool (so objects recur, about 11 times each in 8,000 queries), 5/6 pool objects and 1/6 random patterns (no true outcome, no feedback). Each look flips every wire with probability p=0.08.
Reply as hexn_grade_v2.py (two looks, disagreeing wires unknown, noise estimate, third look if noisy; EXACT / CLOSE by vote / UNKNOWN; strict vote floor; learned confidence per (grade, score band)); the answer is ACCEPTED if the grade is not UNKNOWN and the learned confidence >= 0.5.
Feedback: after each query with a true outcome the true outcome arrives (ASSUMED to arrive whether or not the system answered). Confidence cells are updated for every accepted answer. Storing the pattern (the majority of the 3 looks, about 1.8 percent of wires wrong at p=0.08) in a store of CAP slots, least recently used leaves:
 STATIC  never stores; starts with the same 100 pool objects (no learning)
 LEARN_A stores when the system did not accept an answer (did not know) or the accepted answer was wrong
 LEARN_B as A, and also when a CLOSE answer was right (so the sibling becomes an exact member)
All start with 100 pool objects stored. Reported per window of 1,000 queries (mean of seeds): correct = accepted and right, as a share of pool queries; wrong = accepted and wrong, share of pool queries; random answered = share of random queries accepted. Usage: python3 tools/hexn_learn_v1.py [SEEDS]"""
import sys, numpy as np
from hexn_noise_fb_v2 import estimate, chance, W
F, O, P, CAP, START, NQ = 25, 8, 600, 400, 100, 8000
def run(seed, spread, q, mode, noise=0.08):
    rng = np.random.default_rng(seed); cen = rng.integers(0, 2, (F, W), dtype=np.uint8); fout = rng.integers(0, O, F)
    pool = []; 
    for _ in range(P):
        f = int(rng.integers(0, F)); c = cen[f].copy(); c[rng.choice(W, spread, replace=False)] ^= 1; pool.append((c, int(fout[f]) if rng.random() < q else int(rng.integers(0, O))))
    pats = np.zeros((CAP, W), dtype=np.uint8); outs = np.zeros(CAP, dtype=int); last = np.zeros(CAP); valid = np.zeros(CAP, bool)
    for j, i in enumerate(rng.choice(P, START, replace=False)): pats[j], outs[j] = pool[i]; valid[j] = True
    def store(pat, out, now):
        j = int(np.argmin(np.where(valid, last, -1))) if valid.all() else int(np.argmin(valid)); pats[j], outs[j], last[j], valid[j] = pat, out, now, True
    cells = {}; win = [dict(n=0, ok=0, bad=0, rn=0, ra=0, size=0) for _ in range(NQ // 1000)]; stored_total = 0
    for k in range(NQ):
        is_rand = k % 6 == 5
        if is_rand: base, truth = rng.integers(0, 2, W, dtype=np.uint8), -1
        else: i = int(rng.integers(0, P)); base, truth = pool[i]
        looks = [base ^ (rng.random(W) < noise).astype(np.uint8) for _ in range(3)]
        agree = looks[0] == looks[1]; ph = estimate(1 - agree.mean())
        if ph > 0.12: cue, known = (sum(looks) >= 2).astype(np.uint8), np.ones(W, bool)
        else: cue, known = looks[0], agree
        kk = max(1, int(known.sum())); idx = np.flatnonzero(valid); grade, ans, band, bi = "UNKNOWN", None, None, -1
        if len(idx) >= 2 and kk >= 8:
            sc = ((pats[idx] == cue) & known).sum(1) / kk; o2 = np.argsort(-sc); best, second = sc[o2[0]], sc[o2[1]]; bi = int(idx[o2[0]])
            ch = chance(kk); thr = max(0.60, 1 - ph - 3 * np.sqrt(max(ph * (1 - ph), 1e-4) / kk), ch)
            if best >= thr and best > second: grade, ans = "EXACT", int(outs[bi])
            elif best >= ch: grade, ans = "CLOSE", int(np.bincount(outs[idx], weights=np.clip(sc - 0.5, 0, None) * (sc >= ch), minlength=O).argmax())
            if grade != "UNKNOWN": band = (grade, int(np.clip((best - ch) / max(1e-9, 1 - ch) * 4, 0, 3))); h, t = cells.get(band, (0, 0))
        accepted = ans is not None and (h + 1) / (t + 2) >= 0.5
        w = win[k // 1000]
        if truth < 0: w["rn"] += 1; w["ra"] += accepted
        else:
            w["n"] += 1; w["ok"] += accepted and ans == truth; w["bad"] += accepted and ans != truth
            if band is not None: cells[band] = (h + (ans == truth), t + 1)
            if bi >= 0 and accepted and ans == truth: last[bi] = k
            if mode != "STATIC":
                need = (not accepted) or ans != truth or (mode == "LEARN_B" and grade == "CLOSE")
                if need: store((sum(looks) >= 2).astype(np.uint8), truth, k); stored_total += 1
        w["size"] = int(valid.sum())
    return [(x["ok"] / max(1, x["n"]), x["bad"] / max(1, x["n"]), x["ra"] / max(1, x["rn"]), x["size"]) for x in win]
if __name__ == "__main__":
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"pool of {P} objects in {F} families, store limit {CAP} (start {START}), p=0.08, {seeds} seeds, windows of 1,000 queries. Cells: correct / wrong (share of pool queries) / random answered / store size at the end of the window")
    for spread in (6, 12):
        for q in (0.8, 0.125):
            print(f"\nspread {spread}, Q={q}\nmode    | " + " | ".join(f"win {i+1}" for i in range(NQ // 1000)))
            for mode in ("STATIC", "LEARN_A", "LEARN_B"):
                rs = [run(s, spread, q, mode) for s in range(seeds)]
                print(f"{mode:<7} | " + " | ".join("%.2f/%.2f/%.2f/%d" % tuple(np.mean([r[i][j] for r in rs]) for j in range(4)) for i in range(NQ // 1000)))
