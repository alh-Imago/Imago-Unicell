"""hexn_layer3_tiers_v1: Layer 3's long-term pattern store spread over three tiers, with an on-chip presence bitmap for the slowest one (Python only; builds on tools/hexn_layer3_forget_v1.py, untouched; no RTL). Alan, 27 Oct 2026: keep long-term patterns off the main chip, only the short-term reference table in block RAM; board results the same evening: SDRAM about 300 ns per access (our controller, 8 clocks at 27 MHz), SD card about 0.6 ms per 512-byte block read, 1.4 to 2 ms per block write.
Tiers: FAST (block RAM, `cap` entries), SDRAM (`sdram_cap` entries), SD (unlimited). Eviction is the spill rule of the forgetting model: the lowest faded weight moves down one tier (fast -> SDRAM -> SD); an entry that is used or updated comes back up to FAST.
Every lookup of a context key (once per level per moment when predicting, once when learning) probes SDRAM (cheap, counted) and reads the SD card only if the presence test says the key has entries there. Presence tests compared: `none` (no bit: read the SD every lookup), `exact` (a perfect bit, the least any scheme can do), and hashed bitmaps of 4,096 / 16,384 / 65,536 bits (a counter per bit, so bits clear when keys leave the SD; a real chip would need counting bits or accept stale ones). A false positive costs a wasted SD read.
Assumptions that are NOT measured: all followers of one context key sit in one 512-byte sector (one SD read per lookup); a write is counted when an entry moves to the SD (one sector write each, no batching); the SDRAM probe is one access.
Limits: synthetic world; eviction searches whole tiers; times are from the board figures above, not from a combined design."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_forget_v1 as F
T_SDRAM, T_SD_RD, T_SD_WR = 300e-9, 0.6e-3, 2.0e-3
BITS = (4096, 16384, 65536)
class Tiered(F.Bounded):
    def __init__(s, sdram_cap=1500, skip=False, **k):
        super().__init__(rule="spill", **k); s.sdram_cap = sdram_cap; s.skip = skip; s.tier = {}; s.nsdram = 0
        s.sdkeys = {}; s.bk = {B: [0] * B for B in BITS}
        s.lookups = 0; s.sd_true = 0; s.sd_fp = {B: 0 for B in BITS}; s.sd_pos = {B: 0 for B in BITS}; s.sd_writes = 0; s.sdram_probes = 0
    def _sd_key(s, key, d):
        old = s.sdkeys.get(key, 0); s.sdkeys[key] = old + d
        if old == 0 and d > 0 or old + d == 0 and d < 0:
            for B in BITS: s.bk[B][hash(key) % B] += d
        if s.sdkeys[key] == 0: del s.sdkeys[key]
    def _to_slow(s, key, k, e):
        s.slow.setdefault(key, {})[k] = e; s.tier[(key, k)] = "sdram"; s.nsdram += 1
        while s.nsdram > s.sdram_cap:            # demote the lowest-weight SDRAM entry to the card
            best = None
            for kk, dd in s.slow.items():
                for f, ee in dd.items():
                    if s.tier[(kk, f)] == "sdram":
                        w = s._w(ee)
                        if best is None or w < best[0]: best = (w, kk, f)
            _, kk, f = best; s.tier[(kk, f)] = "sd"; s.nsdram -= 1; s._sd_key(kk, 1); s.sd_writes += 1
    def _from_slow(s, key, k):
        e = s.slow[key].pop(k)
        if s.tier.pop((key, k)) == "sdram": s.nsdram -= 1
        else: s._sd_key(key, -1)
        if not s.slow[key]: del s.slow[key]
        return e
    def _room(s):
        if s.cap is None or s.nent < s.cap: return True
        v = s._victim()
        if v is None: s.refused += 1; return False
        _, key, k = v; e = s.tab[key].pop(k); s.nent -= 1; s.evicted += 1
        if not s.tab[key]: del s.tab[key]
        s._to_slow(key, k, e); return True
    def _look(s, key):
        if s.skip and key in s.tab: return      # skip mode: a context with followers in the fast tier is answered from there, no slow lookup
        s.lookups += 1; s.sdram_probes += 1; t = key in s.sdkeys; s.sd_true += t
        for B in BITS:
            p = s.bk[B][hash(key) % B] > 0; s.sd_pos[B] += p; s.sd_fp[B] += (p and not t)
    def _close(s):
        ch = tuple(sorted(s.pend.items())); s.pend = None
        for j, m in s.levels:
            c = s._ctx(j, m)
            if c is None: continue
            key = (j, m, c); s._look(key)
            if key in s.slow and ch in s.slow[key] and not (s.skip and key in s.tab):
                s.slow_reads += 1
                if s._room(): e0 = s._from_slow(key, ch); s.tab.setdefault(key, {})[ch] = e0; s.nent += 1
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
            key = (j, m, c); s._look(key); d = dict(s.tab.get(key, {}))
            if key in s.slow and not (s.skip and key in s.tab): s.slow_reads += 1; d.update({k: e for k, e in s.slow[key].items() if k not in d})
            if not d: continue
            ws = {k: s._w(e) for k, e in d.items()}; t = sum(ws.values()); dn = len(ws)
            for k, w in ws.items(): p[k] = p.get(k, 0.0) + rem * w / (t + dn)
            rem *= dn / (t + dn)
        r = sorted(p.items(), key=lambda kv: -kv[1]); return r[:top], rem
def run(ev, rare_idx, cap, sdram_cap, L=4, align=2, warm=60, skip=False):
    ms = Tiered(cap=cap, sdram_cap=sdram_cap, skip=skip, nch=3, L=L, align=align); groups = []; cur = []; t0 = None
    for i, (t, c, k) in enumerate(ev):
        if cur and t - t0 > align: groups.append(cur); cur = []
        if not cur: t0 = t
        cur.append((i, c, k))
    groups.append(cur); a = [0, 0, 0.0]; b = [0, 0, 0.0]
    for gi, g in enumerate(groups):
        d = {c: k for _, c, k in g}; isr = any(i in rare_idx for i, _, _ in g)
        if gi >= warm and 0 in d and None not in ms.snap:
            v = ms.channel_view(0, top=10 ** 6); z = sum(w for _, w in v)
            for acc in ((a, b) if isr else (a,)):
                acc[0] += 1
                if z > 0: acc[1] += v[0][0] == d[0]; acc[2] += dict(v).get(d[0], 0.0) / z
        for _, c, k in g: ms.feed(gi * 1000, c, k)
        ms.flush()
    return ms, len(groups), a, b
def report(ev, rare, ref, cap, sc, skip):
    n = len(ev); ms, mom, a, b = run(ev, rare, cap, sc, skip=skip); f = lambda x: round(x[1] / x[0], 3) if x[0] else None
    print("\n=== %s ===" % ("SKIP mode: a context that has followers in the fast tier is not looked up further" if skip else "FULL mode: every lookup also consults the slow tiers"))
    print("%d changes, %d moments; fast cap %d entries, SDRAM cap %d entries" % (n, mom, cap, sc))
    print("accuracy: unbounded top1 %s (rare %s)  |  three tiers top1 %s (rare %s)" % (ref["all_top1"], ref["rare_top1"], f(a), f(b)))
    print("entries: fast %d, SDRAM %d, SD %d; moved to SD (sector writes) %d" % (ms.nent, ms.nsdram, sum(1 for v in ms.tier.values() if v == "sd"), ms.sd_writes))
    print("lookups %d (%.1f per moment); keys really on the SD at lookup time: %d (%.1f%%)" % (ms.lookups, ms.lookups / mom, ms.sd_true, 100.0 * ms.sd_true / ms.lookups))
    wr = ms.sd_writes * T_SD_WR; base = ms.sdram_probes * T_SDRAM
    print("%-12s %10s %10s %12s %14s" % ("presence", "SD reads", "wasted", "per moment", "time/moment"))
    rows = [("none", ms.lookups, ms.lookups - ms.sd_true), ("exact", ms.sd_true, 0)] + [("%d bits" % B, ms.sd_pos[B], ms.sd_fp[B]) for B in BITS]
    for name, rd, w in rows:
        t = (rd * T_SD_RD + base + wr) / mom
        print("%-12s %10d %10d %12.2f %11.2f ms" % (name, rd, w, rd / mom, t * 1000))
    print("(time/moment = SD reads x 0.6 ms + SDRAM probes x 300 ns + SD writes x 2 ms, all divided by moments)")
def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000; cap = int(sys.argv[2]) if len(sys.argv) > 2 else 600; sc = int(sys.argv[3]) if len(sys.argv) > 3 else 1500
    ev, rare = F.world2(n)
    ref = F.run(ev, rare, None, "unbounded")
    for skip in (False, True):
        report(ev, rare, ref, cap, sc, skip)
if __name__ == "__main__":
    main()
