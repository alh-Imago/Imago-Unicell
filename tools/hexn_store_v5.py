"""hexn_store_v5: bit-true model of the layer 2 store with an ADDRESS INDEX and a DENSE ENTRY HEAP (the reference for a future rtl/hexn_store_v5.v). New file; hexn_store_v3.py (the rules) and hexn_store_v4.py (row-per-context) are untouched.
Alan, 27 Oct 2026: the quick lookup becomes a RAM ADDRESS table (the tokenisation); only KNOWN values are stored; a new one is added to both the table and the main RAM store.
Layout:
 INDEX: 2^IB slots. A slot is empty, or holds a context TOKEN (the context length j and the last j events, kept in full as the tag) and the address of that context's first heap row. A lookup hashes the token (XOR fold) to a slot and probes up to P consecutive slots; the first empty slot ends the probe (nothing is ever deleted, so this is safe). A token that is not in the index is NOT KNOWN: the index is the presence table, and it costs one or two index reads, not a walk of the store.
 HEAP: HROWS rows of R entry slots, each (event, seen, contra, value); a full row links to a next row. Rows are handed out in order (a free pointer), so only contexts that really occur use memory; there are no empty rows for contexts that never happen.
 Rules (verdicts, back-off, best, goal read, N in W promotion, REW and queue, candidate table) are those of store v3. If the index or the heap is full, a new known entry is dropped and counted in dropk.
Counters: idx_reads (index slots read), heap_reads (heap rows read), and v3_slots (the slots a v3 scan would read). `mem_bits()` gives the RAM the layout needs for its settings.
Limits: model only; timing is counted in memory reads; the hash is a first choice."""
import collections
CLR, OBS, LOAD, RD, REW = 0, 1, 2, 3, 4
class StoreV5:
    def __init__(s, N=3, W=80, CCAP=32, vshift=3, glvl=1, EVB=4, IB=11, R=4, HROWS=1024, P=4, KCAP_V3=128):
        assert 1 <= N <= 15 and 1 <= EVB <= 8
        s.N, s.W, s.CCAP, s.vshift, s.glvl, s.EVB, s.IB, s.R, s.HROWS, s.P, s.KV3 = N, W, CCAP, vshift, glvl, EVB, IB, R, HROWS, P, KCAP_V3
        s.index = [None] * (1 << IB); s.heap = []      # heap row: dict(slots=[(ev, entry)...], next=None or row number)
        s.c = [None] * CCAP; s.q = collections.deque(maxlen=32); s.hist = []
        s.promoted = s.dropk = s.dropc = 0; s.idx_reads = s.heap_reads = s.v3_slots = 0
    @property
    def n_known(s): return sum(len(r["slots"]) for r in s.heap)
    @property
    def n_cand(s): return sum(1 for e in s.c if e)
    def mem_bits(s):
        pw = max(1, (s.HROWS - 1).bit_length()); tag = 2 + s.EVB * 3; idx = (1 << s.IB) * (1 + tag + pw)
        row = s.HROWS * (s.R * (1 + s.EVB + 8 + 8 + 8) + 1 + pw); return dict(index=idx, heap=row, total=idx + row)
    def _ctx(s, j): return tuple(s.hist[-j:])
    def _h(s, j, ctx):
        """token = (j, ctx) packed, mixed with three shifts and XORs (no multiplier), then XOR-folded to IB bits. A plain fold alone clusters (47 drops in 1,500 games at 2,048 slots); this mix gave none."""
        v = j
        for x in ctx: v = (v << s.EVB) | x
        v ^= v >> 5; v ^= (v << 7) & 0xFFFFFF; v ^= v >> 11
        h = 0
        while v: h ^= v & ((1 << s.IB) - 1); v >>= s.IB
        return h
    def _probe(s, j, ctx):
        """returns (slot or None, free slot or None); counts index reads"""
        h = s._h(j, ctx); mask = (1 << s.IB) - 1
        for p in range(s.P):
            sl = (h + p) & mask; s.idx_reads += 1; e = s.index[sl]
            if e is None: return None, sl
            if e["tag"] == (j, ctx): return sl, None
        return None, None
    def _entries(s, j, ctx):
        sl, _ = s._probe(j, ctx)
        if sl is None: return None
        out = []; rn = s.index[sl]["row"]
        while rn is not None: s.heap_reads += 1; out += s.heap[rn]["slots"]; rn = s.heap[rn]["next"]
        return out
    def _put(s, j, ctx, ev, seen):
        sl, free = s._probe(j, ctx)
        if sl is None:
            if free is None or len(s.heap) >= s.HROWS: s.dropk += 1; return None
            s.heap.append(dict(slots=[], next=None)); s.index[free] = dict(tag=(j, ctx), row=len(s.heap) - 1); sl = free
        rn = s.index[sl]["row"]
        while True:
            row = s.heap[rn]
            if len(row["slots"]) < s.R: break
            if row["next"] is None:
                if len(s.heap) >= s.HROWS: s.dropk += 1; return None
                s.heap.append(dict(slots=[], next=None)); row["next"] = len(s.heap) - 1
            rn = row["next"]
        en = [seen, 0, 0]; row["slots"].append((ev, en)); return en
    def _scan(s, ev):
        out = {}; s.v3_slots += s.KV3
        for j in (1, 2, 3):
            if len(s.hist) < j: continue
            es = s._entries(j, s._ctx(j))
            if not es: continue
            es = sorted(es, key=lambda x: x[0]); bi, best = min(es, key=lambda kv: (-kv[1][0], kv[0])); bv = min(es, key=lambda kv: (-kv[1][2], -kv[1][0], kv[0]))
            out[j] = dict(tot=sum(e[0] for _, e in es), bseen=best[0], bev=bi, ex=any(k == ev for k, _ in es), vev=bv[0], vval=bv[1][2])
        return out
    def step(s, cmd, ev=0, t=0, r=0):
        assert 0 <= ev < (1 << s.EVB)
        t &= 0xFFFF; out = dict(verdict=3, vlevel=0, plevel=0, pbest=0, pbest_seen=0, ptotal=0, gbest=0, gval=0)
        if cmd == CLR: s.hist = []; return out
        if cmd == REW:
            for e in s.q:
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
            for _, e in s._entries(lv, s._ctx(lv)): e[1] = min(255, e[1] + 1)
        for j in (1, 2, 3):
            if len(s.hist) < j: continue
            ctx = s._ctx(j); es = s._entries(j, ctx); hit = next((e for k, e in (es or []) if k == ev), None); key = (j, ctx, ev)
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
