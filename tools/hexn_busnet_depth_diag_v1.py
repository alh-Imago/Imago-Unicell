"""hexn_busnet_depth_diag_v1 (9 Nov 2026): how small does the firing become with depth, and does the feedback loop change it? Alan 17:07 ('look and see how small the firing becomes first'). Direction doc section 51. Measurement only.
5 layers of 4 buses x 16 cells (patched as in hexn_busnet_layers5_v1). For feedback ON (last layer to layer 1, half inhibitory, as before) and OFF (no feedback links), at three stages: untrained / trained dense (40 epochs, homeostat) / pruned to 10 sources per cell and retrained (10 epochs): the average number of cells fired per layer in one clean run of each pattern, the share of runs in which a layer stayed completely silent, and the average threshold per layer.
Usage: python3 tools/hexn_busnet_depth_diag_v1.py [LAYERS]"""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H, hexn_busnet_layers5_v1 as L5


def measure(net, pats, L):
    fires = {l: 0.0 for l in range(1, L + 1)}; silent = {l: 0 for l in range(1, L + 1)}; n = 0
    for k in range(T.NPAT):
        for j in range(2):
            run = T.fresh_run(net, B.noisy(pats[k], random.Random(31337 + 5 * k + j), drop=0.0, jit=0)); n += 1
            for l in range(1, L + 1):
                c = sum(1 for g in run.fires if run.layer_of(g) == l); fires[l] += c; silent[l] += (c == 0)
    th = {l: sum(net.th_cell[g] for g in net.table if net.layer_of(g) == l) / (net.groups * net.per) for l in range(1, L + 1)}
    return {l: fires[l] / n for l in fires}, {l: 100.0 * silent[l] / n for l in silent}, th


def main(L=5, groups=4, per=16, seeds=(1, 2, 3), epochs=40, ft=10, th0=5):
    L5.patch(L); pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]
    for fb in (True, False):
        acc = {}
        for s in seeds:
            kw = dict(fb_k=8, fb_w=2) if fb else dict(fb_k=0, fb_w=0)
            net = H.make(s, 0.5 if fb else 0, k=24, refr=6, th=th0, groups=groups, per=per, layers=L, **kw); tg = T.targets(net, s); t1 = P.layer1_targets(net, pats)
            def rec(stage):
                f, z, t = measure(net, pats, L); a = acc.setdefault(stage, [{l: 0.0 for l in f}, {l: 0.0 for l in f}, {l: 0.0 for l in f}])
                for l in f: a[0][l] += f[l] / len(seeds); a[1][l] += z[l] / len(seeds); a[2][l] += t[l] / len(seeds)
            rec("untrained"); H.train(net, pats, tg, t1, epochs, homeo=True); rec("trained dense"); Q.prune_by(net, P.LEAN_KEEP, "weight"); H.train(net, pats, tg, t1, ft, homeo=True); rec("pruned, retrained")
        print("\nfeedback %s; %d seeds; average over clean runs of 8 patterns" % ("ON" if fb else "OFF", len(seeds)))
        print("  %-18s %s" % ("stage", "   ".join("layer %d" % l for l in range(1, L + 1))))
        for stage, (f, z, t) in acc.items():
            print("  %-18s fired      %s" % (stage, "  ".join("%7.1f" % f[l] for l in f)))
            print("  %-18s silent %%   %s" % ("", "  ".join("%7.0f" % z[l] for l in z)))
            print("  %-18s mean thr   %s" % ("", "  ".join("%7.1f" % t[l] for l in t)))


if __name__ == "__main__":
    a = sys.argv; main(*(int(x) for x in a[1:2]))
