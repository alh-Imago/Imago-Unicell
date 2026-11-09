"""hexn_busnet_shd_blocks_v1 (9 Nov 2026): blocks side by side on the spoken digits. Alan 22:22 ('try the neighbouring blocks first, keep them the same depth for each, maybe 3 is enough'). Direction doc section 56. Simulation only.
The 48 lines of the front end (hexn_shd_frontend_v1) are cut into NB bands of 48 / NB lines. Each band feeds its OWN network of 3 layers x 4 buses x 16 cells (same design, training, homeostat and pruning as hexn_busnet_shd_v1 / section 53; its own random wiring and its own teacher cells). Each block makes its own map for a recording; the JOIN adds up, over the blocks, the Jaccard overlap of the block's map (layers 2+3) with each digit's teacher map in that block, and the digit with the largest sum is the answer. In each time step the TOPN busiest lines OF THE BLOCK send an event (so the total events per recording grow with NB). Cells listen to k = min(24, lines in the block) sources while dense.
Reference: the template classifier on the same lines and events. Chance is 10%.
Usage: python3 tools/hexn_busnet_shd_blocks_v1.py DIR NB TOPN_PER_BLOCK SEEDS EPOCHS"""
import random, sys, os, copy, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H
import hexn_shd_frontend_v1 as F, hexn_busnet_shd_v1 as S

NIN = 48; NBINS = 20; CPB = 2; L = 3; NCL = S.NCL


def prepare(d, nb, topn, ntest, seed=0):
    tr, ytr, _ = F.load(d + "/shd_train.h5"); te, yte, ste = F.load(d + "/shd_test.h5"); w = NIN // nb
    mtr = [F.counts(u, t, NIN, NBINS) for u, t in tr]; mte = [F.counts(u, t, NIN, NBINS) for u, t in te]; sc = F.line_mean(tr, NIN, NBINS)
    r = random.Random(seed); pick = []
    for c in range(NCL): pick += r.sample([i for i in range(len(yte)) if yte[i] == c], ntest)
    blocks = []; tplscore = np.zeros((len(pick), NCL))
    for b in range(nb):
        sl = slice(b * w, (b + 1) * w); xtr = [F.select(m[:, sl], topn, 2, sc[sl]) for m in mtr]; xte = [F.select(mte[i][:, sl], topn, 2, sc[sl]) for i in pick]
        byclass = [[F.events(x, CPB) for x, y in zip(xtr, ytr) if y == c] for c in range(NCL)]
        tests = [F.events(x, CPB) for x in xte]; blocks.append((byclass, tests))
        tpl = np.stack([np.mean([x for x, y in zip(xtr, ytr) if y == c], axis=0).ravel() for c in range(NCL)]); tpl /= np.linalg.norm(tpl, axis=1, keepdims=True)
        tplscore += np.stack([tpl @ (x.ravel() / (np.linalg.norm(x) + 1e-9)) for x in xte])
    labels = [int(yte[i]) for i in pick]; new = [j for j, i in enumerate(pick) if ste[i] in (4, 5)]
    ref = 100 * float(np.mean(np.argmax(tplscore, axis=1) == labels))
    return blocks, labels, new, ref, float(np.mean([sum(len(v) for v in bl[1][j].values()) for bl in blocks for j in range(len(labels))])) * nb


def train_block(byclass, tests, w, seed, epochs, ft, epr, K, prune):
    r = random.Random(seed); k = min(24, w)
    net0 = H.make(seed, 0.5, fb_k=8, fb_w=2, k=k, refr=6, th=5, groups=4, per=16, layers=L, nin=w); tg = S.targets(net0, seed, L)
    t1 = S.layer1_targets(net0, byclass, r); S.train(net0, byclass, tg, t1, epochs, epr, r, copy.deepcopy(net0.table)); net = net0
    if prune: net = copy.deepcopy(net0); Q.prune_by(net, {1: K + 4, 2: K, 3: K}, "weight"); S.train(net, byclass, tg, t1, ft, epr, r, copy.deepcopy(net.table))
    sc = np.zeros((len(tests), NCL)); fired = {l: 0.0 for l in range(1, L + 1)}
    for j, ev in enumerate(tests):
        n = T.fresh_run(net, ev); m = B.map_of(n, (2, 3)); sc[j] = [B.jaccard(m, tg[x]) for x in range(NCL)]
        for l in fired: fired[l] += sum(1 for g in n.fires if n.layer_of(g) == l) / len(tests)
    return sc, fired


def main(d, nb=1, topn=4, seeds=3, epochs=40, ft=10, epr=2, ntest=30, K=14):
    blocks, labels, new, ref, evs = prepare(d, nb, topn, ntest); w = NIN // nb; y = np.array(labels)
    print("%d block(s) of %d lines, top %d per step per block -> %.0f events per recording; template %.1f%% (chance 10%%)" % (nb, w, topn, evs, ref), flush=True)
    for prune in (False, True):
        tot = np.zeros((len(labels), NCL)); single = []; fired = {l: 0.0 for l in range(1, L + 1)}; t0 = time.time(); acc_seed = []
        for s in range(1, seeds + 1):
            sj = np.zeros((len(labels), NCL))
            for b, (byclass, tests) in enumerate(blocks):
                sc, f = train_block(byclass, tests, w, 100 * s + b, epochs, ft, 2, K, prune); sj += sc; single.append(100 * float(np.mean(np.argmax(sc, axis=1) == y)))
                for l in f: fired[l] += f[l] / (seeds * nb)
            acc_seed.append((100 * float(np.mean(np.argmax(sj, axis=1) == y)), 100 * float(np.mean(np.argmax(sj, axis=1)[new] == y[new])))); tot += sj
        print("  %-9s joined recall %.1f%% (unheard speakers %.1f%%; per seed %s) | one block alone %.1f%% | cells fired L1/L2/L3 %.1f/%.1f/%.1f | %.0f s" % ("K=%d" % K if prune else "dense", np.mean([a for a, _ in acc_seed]), np.mean([b for _, b in acc_seed]), " ".join("%.0f" % a for a, _ in acc_seed), np.mean(single), fired[1], fired[2], fired[3], time.time() - t0), flush=True)


if __name__ == "__main__":
    a = sys.argv; main(a[1], *[int(v) for v in a[2:]])
