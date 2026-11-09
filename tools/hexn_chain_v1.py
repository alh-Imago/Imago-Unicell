"""hexn_chain_v1 (10 Nov 2026): the chain layer 1 (window detectors) -> layer 2 (count store of each digit's window path) -> layer 4 style decision, on the spoken digits. Alan 23:04 ('use option 1; the neural net side is a wrong model for a detector system'). Direction doc section 61. Python model only; no RTL.
Layer 1: W windows (20 steps / W each) of the folded recording, one bank of 10 counted detectors per window (hexn_det_shd_v1; trained on training half A). A window's class is the detector with the largest signed margin, or NONE (symbol 10) when no margin is above zero, as the built layer 1 reports a class or NONE. Its margins are also kept.
Layer 2 (counts only, as the store of the earlier layers): for every digit d, position i and previous class c, the number of times each class followed, counted on training half B (labels = the digit). Add-one smoothing over the 11 symbols. Context 0 = class per position given the digit; context 1 = class given the digit, position and previous class. A digit's path score for the windows heard so far is the sum of log probabilities.
Layer 4 style decision: after hearing p windows, the digit with the best score. Three deciders: (D) layer 1 alone = sum of the margins of the windows heard; (P) the path score alone; (C) path score + LAMBDA x margin sum, LAMBDA chosen on a validation part of half B (the store built on the rest), never on the test set.
Reported on the same 300 test recordings (30 per digit; 243 from the two speakers never in training), accuracy % after p = 1 .. W windows, plus store size (non-zero count cells). Chance 10%.
Usage: python3 tools/hexn_chain_v1.py DIR [W]"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_det_shd_v1 as D, hexn_det_net_v1 as N

K = D.K; NONE = K; A = K + 1


def classes_of(m): return np.where(m.max(axis=2) > 0, m.argmax(axis=2), NONE)           # (N, W)


def build_store(cls, y, nwin, ctx):
    if ctx == 0:
        c = np.ones((K, nwin, A))
        for s, d in zip(cls, y):
            for i in range(nwin): c[d, i, s[i]] += 1
    else:
        c = np.ones((K, nwin, A, A))                                                      # [digit, position, previous class, class]
        for s, d in zip(cls, y):
            for i in range(nwin): c[d, i, s[i - 1] if i else NONE, s[i]] += 1
    return c


def path_scores(c, cls, ctx, p):
    """log-likelihood of the first p classes under each digit -> (N, K)"""
    n = len(cls); out = np.zeros((n, K)); logp = np.log(c / c.sum(axis=-1, keepdims=True))
    for j in range(n):
        for i in range(p):
            out[j] += logp[:, i, cls[j, i]] if ctx == 0 else logp[:, i, cls[j, i - 1] if i else NONE, cls[j, i]]
    return out


def main(d, nwin=5):
    Xtr3, ytr, Xte3, yte, new = D.build(d, N.NIN, N.NBINS, N.TOPN); step = N.NBINS // nwin
    import random
    r0 = random.Random(0); pick = []
    for c in range(K): pick += r0.sample([i for i in range(len(yte)) if yte[i] == c], 30)
    pick = np.array(pick); ypick = yte[pick]; is_new = np.isin(pick, new)
    rs = np.random.RandomState(1); half = np.zeros(len(ytr), dtype=bool)
    for c in range(K): idx = np.where(ytr == c)[0]; half[rs.permutation(idx)[:len(idx) // 2]] = True
    def win(X, w): return X[:, w * step:(w + 1) * step, :].reshape(len(X), -1).astype(np.int32)
    banks = []
    for w in range(nwin):
        Xa, ya = win(Xtr3[half], w), ytr[half]; Wt = D.train_bank(Xa, ya, len(ya) // K); banks.append((Wt, D.thresholds(Wt, Xa, ya)))
    def margin_of(X): return np.stack([D.margins(banks[w][0], banks[w][1], win(X, w)) for w in range(nwin)], axis=1)
    mB = margin_of(Xtr3[~half]); yB = ytr[~half]; mT = margin_of(Xte3[pick]); cB = classes_of(mB); cT = classes_of(mT)
    # validation split of half B for LAMBDA
    vs = np.random.RandomState(2).rand(len(yB)) < 0.2
    lams = (0.0, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0); best = {}
    for ctx in (0, 1):
        cv = build_store(cB[~vs], yB[~vs], nwin, ctx)
        for p in range(1, nwin + 1):
            ps = path_scores(cv, cB[vs], ctx, p); ms = mB[vs][:, :p, :].sum(axis=1)
            best[(ctx, p)] = max(lams, key=lambda l: np.mean((ps + l * ms).argmax(axis=1) == yB[vs]))
    print("W=%d windows; accuracy %% after hearing p windows (all 300 test recordings | the 243 from unheard speakers); chance 10%%" % nwin)
    print("%-34s %s" % ("decider", "  ".join("p=%d          " % p for p in range(1, nwin + 1))))
    rows = {}
    for p in range(1, nwin + 1):
        ms = mT[:, :p, :].sum(axis=1); rows.setdefault("D  detectors alone (summed margins)", []).append(ms.argmax(axis=1))
    for ctx in (0, 1):
        c = build_store(cB, yB, nwin, ctx)
        for p in range(1, nwin + 1):
            ps = path_scores(c, cT, ctx, p); ms = mT[:, :p, :].sum(axis=1)
            rows.setdefault("P%d path store alone (context %d)" % (ctx, ctx), []).append(ps.argmax(axis=1)); rows.setdefault("C%d store + detectors (context %d)" % (ctx, ctx), []).append((ps + best[(ctx, p)] * ms).argmax(axis=1))
        print("  context %d store: %d of %d count cells above the add-one floor; lambda chosen on validation by p: %s" % (ctx, int((c > 1).sum()), c.size, [best[(ctx, p)] for p in range(1, nwin + 1)]))
    for name, preds in sorted(rows.items()):
        print("%-34s %s" % (name, "  ".join("%5.1f | %5.1f " % (100 * np.mean(pr == ypick), 100 * np.mean(pr[is_new] == ypick[is_new])) for pr in preds)))


if __name__ == "__main__":
    main(sys.argv[1], *[int(v) for v in sys.argv[2:]])
