"""hexn_busnet_depthfix_v1 (9 Nov 2026): what keeps the deep layers alive? Alan 21:16 (after sections 50 to 53). Direction doc section 54.
5 layers of 4 buses x 16 cells, working point 14 sources per cell (layer 1: 18), trained and pruned as in hexn_busnet_workpoint_v1. One VARIANT per run (the changes are module-level settings, so each variant is its own process):
  base    = nothing changed (rate targets 0.08 / 0.05 / 0.05 / 0.05 / 0.05 for layers 1 to 5 as 0.40, 0.08, 0.05..., threshold floor 2)
  floor1  = the threshold floor is 1 instead of 2 (every layer)
  rates   = firing-rate targets of layers 3 to 5 raised to 0.08 (the layer 2 value)
  weights = the starting weights of the excitatory links in layers 4 and 5 are 1 higher (capped at the weight limit)
  all     = floor1 + rates + weights
Measured: cells fired per layer in a clean run, share of silent runs per layer, and the recall of a matcher on each single layer and on all layers together, at 10 / 50 / 70% of events dropped (4 seeds).
Usage: python3 tools/hexn_busnet_depthfix_v1.py VARIANT"""
import random, sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H, hexn_busnet_layers5_v1 as L5, hexn_busnet_depth_diag_v1 as D

L = 5; K = 14


def main(variant, groups=4, per=16, seeds=(1, 2, 3, 4), epochs=40, ft=10, th=5, ntest=8, drops=(0.1, 0.5, 0.7)):
    L5.patch(L)
    if variant in ("floor1", "all"): H.TH_MIN = 1
    if variant in ("rates", "all"):
        for l in (3, 4, 5): H.TARGET[l] = 0.08
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]
    combos = [("layer %d" % l, (l,)) for l in range(2, L + 1)] + [("all layers", tuple(range(2, L + 1)))]
    ok = {d: [0] * len(combos) for d in drops}; tot = {d: 0 for d in drops}; f = {l: 0.0 for l in range(1, L + 1)}; z = dict(f); thr = dict(f)
    for s in seeds:
        net = H.make(s, 0.5, fb_k=8, fb_w=2, k=24, refr=6, th=th, groups=groups, per=per, layers=L)
        if variant in ("weights", "all"):
            for g in net.table:
                if net.layer_of(g) >= 4:
                    for src in net.table[g]:
                        if net.table[g][src] > 0: net.table[g][src] = min(net.table[g][src] + 1, T.WMAX)
        tg = T.targets(net, s); t1 = P.layer1_targets(net, pats)
        H.train(net, pats, tg, t1, epochs, homeo=True); keep = {1: K + 4}; keep.update({l: K for l in range(2, L + 1)}); Q.prune_by(net, keep, "weight"); H.train(net, pats, tg, t1, ft, homeo=True)
        fs, zs, ts = D.measure(net, pats, L)
        for l in f: f[l] += fs[l] / len(seeds); z[l] += zs[l] / len(seeds); thr[l] += ts[l] / len(seeds)
        tgl = [[{g for g in t if net.layer_of(g) == l} for t in tg] for l in range(L + 1)]
        for d in drops:
            for k in range(T.NPAT):
                for j in range(ntest):
                    run = T.fresh_run(net, B.noisy(pats[k], random.Random(20000 + 97 * k + j), drop=d, jit=3))
                    for i, (name, ls) in enumerate(combos):
                        m = B.map_of(run, ls); sc = [B.jaccard(m, set().union(*(tgl[l][p] for l in ls))) for p in range(T.NPAT)]
                        ok[d][i] += (max(range(T.NPAT), key=lambda x: sc[x]) == k)
                    tot[d] += 1
    print("VARIANT %s: 5 layers, %d sources per cell, %d seeds" % (variant, K, len(seeds)))
    print("  layer           %s" % "   ".join("%6d" % l for l in f))
    print("  cells fired     %s" % "   ".join("%6.1f" % f[l] for l in f))
    print("  silent %%        %s" % "   ".join("%6.0f" % z[l] for l in z))
    print("  mean threshold  %s" % "   ".join("%6.1f" % thr[l] for l in thr))
    print("  recall at 10 / 50 / 70%% dropped")
    for i, (name, ls) in enumerate(combos): print("    %-11s %s" % (name, "  ".join("%3d%%" % (100 * ok[d][i] / tot[d]) for d in drops)))


if __name__ == "__main__":
    main(sys.argv[1])
