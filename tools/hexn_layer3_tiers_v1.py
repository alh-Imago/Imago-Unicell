"""hexn_layer3_tiers_v1: cost of a THREE-TIER long-term store for layer 3 (Python only; clones the 'spill' rule of tools/hexn_layer3_forget_v1.py, which stays untouched; no RTL). Alan, 27 Oct 2026: proven long-term patterns live off-chip and the chip keeps only the short-term table.
Tiers: FAST = on-chip block RAM (cap entries, cost ~0), SDRAM = embedded 8 MiB (sdram_cap entries, 300 ns per probe measured as 8 clocks at 27 MHz), SD = SD card (unlimited, 0.6 ms per probe, measured on the board 27 Oct 2026). Entries evicted from FAST (lowest faded weight) go to SDRAM; the oldest SDRAM entries move on to the SD card; an entry that is updated comes back to FAST.
PRESENCE FILTERS: one bit-table per off-chip tier, `bits` bits each, set (by a hash of the context) when an entry for that context lands in the tier, never cleared (so false positives only grow). A lookup of a context that is not complete in FAST probes a tier only if its bit is set. `bits=None` means no filter: every such lookup probes SDRAM and the card.
Lookup = one per context key per moment, in predict() and again in the learning step (as the forgetting model does). A probe costs the tier's time whether or not it finds anything. Nothing is deleted (entries only move between tiers), but prediction accuracy is NOT measured in this file; only cost is reported.
Limits: synthetic world; one probe per context regardless of how many followers (a real layout would pack one context's followers into one SDRAM word group or one card sector); the SD probe time excludes the writes that moving entries to the card costs (about 2 ms each, counted separately as `sd_writes`); filters use a simple hash."""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_forget_v1 as F
T_SDRAM, T_SD = 300e-9, 0.6e-3; T_SDW = 2.0e-3
class Tiered(F.Bounded):
    def __init__(s, cap, sdram_cap, bits, **k):
        super().__init__(cap=cap, rule="spill", **k); s.sc, s.bits = sdram_cap, bits
        s.sd = {}; s.sdq = collections.OrderedDict(); s.fs = [0] * (bits or 1); s.fd = [0] * (bits or 1)
        s.lookups = 0; s.p_sdram = 0; s.p_sd = 0; s.fp_sdram = 0; s.fp_sd = 0; s.sd_writes = 0; s.moments = 0
    def _h(s, key): return hash(key) % s.bits
    def _tier_has(s, key): return (key in s.slow and any((key, k) in s.sdq for k in s.slow[key]), key in s.sd)
    def _probe(s, key):
        s.lookups += 1; in_sdram, in_sd = s._tier_has(key)
        if s.bits is None: s.p_sdram += 1; s.p_sd += 1; return
        if s.fs[s._h(key)]:
            s.p_sdram += 1; s.fp_sdram += (not in_sdram)
        if s.fd[s._h(key)]:
            s.p_sd += 1; s.fp_sd += (not in_sd)
    def _place(s, key, k, e):
        s.slow.setdefault(key, {})[k] = e; s.sdq[(key, k)] = 1
        if s.bits: s.fs[s._h(key)] = 1
        while s.sc is not None and len(s.sdq) > s.sc:
            (ok, kk), _ = s.sdq.popitem(last=False); ee = s.slow[ok].pop(kk)
            if not s.slow[ok]: del s.slow[ok]
            s.sd.setdefault(ok, {})[kk] = ee; s.sd_writes += 1
            if s.bits: s.fd[s._h(ok)] = 1
    def _room(s):
        if s.cap is None or s.nent < s.cap: return True
        v = s._victim()
        if v is None: s.refused += 1; return False
        _, key, k = v; e = s.tab[key].pop(k); s.nent -= 1; s.evicted += 1
        if not s.tab[key]: del s.tab[key]
        s._place(key, k, e); return True
    def _fetch(s, key, ch):
        if key in s.slow and ch in s.slow[key]: s.sdq.pop((key, ch), None); e = s.slow[key].pop(ch); s.slow[key] or s.slow.pop(key); return e
        if key in s.sd and ch in s.sd[key]: e = s.sd[key].pop(ch); s.sd[key] or s.sd.pop(key); return e
    def _close(s):
        ch = tuple(sorted(s.pend.items())); s.pend = None; s.moments += 1
        for j, m in s.levels:
            c = s._ctx(j, m)
            if c is None: continue
            key = (j, m, c); d = s.tab.get(key); s._probe(key)
            if (key in s.slow and ch in s.slow[key]) or (key in s.sd and ch in s.sd[key]):
                if s._room(): e0 = s._fetch(key, ch); s.tab.setdefault(key, {})[ch] = e0; s.nent += 1
            d = s.tab.get(key)
            if d is not None and ch in d: e = d[ch]; d[ch] = (s._w(e) + 1.0, s.n)
            elif s._room(): s.tab.setdefault(key, {})[ch] = (1.0, s.n); s.nent += 1
            else: continue
            s.hits[(key, ch)] = s.hits.get((key, ch), 0) + 1
        for c, k in ch: s.snap[c] = k
        s.hist.append(tuple(s.snap)); s.hist = s.hist[-s.L:]; s.n += 1; return ch
    def predict(s, top=8):
        for j, m in s.levels:
            c = s._ctx(j, m)
            if c is not None and None not in s.snap: s._probe((j, m, c))
        return super().predict(top)
class TieredCtx(Tiered):
    """Context-granular variant: a context (all its followers) moves between tiers as ONE unit, chosen by the lowest total faded weight, so a lookup touches one tier. Models packing a context into one SDRAM word group / one card sector."""
    def _tier_has(s, key): return (key in s.slow, key in s.sd)
    def _ents(s, d): return sum(len(v) for v in d.values())
    def _evict_ctx(s, keep):
        best = None
        for key, d in s.tab.items():
            if key == keep: continue
            sc = sum(s._w(e) for e in d.values())
            if best is None or sc < best[0]: best = (sc, key)
        if best is None: return False
        key = best[1]; d = s.tab.pop(key); s.nent -= len(d); s.evicted += len(d)
        s.slow[key] = d; s.sdq[key] = len(d)
        if s.bits: s.fs[s._h(key)] += 1
        while s.sc is not None and sum(s.sdq.values()) > s.sc:
            ok, _ = s.sdq.popitem(last=False); dd = s.slow.pop(ok); s.sd[ok] = dd; s.sd_writes += 1
            if s.bits: s.fs[s._h(ok)] -= 1; s.fd[s._h(ok)] += 1
        return True
    def _room(s): return True
    def _close(s):
        ch = tuple(sorted(s.pend.items())); s.pend = None; s.moments += 1
        for j, m in s.levels:
            c = s._ctx(j, m)
            if c is None: continue
            key = (j, m, c); s._probe(key)
            for tier, f in ((s.slow, s.fs), (s.sd, s.fd)):
                if key in tier:
                    if s.bits: f[s._h(key)] -= 1
                    d0 = tier.pop(key); s.sdq.pop(key, None); s.tab.setdefault(key, {}).update(d0); s.nent += len(d0)
            d = s.tab.setdefault(key, {})
            if ch in d: e = d[ch]; d[ch] = (s._w(e) + 1.0, s.n)
            else: d[ch] = (1.0, s.n); s.nent += 1
            s.hits[(key, ch)] = s.hits.get((key, ch), 0) + 1
            while s.cap is not None and s.nent > s.cap and s._evict_ctx(key): pass
        for c, k in ch: s.snap[c] = k
        s.hist.append(tuple(s.snap)); s.hist = s.hist[-s.L:]; s.n += 1; return ch

def run(ev, cap, sc, bits, cls=None):
    m = (cls or Tiered)(cap, sc, bits, nch=3, L=4, align=2); groups = []; cur = []; t0 = None
    for i, (t, c, k) in enumerate(ev):
        if cur and t - t0 > 2: groups.append(cur); cur = []
        if not cur: t0 = t
        cur.append((i, c, k))
    groups.append(cur)
    for gi, g in enumerate(groups):
        d = {c: k for _, c, k in g}
        if gi >= 60 and 0 in d and None not in m.snap: m.channel_view(0, top=10 ** 6)
        for _, c, k in g: m.feed(gi * 1000, c, k)
        m.flush()
    return m
if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    ev, rare = F.world2(n); print("world: %d changes, %d routines; whole-context movement, COUNTING presence filters" % (len(ev), n))
    print("%-9s %-9s %-8s | %7s %8s %8s | %8s %9s | %7s %7s %9s" % ("fast_cap", "sdram_cap", "filter", "moments", "sdramPr", "sdPr", "us/mom", "(of it SD)", "fpSD", "fpSDRAM", "sd_writes"))
    for cap in (600, 1500, 3000):
      for sc in (None, 200):
        for bits in (None, 65536):
            m = run(ev, cap, sc, bits, TieredCtx); mo = max(1, m.moments)
            t_sdram = m.p_sdram * T_SDRAM / mo * 1e6; t_sd = m.p_sd * T_SD / mo * 1e6
            print("%-9d %-9s %-8s | %7d %8d %8d | %8.1f %9.1f | %7d %7d %9d" % (cap, sc if sc else "inf", bits if bits else "none", m.moments, m.p_sdram, m.p_sd, t_sdram + t_sd, t_sd, m.fp_sd, m.fp_sdram, m.sd_writes))
