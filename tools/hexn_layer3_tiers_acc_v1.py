"""hexn_layer3_tiers_acc_v1: does layer 3 predict as well when long-term entries are moved off-chip as whole contexts (tools/hexn_layer3_tiers_v1.py), and what happens when the world CHANGES? (Python only; no RTL; imports the earlier files, untouched.) Alan, 27 Oct 2026: 'check the accuracy of the new system'; the changing-world test was left open earlier.
Worlds: (a) steady = the earlier synthetic world; (b) changing = three phases of equal length: habits A-D, then NEW habits F-I (other key orders), then back to A-D. Phase 3 shows whether the old habits are still known after a different phase filled the memory.
Rules compared at the same on-chip capacity: unbounded (reference), drop_new (store v5 today: refuse when full), drop_low (evict lowest faded weight, delete), tiered (whole-context movement to SDRAM, nothing lost; here the SDRAM is unlimited and a context is read back whole when used).
Measured: for every moment, the model's ranked prediction for channel 0's next value against what happened: top-1 hit rate and the average share of weight on the true value (as in the forgetting model). Limits: synthetic world; the tiered rule moves contexts whole by lowest total weight and the lookup in predict() reads all tiers; no timing here (see the tiers cost file)."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_forget_v1 as F, hexn_layer3_tiers_v1 as T
R = {"A": [0, 1, 2, 5], "B": [3, 1, 2, 6], "C": [0, 4, 2, 6], "D": [3, 4, 2, 5], "F": [1, 0, 5, 2], "G": [4, 6, 0, 3], "H": [2, 5, 6, 1], "I": [6, 3, 4, 0]}
SETS = [("AB", "CD"), ("FG", "HI"), ("AB", "CD")]
def world(n_routines, changing, seed=1):
    r = random.Random(seed); ev = []; ph = []; t = 0; light = 0; th = 1; left = r.randint(8, 15); ev += [(0, 1, 0), (0, 2, th), (0, 0, 7)]; ph += [0, 0, 0]
    for i in range(n_routines):
        p = min(2, 3 * i // n_routines) if changing else 0; sets = SETS[p]
        if left == 0: light ^= 1; left = r.randint(8, 15); t += 4; ev.append((t, 1, light)); ph.append(p)
        left -= 1; name = r.choice(sets[light])
        for n, k in enumerate(R[name]):
            t += 6 if n == 0 else 3; ev.append((t, 0, k)); ph.append(p)
            if r.random() < 0.05: t += 1; th = max(0, min(3, th + r.choice((-1, 1)))); ev.append((t + 40, 2, th)); ph.append(p)
    order = sorted(range(len(ev)), key=lambda i: ev[i][0]); return [ev[i] for i in order], [ph[i] for i in order]
class TierPred(T.TieredCtx):
    def predict(s, top=8):          # as Bounded.predict but reads FAST, SDRAM and SD tiers together
        p = {}; rem = 1.0
        for j, m in s.levels:
            c = s._ctx(j, m)
            if c is None or None in s.snap: continue
            key = (j, m, c); d = dict(s.tab.get(key, {}))
            for tier in (s.slow, s.sd):
                if key in tier: d.update({k: e for k, e in tier[key].items() if k not in d})
            if not d: continue
            ws = {k: s._w(e) for k, e in d.items()}; t = sum(ws.values()); dn = len(ws)
            for k, w in ws.items(): p[k] = p.get(k, 0.0) + rem * w / (t + dn)
            rem *= dn / (t + dn)
        r = sorted(p.items(), key=lambda kv: -kv[1]); return r[:top], rem
def make(rule, cap):
    if rule == "tiered": return TierPred(cap, None, None, nch=3, L=4, align=2)
    return F.Bounded(cap=None if rule == "unbounded" else cap, rule=rule, prot=3, nch=3, L=4, align=2)
def run(ev, ph, rule, cap, warm=60):
    ms = make(rule, cap); groups = []; cur = []; t0 = None
    for i, (t, c, k) in enumerate(ev):
        if cur and t - t0 > 2: groups.append(cur); cur = []
        if not cur: t0 = t
        cur.append((i, c, k))
    groups.append(cur); acc = {}
    for gi, g in enumerate(groups):
        d = {c: k for _, c, k in g}; p = ph[g[0][0]]
        if gi >= warm and 0 in d and None not in ms.snap:
            v = ms.channel_view(0, top=10 ** 6); z = sum(w for _, w in v); a = acc.setdefault(p, [0, 0, 0.0]); a[0] += 1
            if z > 0: a[1] += v[0][0] == d[0]; a[2] += dict(v).get(d[0], 0.0) / z
        for _, c, k in g: ms.feed(gi * 1000, c, k)
        ms.flush()
    ents = ms.nent + (sum(len(x) for x in ms.slow.values()) + sum(len(x) for x in getattr(ms, "sd", {}).values()))
    return acc, ents
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000; cap = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    for changing in (False, True):
        ev, ph = world(n, changing); print("\n%s world, %d changes, on-chip capacity %d entries" % ("CHANGING (A-D, then F-I, then A-D)" if changing else "STEADY", len(ev), cap))
        print("%-10s | " % "rule" + " | ".join("phase %d: n  top1  weight" % (p + 1) for p in range(3 if changing else 1)) + " | entries held")
        for rule in ("unbounded", "drop_new", "drop_low", "tiered"):
            acc, ents = run(ev, ph, rule, cap)
            cells = []
            for p in range(3 if changing else 1):
                a = acc.get(p, [0, 0, 0.0]); cells.append("%7d %6.3f %6.3f" % (a[0], a[1] / a[0] if a[0] else 0, a[2] / a[0] if a[0] else 0))
            print("%-10s | " % rule + " | ".join(cells) + " | %d" % ents)
