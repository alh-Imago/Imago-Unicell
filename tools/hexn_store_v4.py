"""hexn_store_v4: bit-true model of the layer 2 store with a ROW-PER-CONTEXT KNOWN TABLE, a PRESENCE-BIT first stage and a WIDER EVENT FIELD (the reference for a future rtl/hexn_store_v4.v). New file; hexn_store_v3.py is untouched and is the reference this model is checked against.
Alan, 27 Oct 2026: "expansion everywhere", recall by direct pattern, plus a small one-bit table checked first that says whether a pattern exists.
What changes against store v3 (the RULES are the same: verdicts, back-off to the longest known context, best = highest seen, goal read = highest value, promotion N in W, REW, queue):
 - EVENT FIELD of EVB bits (v3: 3). Events 0 .. 2^EVB - 1.
 - KNOWN TABLE as rows. A row belongs to one context (the last 1, 2 or 3 events) and holds, for each possible next event, [seen, contra, value]. Row address: context of length 1 and 2 are DIRECT (no hashing, never collide); length 3 is hashed to ROWS3 rows (XOR fold of the 3-event context) and the row keeps the full context as a TAG. A row is read by walking its 2^EVB events (one word per event), so a lookup costs about 2^EVB word reads per context length that is present, instead of walking all KCAP slots.
 - PRESENCE BITS: one bit per context (direct for length 1 and 2; one valid bit per hashed row for length 3) = 'some pattern follows this context'. Read first; a context with a clear bit is not walked at all; if all three are clear the verdict is novel without any row read.
 - CAPACITY: length 1 and 2 hold every possible entry (no eviction). A length-3 promotion into a hashed row that holds a DIFFERENT context replaces it only if that row's total seen is lower than the promotion count; otherwise the promotion is dropped (counted in dropk).
 - CANDIDATE table unchanged (CCAP slots, count and start time, eviction by lowest count then age).
Counters for the cost: `pres_reads` (presence bits read), `row_words` (row words read), and `v3_slots` (what a v3 scan of KCAP slots would have read per scan) so the saving can be shown.
Limits: model only; no RTL yet; timing is counted in word reads, not clocks."""
import collections
CLR, OBS, LOAD, RD, REW = 0, 1, 2, 3, 4
class StoreV4:
    def __init__(s, N=3, W=80, CCAP=32, vshift=3, glvl=1, EVB=4, ROWS3=256, KCAP_V3=128):
        assert 1 <= N <= 15 and 1 <= EVB <= 8
        s.N, s.W, s.CCAP, s.vshift, s.glvl, s.EVB, s.ROWS3, s.KV3 = N, W, CCAP, vshift, glvl, EVB, ROWS3, KCAP_V3
        s.rows = {}      # (j, rowaddr) -> dict(tag=ctx tuple, e={ev: [seen, contra, val]})
        s.c = [None] * CCAP; s.q = collections.deque(maxlen=32); s.hist = []
        s.promoted = s.dropk = s.dropc = 0; s.pres_reads = s.row_words = s.v3_slots = 0
    @property
    def n_known(s): return sum(len(r["e"]) for r in s.rows.values())
    @property
    def n_cand(s): return sum(1 for e in s.c if e)
    def _ctx(s, j): return tuple(s.hist[-j:])
    def _addr(s, j, ctx):
        if j < 3: return sum(x << (s.EVB * i) for i, x in enumerate(ctx))
        v = sum(x << (s.EVB * i) for i, x in enumerate(ctx)); h = 0; w = max(1, (s.ROWS3 - 1).bit_length())
        while v: h ^= v & (s.ROWS3 - 1); v >>= w
        return h
    def _row(s, j, ctx):
        r = s.rows.get((j, s._addr(j, ctx))); return r if r and r["tag"] == ctx and r["e"] else None
    def _scan(s, ev):
        out = {}; s.v3_slots += s.KV3
        for j in (1, 2, 3):
            if len(s.hist) < j: continue
            s.pres_reads += 1; r = s._row(j, s._ctx(j))
            if r is None: continue
            s.row_words += 1 << s.EVB; es = sorted(r["e"].items())
            bi, best = min(es, key=lambda kv: (-kv[1][0], kv[0])); bv = min(es, key=lambda kv: (-kv[1][2], -kv[1][0], kv[0]))
            out[j] = dict(tot=sum(e[0] for _, e in es), bseen=best[0], bev=bi, ex=any(k == ev for k, _ in es), vev=bv[0], vval=bv[1][2])
        return out
    def _put(s, j, ctx, ev, seen):
        """create entry (value 0); returns the entry or None if the promotion is dropped"""
        a = s._addr(j, ctx); r = s.rows.get((j, a))
        if r and r["e"] and r["tag"] != ctx:
            if sum(e[0] for e in r["e"].values()) >= seen: s.dropk += 1; return None
            r = None
        if r is None or not r["e"]: r = s.rows[(j, a)] = dict(tag=ctx, e={})
        r["e"][ev] = [seen, 0, 0]; return r["e"][ev]
    def step(s, cmd, ev=0, t=0, r=0):
        assert 0 <= ev < (1 << s.EVB)
        t &= 0xFFFF; out = dict(verdict=3, vlevel=0, plevel=0, pbest=0, pbest_seen=0, ptotal=0, gbest=0, gval=0)
        if cmd == CLR: s.hist = []; return out
        if cmd == REW:
            for e in s.q:
                if e is not None:
                    d = r - e[2]; e[2] += ((d + (1 << s.vshift) - 1) >> s.vshift) if d > 0 else (d >> s.vshift)
            s.q.clear(); return out
        if cmd in (OBS, LOAD) and not s.hist: s.hist = [ev]; return out
        sc = s._scan(ev); lv = max(sc) if sc else 0
        if lv: out.update(plevel=lv, pbest=sc[lv]["bev"], pbest_seen=sc[lv]["bseen"], ptotal=sc[lv]["tot"])
        gl = max((j for j in sc if j <= s.glvl), default=0)
        if gl: out.update(gbest=sc[gl]["vev"], gval=sc[gl]["vval"])
        out.update(vlevel=lv, verdict=(2 if not lv else (0 if sc[lv]["ex"] else 1)))
        if cmd == RD: return out
        if cmd == OBS and out["verdict"] == 1:
            for e in s._row(lv, s._ctx(lv))["e"].values(): e[1] = min(255, e[1] + 1)
        for j in (1, 2, 3):
            if len(s.hist) < j: continue
            ctx = s._ctx(j); r_ = s._row(j, ctx); hit = r_["e"].get(ev) if r_ else None; key = (j, ctx, ev)
            if hit is not None:
                hit[0] = min(255, hit[0] + 1)
                if cmd == OBS: s.q.append(hit)
                continue
            if cmd == LOAD: s._put(j, ctx, ev, 1); continue
            ch = next((i for i, e in enumerate(s.c) if e and e[0] == key), None)
            exp = ch is not None and ((t - s.c[ch][2]) & 0xFFFF) >= s.W
            cnt = s.c[ch][1] + 1 if (ch is not None and not exp) else 1
            st = s.c[ch][2] if (ch is not None and not exp) else t
            if cnt >= s.N:
                if ch is not None: s.c[ch] = None
                en = s._put(j, ctx, ev, cnt); s.promoted += 1
                if en is not None: s.q.append(en)
            elif ch is not None: s.c[ch][1], s.c[ch][2] = cnt, st
            else:
                cf = next((i for i, e in enumerate(s.c) if e is None), None)
                if cf is not None: s.c[cf] = [key, 1, t]
                else:
                    cv = min(range(len(s.c)), key=lambda i: (s.c[i][1], -((t - s.c[i][2]) & 0xFFFF), i)); s.c[cv] = [key, 1, t]; s.dropc += 1
        s.hist = (s.hist + [ev])[-3:]
        return out
