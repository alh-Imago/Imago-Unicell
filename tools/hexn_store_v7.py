"""hexn_store_v7: bit-true Python REFERENCE of the layer 2/3 store with a VARIABLE LOOK-BACK and LRU eviction of whole contexts (PLAN: docs/hex-n/STORE_V7_LOOKBACK_v1.md; new file 31 Oct 2026; hexn_store_v5.py untouched).
It models the behaviour of rtl/hexn_store_v6.v (index with stamp and dead bit, dense heap, free list of rows, eviction of the least recently used context when no row is free, candidate table, reward queue) and adds the two numbers of the plan: LMAX (history kept, build time) and `lookback` (levels used, a setting, default 3, capped at LMAX). With LMAX = 3 and lookback = 3 it must equal rtl/hexn_store_v6.v command for command: tools/hexn_store_v7_check_v1.py runs both.
Rules copied from the RTL (not from v5.py where they differ): stamp = (t >> 4) & 0xFF written on every index hit; age = (now - stamp) mod 256; the victim is the live slot with the greatest age (lowest slot on a tie) whose token is not the one being inserted; the victim's slot becomes DEAD (probes pass over it, an insert may reuse it), its entries are cleared and its rows go to the free list in chain order; the insert is retried once; a failed retry or no victim counts dropk; a probe window with no empty or dead slot counts dropk with no eviction. n_known counts inserts and is NOT reduced by an eviction (as in the RTL); n_evict counts evictions. A pending REW address that points into an evicted row hits whatever lives there now if valid (as in the RTL).
`push` (optional argument of step): the value pushed into the history after the command (default: the event). Layer 3 uses it to push a SNAPSHOT ID while the follower is a MOMENT ID; layer 2 leaves it alone. Not in the RTL yet.
Hash: the v5 mix extended to any length: token value v = (j << (j*EVB)) | context packed, v ^= v >> 5; v ^= (v << 7) & 0xFFFFFF; v ^= v >> 11, then XOR-fold to IB bits (identical to v5/v6 while j*EVB + bits(j) fits 32 bits)."""
import collections
CLR, OBS, LOAD, RD, REW = 0, 1, 2, 3, 4
def s8(x): x &= 255; return x - 256 if x & 128 else x
class StoreV7:
    def __init__(s, N=3, W=80, CCAP=32, vshift=3, glvl=1, EVB=4, IB=10, RB=9, RSB=2, P=4, SW=8, LMAX=3, lookback=3):
        assert 1 <= N <= 15 and 1 <= EVB <= 12 and 1 <= LMAX
        s.N, s.W, s.CCAP, s.vshift, s.glvl, s.EVB, s.IB, s.RB, s.R, s.P, s.SW, s.LMAX = N, W, CCAP, vshift, glvl, EVB, IB, RB, 1 << RSB, P, SW, LMAX
        s.lookback = min(lookback, LMAX); s.HROWS = 1 << RB
        s.idx = [None] * (1 << IB)      # None empty | 'dead' | dict(tag, row, stamp)
        s.rows = {}                     # row -> dict(slots=[None|entry]*R, next=row|None)
        s.hp = 0; s.free = []           # rows never used start at hp; freed rows in chain order
        s.c = [None] * CCAP; s.q = collections.deque(maxlen=32); s.hist = []
        s.n_known = s.n_promoted = s.n_dropk = s.n_dropc = s.n_evict = 0
    @property
    def n_cand(s): return sum(1 for e in s.c if e)
    # ---- helpers
    def _nst(s, t): return (t >> 4) & ((1 << s.SW) - 1)
    def _ctx(s, j): return tuple(s.hist[-j:])
    def _h(s, j, ctx):
        v = j
        for x in ctx: v = (v << s.EVB) | x
        v ^= v >> 5; v ^= (v << 7) & 0xFFFFFF; v ^= v >> 11
        h = 0
        while v: h ^= v & ((1 << s.IB) - 1); v >>= s.IB
        return h
    def _lookup(s, j, ctx, t, refresh=True):
        """returns (found slot or None, first free-or-dead slot or None); a hit refreshes the stamp"""
        h = s._h(j, ctx); mask = (1 << s.IB) - 1; fs = None
        for p in range(s.P):
            sl = (h + p) & mask; e = s.idx[sl]
            if e is None:
                if fs is None: fs = sl
                return None, fs
            if e == "dead":
                if fs is None: fs = sl
                continue
            if e["tag"] == (j, ctx):
                if refresh: e["stamp"] = s._nst(t)
                return sl, fs
        return None, fs
    def _chain(s, row):
        while row is not None: yield row; row = s.rows[row]["next"]
    def _entries(s, sl):
        out = []
        for r in s._chain(s.idx[sl]["row"]): out += [(r, i, e) for i, e in enumerate(s.rows[r]["slots"]) if e is not None]
        return out
    def _has_row(s): return bool(s.free) or s.hp != s.HROWS
    def _new_row(s):
        if s.free: r = s.free.pop(0)
        else: r = s.hp; s.hp += 1
        s.rows[r] = dict(slots=[None] * s.R, next=None); return r
    def _evict(s, cur_tag, t):
        best = None; nst = s._nst(t)
        for sl, e in enumerate(s.idx):
            if isinstance(e, dict) and e["tag"] != cur_tag:
                age = (nst - e["stamp"]) & ((1 << s.SW) - 1)
                if best is None or age > best[0]: best = (age, sl)
        if best is None: return False
        sl = best[1]; chain = list(s._chain(s.idx[sl]["row"])); s.idx[sl] = "dead"
        for r in chain: s.rows[r]["slots"] = [None] * s.R
        for r in chain[:-1]: s.rows[r]["next"] = chain[chain.index(r) + 1]
        s.rows[chain[-1]]["next"] = None; s.free = chain; s.n_evict += 1; return True
    def _insert(s, j, ctx, ev, seen, pq, st, t, retry=False):
        """st = lookup state of this level: dict(found=slot|None, fs=slot|None, ffree=(row,i)|None, lastrow); returns True if done or finally dropped, False when an eviction must run first"""
        w = dict(ev=ev, seen=seen, con=0, val=0)
        if st["found"] is not None:
            if st["ffree"] is not None:
                r, i = st["ffree"]; s.rows[r]["slots"][i] = w; s.n_known += 1
                if pq: s.q.append((r, i))
                return True
            if s._has_row():
                r = s._new_row(); s.rows[r]["slots"][0] = w; s.rows[st["lastrow"]]["next"] = r; s.n_known += 1
                if pq: s.q.append((r, 0))
                return True
            if retry: s.n_dropk += 1; return True
            return False
        if st["fs"] is not None and s._has_row():
            r = s._new_row(); s.rows[r]["slots"][0] = w; s.idx[st["fs"]] = dict(tag=(j, ctx), row=r, stamp=s._nst(t)); s.n_known += 1
            if pq: s.q.append((r, 0))
            return True
        if st["fs"] is not None and not retry: return False
        s.n_dropk += 1; return True
    def _level_state(s, j, ctx, ev, t):
        fnd, fs = s._lookup(j, ctx, t); st = dict(found=fnd, fs=fs, ffree=None, lastrow=None, hit=None)
        if fnd is not None:
            for r in s._chain(s.idx[fnd]["row"]):
                st["lastrow"] = r
                for i, e in enumerate(s.rows[r]["slots"]):
                    if e is not None and e["ev"] == ev and st["hit"] is None: st["hit"] = (r, i, e)
                    if e is None and st["ffree"] is None: st["ffree"] = (r, i)
        return st
    def _finish_insert(s, j, ctx, ev, seen, pq, st, t):
        """insert with the lookup state of this level; when no row is free evict once and retry with the SAME state (as the RTL does: the slot chosen before the eviction is kept)"""
        if s._insert(j, ctx, ev, seen, pq, st, t): return
        if not s._evict((j, ctx), t): s.n_dropk += 1; return
        s._insert(j, ctx, ev, seen, pq, st, t, retry=True)
    # ---- command
    def step(s, cmd, ev=0, t=0, r=0, push=None):
        t &= 0xFFFF; pv = ev if push is None else push
        out = dict(verdict=3, vlevel=0, plevel=0, pbest=0, pbest_seen=0, ptotal=0, gbest=0, gval=0)
        if cmd == CLR: s.hist = []; return out
        if cmd == REW:
            for (rr, i) in list(s.q):
                e = s.rows.get(rr, {"slots": [None] * s.R})["slots"][i] if rr in s.rows else None
                if e is None: continue
                d = s8(r) - s8(e["val"]); step_ = ((d + (1 << s.vshift) - 1) >> s.vshift) if d > 0 else (d >> s.vshift); e["val"] = s8(e["val"] + step_)
            s.q.clear(); return out
        if not s.hist:
            if cmd in (OBS, LOAD): s.hist = [pv]; return out
            if cmd == RD: out["verdict"] = 2; return out
        # scan (reads refresh stamps)
        sc = {}
        for j in range(1, min(s.lookback, len(s.hist)) + 1):
            sl, _ = s._lookup(j, s._ctx(j), t)
            if sl is None: continue
            es = [e for _, _, e in s._entries(sl)]
            if not es: continue
            best = min(es, key=lambda e: (-e["seen"], e["ev"])); bv = min(es, key=lambda e: (-e["val"], -e["seen"], e["ev"]))
            sc[j] = dict(tot=sum(e["seen"] for e in es), bseen=best["seen"], bev=best["ev"], ex=any(e["ev"] == ev for e in es), vev=bv["ev"], vval=bv["val"])
        lv = max(sc) if sc else 0
        if lv: out.update(plevel=lv, pbest=sc[lv]["bev"], pbest_seen=sc[lv]["bseen"], ptotal=sc[lv]["tot"])
        gl = max((j for j in sc if j <= s.glvl), default=0)
        if gl: out.update(gbest=sc[gl]["vev"], gval=sc[gl]["vval"])
        out.update(vlevel=lv, verdict=(2 if not lv else (0 if sc[lv]["ex"] else 1)))
        if cmd == RD: return out
        if cmd == OBS and out["verdict"] == 1:
            sl, _ = s._lookup(lv, s._ctx(lv), t)
            for _, _, e in s._entries(sl): e["con"] = min(255, e["con"] + 1)
        for j in range(1, min(s.lookback, len(s.hist)) + 1):
            ctx = s._ctx(j); st = s._level_state(j, ctx, ev, t); key = (j, ctx, ev)
            if st["hit"] is not None:
                e = st["hit"][2]
                if e["seen"] != 255: e["seen"] += 1
                if cmd == OBS: s.q.append((st["hit"][0], st["hit"][1]))
                continue
            if cmd == LOAD:
                s._finish_insert(j, ctx, ev, 1, False, st, t); continue
            ch = next((i for i, e in enumerate(s.c) if e and e[0] == key), None)
            exp = ch is not None and ((t - s.c[ch][2]) & 0xFFFF) >= s.W
            cnt = (s.c[ch][1] + 1) & 15 if (ch is not None and not exp) else 1
            stt = s.c[ch][2] if (ch is not None and not exp) else t
            if cnt >= s.N:
                if ch is not None: s.c[ch] = None
                s._finish_insert(j, ctx, ev, cnt, True, st, t); s.n_promoted += 1
            elif ch is not None: s.c[ch][1], s.c[ch][2] = cnt, stt
            else:
                cf = next((i for i, e in enumerate(s.c) if e is None), None)
                if cf is not None: s.c[cf] = [key, 1, t]
                else:
                    cv = min(range(len(s.c)), key=lambda i: (s.c[i][1], -((t - s.c[i][2]) & 0xFFFF), i)); s.c[cv] = [key, 1, t]; s.n_dropc += 1
        s.hist = (s.hist + [pv])[-s.LMAX:]
        return out
