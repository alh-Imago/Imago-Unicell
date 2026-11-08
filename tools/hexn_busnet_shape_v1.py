"""hexn_busnet_shape_v1 (8 Nov 2026): delay, drops and accuracy against queue depth and number of buses per layer, for the pruned dense network with the self-adjusting threshold. Alan 20:56 ('apply and test') following direction doc section 41. Earlier tools untouched.
Each layer keeps 64 cells; GROUPS buses of PER cells (groups*per = 64). Queue slots = 3 layers x GROUPS x QDEPTH (a memory proxy; the real cost per slot is not measured). Pipeline as hexn_busnet_homeoprune_v1: dense net (24 sources + 8 feedback) trained 40 epochs with homeostasis, pruned by weight to 14/10/10 per cell, 10 epochs retraining with homeostasis. Start threshold 5, 5 seeds.
Delay: clocks from the first input event to the first layer 3 fire, and to the clock by which 90% of the cells in the final layer 2/3 map have fired (averaged over 8 patterns x 3 noisy runs). Simulation only.
Usage: python3 tools/hexn_busnet_shape_v1.py GROUPS PER QDEPTH"""
import random, copy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_gen_v1 as G, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H


def delays(net, pats, nrun=3):
    d1 = []; d90 = []
    for k in range(T.NPAT):
        for j in range(nrun):
            ev = B.noisy(pats[k], random.Random(8000 + 10 * k + j)); t0 = min(ev); n = T.fresh_run(net, ev); l3 = [t for g, t in n.fire_t.items() if n.layer_of(g) == 3]
            mp = sorted(t for g, t in n.fire_t.items() if n.layer_of(g) in (2, 3))
            if l3: d1.append(min(l3) - t0)
            if mp: d90.append(mp[min(len(mp) - 1, int(0.9 * len(mp)))] - t0)
    return (sum(d1) / len(d1) if d1 else float("nan")), (sum(d90) / len(d90) if d90 else float("nan"))


def main(groups, per, qd, th=5, seeds=(1, 2, 3, 4, 5), epochs=40, ft=10):
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; ok = [0] * 4; tot = [0] * 4; dr = d1 = d90 = 0.0
    for s in seeds:
        net = H.make(s, 0.5, fb_k=8, fb_w=2, k=24, refr=6, th=th, groups=groups, per=per, qdepth=qd); tg2 = T.targets(net, s); t1 = P.layer1_targets(net, pats)
        H.train(net, pats, tg2, t1, epochs, homeo=True); Q.prune_by(net, P.LEAN_KEEP, "weight"); H.train(net, pats, tg2, t1, ft, homeo=True)
        rec = [G.recall(net, pats, tg2, d, 3, ntest=10) for d in (0.1, 0.3, 0.5, 0.7)]
        for i in range(4): ok[i] += rec[i][0]; tot[i] += rec[i][1]
        dr += P.traffic(net, pats)[1]; a, b = delays(net, pats); d1 += a; d90 += b
    n = len(seeds)
    print("buses/layer %2d x %2d cells  queue depth %3d  slots %4d : %s  dropped %5.1f  delay first L3 %.1f  90%% of map %.1f clocks" % (groups, per, qd, 3 * groups * qd, "  ".join("%3d%%" % (100 * ok[i] / tot[i]) for i in range(4)), dr / n, d1 / n, d90 / n))


if __name__ == "__main__": main(int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))
