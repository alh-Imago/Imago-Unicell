"""hexn_busnet_layermatch_v1 (9 Nov 2026): does matching PER LAYER recall better than the combined layer 2 + 3 map? Alan 16:52 (matcher at a finer grain, per layer). Direction doc section 49.
Same network as hexn_busnet_hw_v1 'ideal model, pruned dense' (4 x 16 cells by default, dense start, homeostat, pruned to the lean count, retrained) and the same noisy test patterns as hexn_busnet_gen_v1.recall. Four ways to pick the stored pattern from the live map:
  combined = overlap of the whole layer 2 + 3 map with each stored map (what every earlier section used)
  layer 2  = overlap of the layer 2 cells only;  layer 3 = overlap of the layer 3 cells only
  sum      = layer 2 overlap + layer 3 overlap (two per-layer matchers whose scores are added)
  both     = the pattern both per-layer matchers pick (counted right only when they agree and are right; disagreement counts as wrong)
Usage: python3 tools/hexn_busnet_layermatch_v1.py [GROUPS PER]"""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H


def main(groups=4, per=16, seeds=(1, 2, 3, 4, 5), epochs=40, ft=10, th=5, ntest=10):
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; drops = (0.1, 0.3, 0.5, 0.7)
    names = ("combined", "layer 2", "layer 3", "sum", "both agree"); ok = {d: [0] * 5 for d in drops}; tot = {d: 0 for d in drops}
    for s in seeds:
        net = H.make(s, 0.5, fb_k=8, fb_w=2, k=24, refr=6, th=th, groups=groups, per=per); tg = T.targets(net, s); t1 = P.layer1_targets(net, pats)
        H.train(net, pats, tg, t1, epochs, homeo=True); Q.prune_by(net, P.LEAN_KEEP, "weight"); H.train(net, pats, tg, t1, ft, homeo=True)
        tg2 = [{g for g in t if net.layer_of(g) == 2} for t in tg]; tg3 = [{g for g in t if net.layer_of(g) == 3} for t in tg]
        for d in drops:
            for k in range(T.NPAT):
                for j in range(ntest):
                    ev = B.noisy(pats[k], random.Random(20000 + 97 * k + j), drop=d, jit=3); run = T.fresh_run(net, ev); m = B.map_of(run); m2 = B.map_of(run, (2,)); m3 = B.map_of(run, (3,))
                    c = [B.jaccard(m, t) for t in tg]; a = [B.jaccard(m2, t) for t in tg2]; b = [B.jaccard(m3, t) for t in tg3]; pick = lambda sc: max(range(T.NPAT), key=lambda x: sc[x])
                    p2, p3 = pick(a), pick(b); res = (pick(c) == k, p2 == k, p3 == k, pick([x + y for x, y in zip(a, b)]) == k, p2 == p3 == k)
                    for i, r in enumerate(res): ok[d][i] += r
                    tot[d] += 1
    print("%d buses x %d cells, %d seeds; recall (%%) at 10 / 30 / 50 / 70%% of events dropped" % (groups, per, len(seeds)))
    for i, n in enumerate(names): print("  %-11s %s" % (n, "  ".join("%3d%%" % (100 * ok[d][i] / tot[d]) for d in drops)))


if __name__ == "__main__":
    a = sys.argv; main(*(int(x) for x in a[1:3]))
