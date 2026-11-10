"""hexn_net_novelty_v1 (10 Nov 2026): two jobs for the bus network that are about MATCHING, not signal processing. Alan 00:05 ('the neural net side is more of a pattern search matching system'). Direction doc section 66. Simulation only.
Same network, training and pruned working point (K=14, 1 seed) as hexn_busnet_shd_v1.py (untouched; its prepare() and training calls are reused). Test recordings are the 300 English test recordings (30 per digit, same pick as before) and 300 German recordings (labels 10 to 19, never shown to anything).
 A. NOVELTY: score each recording by how well it matches what was taught, and measure how well that score separates English from German (area under the ROC curve; 0.5 = no better than chance, 1.0 = perfect).
    net score = largest Jaccard overlap of the recording's map with a taught class map; detector score = largest summed margin over the 5 window banks of hexn_chain_hw_v1 (banks trained on half A of the training set);
    template score = largest normalised overlap with a class template. Higher = more familiar.
 B. DAMAGE: delete a fraction of the events of every English test recording at random and report recall (correct class) for the net (map overlap), the detector banks (largest summed margin) and the template.
Usage: python3 tools/hexn_net_novelty_v1.py DIR [EPOCHS FT]"""
import sys, os, random, copy, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_shd_v1 as S, hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H
import hexn_shd_frontend_v1 as F, hexn_det_shd_v1 as D

NIN, NBINS, CPB, TOPN, NWIN, NCL = 48, 20, 2, 8, 5, 10


def auroc(pos, neg):
    pos = np.asarray(pos); neg = np.asarray(neg); a = 0.0
    for p in pos: a += (neg < p).sum() + 0.5 * (neg == p).sum()
    return a / (len(pos) * len(neg))


def main(d, epochs=30, ft=10):
    tr, ytr, _ = F.load(d + "/shd_train.h5"); te, yte, _ = F.load(d + "/shd_test.h5"); ge, yge, _ = F.load(d + "/shd_test.h5", classes=range(10, 20))
    xtr, sc = F.front(tr, NIN, NBINS, TOPN, 2, True); xte, _ = F.front(te, NIN, NBINS, TOPN, 2, True, scale=sc); xge, _ = F.front(ge, NIN, NBINS, TOPN, 2, True, scale=sc)
    xtr = np.stack(xtr); xte = np.stack(xte); xge = np.stack(xge); print("train %d, English test %d, German test %d" % (len(xtr), len(xte), len(xge)), flush=True)
    r0 = random.Random(0); pick = []
    for c in range(NCL): pick += r0.sample([i for i in range(len(yte)) if yte[i] == c], 30)
    gpick = random.Random(5).sample(range(len(xge)), 300); XE = xte[pick]; yE = yte[pick]; XG = xge[gpick]
    # detector banks, half A of the training set, 5 windows of 4 steps (as hexn_chain_hw_v1)
    rs = np.random.RandomState(1); half = np.zeros(len(ytr), dtype=bool)
    for c in range(NCL): idx = np.where(ytr == c)[0]; half[rs.permutation(idx)[:len(idx) // 2]] = True
    st = NBINS // NWIN
    def win(X, w): return X[:, w * st:(w + 1) * st, :].reshape(len(X), -1).astype(np.int32)
    banks = []
    for w in range(NWIN):
        Xa, ya = win(xtr[half], w), ytr[half]; Wt = D.train_bank(Xa, ya, len(ya) // NCL); banks.append((Wt, D.thresholds(Wt, Xa, ya)))
    def det_sums(X): return sum(D.margins(banks[w][0], banks[w][1], win(X, w)) for w in range(NWIN))          # (N, 10)
    tpl = np.stack([xtr[ytr == c].reshape((ytr == c).sum(), -1).mean(axis=0) for c in range(NCL)]); tpl /= np.linalg.norm(tpl, axis=1, keepdims=True)
    def tpl_sc(X): Z = X.reshape(len(X), -1); return (Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9)) @ tpl.T
    # the network
    byclass, _t, _a, _b, _c, _e = S.prepare(d, NIN, NBINS, CPB, TOPN, 1)
    s = 1; L = 3; K = 14; r = random.Random(s); net0 = H.make(s, 0.5, fb_k=8, fb_w=2, k=24, refr=6, th=5, groups=4, per=16, layers=L, nin=NIN)
    tg = S.targets(net0, s, L); tg2 = [{g for g in t if net0.layer_of(g) == 2} for t in tg]; t1 = S.layer1_targets(net0, byclass, r); w0 = copy.deepcopy(net0.table); t0 = time.time()
    S.train(net0, byclass, tg, t1, epochs, 2, r, w0); print("dense net trained, %.0f s" % (time.time() - t0), flush=True)
    net = copy.deepcopy(net0); Q.prune_by(net, dict([(1, K + 4)] + [(l, K) for l in range(2, L + 1)]), "weight"); S.train(net, byclass, tg, t1, ft, 2, r, copy.deepcopy(net.table)); print("pruned and retrained, %.0f s" % (time.time() - t0), flush=True)
    def net_scores(X):
        out = []
        for x in X:
            n = T.fresh_run(net, F.events(x, CPB)); m = B.map_of(n, tuple(range(2, L + 1))); out.append([B.jaccard(m, tg[k]) for k in range(NCL)])
        return np.array(out)
    # A. novelty
    sE = dict(net=net_scores(XE).max(axis=1), det=det_sums(XE).max(axis=1), tpl=tpl_sc(XE).max(axis=1)); sG = dict(net=net_scores(XG).max(axis=1), det=det_sums(XG).max(axis=1), tpl=tpl_sc(XG).max(axis=1))
    print("\nA. NOVELTY: English (known) vs German (never seen), 300 each; area under ROC (0.5 chance, 1.0 perfect)")
    for k, nm in (("net", "bus network, best map overlap"), ("det", "detector banks, best summed margin"), ("tpl", "template, best overlap")):
        print("  %-38s %.3f   (mean score English %.3f, German %.3f)" % (nm, auroc(sE[k], sG[k]), sE[k].mean(), sG[k].mean()))
    # B. damage
    print("\nB. DAMAGE: recall %% on the 300 English test recordings after deleting a fraction of the events at random (chance 10%)")
    print("  %-10s %-10s %-10s %-10s" % ("deleted", "network", "detectors", "template"))
    for f in (0.0, 0.3, 0.5, 0.7, 0.85):
        rr = np.random.RandomState(int(f * 100) + 1); Xd = XE * (rr.rand(*XE.shape) >= f)
        print("  %-10s %-10.1f %-10.1f %-10.1f" % ("%d%%" % round(100 * f), 100 * np.mean(net_scores(Xd).argmax(axis=1) == yE), 100 * np.mean(det_sums(Xd).argmax(axis=1) == yE), 100 * np.mean(tpl_sc(Xd).argmax(axis=1) == yE)), flush=True)


if __name__ == "__main__":
    a = sys.argv; main(a[1], *[int(v) for v in a[2:]])
