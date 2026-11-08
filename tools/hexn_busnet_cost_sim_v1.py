"""hexn_busnet_cost_sim_v1 (8 Nov 2026): the two things the synthesised bus module does NOT cover and the Python model hides (direction doc section 43): (1) how many packets the model delivers to ONE bus queue in ONE clock (the module takes one push per clock), and (2) how far the accumulators range (the module saturates at -32..31). Measured on the trained pruned dense network (hexn_busnet_homeoprune_v1 pipeline, start threshold 5, seed 1) and on the lean network. Simulation only.
Usage: python3 tools/hexn_busnet_cost_sim_v1.py"""
import random, copy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H


def measure(net, pats, nrun=3):
    hist = {}; amin = 0; amax = 0; busy = 0; tot_push = 0; per_layer_max = {}
    for k in range(T.NPAT):
        for j in range(nrun):
            n = copy.deepcopy(net); n.acc = {g: 0 for g in n.acc}; n.rleft = {g: 0 for g in n.rleft}
            for q in n.queues.values(): q.clear()
            n.reset_stats(); cur = {}; orig = n.push

            def hook(bus, src, cur=cur, orig=orig): cur[bus] = cur.get(bus, 0) + 1; orig(bus, src)
            n.push = hook; ev = B.noisy(pats[k], random.Random(8000 + 10 * k + j))
            for t in range(100):
                cur.clear(); n.step(t, ev.get(t, ()))
                for bus, c in cur.items():
                    hist[c] = hist.get(c, 0) + 1; per_layer_max[bus[0]] = max(per_layer_max.get(bus[0], 0), c); busy += 1; tot_push += c
                amin = min(amin, min(n.acc.values())); amax = max(amax, max(n.acc.values()))
    return hist, busy, tot_push, per_layer_max, amin, amax


def report(lab, net, pats):
    hist, busy, tp, plm, amin, amax = measure(net, pats)
    multi = sum(v for c, v in hist.items() if c > 1); print("%-14s bus-clocks with a push: %d; with MORE than one push: %d (%.0f%%); most pushes to one bus in one clock: %d (layer 1/2/3: %s); accumulator range seen %d..%d" % (lab, busy, multi, 100.0 * multi / busy, max(hist), "/".join(str(plm.get(l, 0)) for l in (1, 2, 3)), amin, amax))
    print("               distribution of pushes per busy bus-clock: %s" % ", ".join("%d: %d" % (c, hist[c]) for c in sorted(hist)))


def main(s=1, th=5):
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]
    lean = H.make(s, 0.5, fb_k=4, fb_w=2, k=10, refr=6, th=th); tg2 = T.targets(lean, s); t1 = P.layer1_targets(lean, pats); H.train(lean, pats, tg2, t1, 50)
    rich = H.make(s, 0.5, fb_k=8, fb_w=2, k=24, refr=6, th=th); t1r = P.layer1_targets(rich, pats); H.train(rich, pats, tg2, t1r, 40); Q.prune_by(rich, P.LEAN_KEEP, "weight"); H.train(rich, pats, tg2, t1r, 10)
    report("lean", lean, pats); report("pruned dense", rich, pats)


if __name__ == "__main__": main()
