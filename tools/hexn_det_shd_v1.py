"""hexn_det_shd_v1 (9 Nov 2026): the counted detector bank, in its own arithmetic, on the Heidelberg spoken digits. Alan 22:44 ('yes apply the detector, but you may have to widen the detector design to accommodate this kind of data'). Direction doc section 58. Python model only; no RTL, no card.
The detector as modelled in tools/hexn_det_v4_model_v1.py and tools/hexn_ring_v1.py: one detector per class, each lane weight +1 / -1 / 0 by the counted rule (a lane that is on counts up by K-1 in the own class and down by 1 in every other class, saturating at +-31; weight +1 if the count is at least T, -1 if at most -T, T = max(1, min(16, round(S/2))), S = training samples per class); total = PL x (sum of weight x wire) with PL = 10 (wires held for the window), signed, saturating at +-(2^AW - 1); threshold per detector = midpoint of the mean own-class and other-class training totals; the answer is the largest signed margin (total - threshold).
WIDENING: the built detector hears 12 to 20 wires. Here a recording is the folded event matrix of hexn_shd_frontend_v1 (NIN lines x NBINS time steps, at most TOPN lines on per step) laid out as NIN x NBINS wires, so the bank hears hundreds of wires, and the accumulator must be wider (the width needed is printed). BANDS = NB splits the lines into NB bands, each with its own bank (fewer wires per detector), joined by adding the margins.
Reference: nearest template (mean binary template, cosine). Chance 10%. Test = all 1,079 English test recordings and the part of them from the two speakers never in training.
Usage: python3 tools/hexn_det_shd_v1.py DIR"""
import sys, os, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_shd_frontend_v1 as F

PL = 10; CAP = 31; TMAX = 16; K = 10


def train_bank(X, y, S, cap=CAP, tmax=TMAX, order_seed=0):
    nb = X.shape[1]; cnt = np.zeros((K, nb), dtype=np.int32); idx = np.random.RandomState(order_seed).permutation(len(y))
    for i in idx:
        d = np.full(K, -1, dtype=np.int32); d[y[i]] = K - 1
        on = X[i] > 0; cnt[:, on] = np.clip(cnt[:, on] + d[:, None], -cap, cap)
    T = max(1, min(tmax, round(0.5 * S))); return (cnt >= T).astype(np.int32) - (cnt <= -T).astype(np.int32)


def totals(W, X, aw=None):
    t = PL * (X @ W.T)
    if aw: m = (1 << aw) - 1; t = np.clip(t, -m, m)
    return t


def thresholds(W, X, y, aw=None):
    t = totals(W, X, aw); return np.array([round((t[y == k, k].mean() + t[y != k, k].mean()) / 2) for k in range(K)])


def margins(W, thr, X, aw=None): return totals(W, X, aw) - thr


def bank_accuracy(Xtr, ytr, Xte, yte, new, S, aw=None):
    W = train_bank(Xtr, ytr, S); thr = thresholds(W, Xtr, ytr, aw); m = margins(W, thr, Xte, aw); p = m.argmax(axis=1)
    return m, 100 * float(np.mean(p == yte)), 100 * float(np.mean(p[new] == yte[new])), int(np.abs(PL * (Xtr @ W.T)).max()), int((W != 0).sum())


def template(Xtr, ytr, Xte, yte):
    tpl = np.stack([Xtr[ytr == c].mean(axis=0) for c in range(K)]); tpl /= np.linalg.norm(tpl, axis=1, keepdims=True)
    return 100 * float(np.mean((Xte / (np.linalg.norm(Xte, axis=1, keepdims=True) + 1e-9) @ tpl.T).argmax(axis=1) == yte))


def build(d, nin, nbins, topn):
    tr, ytr, _ = F.load(d + "/shd_train.h5"); te, yte, ste = F.load(d + "/shd_test.h5")
    xtr, sc = F.front(tr, nin, nbins, topn, 2, True); xte, _ = F.front(te, nin, nbins, topn, 2, True, scale=sc)
    return np.stack(xtr), ytr, np.stack(xte), yte, np.where((ste == 4) | (ste == 5))[0]      # arrays (N, nbins, nin)


def main(d):
    print("%-26s %-11s | %-6s %-8s %-10s | %s" % ("front end (lines x steps, top)", "bands x wires", "S", "all %", "unheard %", "max |total| (bits needed incl. sign); non-zero lanes; template %"), flush=True)
    for nin, nbins, topn in ((48, 20, 4), (48, 20, 8), (48, 40, 4), (48, 10, 8), (96, 20, 8)):
        Xtr3, ytr, Xte3, yte, new = build(d, nin, nbins, topn); ref = None
        for nbd in (1, 4):
            w = nin // nbd
            for S in (16, 400):
                if S == 16:
                    sel = np.concatenate([np.where(ytr == c)[0][:16] for c in range(K)]); Xa, ya = Xtr3[sel], ytr[sel]
                else: Xa, ya = Xtr3, ytr
                tot = 0; nz = 0; mxt = 0
                for b in range(nbd):
                    Xt = Xa[:, :, b * w:(b + 1) * w].reshape(len(ya), -1).astype(np.int32); Xe = Xte3[:, :, b * w:(b + 1) * w].reshape(len(yte), -1).astype(np.int32)
                    m, a, an, mx, z = bank_accuracy(Xt, ya, Xe, yte, new, S); tot = tot + m; nz += z; mxt = max(mxt, mx)
                p = tot.argmax(axis=1); acc = 100 * float(np.mean(p == yte)); accn = 100 * float(np.mean(p[new] == yte[new]))
                if ref is None: ref = template(Xtr3.reshape(len(ytr), -1), ytr, Xte3.reshape(len(yte), -1), yte)
                print("%-26s %-11s | %-6d %-8.1f %-10.1f | %d (%d bits); %d lanes; %.1f" % ("%d x %d, top %d" % (nin, nbins, topn), "%d x %d" % (nbd, w * nbins), S, acc, accn, mxt, math.ceil(math.log2(mxt + 1)) + 1, nz, ref), flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
