"""hexn_busnet_workpoint_v1 (9 Nov 2026): move the working point from 10 to 14 sources per cell and see whether the layered firing changes. Alan 20:21 (after section 52). Direction doc section 53.
Same dense start, training, pruning and retraining as hexn_busnet_prunelevel_v1; only the kept sources differ: K = 10 (layer 1: 14, the working point of sections 37 to 52) against K = 14 (layer 1: 18). LAYERS = 3 is the design; LAYERS = 5 is patched as in hexn_busnet_layers5_v1 (rate targets of deep layers guessed). Per layer: cells fired per run (clean), share of runs where the layer is silent, mean threshold; recall at 10 / 30 / 50 / 70% dropped for the combined map and the layer 2 map.
Usage: python3 tools/hexn_busnet_workpoint_v1.py LAYERS"""
import random, sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H, hexn_busnet_layers5_v1 as L5
import hexn_busnet_depth_diag_v1 as D, hexn_busnet_prunelevel_v1 as PL


def main(L=3, groups=4, per=16, seeds=(1, 2, 3, 4, 5), epochs=40, ft=10, th=5, ntest=10, levels=(10, 14)):
    if L > 3: L5.patch(L)
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; drops = (0.1, 0.3, 0.5, 0.7); res = {}
    for s in seeds:
        net0 = H.make(s, 0.5, fb_k=8, fb_w=2, k=24, refr=6, th=th, groups=groups, per=per, layers=L); tg = T.targets(net0, s); t1 = P.layer1_targets(net0, pats); tg2 = [{g for g in t if net0.layer_of(g) == 2} for t in tg]
        H.train(net0, pats, tg, t1, epochs, homeo=True)
        for K in levels:
            net = copy.deepcopy(net0); keep = {1: K + 4}; keep.update({l: K for l in range(2, L + 1)}); Q.prune_by(net, keep, "weight"); H.train(net, pats, tg, t1, ft, homeo=True)
            ok, tot, _ = PL.evaluate(net, pats, tg, tg2, drops, ntest); f, z, t = D.measure(net, pats, L)
            r = res.setdefault(K, dict(conn=0, ok={d: [0, 0] for d in drops}, tot={d: 0 for d in drops}, f={l: 0.0 for l in f}, z={l: 0.0 for l in f}, t={l: 0.0 for l in f}))
            r["conn"] += sum(len(v) for v in net.table.values()) / len(seeds)
            for l in f: r["f"][l] += f[l] / len(seeds); r["z"][l] += z[l] / len(seeds); r["t"][l] += t[l] / len(seeds)
            for d in drops:
                r["tot"][d] += tot[d]
                for i in (0, 1): r["ok"][d][i] += ok[d][i]
    print("%d layers of %d buses x %d cells, %d seeds" % (L, groups, per, len(seeds)))
    for K, r in res.items():
        print("\n  %d sources per cell (layer 1: %d), %d connections" % (K, K + 4, r["conn"]))
        print("    recall 10/30/50/70%%: combined %s | layer 2 %s" % ("  ".join("%3d%%" % (100 * r["ok"][d][0] / r["tot"][d]) for d in drops), "  ".join("%3d%%" % (100 * r["ok"][d][1] / r["tot"][d]) for d in drops)))
        print("    %-12s %s" % ("layer", "   ".join("%6d" % l for l in r["f"])))
        print("    %-12s %s" % ("cells fired", "   ".join("%6.1f" % r["f"][l] for l in r["f"])))
        print("    %-12s %s" % ("silent %", "   ".join("%6.0f" % r["z"][l] for l in r["z"])))
        print("    %-12s %s" % ("mean thr", "   ".join("%6.1f" % r["t"][l] for l in r["t"])))


if __name__ == "__main__":
    main(int(sys.argv[1]))
