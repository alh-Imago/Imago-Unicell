"""hexn_busnet_prunelevel_v1 (9 Nov 2026): is the pruning too harsh? Alan 17:15. Direction doc section 52.
3 layers of 4 buses x 16 cells (the design). Dense start (24 sources per cell + 8 feedback links), trained 40 epochs with the homeostat, then pruned by weight size to K sources per cell (layer 1 gets K + 4, as the lean net has 10 + 4) and retrained 10 epochs. K = 10 is what every section since 37 used. The dense copy is trained once per seed and each level is pruned from a copy of it.
For each K: connections in all (the sum of the table sizes), recall at 10 / 30 / 50 / 70% of events dropped for the combined layer 2 + 3 map and for the layer 2 map alone, and the cells fired per run in layers 2 and 3.
Usage: python3 tools/hexn_busnet_prunelevel_v1.py"""
import random, sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H


def evaluate(net, pats, tg, tg2, drops, ntest):
    ok = {d: [0, 0] for d in drops}; tot = {d: 0 for d in drops}
    for d in drops:
        for k in range(T.NPAT):
            for j in range(ntest):
                run = T.fresh_run(net, B.noisy(pats[k], random.Random(20000 + 97 * k + j), drop=d, jit=3)); m = B.map_of(run); m2 = B.map_of(run, (2,))
                ok[d][0] += (max(range(T.NPAT), key=lambda x: B.jaccard(m, tg[x])) == k); ok[d][1] += (max(range(T.NPAT), key=lambda x: B.jaccard(m2, tg2[x])) == k); tot[d] += 1
    fired = {2: 0.0, 3: 0.0}; n = 0
    for k in range(T.NPAT):
        run = T.fresh_run(net, B.noisy(pats[k], random.Random(31337 + k), drop=0.0, jit=0)); n += 1
        for l in fired: fired[l] += sum(1 for g in run.fires if run.layer_of(g) == l)
    return ok, tot, {l: fired[l] / n for l in fired}


def main(seeds=(1, 2, 3, 4, 5), epochs=40, ft=10, th=5, ntest=10, levels=(None, 20, 14, 10, 6, 4)):
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; drops = (0.1, 0.3, 0.5, 0.7); res = {}
    for s in seeds:
        net0 = H.make(s, 0.5, fb_k=8, fb_w=2, k=24, refr=6, th=th, groups=4, per=16); tg = T.targets(net0, s); t1 = P.layer1_targets(net0, pats); tg2 = [{g for g in t if net0.layer_of(g) == 2} for t in tg]
        H.train(net0, pats, tg, t1, epochs, homeo=True)
        for K in levels:
            net = copy.deepcopy(net0)
            if K is not None: Q.prune_by(net, {1: K + 4, 2: K, 3: K}, "weight"); H.train(net, pats, tg, t1, ft, homeo=True)
            ok, tot, fired = evaluate(net, pats, tg, tg2, drops, ntest); r = res.setdefault(K, dict(conn=0, ok={d: [0, 0] for d in drops}, tot={d: 0 for d in drops}, f2=0.0, f3=0.0))
            r["conn"] += sum(len(v) for v in net.table.values()) / len(seeds); r["f2"] += fired[2] / len(seeds); r["f3"] += fired[3] / len(seeds)
            for d in drops:
                r["tot"][d] += tot[d]
                for i in (0, 1): r["ok"][d][i] += ok[d][i]
    print("3 layers of 4 buses x 16 cells, %d seeds; recall at 10 / 30 / 50 / 70%% of events dropped" % len(seeds))
    print("  %-12s %12s   %-22s   %-22s   %s" % ("sources/cell", "connections", "combined L2+3", "layer 2 only", "fired L2 / L3"))
    for K, r in res.items():
        print("  %-12s %12.0f   %-22s   %-22s   %.1f / %.1f" % ("unpruned" if K is None else "%d (L1 %d)" % (K, K + 4), r["conn"], "  ".join("%3d%%" % (100 * r["ok"][d][0] / r["tot"][d]) for d in drops), "  ".join("%3d%%" % (100 * r["ok"][d][1] / r["tot"][d]) for d in drops), r["f2"], r["f3"]))


if __name__ == "__main__":
    main()
