"""hexn_busnet_gen_v1 (8 Nov 2026): the trained, stabilised bus network on inputs it was not trained on, and on a task where feedback should matter (pattern completion: part of the spikes missing). Alan 19:19 ('yes if you can') following direction doc section 35.
Three networks per wiring seed, all trained with the teacher-target map feedback (40 epochs, ceiling 6): no feedback; plain feedback +2; feedback +2 with 50% inhibitory links and refractory 6.
Tests: (1) recall when the share of spikes dropped is 10, 30, 50, 70 percent (the training used 10 percent); (2) heavier jitter; (3) afterglow on 8 NEW random patterns never seen in training (is the runaway still absent?).
Simulation only. Usage: python3 tools/hexn_busnet_gen_v1.py"""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_fb_v1 as F

SETS = (("no feedback", {}, 0.0), ("feedback +2 plain", dict(fb_k=4, fb_w=2), 0.0), ("feedback +2, 50% inhibitory, refr 6", dict(fb_k=4, fb_w=2, refr=6), 0.5))


def recall(net, pats, tg, drop, jit, ntest=10):
    ok = tot = 0
    for k in range(T.NPAT):
        for j in range(ntest):
            ev = B.noisy(pats[k], random.Random(20000 + 97 * k + j), drop=drop, jit=jit); m = B.map_of(T.fresh_run(net, ev)); sc = [B.jaccard(m, t) for t in tg]
            ok += (max(range(T.NPAT), key=lambda x: sc[x]) == k); tot += 1
    return ok, tot


def main(seeds=(1, 2, 3, 4, 5), epochs=40, ceil=6):
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; new = [B.pattern(random.Random(500 + k)) for k in range(T.NPAT)]
    drops = (0.1, 0.3, 0.5, 0.7); print("%-38s %s %8s %10s %12s" % ("network (trained)", "  ".join("drop%2d%%" % (d * 100) for d in drops), "jitter 8", "glow:known", "glow:unseen"))
    for label, kw, inh in SETS:
        acc = {d: [0, 0] for d in drops}; jt = [0, 0]; gk = gu = 0.0
        for s in seeds:
            net = F.make(s, inh, **kw); tg = T.targets(net, s); T.train(net, pats, tg, epochs, ceil=ceil)
            for d in drops:
                ok, t = recall(net, pats, tg, d, 3); acc[d][0] += ok; acc[d][1] += t
            ok, t = recall(net, pats, tg, 0.1, 8); jt[0] += ok; jt[1] += t
            gk += F.afterglow(net, pats, 3)[0]; gu += F.afterglow(net, new, 3)[0]
        print("%-38s %s %7d%% %10.1f %12.1f" % (label, "  ".join("%6d%%" % (100 * acc[d][0] / acc[d][1]) for d in drops), 100 * jt[0] / jt[1], gk / len(seeds), gu / len(seeds)))


if __name__ == "__main__": main()
