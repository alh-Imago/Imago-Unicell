"""Parameter check for the planned Kintex memory model: Tier3 with SPS=8 (LUT table -> block RAM -> DDR3 bucket lines of 8 entries).
Level mapping: fast = LUT-RAM (FB bits), 'sdram' = block RAM (RAMB bits), 'card' = DDR3 lines (SB bits, SPS=8).
Prints counters for a random workload. Not a test of RTL; a sizing look only."""
import random, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from hexn_tier_ref_v3 import Tier3
def run(nkeys, gets, KW=24, FB=10, RAMB=14, SB=17, BMB=17, seed=1):
    t = Tier3(KW=KW, FB=FB, BMB=BMB, RAMB=RAMB, SB=SB, SPS=8); r = random.Random(seed)
    keys = r.sample(range(1, 1 << KW), nkeys)
    for i, k in enumerate(keys): t.put(k, i & 0x3FFFF)
    bad = 0
    for _ in range(gets):
        j = r.randrange(nkeys); ok, v = t.get(keys[j])
        if ok and v != (j & 0x3FFFF): bad += 1
    t.flush(); return t.n, bad
for nk, kw in ((100000, 24), (1000000, 26)):
    n, bad = run(nk, 200000, KW=kw, SB=17 if nk == 100000 else 20, BMB=17 if nk == 100000 else 20)
    print(nk, "wrong values:", bad); print(" ", n)
