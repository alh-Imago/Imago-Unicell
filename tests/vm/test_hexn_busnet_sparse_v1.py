import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_busnet_v1 as B, hexn_busnet_sparse_v1 as S


def _net():
    r = random.Random(3); ev = {}
    for i, t in B.pattern(r): ev.setdefault(t, []).append(i)
    return B.trial(1, ev)[0]


def test_early_map_is_smaller_and_inside_all():
    n = _net(); a = S.sparse_map(n, "all"); e = S.sparse_map(n, "early", 12)
    assert len(e) == 12 and e <= a


def test_strong_inside_all():
    n = _net(); assert S.sparse_map(n, "strong") <= S.sparse_map(n, "all")


def test_idf_prefers_unique_cells():
    s = [{1, 2, 3}, {3, 4, 5}]
    sc = S.scores({1, 2}, s, "idf"); assert sc[0] > sc[1]
