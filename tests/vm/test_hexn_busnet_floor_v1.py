import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_busnet_floor_v1 as F


def test_floor_clamps_accumulators():
    n = F.ClampNet(1, floor=-3, k=3, nin=6, layers=1, groups=1, per=2, leak_every=0); g = n.gid(1, 0); n.table[g] = {0: -2}; n.targets = {0: {(1, 0)}}
    for t in range(5): n.step(t, [0])
    assert n.acc[g] == -3
