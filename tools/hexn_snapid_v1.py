"""hexn_snapid_v1: SNAPSHOT-ID TABLE for layer 3 (Python model only; new file 31 Oct 2026). Alan, 31 Oct 02:29: 'then the Id for the table'.
Layer 3's context elements are SNAPSHOTS (one key per sensor, with some sensors hidden by a mask). Store v7 keeps events of a few bits, so each distinct (masked) snapshot is given a small ID, the way store v5 tokenises known values: an index of 2^IB slots hashes the snapshot (its keys packed, KB bits each, a hidden sensor = all ones) to a slot (probe P); the slot holds the full key (tag), the ID and a stamp. A snapshot not yet known gets the next free ID. When the IDs are used up, or the probe window is full of live entries, policy 'refuse' gives no ID (that context is not learned or used) and policy 'lru' re-uses the ID of the least recently used snapshot (the old snapshot's contexts in the store then alias the new one until they age out; nothing is cleaned).
Class Layer3Id runs the layer 3 model of hexn_layer3_v1.py with context elements taken as IDs; followers stay full moments (a moment-ID table is the same idea and is only counted here). hexn_layer3_v1.py is untouched."""
import argparse, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_v1 as L3, hexn_layer3_cap_v1 as CAP, hexn_layer3_l2in_v2 as V2

class SnapTable:
    def __init__(s, IB=9, P=4, IDW=8, KB=4, policy="refuse"):
        s.IB, s.P, s.IDW, s.KB, s.policy = IB, P, IDW, KB, policy
        s.idx = [None] * (1 << IB); s.next_id = 0; s.assigned = 0; s.refused = 0; s.reused = 0; s.lookups = 0; s.live_peak = 0; s.live = 0
    def _h(s, key):
        v = 0
        for k in key: v = (v << s.KB) | ((1 << s.KB) - 1 if k is None else k)
        v ^= v >> 5; v ^= (v << 7) & 0xFFFFFF; v ^= v >> 11; h = 0
        while v: h ^= v & ((1 << s.IB) - 1); v >>= s.IB
        return h
    def get(s, key, now, assign=True):
        s.lookups += 1; h = s._h(key); mask = (1 << s.IB) - 1; free = None; win = []
        for p in range(s.P):
            sl = (h + p) & mask; e = s.idx[sl]
            if e is None:
                if free is None: free = sl
                break
            if e["key"] == key: e["stamp"] = now; return e["id"]
            win.append(sl)
        if not assign: return None
        if free is None and s.policy == "refuse": s.refused += 1; return None
        if free is None: free = min(win, key=lambda sl: s.idx[sl]["stamp"]); i = s.idx[free]["id"]; s.reused += 1; s.live -= 1
        elif s.next_id < (1 << s.IDW): i = s.next_id; s.next_id += 1
        elif s.policy == "refuse": s.refused += 1; return None
        else:
            vs = min((sl for sl, e in enumerate(s.idx) if e is not None), key=lambda sl: s.idx[sl]["stamp"]); i = s.idx[vs]["id"]; s.idx[vs] = None; s.reused += 1; s.live -= 1
            free = free if s.idx[free] is None else free
        s.idx[free] = dict(key=key, id=i, stamp=now); s.assigned += 1; s.live += 1; s.live_peak = max(s.live_peak, s.live); return i

class Layer3Id(L3.Layer3):
    def __init__(s, table, **kw): super().__init__(**kw); s.T = table; s.hid = []
    def _masked(s, sn, m): return tuple(k if on else None for k, on in zip(sn, m))
    def _ctx(s, j, m):
        if len(s.hist) < j: return None
        mi = s.masks.index(m); ids = [h[mi] for h in s.hid[-j:]]
        return None if any(i is None for i in ids) else tuple(ids)
    def _close(s):
        ch = tuple(sorted(s.pend.items())); s.pend = None
        for j, m in s.levels:
            c = s._ctx(j, m)
            if c is None: continue
            d = s.tab.setdefault((j, m, c), {}); e = d.get(ch, (0.0, s.n)); d[ch] = (s._w(e) + 1.0, s.n)
        for c, k in ch: s.snap[c] = k
        sn = tuple(s.snap); s.hist.append(sn); s.hist = s.hist[-s.L:]
        s.hid.append([s.T.get(s._masked(sn, m), s.n) if None not in sn else None for m in s.masks]); s.hid = s.hid[-s.L:]; s.n += 1; return ch

def score(events, spans, L, table=None, warm=40):
    seq = L3.moments(events, 2); ms = L3.Layer3(nch=3, L=L, half=200) if table is None else Layer3Id(table, nch=3, L=L, half=200); res = [[0, 0] for _ in spans]; snaps = set(); moms = set()
    for i, mo in enumerate(seq):
        d = dict(mo); moms.add(mo)
        if i >= warm and 0 in d and None not in ms.snap:
            v = ms.channel_view(0, top=10 ** 6); ok = bool(v) and v[0][0] == d[0]
            for k, (a, b) in enumerate(spans):
                if a <= i < b: res[k][0] += ok; res[k][1] += 1
        for c, k in mo: ms.feed(i * 1000, c, k)
        ms.flush()
        if None not in ms.snap:
            for m in ms.masks: snaps.add(tuple(k if on else None for k, on in zip(ms.snap, m)))
    return [a / max(1, b) for a, b in res], len(snaps), len(moms)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=6); ap.add_argument("--L", type=int, default=6); a = ap.parse_args()
    for name, mk, spans in (("WORLD 3", lambda s: V2.world3(500, s), [(200, 900)]), ("STEADY world", lambda s: L3.world(400, s), [(200, 700)]), ("RULE SWITCH (before | just after | long after)", lambda s: CAP.world2(600, s, 300), [(1000, 1500), (1500, 1900), (2300, 3000)])):
        r0 = [score(mk(s), spans, a.L) for s in range(a.seeds)]
        print(f"\n{name}: L={a.L}, default masks (3 per snapshot); distinct masked snapshots {st.mean(r[1] for r in r0):.0f} (max {max(r[1] for r in r0)}), distinct moments {st.mean(r[2] for r in r0):.0f} (max {max(r[2] for r in r0)}); {a.seeds} seeds")
        print("  no table (full snapshots in the context)   " + "  ".join(f"{st.mean(r[0][i] for r in r0):.3f}" for i in range(len(spans))))
        for idw, pol in ((8, "refuse"), (7, "refuse"), (6, "refuse"), (6, "lru"), (5, "lru"), (4, "lru")):
            rs = []; tabs = []
            for s in range(a.seeds):
                T = SnapTable(IB=9, P=4, IDW=idw, policy=pol); rs.append(score(mk(s), spans, a.L, T)[0]); tabs.append(T)
            print(f"  IDs {1 << idw:3d} {pol:6s} (index 512)            " + "  ".join(f"{st.mean(r[i] for r in rs):.3f}" for i in range(len(spans))) + f" | refused {st.mean(t.refused for t in tabs):.0f} reused {st.mean(t.reused for t in tabs):.0f} peak live {max(t.live_peak for t in tabs)}", flush=True)
