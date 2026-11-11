"""hexn_busnet_compete_v1 (11 Nov 2026): COMPETITION BETWEEN CELLS in the bus network toy. Alan 19:25 (explore inter-cell competition; thought directions of sections 94 and 95: the path of least effort, first to fire wins).
Direction doc section 96. Earlier tools untouched. Simulation only, toy patterns.
Network and test as section 49 (hexn_busnet_layermatch_v1): 3 layers, 4 buses x 16 cells, dense start, homeostat, pruned, retrained, 8 patterns, 5 seeds, 10 noisy tests per pattern at 10/30/50/70% of events dropped.
CompNet = the same cells plus one rule: when a cell of layer 2 or 3 FIRES, the cells that share its SCOPE and did not fire in that clock are held down:
  scope   bus = the 16 cells on the same bus; layer = all 64 cells of the layer
  form    soft k = their accumulators lose k (not below 0);  hard = their accumulators are cleared (first to fire wins, the others start again);  quiet = they are also made refractory (cannot fire for the refractory time)
Two ways to use it: added to a network trained WITHOUT it (test only), or present during training as well (the cells learn with it).
Measured: recall of the stored pattern from the layer 2 map, the layer 3 map and both (overlap with the target maps, as section 49); and what the competition does to the maps: cells fired per run in layers 2 and 3,
and how many of them are NOT in the pattern's target map (stray cells).
Usage: python3 tools/hexn_busnet_compete_v1.py [SEEDS]"""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H

DROPS = (0.1, 0.3, 0.5, 0.7)


class CompNet(H.AdaptNet):
    comp = None                                   # (scope, form, k)

    def step(self, t, inputs=()):
        fired = H.AdaptNet.step(self, t, inputs)
        if self.comp and fired:
            scope, form, k = self.comp; fs = set(fired); ncell = self.groups * self.per
            for g in fired:
                l = self.layer_of(g)
                if l not in (2, 3): continue
                i = g - self.gid(l, 0)
                others = [self.gid(l, j) for j in (range((i // self.per) * self.per, (i // self.per + 1) * self.per) if scope == "bus" else range(ncell))]
                for o in others:
                    if o in fs: continue
                    if form == "soft": self.acc[o] = max(0, self.acc[o] - k) if self.acc[o] > 0 else self.acc[o]
                    else:
                        self.acc[o] = 0
                        if form == "quiet": self.rleft[o] = max(self.rleft[o], self.refr)
        return fired


def build(seed, pats, comp_train, epochs=40, ft=10, th=5):
    net = H.make(seed, 0.5, fb_k=8, fb_w=2, k=24, refr=6, th=th, groups=4, per=16); net.__class__ = CompNet; net.comp = comp_train
    tg = T.targets(net, seed); t1 = P.layer1_targets(net, pats)
    H.train(net, pats, tg, t1, epochs, homeo=True); Q.prune_by(net, P.LEAN_KEEP, "weight"); H.train(net, pats, tg, t1, ft, homeo=True)
    return net, tg


def measure(net, tg, pats, ntest=10):
    tg2 = [{g for g in t if net.layer_of(g) == 2} for t in tg]; tg3 = [{g for g in t if net.layer_of(g) == 3} for t in tg]
    ok = {d: [0, 0, 0] for d in DROPS}; n = 0; fired = [0, 0]; stray = [0, 0]; nr = 0
    for d in DROPS:
        for k in range(T.NPAT):
            for j in range(ntest):
                run = T.fresh_run(net, B.noisy(pats[k], random.Random(20000 + 97 * k + j), drop=d, jit=3)); m = B.map_of(run); m2 = B.map_of(run, (2,)); m3 = B.map_of(run, (3,))
                pick = lambda mm, tt: max(range(T.NPAT), key=lambda x: B.jaccard(mm, tt[x]))
                ok[d][0] += (pick(m2, tg2) == k); ok[d][1] += (pick(m3, tg3) == k); ok[d][2] += (pick(m, tg) == k)
                if d == 0.1: fired[0] += len(m2); fired[1] += len(m3); stray[0] += len(m2 - tg2[k]); stray[1] += len(m3 - tg3[k]); nr += 1
        n = T.NPAT * ntest
    return ok, n, [x / nr for x in fired], [x / nr for x in stray]


def main(seeds):
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]
    variants = [("no competition", None, None)]
    for nm, c in (("bus, soft 1", ("bus", "soft", 1)), ("bus, soft 2", ("bus", "soft", 2)), ("bus, hard", ("bus", "hard", 0)), ("bus, quiet", ("bus", "quiet", 0)), ("layer, soft 1", ("layer", "soft", 1)), ("layer, hard", ("layer", "hard", 0))):
        variants.append((nm + "  (test only)", None, c)); variants.append((nm + "  (trained with it)", c, c))
    print("%d seeds; recall = percent right at 10 / 30 / 50 / 70%% dropped; fired and stray = cells per run at 10%% dropped (target map = 5 cells per layer)" % len(seeds))
    print("%-34s | %-17s | %-17s | %-17s | %-13s | %s" % ("competition", "layer 2 map", "layer 3 map", "both layers", "fired L2 / L3", "stray L2 / L3"))
    cache = {}
    for nm, ctrain, ctest in variants:
        tot = {d: [0, 0, 0] for d in DROPS}; n = 0; fr = [0.0, 0.0]; st = [0.0, 0.0]
        for s in seeds:
            if (s, ctrain) not in cache: cache[(s, ctrain)] = build(s, pats, ctrain)
            net, tg = cache[(s, ctrain)]; net.comp = ctest; ok, k, f, y = measure(net, tg, pats); n += k
            for d in DROPS:
                for i in range(3): tot[d][i] += ok[d][i]
            fr = [fr[i] + f[i] for i in range(2)]; st = [st[i] + y[i] for i in range(2)]
        col = lambda i: " / ".join("%.0f" % (100.0 * tot[d][i] / n) for d in DROPS)
        print("%-34s | %-17s | %-17s | %-17s | %4.1f / %4.1f   | %4.1f / %4.1f" % (nm, col(0), col(1), col(2), fr[0] / len(seeds), fr[1] / len(seeds), st[0] / len(seeds), st[1] / len(seeds)), flush=True)


if __name__ == "__main__":
    main(tuple(range(1, 1 + (int(sys.argv[1]) if len(sys.argv) > 1 else 5))))
