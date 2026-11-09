"""hexn_det_net_v1 (9 Nov 2026): option 2 - short-window detectors as layer 1 of the bus network, on the spoken digits. Alan 22:50. Direction doc section 59. Python model only.
The folded recording (48 lines x 20 time steps, top TOPN per step, hexn_shd_frontend_v1) is cut into W windows of 20/W steps. Each window has its own detector bank (hexn_det_shd_v1: counted rule, 10 detectors, +1/-1/0 lanes, signed margin) listening to that window's 48 x (20/W) wires. The bank is trained with the recording's digit as the label of every window (weak labels, nothing finer is known). A window sends an event for each of its TOP best detectors whose margin is above zero: input line = window x 10 + digit, at the clock of the window (the 40-clock span of the earlier tests). The bus network (3 layers x 4 buses x 16 cells, same training, homeostat and pruning as section 53) then takes W x 10 input lines instead of the 48 raw lines.
No test on its own training data: the detectors are trained on one half of the training recordings, the network on the other half.
Reported on the same 300 test recordings as sections 55 to 57 (30 per digit; 243 from the two unheard speakers): (a) the detector windows summed (margins added over windows = one wide bank); (b) a vote of the windows' winners; (c) the network's recall by teacher maps, combined layers 2+3 and layer 2 alone, dense and pruned to 14 sources per cell; (d) cells fired per layer.
Usage: python3 tools/hexn_det_net_v1.py DIR W TOP [SEEDS EPOCHS]"""
import sys, os, copy, random, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H
import hexn_busnet_shd_v1 as S, hexn_det_shd_v1 as D

NIN = 48; NBINS = 20; TOPN = 8; K = D.K


def window_events(margins, w, nwin, top):
    """margins (K,) of window w -> list of input line ids"""
    order = np.argsort(-margins, kind="stable")[:top]; return [w * K + int(c) for c in order if margins[c] > 0]


def main(d, nwin=5, top=2, seeds=2, epochs=40, ft=10, epr=2, K14=14):
    Xtr3, ytr, Xte3, yte, new = D.build(d, NIN, NBINS, TOPN); step = NBINS // nwin; span = 40 // nwin
    r0 = random.Random(0); pick = []
    for c in range(K): pick += r0.sample([i for i in range(len(yte)) if yte[i] == c], 30)
    pick = np.array(pick); ypick = yte[pick]; is_new = np.isin(pick, new)
    rs = np.random.RandomState(1); half = np.zeros(len(ytr), dtype=bool)
    for c in range(K): idx = np.where(ytr == c)[0]; half[rs.permutation(idx)[:len(idx) // 2]] = True      # True = detector training half
    def win(X, w): return X[:, w * step:(w + 1) * step, :].reshape(len(X), -1).astype(np.int32)
    banks = []
    for w in range(nwin):
        Xa, ya = win(Xtr3[half], w), ytr[half]; Wt = D.train_bank(Xa, ya, len(ya) // K); banks.append((Wt, D.thresholds(Wt, Xa, ya)))
    def margin_of(X): return np.stack([D.margins(banks[w][0], banks[w][1], win(X, w)) for w in range(nwin)], axis=1)      # (N, nwin, K)
    mtr = margin_of(Xtr3[~half]); ynet = ytr[~half]; mte = margin_of(Xte3[pick])
    tot = mte.sum(axis=1); vote = np.array([np.bincount(mte[i].argmax(axis=1), minlength=K).argmax() for i in range(len(pick))])
    a_sum = 100 * np.mean(tot.argmax(axis=1) == ypick); a_vote = 100 * np.mean(vote == ypick)
    def ev_of(m):
        ev = {}
        for w in range(nwin):
            ids = window_events(m[w], w, nwin, top)
            if ids: ev[w * span] = ids
        return ev
    byclass = [[ev_of(m) for m, y in zip(mtr, ynet) if y == c] for c in range(K)]; tests = [(int(y), ev_of(m)) for y, m in zip(ypick, mte)]
    nev = np.mean([sum(len(v) for v in e.values()) for _, e in tests])
    print("W=%d windows of %d steps, top %d per window -> %.1f events per recording on %d lines" % (nwin, step, top, nev, nwin * K))
    print("  detectors alone on the 300 test recordings: windows summed %.1f%% | vote of window winners %.1f%% | chance 10%%" % (a_sum, a_vote), flush=True)
    res = {}; L = 3; nin = nwin * K; t0 = time.time()
    for s in range(1, seeds + 1):
        r = random.Random(s); net0 = H.make(s, 0.5, fb_k=8, fb_w=2, k=min(24, nin), refr=6, th=3, groups=4, per=16, layers=L, nin=nin); tg = S.targets(net0, s, L); tg2 = [{g for g in t if net0.layer_of(g) == 2} for t in tg]
        t1 = S.layer1_targets(net0, byclass, r); S.train(net0, byclass, tg, t1, epochs, epr, r, copy.deepcopy(net0.table))
        for name, kp in (("dense", None), ("K=%d" % K14, K14)):
            net = copy.deepcopy(net0)
            if kp: Q.prune_by(net, {1: kp + 4, 2: kp, 3: kp}, "weight"); S.train(net, byclass, tg, t1, ft, epr, r, copy.deepcopy(net.table))
            a, f, z, dr = S.evaluate(net, tests, tg, tg2, L); x = res.setdefault(name, dict(a=[0, 0], f={l: 0.0 for l in f}, dr=0.0))
            x["a"][0] += a[0] / seeds; x["a"][1] += a[1] / seeds; x["dr"] += dr / seeds
            for l in f: x["f"][l] += f[l] / seeds
    for name, x in res.items(): print("  net block %-6s: recall combined %.1f%%  layer 2 alone %.1f%% | cells fired L1/L2/L3 %.1f/%.1f/%.1f | packets dropped %.1f%%" % (name, x["a"][0], x["a"][1], x["f"][1], x["f"][2], x["f"][3], x["dr"]))
    print("  %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    a = sys.argv; main(a[1], *[int(v) for v in a[2:]])
