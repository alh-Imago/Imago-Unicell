"""hexn_chain_multi_v1 (12 Nov 2026): SEVERAL TEMPLATES PER DIGIT AND WINDOW in the speech chain. Alan 08:30 / 08:37 (yes: the lower layers in their current state have reached their limit). Direction doc section 100.
Python only. Same data build as the kit. The chain's own method, written again here in a general form so the number of detectors can change (K = 1 must reproduce the kit's 936 of 1,079: checked at the start of every run):
  per window a bank of ternary templates trained by counting (as hexn_det_shd_v1.train_bank), a threshold per template, count tables over the window codes, shift code per window chosen on a validation part, decision
  score = table path + shifted sum of margins (as hexn_chain_hw_v1).
NEW: K templates per digit and window instead of 1. The recordings of a digit are split into K groups by how that window looks (k-means on the window's line-and-step pattern, half A, fixed seed), and each group gets its own
template ('one' said in K different ways). A digit's margin in a window = the largest margin among its K templates. Two ways to form the window code that goes into the count tables:
  digit code : the digit of the best template (11 values with NONE), tables as today
  group code : the best template itself (10 K + 1 values): the tables also see WHICH way the digit was said
Reported: test set after window 3 and after window 5, the training set (all 4,011, as section 93), and 'one' and 'three' on the test set.
Usage: python3 tools/hexn_chain_multi_v1.py DIR"""
import sys, os, math
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import numpy as np
import hexn_det_shd_v1 as D, hexn_det_net_v1 as N
NC = 10; NWIN = 5


def kmeans(X, k, seed):
    rs = np.random.RandomState(seed); c = X[rs.choice(len(X), k, replace=False)].astype(float); lab = np.zeros(len(X), int)
    for _ in range(20):
        d = ((X[:, None, :] - c[None, :, :]) ** 2).sum(axis=2); new = d.argmin(axis=1)
        if (new == lab).all() and _ > 0: break
        lab = new
        for j in range(k):
            if (lab == j).any(): c[j] = X[lab == j].mean(axis=0)
    return lab


def train_bank(X, y, ncls, S, cap=D.CAP, tmax=D.TMAX, order_seed=0):
    """hexn_det_shd_v1.train_bank for any number of classes"""
    cnt = np.zeros((ncls, X.shape[1]), dtype=np.int32); idx = np.random.RandomState(order_seed).permutation(len(y))
    for i in idx:
        d = np.full(ncls, -1, dtype=np.int32); d[y[i]] = ncls - 1
        on = X[i] > 0; cnt[:, on] = np.clip(cnt[:, on] + d[:, None], -cap, cap)
    T = max(1, min(tmax, round(0.5 * S))); return (cnt >= T).astype(np.int32) - (cnt <= -T).astype(np.int32)


def shift(v, code): return np.zeros_like(v) if code == 0 else (v >> 1) if code == 1 else (v << (code - 2))


def run(Xtr3, ytr, Xte3, yte, K, group_code):
    steps = Xtr3.shape[1] // NWIN; win = lambda X, w: X[:, w * steps:(w + 1) * steps, :].reshape(len(X), -1).astype(np.int32)
    rs = np.random.RandomState(1); half = np.zeros(len(ytr), dtype=bool)
    for c in range(NC): idx = np.where(ytr == c)[0]; half[rs.permutation(idx)[:len(idx) // 2]] = True
    banks = []
    for w in range(NWIN):
        Xa, ya = win(Xtr3[half], w), ytr[half]; sub = np.zeros(len(ya), int)
        if K > 1:
            for c in range(NC): m = ya == c; sub[m] = kmeans(Xa[m], K, 100 + 10 * w + c)
        ys = ya * K + sub; Wt = train_bank(Xa, ys, NC * K, len(ya) // NC if K == 1 else len(ya) // (NC * K)); net = Xa @ Wt.T
        thr = np.array([int(math.floor((net[ys == j, j].mean() + net[ys != j, j].mean()) / 2 + 0.5)) if (ys == j).any() else 10 ** 6 for j in range(NC * K)]); banks.append((Wt, thr))
    def feats(X):
        mg = np.zeros((len(X), NWIN, NC), int); cd = np.zeros((len(X), NWIN), int)
        for w in range(NWIN):
            Wt, thr = banks[w]; m = win(X, w) @ Wt.T - thr[None, :]; md = m.reshape(len(X), NC, K); mg[:, w] = md.max(axis=2)
            if group_code: b = m.argmax(axis=1); cd[:, w] = np.where(m[np.arange(len(X)), b] > 0, b, NC * K)
            else: b = mg[:, w].argmax(axis=1); cd[:, w] = np.where(mg[np.arange(len(X)), w, b] > 0, b, NC)
        return mg, cd
    A = (NC * K if group_code else NC) + 1; NONE = A - 1
    def store(cd, y):
        c = np.ones((NC, NWIN, A, A))
        for s, d in zip(cd, y):
            for i in range(NWIN): c[d, i, s[i - 1] if i else NONE, s[i]] += 1
        return np.clip(np.round(16 * np.log(c / c.sum(axis=-1, keepdims=True))), -127, 0).astype(int)
    def decide(mg, cd, lp, codes, upto):
        n = len(mg); path = np.zeros((n, NC), int); ms = np.zeros((n, NC), int); out = []
        for w in range(upto):
            prev = cd[:, w - 1] if w else np.full(n, NONE); path = path + lp[:, w, prev, cd[:, w]].T; ms = ms + mg[:, w]
            out.append((path + shift(ms, codes[w])).argmax(axis=1))
        return out
    mB, cB = feats(Xtr3[~half]); yB = ytr[~half]; vs = np.random.RandomState(2).rand(len(yB)) < 0.2
    lp = store(cB, yB); lpv = store(cB[~vs], yB[~vs]); codes = [0] * NWIN
    for w in range(NWIN):
        bestc = (-1.0, 0)
        for code in range(11):
            codes[w] = code; acc = (decide(mB[vs], cB[vs], lpv, codes, w + 1)[w] == yB[vs]).mean()
            if acc > bestc[0] + 1e-9: bestc = (acc, code)
        codes[w] = bestc[1]
    mT, cT = feats(Xte3); pT = decide(mT, cT, lp, codes, NWIN); mA, cA = feats(Xtr3); pA = decide(mA, cA, lp, codes, NWIN)
    return dict(t3=(pT[2] == yte).sum(), t5=(pT[4] == yte).sum(), tr3=(pA[2] == ytr).sum(), one=((pT[2] == yte) & (yte == 1)).sum(), three=((pT[2] == yte) & (yte == 3)).sum(),
                none=(cT[:, :3] == NONE).mean(), b3=(decide(mB, cB, lp, codes, 3)[2] == yB).sum(), nb=len(yB))


def main(d):
    Xtr3, ytr, Xte3, yte, new = D.build(d, N.NIN, N.NBINS, N.TOPN); n = len(yte)
    r = run(Xtr3, ytr, Xte3, yte, 1, False)
    print("check: K = 1 written again here gives %d of %d after window 3 (the kit's chain: 936)%s" % (r["t3"], n, "" if r["t3"] == 936 else "   <-- DIFFERENT: the figures below are not comparable with the card"))
    print("\n%-28s | %-15s | %-15s | %-22s | %-10s | %-10s | %s" % ("templates per digit, code", "test, window 3", "test, window 5", "training set, window 3", "'one'/108", "'three'/102", "windows with code NONE (test, 1 to 3)"))
    for K in (1, 2, 3, 4, 6):
        for gc in ((False,) if K == 1 else (False, True)):
            r = run(Xtr3, ytr, Xte3, yte, K, gc)
            print("%-28s | %4d (%.1f%%)    | %4d (%.1f%%)    | %4d of %d (%.1f%%)   | %-10d | %-10d | %.1f%%" % ("%d, %s code" % (K, "group" if gc else "digit"), r["t3"], 100.0 * r["t3"] / n, r["t5"], 100.0 * r["t5"] / n,
                  r["tr3"], len(ytr), 100.0 * r["tr3"] / len(ytr), r["one"], r["three"], 100 * r["none"]), flush=True)


if __name__ == "__main__": main(sys.argv[1])
