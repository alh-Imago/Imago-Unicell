import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_busnet_homeo_v1 as H, hexn_busnet_traffic_v1 as TR


def test_target_rate_is_a_module_setting_and_lower_rate_raises_thresholds():
    import random, hexn_busnet_v1 as B
    pats = [B.pattern(random.Random(100 + k)) for k in range(8)]; old = H.TARGET[1]
    try:
        a = H.make(1, 0.5, th=3, k=10, fb_k=4, fb_w=2); b = H.make(1, 0.5, th=3, k=10, fb_k=4, fb_w=2)
        H.TARGET[1] = 0.40; H.homeostat(a, pats); H.TARGET[1] = 0.05; H.homeostat(b, pats)
        s = lambda n: sum(v for g, v in n.th_cell.items() if n.layer_of(g) == 1); assert s(b) >= s(a)
    finally: H.TARGET[1] = old
