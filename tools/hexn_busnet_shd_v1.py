"""hexn_busnet_shd_v1 (9 Nov 2026): the bus network on real data, the Heidelberg spoken digits (SHD). Alan 22:07 / 22:11. Direction doc section 55. Simulation only; every number is a property of this toy.
Same network, training rule, homeostat and pruning as sections 37 to 53 (hexn_busnet_v1 / _homeo_v1 / _prune_v1 / _prune2_v1, all untouched); what changes is the INPUT and the TEACHER:
 - Input: hexn_shd_frontend_v1 folds a recording to NIN lines, NBINS time steps of CPB clocks, the TOPN busiest lines per step send one event each.
 - Classes: the 10 English digits. Teacher map of class k = 5 cells in each of layers 2..L, disjoint between classes (50 of 64 cells per layer). Layer 1 target of class k = the layer 1 cells that fire for at least half of 6 training recordings of that class on the starting net.
 - Training: each epoch shows EPR random TRAINING recordings of every class (speakers 0-3, 6-11), with the homeostat after each epoch (rates measured on training recordings).
 - Test: TEST recordings per class drawn from the test file, which also holds speakers 4 and 5 that the network has never heard. A recording is recalled as the class whose teacher map has the largest Jaccard overlap with the map the recording makes (combined layers 2+3, and layer 2 alone).
 - Reference: the template classifier of the front end on the SAME test recordings, and chance (10%).
Dense start (24 sources per cell + 8 feedback links), trained EPOCHS epochs, then pruned by weight to K sources per cell (layer 1: K + 4) and retrained FT epochs; K = 14 is the working point of section 53.
Usage: python3 tools/hexn_busnet_shd_v1.py DIR [NIN NBINS CPB TOPN SEEDS EPOCHS]"""
import random, sys, os, copy, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H
import hexn_shd_frontend_v1 as F

NCL = 10; PERL = 5


def targets(net, seed, L):
    r = random.Random(900 + seed); out = [set() for _ in range(NCL)]
    for l in range(2, L + 1):
        ids = [net.gid(l, i) for i in range(net.groups * net.per)]; r.shuffle(ids)
        for k in range(NCL): out[k] |= set(ids[k * PERL:(k + 1) * PERL])
    return out


def layer1_targets(net, byclass, r):
    out = []
    for k in range(NCL):
        cnt = {}
        for ev in r.sample(byclass[k], 6):
            for g in T.fresh_run(net, ev).fires:
                if net.layer_of(g) == 1: cnt[g] = cnt.get(g, 0) + 1
        out.append({g for g, c in cnt.items() if c >= 3})
    return out


def rates(net, byclass, r, nrun=2):
    cnt = {g: 0 for g in net.table}; tot = 0
    for k in range(NCL):
        for ev in r.sample(byclass[k], nrun):
            for g in T.fresh_run(net, ev).fires: cnt[g] += 1
            tot += 1
    return {g: c / tot for g, c in cnt.items()}


def homeostat(net, byclass, r):
    for g, x in rates(net, byclass, r).items():
        tgt = H.TARGET[net.layer_of(g)]
        if x > 1.5 * tgt + 0.02 and net.th_cell[g] < H.TH_MAX: net.th_cell[g] += 1
        elif x < 0.5 * tgt and net.th_cell[g] > H.TH_MIN: net.th_cell[g] -= 1


def train(net, byclass, tg2, tg1, epochs, epr, r, w0, ceil=6):
    for e in range(epochs):
        for k in range(NCL):
            for ev in r.sample(byclass[k], epr):
                n = T.fresh_run(net, ev); P.step_all(n, w0, ev, tg2[k] | tg1[k], ceil=ceil)
                for g in net.table: net.table[g] = n.table[g]
        homeostat(net, byclass, r)


def evaluate(net, tests, tg, tg2, L):
    ok = [0, 0]; tot = 0; fired = {l: 0.0 for l in range(1, L + 1)}; silent = {l: 0 for l in range(1, L + 1)}; pushed = dropped = 0; layers = tuple(range(2, L + 1))
    for k, ev in tests:
        n = T.fresh_run(net, ev); m = B.map_of(n, layers); m2 = B.map_of(n, (2,)); tot += 1; pushed += n.pushed; dropped += n.dropped
        ok[0] += (max(range(NCL), key=lambda x: (B.jaccard(m, tg[x]), -x)) == k); ok[1] += (max(range(NCL), key=lambda x: (B.jaccard(m2, tg2[x]), -x)) == k)
        for l in fired:
            c = sum(1 for g in n.fires if n.layer_of(g) == l); fired[l] += c; silent[l] += (c == 0)
    return [100 * o / tot for o in ok], {l: fired[l] / tot for l in fired}, {l: 100 * silent[l] / tot for l in silent}, 100 * dropped / max(1, pushed + dropped)


def prepare(d, nin, nbins, cpb, topn, ntest, seed=0):
    tr, ytr, _ = F.load(d + "/shd_train.h5"); te, yte, ste = F.load(d + "/shd_test.h5")
    xtr, sc = F.front(tr, nin, nbins, topn, 2, True); xte, _ = F.front(te, nin, nbins, topn, 2, True, scale=sc)
    tpl = np.stack([np.mean([x for x, y in zip(xtr, ytr) if y == c], axis=0).ravel() for c in range(NCL)]); tpl /= np.linalg.norm(tpl, axis=1, keepdims=True)
    byclass = [[F.events(x, cpb) for x, y in zip(xtr, ytr) if y == c] for c in range(NCL)]
    r = random.Random(seed); pick = []
    for c in range(NCL): pick += r.sample([i for i in range(len(yte)) if yte[i] == c], ntest)
    tests = [(int(yte[i]), F.events(xte[i], cpb)) for i in pick]
    ref = 100 * float(np.mean([int(np.argmax(tpl @ (xte[i].ravel() / (np.linalg.norm(xte[i]) + 1e-9)))) == yte[i] for i in pick]))
    new = [i for i in pick if ste[i] in (4, 5)]
    ref_new = 100 * float(np.mean([int(np.argmax(tpl @ (xte[i].ravel() / (np.linalg.norm(xte[i]) + 1e-9)))) == yte[i] for i in new])) if new else float("nan")
    return byclass, tests, ref, ref_new, len(new), float(np.mean([x.sum() for x in xte]))


def main(d, nin=48, nbins=20, cpb=2, topn=8, seeds=3, epochs=30, ft=10, epr=2, ntest=30, K=14, L=3):
    byclass, tests, ref, ref_new, nnew, evs = prepare(d, nin, nbins, cpb, topn, ntest)
    print("front end: %d lines, %d steps x %d clocks, top %d per step -> %.0f events per recording" % (nin, nbins, cpb, topn, evs))
    print("test: %d recordings (%d from the 2 unheard speakers). template classifier: %.1f%% (unheard speakers %.1f%%), chance 10%%" % (len(tests), nnew, ref, ref_new), flush=True)
    res = {}; t0 = time.time()
    for s in range(1, seeds + 1):
        r = random.Random(s); net0 = H.make(s, 0.5, fb_k=8, fb_w=2, k=24, refr=6, th=5, groups=4, per=16, layers=L, nin=nin); tg = targets(net0, s, L); tg2 = [{g for g in t if net0.layer_of(g) == 2} for t in tg]
        t1 = layer1_targets(net0, byclass, r); w0 = copy.deepcopy(net0.table); train(net0, byclass, tg, t1, epochs, epr, r, w0)
        for name, kp in (("dense", None), ("K=%d" % K, K)):
            net = copy.deepcopy(net0)
            if kp: Q.prune_by(net, dict([(1, kp + 4)] + [(l, kp) for l in range(2, L + 1)]), "weight"); train(net, byclass, tg, t1, ft, epr, r, copy.deepcopy(net.table))
            a, f, z, dr = evaluate(net, tests, tg, tg2, L); x = res.setdefault(name, dict(a=[0, 0], f={l: 0.0 for l in f}, z={l: 0.0 for l in f}, dr=0.0, conn=0))
            x["a"][0] += a[0] / seeds; x["a"][1] += a[1] / seeds; x["dr"] += dr / seeds; x["conn"] += sum(len(v) for v in net.table.values()) / seeds
            for l in f: x["f"][l] += f[l] / seeds; x["z"][l] += z[l] / seeds
        print("  seed %d done, %.0f s" % (s, time.time() - t0), flush=True)
    for name, x in res.items():
        print("\n%s: %d connections, packets dropped %.1f%%" % (name, x["conn"], x["dr"]))
        print("  recall: combined map %.1f%%   layer 2 alone %.1f%%" % tuple(x["a"]))
        print("  layer          " + "  ".join("%6d" % l for l in x["f"])); print("  cells fired    " + "  ".join("%6.1f" % x["f"][l] for l in x["f"])); print("  silent %%       " + "  ".join("%6.0f" % x["z"][l] for l in x["z"]))


if __name__ == "__main__":
    a = sys.argv; v = [int(x) for x in a[2:]]; main(a[1], *v)   # NIN NBINS CPB TOPN SEEDS EPOCHS in main()'s order
