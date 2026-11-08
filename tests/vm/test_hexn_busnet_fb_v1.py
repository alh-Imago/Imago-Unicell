import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_busnet_v1 as B, hexn_busnet_fb_v1 as F


def test_fb_inhib_flips_only_feedback_links():
    a = F.make(1, 0.0, fb_k=4, fb_w=2); b = F.make(1, 1.0, fb_k=4, fb_w=2); l3 = {a.gid(3, j) for j in range(64)}
    for g in a.table:
        for s, w in a.table[g].items():
            if a.layer_of(g) == 1 and s in l3: assert b.table[g][s] == -abs(w)
            else: assert b.table[g][s] == w


def test_afterglow_zero_without_feedback():
    pats = [B.pattern(random.Random(100 + k)) for k in range(8)]; c, p, d = F.afterglow(B.Net(1), pats, nrun=1); assert c == 0 and p == 0
