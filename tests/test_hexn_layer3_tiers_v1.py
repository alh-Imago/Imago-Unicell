"""Tests for the three-tier long-term store model (tools/hexn_layer3_tiers_v1.py): moving entries down the tiers loses no accuracy against the unbounded store; the presence tests order as exact <= hashed bitmap <= none; skip mode looks up the slow tiers far less. Python only."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import hexn_layer3_forget_v1 as F
import hexn_layer3_tiers_v1 as T
def test_tiers():
    ev, rare = F.world2(800)
    ref = F.run(ev, rare, None, "unbounded")
    ms, mom, a, b = T.run(ev, rare, 120, 300)
    assert round(a[1] / a[0], 3) == ref["all_top1"]
    assert ms.sd_writes > 0 and ms.sd_true <= ms.lookups
    for B in T.BITS: assert ms.sd_true <= ms.sd_pos[B] <= ms.lookups and ms.sd_fp[B] == ms.sd_pos[B] - ms.sd_true
    ms2, _, a2, _ = T.run(ev, rare, 120, 300, skip=True)
    assert ms2.lookups < ms.lookups * 0.6
    assert a2[1] / a2[0] > 0.8 * (a[1] / a[0])
