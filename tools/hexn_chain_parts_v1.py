"""hexn_chain_parts_v1 (12 Nov 2026): THE PARTS AS ONE WHOLE, FIRST STEP ON REAL DATA: a shared memory of wholes on top of the speech chain's own per-window outputs. Alan 12 Nov 03:03 to 08:30; direction doc sections 98 and 99.
Python only; the chain is the one on the card (same data build and training as the kit; reference 936 of 1,079 after window 3). Earlier tools untouched.
The PARTS are the 5 time windows of a recording. Per window the chain's detectors give 10 margins (one per digit detector) and a CODE: the detector with the largest margin if it is above 0, else NONE (11 values).
The chain already ties its windows together with count tables (how often code follows code for each digit). Tested here instead: a MEMORY OF WHOLES in the style of sections 80 and 97: every training recording is stored as a
known thing = its 5 codes + its digit (4,011 things). A new recording is identified by the stored things that fit its parts best:
  votes    : windows whose code equals the stored thing's code; the digit with the most best-fitting things wins
  scores   : per window the margin of the detector the stored thing expects there (0 for NONE), summed; the digit of the best things wins (full scores instead of the single best code, as section 80)
  weighted : scores, each window weighted 0 / 1 / 2 by the INPUT CHECK of section 87 (events in the window against the window's normal count in training: at least 3/4, at least 1/2, below)
For each: using windows 1 to 3 (the kit's decision point) and all 5. Ties between digits go to the chain's own answer. References: the chain itself, and the plain sum of margins.
Also: SECOND LOOK between the top two (section 93): when the chain's best and second digits are close, the memory of wholes decides between just those two.
Usage: python3 tools/hexn_chain_parts_v1.py DIR [B]     (B: store only the half of the training recordings the detectors were not fitted on)"""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import numpy as np
import hexn_chain_hw_v1 as M, hexn_det_shd_v1 as D, hexn_det_net_v1 as N


def features(P, X):
    """-> margins (n, nwin, 10), codes (n, nwin) with 10 = NONE, chain prediction after each window (n, nwin), chain scores S (n, nwin, 10), events per window (n, nwin)"""
    n = len(X); nw = P.nwin; mg = np.zeros((n, nw, M.NC), int); cd = np.zeros((n, nw), int); pr = np.zeros((n, nw), int); S = np.zeros((n, nw, M.NC), int); ne = np.zeros((n, nw), int)
    for i in range(n):
        ev = M.events_of(X[i]); res = M.run_recording(P, ev); prev = np.zeros(M.NC, int)
        for w in range(nw):
            ms = np.array(res[w]["msum"]); mg[i, w] = ms - prev; prev = ms; cd[i, w] = res[w]["cls"]; pr[i, w] = res[w]["pred"]; S[i, w] = res[w]["S"]
        for st, ln in ev: ne[i, st // P.steps] += 1
    return mg, cd, pr, S, ne


def pick(fit, ytr, fallback, among=None):
    """fit: (ntrain,) fit of every stored thing -> digit: the digit with the most things at the best fit; ties to fallback"""
    best = fit.max(); cnt = np.bincount(ytr[fit == best], minlength=M.NC)
    if among is not None:
        c2 = np.zeros(M.NC, int); c2[list(among)] = cnt[list(among)]
        if c2.max() == 0:                                  # none of the best things is one of the two: take each one's own best thing
            f = [fit[ytr == d].max() for d in among]; return among[0] if f[0] >= f[1] else among[1]
        cnt = c2
    top = np.flatnonzero(cnt == cnt.max())
    return int(fallback) if fallback in top else int(top[0])


def main(d):
    Xtr3, ytr, Xte3, yte, new = D.build(d, N.NIN, N.NBINS, N.TOPN); P = M.train(Xtr3, ytr, 5, N.NIN, gap=10)
    mtr, ctr, ptr, Str, ntr = features(P, Xtr3); mte, cte, pte, Ste, nte = features(P, Xte3); n = len(yte); normal = ntr.mean(axis=0)
    if len(sys.argv) > 2 and sys.argv[2] == "B":          # store only the half of the training recordings the detectors were NOT fitted on (half B of hexn_chain_hw_v1.train, the half its count tables use)
        rs = np.random.RandomState(1); half = np.zeros(len(ytr), dtype=bool)
        for c in range(M.NC): idx = np.where(ytr == c)[0]; half[rs.permutation(idx)[:len(idx) // 2]] = True
        mtr, ctr, ytr = mtr[~half], ctr[~half], ytr[~half]; print("STORED THINGS: half B only (the recordings the detectors were not fitted on)")
    print("test recordings %d, stored things (training recordings) %d; events per window in training, mean: %s" % (n, len(ytr), " ".join("%.1f" % x for x in normal)))
    print("different code tuples among the stored things: %d (5 windows), %d (3 windows)" % (len({tuple(r) for r in ctr}), len({tuple(r[:3]) for r in ctr})))
    exp = np.concatenate([mtr, np.zeros((len(ytr), P.nwin, 1), int)], axis=2)        # margin table with a 0 column for NONE
    res = {}
    for W in (3, 5):
        ref = pte[:, W - 1]; res[("the chain itself", W)] = ref
        res[("plain sum of margins", W)] = mte[:, :W].sum(axis=1).argmax(axis=1)
        v = np.zeros(n, int); s = np.zeros(n, int); sw = np.zeros(n, int); sl = np.zeros(n, int); nsl = 0; fixed = 0; broke = 0
        for i in range(n):
            fitv = (ctr[:, :W] == cte[i, :W]).sum(axis=1); v[i] = pick(fitv, ytr, ref[i])
            mt = np.concatenate([mte[i], np.zeros((P.nwin, 1), int)], axis=1)        # this recording's margins + 0 for NONE
            per = mt[np.arange(W)[None, :], ctr[:, :W]]                               # (ntrain, W): margin of the detector each stored thing expects
            fits = per.sum(axis=1); s[i] = pick(fits, ytr, ref[i])
            wt = np.where(4 * nte[i, :W] >= 3 * normal[:W], 2, np.where(2 * nte[i, :W] >= normal[:W], 1, 0)); fitw = (per * wt[None, :]).sum(axis=1); sw[i] = pick(fitw, ytr, ref[i])
            o = np.argsort(-Ste[i, W - 1], kind="stable"); sl[i] = ref[i]
            if Ste[i, W - 1][o[0]] - Ste[i, W - 1][o[1]] <= 16:                       # the chain's top two are close: the memory decides between them
                nsl += 1; sl[i] = pick(fits, ytr, ref[i], among=(int(o[0]), int(o[1])))
                fixed += (ref[i] != yte[i] and sl[i] == yte[i]); broke += (ref[i] == yte[i] and sl[i] != yte[i])
        res[("memory of wholes: votes", W)] = v; res[("memory of wholes: scores", W)] = s; res[("memory of wholes: scores, input-weighted", W)] = sw; res[("chain + second look by the memory", W)] = sl
        print("windows 1 to %d: second look used on %d recordings: %d wrong answers put right, %d right answers spoiled" % (W, nsl, fixed, broke))
    print("\n%-44s %-22s %-22s" % ("method", "windows 1 to 3", "all 5 windows"))
    for nm in ("the chain itself", "plain sum of margins", "memory of wholes: votes", "memory of wholes: scores", "memory of wholes: scores, input-weighted", "chain + second look by the memory"):
        print("%-44s %-22s %-22s" % (nm, *["%d right (%.1f%%)" % ((res[(nm, W)] == yte).sum(), 100.0 * (res[(nm, W)] == yte).mean()) for W in (3, 5)]))
    print("\nper digit, right of total (windows 1 to 3): digit: chain / memory scores / chain + second look")
    print("   " + "  ".join("%d: %d / %d / %d of %d" % (c, ((res[("the chain itself", 3)] == yte) & (yte == c)).sum(), ((res[("memory of wholes: scores", 3)] == yte) & (yte == c)).sum(),
                                                       ((res[("chain + second look by the memory", 3)] == yte) & (yte == c)).sum(), (yte == c).sum()) for c in range(M.NC)))
    a = res[("the chain itself", 3)]; b = res[("memory of wholes: scores", 3)]
    print("chain and memory (scores, 3 windows): both right %d, only the chain %d, only the memory %d, both wrong %d" % (((a == yte) & (b == yte)).sum(), ((a == yte) & (b != yte)).sum(), ((a != yte) & (b == yte)).sum(), ((a != yte) & (b != yte)).sum()))


if __name__ == "__main__": main(sys.argv[1])
