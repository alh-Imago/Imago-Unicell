"""hexn_det_net_seq_v1 (9 Nov 2026): the sequence test. Alan 22:59 ('try the sequence test first, though this is leaning back toward the earlier model of the 4 layers, with layer 4 doing the predictive work'). Direction doc section 60. Python model only.
Same window detectors as hexn_det_net_v1 (W windows, 10 counted detectors per window, trained on one half of the training recordings; events = the TOP best detectors of each window with a margin above zero). Task: after the first p windows (p = 1 .. W-1), PREDICT THE WINNING DIGIT OF WINDOW p (the detector with the largest margin there, whether or not it is above zero). The net sees only the events of windows 0 .. p-1.
 - Bus network: the teacher map of class k is used for 'the next winner is k' (5 cells per layer, section 55); trained on prefixes of the other half of the training recordings; the prediction = the digit whose teacher map overlaps the network's map most (Jaccard, layers 2+3).
 - Reference predictors on exactly the same test items, built from counts on the same training half, as a layer 2 history store would: (U) the most common winner of window p, ignoring history; (R) repeat the last window's winner; (B) bigram: the most common next winner given (p, last winner); (T) trigram: given (p, last two winners); chance 10%.
Test items: the same 300 test recordings as sections 55 to 59, every prefix length -> (W-1) x 300 items.
Usage: python3 tools/hexn_det_net_seq_v1.py DIR W TOP [SEEDS EPOCHS]"""
import sys, os, copy, random, time
import numpy as np
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H
import hexn_busnet_shd_v1 as S, hexn_det_shd_v1 as D, hexn_det_net_v1 as N

K = D.K


def top_table(counts, key, fallback):
    c = counts.get(key); return c.most_common(1)[0][0] if c else fallback


def main(d, nwin=5, top=2, seeds=2, epochs=40, ft=10, epr=2, K14=14):
    Xtr3, ytr, Xte3, yte, new = D.build(d, N.NIN, N.NBINS, N.TOPN); step = N.NBINS // nwin; span = 40 // nwin
    r0 = random.Random(0); pick = []
    for c in range(K): pick += r0.sample([i for i in range(len(yte)) if yte[i] == c], 30)
    pick = np.array(pick)
    rs = np.random.RandomState(1); half = np.zeros(len(ytr), dtype=bool)
    for c in range(K): idx = np.where(ytr == c)[0]; half[rs.permutation(idx)[:len(idx) // 2]] = True
    def win(X, w): return X[:, w * step:(w + 1) * step, :].reshape(len(X), -1).astype(np.int32)
    banks = []
    for w in range(nwin):
        Xa, ya = win(Xtr3[half], w), ytr[half]; Wt = D.train_bank(Xa, ya, len(ya) // K); banks.append((Wt, D.thresholds(Wt, Xa, ya)))
    def margin_of(X): return np.stack([D.margins(banks[w][0], banks[w][1], win(X, w)) for w in range(nwin)], axis=1)
    mtr = margin_of(Xtr3[~half]); mte = margin_of(Xte3[pick]); wtr = mtr.argmax(axis=2); wte = mte.argmax(axis=2)        # winners (N, nwin)
    def prefix_ev(m, p):
        ev = {}
        for w in range(p):
            ids = N.window_events(m[w], w, nwin, top)
            if ids: ev[w * span] = ids
        return ev
    # reference predictors, counts from the network's training half
    uni = {}; bi = {}; tri = {}
    for i in range(len(wtr)):
        for p in range(1, nwin):
            uni.setdefault(p, Counter())[wtr[i, p]] += 1; bi.setdefault((p, wtr[i, p - 1]), Counter())[wtr[i, p]] += 1
            if p >= 2: tri.setdefault((p, wtr[i, p - 1], wtr[i, p - 2]), Counter())[wtr[i, p]] += 1
    items = [(i, p) for i in range(len(pick)) for p in range(1, nwin)]; truth = np.array([wte[i, p] for i, p in items]); pp = np.array([p for _, p in items])
    pred_u = np.array([top_table(uni, p, 0) for _, p in items]); pred_r = np.array([wte[i, p - 1] for i, p in items])
    pred_b = np.array([top_table(bi, (p, wte[i, p - 1]), int(wte[i, p - 1])) for i, p in items])
    pred_t = np.array([top_table(tri, (p, wte[i, p - 1], wte[i, p - 2]), top_table(bi, (p, wte[i, p - 1]), int(wte[i, p - 1]))) if p >= 2 else top_table(bi, (p, wte[i, p - 1]), int(wte[i, p - 1])) for i, p in items])
    def acc(pred, mask=None): m = np.ones(len(truth), dtype=bool) if mask is None else mask; return 100 * float(np.mean(pred[m] == truth[m]))
    print("W=%d windows, top %d events per window; predict the winner of window p from windows 0..p-1; %d test items" % (nwin, top, len(items)))
    print("  reference predictors (all prefixes; by p=%s): " % ",".join(str(p) for p in range(1, nwin)))
    for name, pr in (("U unigram by position", pred_u), ("R repeat last winner", pred_r), ("B bigram (p, last)", pred_b), ("T trigram (p, last two)", pred_t)):
        print("    %-24s %5.1f%%  | %s" % (name, acc(pr), " ".join("%5.1f" % acc(pr, pp == p) for p in range(1, nwin))))
    byclass = [[] for _ in range(K)]
    for i in range(len(wtr)):
        for p in range(1, nwin): byclass[wtr[i, p]].append(prefix_ev(mtr[i], p))
    print("  net training prefixes per target digit: min %d max %d" % (min(len(b) for b in byclass), max(len(b) for b in byclass)), flush=True)
    tests = [(int(wte[i, p]), prefix_ev(mte[i], p)) for i, p in items]; res = {}; L = 3; nin = nwin * K
    for s in range(1, seeds + 1):
        r = random.Random(s); net0 = H.make(s, 0.5, fb_k=8, fb_w=2, k=min(24, nin), refr=6, th=3, groups=4, per=16, layers=L, nin=nin); tg = S.targets(net0, s, L)
        t1 = S.layer1_targets(net0, byclass, r); S.train(net0, byclass, tg, t1, epochs, epr, r, copy.deepcopy(net0.table))
        for name, kp in (("dense", None), ("K=%d" % K14, K14)):
            net = copy.deepcopy(net0)
            if kp: Q.prune_by(net, {1: kp + 4, 2: kp, 3: kp}, "weight"); S.train(net, byclass, tg, t1, ft, epr, r, copy.deepcopy(net.table))
            pred = []
            for k, ev in tests:
                n = T.fresh_run(net, ev); m = B.map_of(n, (2, 3)); pred.append(max(range(K), key=lambda x: (B.jaccard(m, tg[x]), -x)))
            pred = np.array(pred); x = res.setdefault(name, [0.0, np.zeros(nwin - 1)]); x[0] += acc(pred) / seeds
            for p in range(1, nwin): x[1][p - 1] += acc(pred, pp == p) / seeds
    for name, (a, per) in res.items(): print("  bus network %-6s %5.1f%%  | %s" % (name, a, " ".join("%5.1f" % v for v in per)))


if __name__ == "__main__":
    a = sys.argv; main(a[1], *[int(v) for v in a[2:]])
