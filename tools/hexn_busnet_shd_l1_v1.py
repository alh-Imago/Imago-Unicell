"""hexn_busnet_shd_l1_v1 (9 Nov 2026): layer 1 of the bus network on its own, on the spoken digits. Alan 22:35 (option 1: see whether layer 1 can be fixed before bringing in the detector). Direction doc section 57. Simulation only.
A network of ONE layer (4 buses x 16 cells), no feedback, listening to the NIN lines of the front end (hexn_shd_frontend_v1; same settings as sections 55 and 56). Question: does the set of layer 1 cells that fire carry the digit, and how does that depend on how many sources a cell listens to (K) and on its threshold (TH)?
Measure per setting (random wiring, NO training, fixed threshold): cells fired per recording (of 64) and the accuracy of a nearest-centroid classifier on the vector of fire counts (centroids from NTRAIN training recordings per digit, tested on the same 300 test recordings as before; chance 10%). The template classifier on the raw events is printed as the reference.
Usage: python3 tools/hexn_busnet_shd_l1_v1.py DIR [TOPN]"""
import random, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_shd_v1 as S, hexn_shd_frontend_v1 as F

NIN = 48; NBINS = 20; CPB = 2; NCL = 10


def fire_vec(net, ev, ncell):
    net.acc = {g: 0 for g in net.acc}; net.rleft = {g: 0 for g in net.rleft}
    for q in net.queues.values(): q.clear()
    net.reset_stats(); net.run(ev, 100); v = np.zeros(ncell)
    for g, c in net.fires.items(): v[g - NIN] = c
    return v


def accuracy(vtr, ytr, vte, yte):
    cen = np.stack([vtr[ytr == c].mean(axis=0) for c in range(NCL)]); cen = cen - vtr.mean(axis=0) * 0; cen /= (np.linalg.norm(cen, axis=1, keepdims=True) + 1e-9)
    return 100 * float(np.mean([int(np.argmax(cen @ (v / (np.linalg.norm(v) + 1e-9)))) == y for v, y in zip(vte, yte)]))


def main(d, topn=4, ntrain=40, ntest=30, seeds=2):
    byclass, tests, ref, ref_new, nnew, evs = S.prepare(d, NIN, NBINS, CPB, topn, ntest)
    r = random.Random(3); tr = [(k, ev) for k in range(NCL) for ev in r.sample(byclass[k], ntrain)]; ytr = np.array([k for k, _ in tr]); yte = np.array([k for k, _ in tests])
    print("%.0f events per recording; template classifier %.1f%% on the raw events (chance 10%%)" % (evs, ref))
    print("%-4s %-4s | %s" % ("K", "TH", "cells fired per recording / centroid accuracy %%  (mean of %d seeds)" % seeds), flush=True)
    for K in (4, 8, 14, 24):
        for TH in (3, 6, 10, 16, 24, 36):
            fr = acc = 0.0
            for s in range(1, seeds + 1):
                net = B.Net(s, th=TH, leak_every=4, refr=6, qdepth=8, fb_k=0, k=K, nin=NIN, layers=1, groups=4, per=16)
                vtr = np.stack([fire_vec(net, ev, 64) for _, ev in tr]); vte = np.stack([fire_vec(net, ev, 64) for _, ev in tests])
                fr += (vtr > 0).sum(axis=1).mean() / seeds; acc += accuracy(vtr, ytr, vte, yte) / seeds
            print("%-4d %-4d | %5.1f / %5.1f" % (K, TH, fr, acc), flush=True)


if __name__ == "__main__":
    main(sys.argv[1], *[int(v) for v in sys.argv[2:]])
