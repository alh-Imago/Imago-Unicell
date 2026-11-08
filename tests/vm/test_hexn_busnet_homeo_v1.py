import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_busnet_v1 as B, hexn_busnet_homeo_v1 as H


def test_adaptnet_matches_plain_net_when_thresholds_equal():
    ev = {}
    for i, t in B.pattern(random.Random(3)): ev.setdefault(t, []).append(i)
    a = B.Net(1); b = H.AdaptNet(1); a.run(ev, 100); b.run(ev, 100); assert a.fires == b.fires


def test_per_cell_threshold_is_used():
    n = H.AdaptNet(1, k=3, nin=6, layers=1, groups=1, per=2, leak_every=0); g0, g1 = n.gid(1, 0), n.gid(1, 1)
    n.table[g0] = {0: 2}; n.table[g1] = {0: 2}; n.targets = {0: {(1, 0)}}; n.th_cell[g0] = 2; n.th_cell[g1] = 3
    assert n.step(0, [0]) == [g0]


def test_homeostat_moves_thresholds_toward_target():
    pats = [B.pattern(random.Random(100 + k)) for k in range(8)]; n = H.make(1, 0.5, th=2, k=24, fb_k=8, fb_w=2)
    before = sum(n.th_cell.values()); up, down = H.homeostat(n, pats); assert up > 0 and sum(n.th_cell.values()) > before


def test_threshold_limits():
    pats = [B.pattern(random.Random(100 + k)) for k in range(8)]; n = H.make(1, 0.5, th=2, k=24, fb_k=8, fb_w=2)
    for _ in range(12): H.homeostat(n, pats)
    assert all(H.TH_MIN <= v <= H.TH_MAX for v in n.th_cell.values())
