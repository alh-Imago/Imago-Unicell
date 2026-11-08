import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_busnet_v1 as B, hexn_busnet_homeo_v1 as H, hexn_busnet_shape_v1 as S


def test_net_shape_options_keep_64_cells_per_layer():
    for g, p in ((4, 16), (8, 8), (16, 4)):
        n = H.make(1, 0.5, groups=g, per=p, k=10, fb_k=4, fb_w=2); assert sum(1 for c in n.table if n.layer_of(c) == 2) == 64 and len({b for b in n.queues if b[0] == 2}) == g


def test_delays_are_finite_for_active_net():
    pats = [B.pattern(random.Random(100 + k)) for k in range(8)]; n = H.make(1, 0.5, k=24, fb_k=8, fb_w=2, th=4); a, b = S.delays(n, pats, nrun=1); assert a == a and b == b and b >= 0
