import os, sys, random, copy
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_busnet_v1 as B, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H


def test_pruning_keeps_per_cell_thresholds_and_trains_without_homeostasis():
    n = H.make(1, 0.5, fb_k=8, fb_w=2, k=24, th=4); n.th_cell[next(iter(n.th_cell))] = 6; before = dict(n.th_cell)
    Q.prune_by(n, P.LEAN_KEEP, "weight"); assert n.th_cell == before and all(len(t) <= 14 for t in n.table.values())
    pats = [B.pattern(random.Random(100 + k)) for k in range(8)]; tg2 = __import__("hexn_busnet_train_v1").targets(n); t1 = P.layer1_targets(n, pats)
    H.train(n, pats, tg2, t1, 1, homeo=False); assert n.th_cell == before
