"""hexn_layer4_v1 (10 Nov 2026): the layer 4 job on the chain of hexn_chain_v1 (window detectors -> count store of each digit's path), on the spoken digits. Alan 23:10 ('apply the layer 4, to see if it can improve or predict the data at all'). Direction doc section 62. Python model only; no RTL.
Layer 4 here has two parts, both built only from the layer 1 margins and the layer 2 counts of hexn_chain_v1 (same halves, same windows, same 300 test recordings):
 (1) PREDICT. After p windows it holds a posterior over the digits (softmax of path score + LAMBDA x summed margins; context 1 store; LAMBDA chosen on the validation part as in hexn_chain_v1) and predicts the class of window p as the class with the largest posterior-weighted probability, sum over digits d of post(d) x P(class | d, position p, previous class). Reference predictors on the same items, all from the same counts: U (most common class at that position), B (bigram, the previous class only, digits summed over), O (the TRUE digit known: an upper bound for what knowing the digit buys), and 'repeat the last class'.
 (2) DECIDE EARLY. Stop at the first p where the layer 4 posterior of the best digit reaches TAU, else decide after the last window; compared with a layer 1 only rule that stops when the gap between the best and second summed margin reaches GAP. Both swept; result = mean windows used and accuracy. Fixed-p accuracy of the detectors is printed for the same mean p.
Prediction is scored on all windows and on 'active' windows (the actual class is not NONE; NONE windows are silence, which a table predicts trivially). Chance 10% (11 symbols).
Usage: python3 tools/hexn_layer4_v1.py DIR [W]"""
import sys, os, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_det_shd_v1 as D, hexn_det_net_v1 as N, hexn_chain_v1 as C

K = D.K; NONE = C.NONE; A = C.A


def softmax(x): x = x - x.max(axis=1, keepdims=True); e = np.exp(x); return e / e.sum(axis=1, keepdims=True)


def main(d, nwin=10):
    Xtr3, ytr, Xte3, yte, new = D.build(d, N.NIN, N.NBINS, N.TOPN); step = N.NBINS // nwin
    r0 = random.Random(0); pick = []
    for c in range(K): pick += r0.sample([i for i in range(len(yte)) if yte[i] == c], 30)
    pick = np.array(pick); ypick = yte[pick]
    rs = np.random.RandomState(1); half = np.zeros(len(ytr), dtype=bool)
    for c in range(K): idx = np.where(ytr == c)[0]; half[rs.permutation(idx)[:len(idx) // 2]] = True
    def win(X, w): return X[:, w * step:(w + 1) * step, :].reshape(len(X), -1).astype(np.int32)
    banks = []
    for w in range(nwin):
        Xa, ya = win(Xtr3[half], w), ytr[half]; Wt = D.train_bank(Xa, ya, len(ya) // K); banks.append((Wt, D.thresholds(Wt, Xa, ya)))
    def margin_of(X): return np.stack([D.margins(banks[w][0], banks[w][1], win(X, w)) for w in range(nwin)], axis=1)
    mB = margin_of(Xtr3[~half]); yB = ytr[~half]; mT = margin_of(Xte3[pick]); cB = C.classes_of(mB); cT = C.classes_of(mT)
    vs = np.random.RandomState(2).rand(len(yB)) < 0.2; lams = (0.0, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0); lam = {}
    cv = C.build_store(cB[~vs], yB[~vs], nwin, 1)
    for p in range(1, nwin + 1):
        ps = C.path_scores(cv, cB[vs], 1, p); ms = mB[vs][:, :p, :].sum(axis=1); lam[p] = max(lams, key=lambda l: np.mean((ps + l * ms).argmax(axis=1) == yB[vs]))
    st = C.build_store(cB, yB, nwin, 1); prob = st / st.sum(axis=-1, keepdims=True)                      # P(class | digit, position, previous class)
    marg = st.sum(axis=0); bigram = marg / marg.sum(axis=-1, keepdims=True); unig = marg.sum(axis=1); unig = unig / unig.sum(axis=-1, keepdims=True)
    post = {}
    for p in range(1, nwin + 1): post[p] = softmax(C.path_scores(st, cT, 1, p) + lam[p] * mT[:, :p, :].sum(axis=1))
    # (1) predict
    print("W=%d windows. (1) PREDICT the class of window p from windows 0..p-1; accuracy %% on all windows | on active windows (actual class not NONE); chance 10%%" % nwin)
    res = {k: ([], []) for k in ("U position only", "R repeat last class", "B bigram, digits summed", "L4 posterior-weighted (layer 4)", "O true digit known (upper bound)")}
    for p in range(1, nwin):
        prev = cT[:, p - 1]; act = cT[:, p]; pred = {"U position only": np.full(len(pick), int(unig[p].argmax())), "R repeat last class": prev, "B bigram, digits summed": bigram[p, prev].argmax(axis=1),
            "L4 posterior-weighted (layer 4)": np.einsum("nd,ndc->nc", post[p], prob[:, p, prev, :].transpose(1, 0, 2)).argmax(axis=1), "O true digit known (upper bound)": prob[ypick, p, prev, :].argmax(axis=1)}
        for k, v in pred.items(): res[k][0].append(v == act); res[k][1].append((v == act)[act != NONE] if (act != NONE).any() else np.array([]))
    print("%-36s %-14s %-14s | active windows by position p = 1..%d" % ("predictor", "all", "active", nwin - 1))
    for k, (a, b) in res.items():
        print("%-36s %-14.1f %-14.1f | %s" % (k, 100 * np.concatenate(a).mean(), 100 * np.concatenate(b).mean(), " ".join("%4.0f" % (100 * x.mean()) if len(x) else "   -" for x in b)))
    # (2) decide early
    print("\n(2) DECIDE EARLY: mean windows used | accuracy %% (all 300 test recordings)")
    def run(rule, thr):
        used = []; ok = []
        for j in range(len(pick)):
            stop = nwin
            for p in range(1, nwin + 1):
                if rule == "tau":
                    if post[p][j].max() >= thr: stop = p; break
                else:
                    s = np.sort(mT[j, :p, :].sum(axis=0));
                    if s[-1] - s[-2] >= thr: stop = p; break
            pr = (post[stop][j].argmax() if rule == "tau" else mT[j, :stop, :].sum(axis=0).argmax()); used.append(stop); ok.append(pr == ypick[j])
        return np.mean(used), 100 * np.mean(ok)
    print("  detectors, fixed p: " + "  ".join("p=%d %.1f" % (p, 100 * np.mean(mT[:, :p, :].sum(axis=1).argmax(axis=1) == ypick)) for p in range(1, nwin + 1)))
    print("  layer 4 posterior >= TAU:  " + "  ".join("%.2f: %.1f|%.1f" % (t, *run("tau", t)) for t in (0.5, 0.7, 0.9, 0.99, 0.999)))
    print("  layer 1 only, margin gap >= GAP: " + "  ".join("%d: %.1f|%.1f" % (g, *run("gap", g)) for g in (100, 200, 300, 500, 800, 1200)))
    print("  LAMBDA by p: %s" % [lam[p] for p in range(1, nwin + 1)])


if __name__ == "__main__":
    main(sys.argv[1], *[int(v) for v in sys.argv[2:]])
