import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_gen_v1 as G


def test_recall_counts_and_totals():
    n = B.Net(1); pats = [B.pattern(random.Random(100 + k)) for k in range(8)]; ok, t = G.recall(n, pats, T.targets(n), 0.1, 3, ntest=2)
    assert t == 16 and 0 <= ok <= 16


def test_higher_drop_removes_more_events():
    p = B.pattern(random.Random(100)); a = B.noisy(p, random.Random(1), drop=0.0, extra=0); b = B.noisy(p, random.Random(1), drop=0.8, extra=0)
    assert sum(len(v) for v in b.values()) < sum(len(v) for v in a.values())
