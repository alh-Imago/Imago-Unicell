"""hexn_ctxstore_v1: bit-true Python model of the SDRAM-backed CONTEXT STORE for layer 3 (the hardware plan from the tiers cost model; the RTL rtl/hexn_ctxstore_v1.v must match this file exactly, including its counters). Alan, 27 Oct 2026: check the accuracy, then build the hardware store.
What it is: a table from a 31-bit context key to up to SLOTS followers, each a (follower id 8 bits, weight 8 bits) pair. ALL contexts live in SDRAM (hash table, 4 probes, linear); a small direct-mapped write-through CACHE (CACHE_BITS) sits on chip; a one-bit-per-hash PRESENCE FILTER (never cleared; nothing is ever deleted) lets a lookup of an unknown context skip the SDRAM.
Record in SDRAM = 8 words of 32 bits at word address bucket*8: word 0 = {1, key[30:0]} (bit 31 = occupied), word 1+j//2 = slot j in bits [16*(j%2)+15 : 16*(j%2)] as {fid, weight} (weight 0 = empty slot). SLOTS = 14 fills the 8 words.
Hash: P = (key * 0x9E3779B1) mod 2^32; bucket = P[31:32-BB]; cache index = P[31:32-CB]; filter index = P[23:8] (16 bits). Probe i uses bucket+i mod 2^BB.
Operations: RD(key) -> (found, slots) ; OBS(key, fid): if a slot has fid, weight+1 (if it was 255, first every weight w -> (w+1)>>1); else the first empty slot takes (fid, 1); else the lowest-weight slot (lowest index on a tie) is replaced by (fid, 1) (counted slot_evict). A new context is created in the first empty bucket of its probe sequence; if 4 buckets are taken by other keys the OBS is dropped (counted overflow).
Counters (all must match the RTL): ops, cache_hit, filter_skip (a RD or OBS that missed the cache and found filter bit 0), sd_probe (word-0 reads during probing), sd_rd (all SDRAM word reads), sd_wr (SDRAM word writes), created, slot_evict, overflow.
Limits: weights do not fade with time (the earlier models use a time-faded weight), a context holds at most SLOTS followers, collisions beyond 4 probes drop, no deletion, no card tier."""
import zlib
MASK32 = 0xFFFFFFFF
class CtxStore:
    def __init__(s, bb=16, cb=8, slots=14):
        s.bb, s.cb, s.S = bb, cb, slots
        s.mem = {}                       # bucket -> (key, [ (fid,w) ] * S)
        s.cache = {}                     # index -> (key, bucket, slots)
        s.filt = set()
        s.c = dict(ops=0, cache_hit=0, filter_skip=0, sd_probe=0, sd_rd=0, sd_wr=0, created=0, slot_evict=0, overflow=0)
    def hashes(s, key):
        P = (key * 0x9E3779B1) & MASK32
        return P >> (32 - s.bb), P >> (32 - s.cb), (P >> 8) & 0xFFFF
    def _find(s, key, bkt):
        """probe from bkt; returns ('hit', bucket) / ('empty', bucket) / ('full', None); counts probes and reads"""
        for i in range(4):
            b = (bkt + i) & ((1 << s.bb) - 1); s.c["sd_probe"] += 1; s.c["sd_rd"] += 1
            r = s.mem.get(b)
            if r is None: return "empty", b
            if r[0] == key: s.c["sd_rd"] += 7; return "hit", b
        return "full", None
    def _locate(s, key):
        """returns (state, bucket, slots) with state 'found' / 'absent_at' (bucket empty) / 'absent_full' / 'absent_skip' """
        s.c["ops"] += 1; bkt, ci, fi = s.hashes(key)
        ln = s.cache.get(ci)
        if ln is not None and ln[0] == key: s.c["cache_hit"] += 1; return "found", ln[1], list(ln[2])
        skip = fi not in s.filt
        if skip: s.c["filter_skip"] += 1
        st, b = s._find(key, bkt)
        if st == "hit":
            sl = list(s.mem[b][1]); s.cache[ci] = (key, b, list(sl)); return "found", b, sl
        return ("absent_at" if st == "empty" else "absent_full"), b, None
    def rd(s, key):
        st, b, sl = s._locate(key)
        return (1, sl) if st == "found" else (0, [(0, 0)] * s.S)
    def obs(s, key, fid):
        st, b, sl = s._locate(key)
        if st == "absent_full": s.c["overflow"] += 1; return
        if st == "absent_at": sl = [(0, 0)] * s.S; s.c["created"] += 1; s.filt.add(s.hashes(key)[2])
        for j, (f, w) in enumerate(sl):
            if w and f == fid:
                if w == 255: sl = [((ff, (ww + 1) >> 1) if ww else (ff, 0)) for ff, ww in sl]; w = sl[j][1]
                sl[j] = (fid, w + 1); break
        else:
            e = [j for j, (f, w) in enumerate(sl) if w == 0]
            if e: sl[e[0]] = (fid, 1)
            else: j = min(range(s.S), key=lambda j: (sl[j][1], j)); sl[j] = (fid, 1); s.c["slot_evict"] += 1
        ci = s.hashes(key)[1]; s.cache[ci] = (key, b, list(sl)); s.mem[b] = (key, list(sl)); s.c["sd_wr"] += 8
