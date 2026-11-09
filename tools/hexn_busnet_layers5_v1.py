"""hexn_busnet_layers5_v1 (9 Nov 2026): the same test as hexn_busnet_layermatch_v1 on a network of more layers (default 5). Alan 16:59: 'if you extend the model to 5 layers, does this rule follow, only the middle or every 2 layers?'. Direction doc section 50.
The model code is written for 3 layers in a few places; this tool patches those at run time and leaves the earlier tools untouched:
  * target maps: PER_LAYER (5) cells per pattern in EACH of layers 2..L (as before for layers 2 and 3)
  * map = the cells that fired in layers 2..L;  the run is 200 clocks, not 100 (more layers take longer to settle)
  * homeostat firing-rate targets: layers 4 and later use 0.05, the layer 3 value. THIS IS A GUESS, not tuned.
  * pruning keeps 10 sources per cell in the layers added (as layers 2 and 3).
Feedback goes from the last layer to layer 1 (as in the model). Matchers compared: each single layer, all layers together, layers 2+4 (every second), layers 3+5.
Usage: python3 tools/hexn_busnet_layers5_v1.py [LAYERS] [GROUPS] [PER]"""
import random, sys, os, functools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H


def patch(L):
    def targets(net, seed=0):
        r = random.Random(900 + seed); out = [set() for _ in range(T.NPAT)]
        for l in range(2, L + 1):
            ids = [net.gid(l, i) for i in range(net.groups * net.per)]; r.shuffle(ids)
            for k in range(T.NPAT): out[k] |= set(ids[k * T.PER_LAYER:(k + 1) * T.PER_LAYER])
        return out
    T.targets = targets
    orig_map_of = B.map_of; B.map_of = lambda net, layers=tuple(range(2, L + 1)): orig_map_of(net, layers)
    orig_fresh = T.fresh_run; T.fresh_run = lambda t, ev, total=200: orig_fresh(t, ev, total)
    for l in range(4, L + 1): H.TARGET[l] = 0.05
    for l in range(4, L + 1): P.LEAN_KEEP[l] = 10


def main(L=5, groups=4, per=16, seeds=(1, 2, 3, 4, 5), epochs=40, ft=10, th=5, ntest=10):
    patch(L); pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; drops = (0.1, 0.3, 0.5, 0.7)
    combos = [("layer %d" % l, (l,)) for l in range(2, L + 1)] + [("all layers", tuple(range(2, L + 1))), ("layers 2+4", (2, 4)), ("layers 3+5", (3, 5))]
    ok = {d: [0] * len(combos) for d in drops}; tot = {d: 0 for d in drops}; fired = {l: 0.0 for l in range(1, L + 1)}
    for s in seeds:
        net = H.make(s, 0.5, fb_k=8, fb_w=2, k=24, refr=6, th=th, groups=groups, per=per, layers=L); tg = T.targets(net, s); t1 = P.layer1_targets(net, pats)
        H.train(net, pats, tg, t1, epochs, homeo=True); Q.prune_by(net, P.LEAN_KEEP, "weight"); H.train(net, pats, tg, t1, ft, homeo=True)
        for k in range(T.NPAT):
            run = T.fresh_run(net, B.noisy(pats[k], random.Random(31337 + k)))
            for l in range(1, L + 1): fired[l] += sum(1 for g in run.fires if run.layer_of(g) == l) / T.NPAT / len(seeds)
        tgl = [[{g for g in t if net.layer_of(g) == l} for t in tg] for l in range(0, L + 1)]
        for d in drops:
            for k in range(T.NPAT):
                for j in range(ntest):
                    run = T.fresh_run(net, B.noisy(pats[k], random.Random(20000 + 97 * k + j), drop=d, jit=3))
                    for i, (name, ls) in enumerate(combos):
                        m = B.map_of(run, ls); sc = [B.jaccard(m, set().union(*(tgl[l][p] for l in ls))) for p in range(T.NPAT)]
                        ok[d][i] += (max(range(T.NPAT), key=lambda x: sc[x]) == k)
                    tot[d] += 1
    print("%d layers of %d buses x %d cells, %d seeds; cells fired per run by layer: %s" % (L, groups, per, len(seeds), "  ".join("L%d %.0f" % (l, fired[l]) for l in fired)))
    print("recall (%) at 10 / 30 / 50 / 70% of events dropped")
    for i, (name, ls) in enumerate(combos): print("  %-11s %s" % (name, "  ".join("%3d%%" % (100 * ok[d][i] / tot[d]) for d in drops)))


if __name__ == "__main__":
    a = sys.argv; main(*(int(x) for x in a[1:4]))
