"""Store v4 (rows, presence bits, wider events) must give the same answers as store v3 whenever v3 does not have to evict."""
import os, sys, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import hexn_store_v3 as A, hexn_store_v4 as B
def workload(seed, n, nev):
    r = random.Random(seed); cmds = []; t = 0
    for i in range(n):
        t += r.randint(1, 5); c = r.random()
        if c < 0.03: cmds.append((A.CLR, 0, t, 0))
        elif c < 0.15: cmds.append((A.LOAD, r.randrange(nev), t, 0))
        elif c < 0.30: cmds.append((A.RD, 0, t, 0))
        elif c < 0.40: cmds.append((A.REW, 0, t, r.choice((64, -32, 16, 0))))
        else: cmds.append((A.OBS, r.choice([0, 1, 2, 3, 4]) if r.random() < 0.8 else r.randrange(nev), t, 0))
    return cmds
def same(seed, n=1500, N=3, W=80, glvl=1, nev=8):
    a = A.StoreV3(N=N, W=W, KCAP=1024, CCAP=32, glvl=glvl); b = B.StoreV4(N=N, W=W, CCAP=32, glvl=glvl, EVB=3, ROWS3=1 << 12)
    for cmd, ev, t, r in workload(seed, n, nev):
        x, y = a.step(cmd, ev, t, r), b.step(cmd, ev, t, r)
        if x != y: return False, (cmd, ev, t, x, y)
    assert a.dropk == 0 and b.dropk == 0
    return True, (a.n_known, b.n_known, a.n_cand, b.n_cand)
def test_equivalent_to_v3():
    for seed in range(6):
        for N, W, g in ((3, 80, 1), (2, 40, 2), (3, 200, 3)):
            ok, info = same(seed, N=N, W=W, glvl=g); assert ok, info
            assert info[0] == info[1] and info[2] == info[3]
def test_wide_events_and_presence_saves_reads():
    b = B.StoreV4(N=2, W=1000, EVB=4); r = random.Random(1); t = 0
    for i in range(3000): t += 1; b.step(B.OBS, r.randrange(16) if r.random() < 0.3 else (i % 9), t)
    assert b.n_known > 0 and b.row_words < b.v3_slots * 3 and b.pres_reads > 0
