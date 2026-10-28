"""Bit-true reference of rtl/hexn_tier_v1.v (same hashes, same probe order, same counters). Python model of the algorithm only; the RTL is checked against it by tests/test_hexn_tier_v1.py.
Usage as a library: Tier(KW, FB, BMB, RAMB, P) with .put(key, val) and .get(key) -> (found, val); counters in .n (dict)."""
M = 0xFFFFFFFF
def hash32(x):
    m = (x * 0x9E3779B1) & M; m ^= m >> 15; m = (m * 0x85EBCA6B) & M; return m ^ (m >> 13)
class Tier:
    def __init__(s, KW=24, FB=10, BMB=14, RAMB=12, P=8):
        s.KW, s.FB, s.BMB, s.RAMB, s.P = KW, FB, BMB, RAMB, P
        s.fast = {}; s.bm = set(); s.sd = {}
        s.n = dict(fast_put=0, sd_put=0, overflow=0, fast_hit=0, skip=0, sd_get=0, fp=0, sd_rd=0, sd_wr=0, found=0, notfound=0)
    def _h(s, k):
        return hash32(k) & ((1 << s.FB) - 1), hash32((k + 0x1234) & M) & ((1 << s.RAMB) - 1), hash32((k + 0x5678) & M) & ((1 << s.BMB) - 1)
    def _probe(s, k, slot0):
        """Returns (slot, state) with state 'same', 'empty' or 'full'; counts one SDRAM read per slot looked at."""
        slot = slot0
        for p in range(s.P):
            s.n["sd_rd"] += 1
            t = s.sd.get(slot)
            if t is None: return slot, "empty"
            if t[0] == k: return slot, "same"
            slot = (slot + 1) & ((1 << s.RAMB) - 1)
        return slot, "full"
    def put(s, k, v):
        hf, hs, hb = s._h(k); r = s.fast.get(hf)
        if r is None or r[0] == k:
            s.fast[hf] = (k, v); s.n["fast_put"] += 1; return
        s.bm.add(hb); s.n["sd_put"] += 1
        slot, st = s._probe(k, hs)
        if st == "full": s.n["overflow"] += 1; return
        s.sd[slot] = (k, v); s.n["sd_wr"] += 2
    def get(s, k):
        hf, hs, hb = s._h(k); r = s.fast.get(hf)
        if r is not None and r[0] == k:
            s.n["fast_hit"] += 1; s.n["found"] += 1; return True, r[1]
        if hb not in s.bm:
            s.n["skip"] += 1; s.n["notfound"] += 1; return False, 0
        s.n["sd_get"] += 1
        slot, st = s._probe(k, hs)
        if st == "same":
            s.n["sd_rd"] += 1; s.n["found"] += 1; return True, s.sd[slot][1]
        s.n["fp"] += 1; s.n["notfound"] += 1; return False, 0
