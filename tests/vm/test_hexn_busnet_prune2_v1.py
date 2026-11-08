import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_busnet_v1 as B, hexn_busnet_fb_v1 as F, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q


def test_prune_by_weight_keeps_largest():
    n = F.make(1, 0.5, fb_k=4, fb_w=2); before = {g: dict(t) for g, t in n.table.items()}; Q.prune_by(n, P.LEAN_KEEP, "weight")
    for g, t in n.table.items():
        kp = P.LEAN_KEEP[n.layer_of(g)]; assert len(t) == min(kp, len(before[g]))
        cut = sorted((abs(w) for w in before[g].values()), reverse=True)[len(t) - 1]
        assert all(abs(w) >= cut for w in t.values())


def test_prune_by_use_prefers_used():
    n = F.make(1, 0.5, fb_k=4, fb_w=2); use = {g: {s: (1 if i < 3 else 0) for i, s in enumerate(n.table[g])} for g in n.table}; first = {g: list(n.table[g])[:3] for g in n.table}
    Q.prune_by(n, {1: 3, 2: 3, 3: 3}, "use", use)
    assert all(set(n.table[g]) == set(first[g]) for g in n.table)


def test_stats_shapes():
    n = F.make(1, 0.5, k=10); pats = [B.pattern(random.Random(100 + k)) for k in range(8)]; z, h = Q.stats(n, pats, __import__("hexn_busnet_train_v1").targets(n)); assert z >= 0 and 0 <= h <= 1
