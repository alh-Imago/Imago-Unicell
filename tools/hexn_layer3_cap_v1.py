"""hexn_layer3_cap_v1: LAYER 3 with a BOUNDED table (Python model only; new file 31 Oct 2026). Alan, 31 Oct 02:15: decisions for layer 3 recorded ('carry the layer 2 refinements over'). The layer 3 model of tools/hexn_layer3_v1.py keeps every context it has ever seen; hardware cannot. This tests what a size limit costs and which entry is best dropped when the table is full: 'weight' = the entry (context, moment) with the lowest decayed weight (the v5 rule in spirit), 'lru' = the entry touched longest ago, 'newest-drop' = a full table refuses new entries (what store v5 does). An entry = one (level, mask, context, moment) with its weight. Scored as in hexn_layer3_v1.evaluate_remote on the synthetic coupled world (remote keys), plus a world whose light-to-routine rule changes half way (switch_rule)."""
import argparse, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_v1 as L3

class Capped(L3.Layer3):
    def __init__(s, cap=None, policy="lru", **kw): super().__init__(**kw); s.cap = cap; s.policy = policy; s.count = 0; s.touch = {}; s.dropped = 0; s.evicted = 0
    def _close(s):
        ch = tuple(sorted(s.pend.items())); s.pend = None
        for j, m in s.levels:
            c = s._ctx(j, m)
            if c is None: continue
            d = s.tab.setdefault((j, m, c), {}); key = (j, m, c, ch)
            if ch not in d:
                if s.cap is not None and s.count >= s.cap:
                    if s.policy == "newest-drop": s.dropped += 1; continue
                    s._evict(keep=key)
                s.count += 1
            e = d.get(ch, (0.0, s.n)); d[ch] = (s._w(e) + 1.0, s.n); s.touch[key] = s.n
        for c, k in ch: s.snap[c] = k
        s.hist.append(tuple(s.snap)); s.hist = s.hist[-s.L:]; s.n += 1; return ch
    def _evict(s, keep):
        best = None
        for (j, m, c), d in s.tab.items():
            for ch, e in d.items():
                k = (j, m, c, ch)
                if k == keep: continue
                score = s._w(e) if s.policy == "weight" else s.touch.get(k, -1)
                if best is None or score < best[0]: best = (score, k)
        if best is None: return
        j, m, c, ch = best[1]; d = s.tab[(j, m, c)]; del d[ch]; s.touch.pop(best[1], None); s.count -= 1; s.evicted += 1
        if not d: del s.tab[(j, m, c)]

def world2(n=600, seed=1, switch_at=300):
    """as L3.world, but at routine `switch_at` the light-to-routine rule swaps (light 0 -> C or D, light 1 -> A or B)."""
    import random
    r = random.Random(seed); R = {"A": [0, 1, 2, 5], "B": [3, 1, 2, 6], "C": [0, 4, 2, 6], "D": [3, 4, 2, 5]}
    ev = []; t = 0; light = 0; th = 1; left = r.randint(8, 15); ev.append((0, 1, 0)); ev.append((0, 2, th)); ev.append((0, 0, 7))
    for i in range(n):
        if left == 0: light ^= 1; left = r.randint(8, 15); t += 4; ev.append((t, 1, light))
        left -= 1; grp = ("AB" if light == 0 else "CD") if i < switch_at else ("CD" if light == 0 else "AB"); name = r.choice(grp)
        for k in R[name]:
            t += 6 if k == R[name][0] else 3; ev.append((t, 0, k))
            if r.random() < 0.05: t += 1; th = max(0, min(3, th + r.choice((-1, 1)))); ev.append((t + 40, 2, th))
    ev.sort(key=lambda e: e[0]); return ev

def score(events, spans, cap, policy, L=4, half=200, warm=40):
    seq = L3.moments(events, 2); ms = Capped(cap=cap, policy=policy, nch=3, L=L, half=half); res = [[0, 0] for _ in spans]
    for i, mo in enumerate(seq):
        d = dict(mo)
        if i >= warm and 0 in d and None not in ms.snap:
            v = ms.channel_view(0, top=10 ** 6); ok = bool(v) and v[0][0] == d[0]
            for k, (a, b) in enumerate(spans):
                if a <= i < b: res[k][0] += ok; res[k][1] += 1
        for c, k in mo: ms.feed(i * 1000, c, k)
        ms.flush()
    return [a / max(1, b) for a, b in res], ms

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=8); a = ap.parse_args()
    for name, mk, spans in (("STEADY world", lambda s: L3.world(400, s), [(200, 700)]), ("RULE SWITCH (light-to-routine swaps at routine 300, about moment 1,500)", lambda s: world2(600, s, 300), [(1000, 1500), (1500, 1900), (2300, 3000)])):
        ev0 = mk(1); nm = len(L3.moments(ev0, 2)); print(f"\n{name}: {nm} moments; remote-key top-1, {a.seeds} seeds, windows {spans}")
        _, ms = score(ev0, spans, None, "lru"); full = ms.count; print(f"  unbounded table holds {full} entries (seed 1)")
        for cap, pol in ((None, "lru"), (full // 2, "lru"), (full // 2, "weight"), (full // 2, "newest-drop"), (full // 4, "lru"), (full // 4, "weight"), (full // 4, "newest-drop")):
            rs = [score(mk(s), spans, cap, pol)[0] for s in range(a.seeds)]
            print(f"  cap {str(cap):>5s} {pol:12s} " + "  ".join(f"{st.mean(r[i] for r in rs):.3f}" for i in range(len(spans))), flush=True)
