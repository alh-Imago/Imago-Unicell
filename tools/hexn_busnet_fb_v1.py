"""hexn_busnet_fb_v1 (8 Nov 2026): stabilised feedback links together with map-feedback training (hexn_busnet_v1 and hexn_busnet_train_v1 untouched). Alan 19:05: stabilise the feedbacks.
Feedback = layer 3 cells linked back to layer 1 cells (4 links per layer 1 cell, weight FBW). Stabilisers tried: leak every clock, a share of the feedback links made inhibitory (sign flipped), a longer refractory period, a lower threshold to pay for a heavier leak.
Per setting and wiring seed: train (teacher target maps, as hexn_busnet_train_v1) WITH the feedback links present, then measure single recall, mixture hits, 'afterglow' (cells firing and packets per clock in clocks 60 to 100, input stops by clock about 40) and dropped packets, averaged over 8 test runs of the 8 patterns; and the same for the untrained net.
Simulation only. Usage: python3 tools/hexn_busnet_fb_v1.py [epochs]"""
import random, copy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T


def make(seed, fb_inhib=0.0, **kw):
    n = B.Net(seed, **kw)
    if fb_inhib:
        r = random.Random(4000 + seed); l3 = {n.gid(n.layers, j) for j in range(n.groups * n.per)}
        for g in n.table:
            if n.layer_of(g) == 1:
                for s in list(n.table[g]):
                    if s in l3 and r.random() < fb_inhib: n.table[g][s] = -abs(n.table[g][s])
    return n


def afterglow(net, pats, nrun=8):
    cells = pk = dr = 0; tot = 0
    for k in range(T.NPAT):
        for j in range(nrun):
            n = copy.deepcopy(net); n.acc = {g: 0 for g in n.acc}; n.rleft = {g: 0 for g in n.rleft}
            for q in n.queues.values(): q.clear()
            n.reset_stats(); ev = B.noisy(pats[k], random.Random(8000 + 10 * k + j)); late = set(); lp = 0
            for t in range(100):
                b = n.pushed; f = n.step(t, ev.get(t, ()))
                if t >= 60: late |= set(f); lp += n.pushed - b
            cells += len(late); pk += lp / 40.0; dr += n.dropped; tot += 1
    return cells / tot, pk / tot, dr / tot


def run_setting(label, seeds, epochs, ceil, fb_inhib=0.0, **kw):
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; res = {"before": [0, 0, 0, 0, 0, 0, 0], "after": [0, 0, 0, 0, 0, 0, 0]}
    for s in seeds:
        net = make(s, fb_inhib, **kw); tg = T.targets(net, s)
        for state in ("before", "after"):
            if state == "after": T.train(net, pats, tg, epochs, ceil=ceil)
            ok, t, hit, mt, ov = T.evaluate(net, pats, tg); c, p, d = afterglow(net, pats)
            for i, v in enumerate((ok, hit, c, p, d, ov, 1)): res[state][i] += v
    n = len(seeds)
    for st in ("before", "after"):
        r = res[st]; print("%-44s %-6s %8.0f%% %8.0f%% %9.1f %9.2f %9.1f %8.2f" % (label, st, 100.0 * r[0] / (800 * n / 5.0 * 1.0) if False else 100.0 * r[0] / (160 * n), 100.0 * r[1] / (100 * n), r[2] / n, r[3] / n, r[4] / n, r[5] / n))


def main(epochs=40, ceil=6, seeds=(1, 2, 3, 4, 5)):
    print("%-44s %-6s %9s %9s %9s %9s %9s %8s" % ("setting (feedback = layer 3 to layer 1, 4 links)", "state", "single", "mixture", "glowcells", "glow pk/c", "dropped", "overlap"))
    run_setting("no feedback", seeds, epochs, ceil)
    run_setting("fb +2, nothing added", seeds, epochs, ceil, fb_k=4, fb_w=2)
    run_setting("fb +2, leak every clock", seeds, epochs, ceil, fb_k=4, fb_w=2, leak_every=1)
    run_setting("fb +2, leak every clock, threshold 2", seeds, epochs, ceil, fb_k=4, fb_w=2, leak_every=1, th=2)
    run_setting("fb +2, 50% of feedback links inhibitory", seeds, epochs, ceil, fb_inhib=0.5, fb_k=4, fb_w=2)
    run_setting("fb +2, 50% inhibitory, refractory 6", seeds, epochs, ceil, fb_inhib=0.5, fb_k=4, fb_w=2, refr=6)
    run_setting("fb +2, leak every 2 clocks, refractory 8", seeds, epochs, ceil, fb_k=4, fb_w=2, leak_every=2, refr=8)


if __name__ == "__main__": main(*(int(a) for a in sys.argv[1:2]))
