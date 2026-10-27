"""hexn_layer3_forget_v1: what to do when layer 3's memory is full (Python only; extends tools/hexn_layer3_v1.py, untouched; no RTL). Alan, 27 Oct 2026: once the store is full the patterns could fade to zero and be removed, but layer 3 needs its long-term patterns; slow memory (SD card on the Tang; main RAM / JTAG on the Kintex card) can hold what is spilled.
Memory is capped at `cap` ENTRIES (a context plus one follower). Rules when a new entry needs space and the memory is full:
  unbounded   no cap (the reference, what v1 does)
  drop_new    refuse the new entry (what store v5 does now)
  drop_oldest evict the entry not touched for longest
  drop_low    evict the entry with the lowest faded weight
  protect     as drop_low, but entries seen `prot` or more times in all are never evicted (if all are protected, refuse the new entry)
  spill       evict the lowest faded weight into a SLOW tier instead of deleting it; a context whose followers sit in the slow tier is read from there (counted as slow reads) and its entries come back into the fast tier when updated
World: the v1 synthetic coupled world plus a RARE routine E (remote keys 6 0 3 5, none of whose steps occur in routines A to D) inserted about once in 250 routines; the fast memory sees hundreds of moments of other traffic between two occurrences of E. Scores are on the remote channel, as in hexn_layer3_v1.evaluate_remote: weight given to the key that happened, and whether it was the top choice; for all remote keys and for the rare routine's keys alone.
Limits: synthetic world; eviction here searches the whole memory (hardware would look only at a few nearby entries, which can only do worse or equal); the slow tier is unlimited and costs nothing but a count."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_v1 as V1
RARE = [6, 0, 3, 5]
def world2(n_routines=3000, seed=1, rare_every=250):
    r = random.Random(seed); R = {"A": [0, 1, 2, 5], "B": [3, 1, 2, 6], "C": [0, 4, 2, 6], "D": [3, 4, 2, 5], "E": RARE}
    ev = []; rare = set(); t = 0; light = 0; th = 1; left = r.randint(8, 15); ev += [(0, 1, 0), (0, 2, th), (0, 0, 7)]
    for i in range(n_routines):
        if left == 0: light ^= 1; left = r.randint(8, 15); t += 4; ev.append((t, 1, light))
        left -= 1; name = "E" if r.random() < 1 / rare_every else r.choice("AB" if light == 0 else "CD")
        for n, k in enumerate(R[name]):
            t += 6 if n == 0 else 3; ev.append((t, 0, k))
            if name == "E" and n > 0: rare.add(len(ev) - 1)
            if r.random() < 0.05: t += 1; th = max(0, min(3, th + r.choice((-1, 1)))); ev.append((t + 40, 2, th))
    order = sorted(range(len(ev)), key=lambda i: ev[i][0]); return [ev[i] for i in order], {order.index(i) for i in rare}
class Bounded(V1.Layer3):
    def __init__(s, cap=None, rule="unbounded", prot=3, **k):
        super().__init__(**k); s.cap, s.rule, s.prot = cap, rule, prot; s.nent = 0; s.slow = {}; s.slow_reads = 0; s.evicted = 0; s.refused = 0; s.hits = {}
    def _victim(s):
        best = None
        for key, d in s.tab.items():
            for k, e in d.items():
                if s.rule == "protect" and s.hits.get((key, k), 0) >= s.prot: continue
                sc = e[1] if s.rule == "drop_oldest" else s._w(e)
                if best is None or sc < best[0]: best = (sc, key, k)
        return best
    def _room(s):
        if s.cap is None or s.nent < s.cap: return True
        if s.rule == "drop_new": s.refused += 1; return False
        v = s._victim()
        if v is None: s.refused += 1; return False
        _, key, k = v; e = s.tab[key].pop(k); s.nent -= 1; s.evicted += 1
        if not s.tab[key]: del s.tab[key]
        if s.rule == "spill": s.slow.setdefault(key, {})[k] = e
        return True
    def _close(s):
        ch = tuple(sorted(s.pend.items())); s.pend = None
        for j, m in s.levels:
            c = s._ctx(j, m)
            if c is None: continue
            key = (j, m, c); d = s.tab.get(key)
            if s.rule == "spill" and key in s.slow and ch in s.slow[key]:
                s.slow_reads += 1
                if s._room():
                    e0 = s.slow[key].pop(ch); s.tab.setdefault(key, {})[ch] = e0; s.nent += 1
                    if not s.slow[key]: del s.slow[key]
            d = s.tab.get(key)
            if d is not None and ch in d: e = d[ch]; d[ch] = (s._w(e) + 1.0, s.n)
            elif s._room(): s.tab.setdefault(key, {})[ch] = (1.0, s.n); s.nent += 1
            else: continue
            s.hits[(key, ch)] = s.hits.get((key, ch), 0) + 1
        for c, k in ch: s.snap[c] = k
        s.hist.append(tuple(s.snap)); s.hist = s.hist[-s.L:]; s.n += 1; return ch
    def predict(s, top=8):
        p = {}; rem = 1.0
        for j, m in s.levels:
            c = s._ctx(j, m)
            if c is None or None in s.snap: continue
            key = (j, m, c); d = dict(s.tab.get(key, {}))
            if s.rule == "spill" and key in s.slow: s.slow_reads += 1; d.update({k: e for k, e in s.slow[key].items() if k not in d})
            if not d: continue
            ws = {k: s._w(e) for k, e in d.items()}; t = sum(ws.values()); dn = len(ws)
            for k, w in ws.items(): p[k] = p.get(k, 0.0) + rem * w / (t + dn)
            rem *= dn / (t + dn)
        r = sorted(p.items(), key=lambda kv: -kv[1]); return r[:top], rem
def run(ev, rare_idx, cap, rule, L=4, align=2, warm=60, prot=3):
    ms = Bounded(cap=cap, rule=rule, prot=prot, nch=3, L=L, align=align); groups = []; cur = []; t0 = None
    for i, (t, c, k) in enumerate(ev):
        if cur and t - t0 > align: groups.append(cur); cur = []
        if not cur: t0 = t
        cur.append((i, c, k))
    groups.append(cur)
    a = [0, 0, 0.0]; b = [0, 0, 0.0]
    for gi, g in enumerate(groups):
        d = {c: k for _, c, k in g}; isr = any(i in rare_idx for i, _, _ in g)
        if gi >= warm and 0 in d and None not in ms.snap:
            v = ms.channel_view(0, top=10 ** 6); z = sum(w for _, w in v)
            for acc in ((a, b) if isr else (a,)):
                acc[0] += 1
                if z > 0: acc[1] += v[0][0] == d[0]; acc[2] += dict(v).get(d[0], 0.0) / z
        for _, c, k in g: ms.feed(gi * 1000, c, k)
        ms.flush()
    f = lambda x: (round(x[1] / x[0], 3), round(x[2] / x[0], 3)) if x[0] else (None, None)
    return dict(all_n=a[0], all_top1=f(a)[0], all_w=f(a)[1], rare_n=b[0], rare_top1=f(b)[0], rare_w=f(b)[1], entries=ms.nent + sum(len(d) for d in ms.slow.values()) * (rule == "spill" and 0), fast=ms.nent, slow=sum(len(d) for d in ms.slow.values()), evicted=ms.evicted, refused=ms.refused, slow_reads=ms.slow_reads)
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000; cap = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    re_ = int(sys.argv[3]) if len(sys.argv) > 3 else 250; ev, rare = world2(n, rare_every=re_); print("world: %d changes, %d routines, %d rare-routine keys; memory cap %d entries (fast tier)" % (len(ev), n, len(rare), cap))
    print("%-12s %7s %7s %7s | %6s %7s %7s | %6s %7s %7s %9s %9s" % ("rule", "all_n", "top1", "weight", "rare_n", "top1", "weight", "fast", "slow", "evicted", "refused", "slowreads"))
    for rule in ("unbounded", "drop_new", "drop_oldest", "drop_low", "protect", "spill"):
        d = run(ev, rare, None if rule == "unbounded" else cap, rule)
        print("%-12s %7d %7s %7s | %6d %7s %7s | %6d %7d %7d %9d %9d" % (rule, d["all_n"], d["all_top1"], d["all_w"], d["rare_n"], d["rare_top1"], d["rare_w"], d["fast"], d["slow"], d["evicted"], d["refused"], d["slow_reads"]))
