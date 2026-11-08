"""hexn_busnet_prune2_v1 (8 Nov 2026): why the rich net trained worse, and a gentler dense start. Alan 20:05 ('yes if you can') following direction doc section 37. Earlier tools untouched.
Diagnosis (run 'diag'): the rich net (24 sources per cell) starts with about 120 of 128 layer 2/3 cells firing, so the training rule (raise missed target cells, lower every wrong firer) is dominated by 'lower': ~110 wrong firers against ~10 missed. It over-suppresses (maps of 9 to 11 cells) and the share of target cells it actually hits falls from 0.9 to 0.3.
Gentler dense start: raise the rich net's firing threshold so its starting activity is closer to the lean net's (thresholds 3, 5, 7). After training and pruning the threshold is set back to the lean value (3), like synaptic scaling after pruning. Prune criteria: 'use' (counts from the correct map, as before) or 'weight' (largest |weight| kept).
Compared with the lean net trained for the same total epochs. Simulation only.
Usage: python3 tools/hexn_busnet_prune2_v1.py diag | run TH CRITERION"""
import random, copy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_fb_v1 as F, hexn_busnet_gen_v1 as G, hexn_busnet_prune_v1 as P


def prune_by(net, keep, criterion, use=None):
    """keep: {layer: n}; criterion 'use' needs the useful counts, 'weight' keeps the largest |weight|"""
    for g in net.table:
        kp = keep[net.layer_of(g)]
        key = (lambda s: (-use[g][s], -abs(net.table[g][s]), s)) if criterion == "use" else (lambda s: (-abs(net.table[g][s]), s))
        net.table[g] = {s: net.table[g][s] for s in sorted(net.table[g], key=key)[:kp]}
    P.rebuild_targets(net)


def stats(net, pats, tg2):
    sz = []; hit = []
    for k in range(T.NPAT):
        for j in range(3):
            n = T.fresh_run(net, B.noisy(pats[k], random.Random(40 + k * 7 + j))); m = B.map_of(n); sz.append(len(m)); hit.append(len(m & tg2[k]) / 10.0)
    return sum(sz) / len(sz), sum(hit) / len(hit)


def diag(seeds=(1, 2, 3)):
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]
    print("%-22s %-8s %12s %16s" % ("net", "state", "map size 2+3", "target cells hit"))
    for lab, kw in (("rich th3", dict(fb_k=8, k=24)), ("rich th5", dict(fb_k=8, k=24, th=5)), ("rich th7", dict(fb_k=8, k=24, th=7)), ("lean th3", dict(fb_k=4, k=10))):
        a = {"start": [0, 0], "after 40": [0, 0]}
        for s in seeds:
            net = F.make(s, 0.5, fb_w=2, refr=6, **kw); tg2 = T.targets(net, s); t1 = P.layer1_targets(net, pats)
            for st in a:
                if st == "after 40": P.train(net, pats, tg2, t1, 40)
                z, h = stats(net, pats, tg2); a[st][0] += z; a[st][1] += h
        for st, v in a.items(): print("%-22s %-8s %12.1f %16.2f" % (lab, st, v[0] / len(seeds), v[1] / len(seeds)))


def run(th, criterion, seeds=(1, 2, 3, 4, 5), epochs=40, ft=10, post_th=3, lean_th=3):
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; agg = {}
    for s in seeds:
        rich = F.make(s, 0.5, fb_k=8, fb_w=2, k=24, refr=6, th=th); lean = F.make(s, 0.5, fb_k=4, fb_w=2, k=10, refr=6, th=lean_th); tg2 = T.targets(rich, s)
        t1r = P.layer1_targets(rich, pats); t1l = P.layer1_targets(lean, pats)
        P.train(rich, pats, tg2, t1r, epochs); unp = copy.deepcopy(rich)
        use = P.useful_counts(rich, pats, tg2, t1r) if criterion == "use" else None
        prune_by(rich, P.LEAN_KEEP, criterion, use); rich.th = post_th; w0 = copy.deepcopy(rich.table); P.train(rich, pats, tg2, t1r, ft, w0=w0, seed=78)
        P.train(lean, pats, tg2, t1l, epochs + ft)
        for name, net in (("rich th%d trained, not pruned" % th, unp), ("rich th%d pruned by %s, th then %d" % (th, criterion, post_th), rich), ("lean th%d same epochs" % lean_th, lean)):
            lab, c, ok, tot, pk, dr, gl = P.report(name, net, pats, tg2); a = agg.setdefault(lab, [0, [0] * 4, [0] * 4, 0, 0])
            a[0] += c; a[3] += dr; a[4] += 1
            for i in range(4): a[1][i] += ok[i]; a[2][i] += tot[i]
    for lab, a in agg.items(): print("%-44s %6d  %s  dropped %5.1f" % (lab, a[0] / a[4], "  ".join("%3d%%" % (100 * a[1][i] / a[2][i]) for i in range(4)), a[3] / a[4]))


if __name__ == "__main__":
    if sys.argv[1] == "diag": diag()
    else: run(int(sys.argv[2]), sys.argv[3], post_th=int(sys.argv[4]) if len(sys.argv) > 4 else 3, lean_th=int(sys.argv[5]) if len(sys.argv) > 5 else 3)
