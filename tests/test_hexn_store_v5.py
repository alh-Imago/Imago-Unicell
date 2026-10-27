"""Store v5 (address index + dense heap) must give the same answers as store v3 whenever neither runs out of room."""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import hexn_store_v3 as A, hexn_store_v5 as B
from test_hexn_store_v4 import workload
def same(seed, N, W, g, n=1500):
    a = A.StoreV3(N=N, W=W, KCAP=1024, CCAP=32, glvl=g); b = B.StoreV5(N=N, W=W, CCAP=32, glvl=g, EVB=3, IB=13, R=2, HROWS=4096, P=16)
    for cmd, ev, t, r in workload(seed, n, 8):
        x, y = a.step(cmd, ev, t, r), b.step(cmd, ev, t, r)
        if x != y: return False, (cmd, ev, t, x, y)
    assert a.dropk == 0 and b.dropk == 0 and a.n_known == b.n_known and a.n_cand == b.n_cand
    return True, None
def test_equivalent_to_v3():
    for seed in range(5):
        for N, W, g in ((3, 80, 1), (2, 40, 2), (3, 200, 3)):
            ok, info = same(seed, N, W, g); assert ok, info
def test_full_index_drops_and_counts():
    b = B.StoreV5(N=1, W=100, EVB=4, IB=3, R=2, HROWS=4, P=2); r = random.Random(0)
    for i in range(300): b.step(B.OBS, r.randrange(16), i)
    assert b.dropk > 0 and len(b.heap) <= 4
