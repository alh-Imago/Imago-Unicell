"""hexn_busnet_homeoprune_v1 (8 Nov 2026): pruning (by weight size) of the dense network with the self-adjusting threshold (hexn_busnet_homeo_v1), against the same without homeostasis after pruning and against the lean net. Alan 20:32 ('yes that looks good') following direction doc section 39. Earlier tools untouched.
Dense net (24 sources + 8 feedback links on layer 1) trained 40 epochs with homeostasis, pruned to the lean connection count (14 / 10 / 10 per cell), then retrained 10 epochs (a) with homeostasis still running, (b) with thresholds frozen at their trained values. Lean net trained 50 epochs with homeostasis. 5 seeds. Simulation only.
Usage: python3 tools/hexn_busnet_homeoprune_v1.py START_TH"""
import random, copy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_gen_v1 as G, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H


def main(th, seeds=(1, 2, 3, 4, 5), epochs=40, ft=10):
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; agg = {}
    for s in seeds:
        rich = H.make(s, 0.5, fb_k=8, fb_w=2, k=24, refr=6, th=th); lean = H.make(s, 0.5, fb_k=4, fb_w=2, k=10, refr=6, th=th); tg2 = T.targets(rich, s)
        t1r = P.layer1_targets(rich, pats); t1l = P.layer1_targets(lean, pats)
        H.train(rich, pats, tg2, t1r, epochs, homeo=True); unp = copy.deepcopy(rich)
        Q.prune_by(rich, P.LEAN_KEEP, "weight"); pa = copy.deepcopy(rich); pb = copy.deepcopy(rich)
        H.train(pa, pats, tg2, t1r, ft, homeo=True); H.train(pb, pats, tg2, t1r, ft, homeo=False)
        H.train(lean, pats, tg2, t1l, epochs + ft, homeo=True)
        for name, net in (("dense, trained, not pruned", unp), ("dense, pruned, retrained WITH homeostasis", pa), ("dense, pruned, retrained thresholds frozen", pb), ("lean, homeostatic, same epochs", lean)):
            lab, c, ok, tot, pk, dr, gl = P.report(name, net, pats, tg2); a = agg.setdefault(lab, [0, [0] * 4, [0] * 4, 0, 0, 0, 0])
            a[0] += c; a[3] += dr; a[4] += 1; m = H.mean_th(net); a[5] += m[1]; a[6] += m[2]
            for i in range(4): a[1][i] += ok[i]; a[2][i] += tot[i]
    print("start threshold %d" % th)
    for lab, a in agg.items(): print("%-44s %5d  %s  dropped %6.1f  th L1 %.1f L2 %.1f" % (lab, a[0] / a[4], "  ".join("%3d%%" % (100 * a[1][i] / a[2][i]) for i in range(4)), a[3] / a[4], a[5] / a[4], a[6] / a[4]))


if __name__ == "__main__": main(int(sys.argv[1]))
