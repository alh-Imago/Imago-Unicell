"""Python model only (no RTL): how to batch the card writes of the Tang tier. Three card-side strategies behind the same two upper levels (fast table, SDRAM victim level, rules of tools/hexn_tier_ref_v3.py):
 S0 'one buffer'   the hexn_tier_v3 rule: read-modify-write of the entry's sector through one write-back sector buffer.
 S1 'write queue'  demoted entries wait in a queue of Q entries (held in RAM) and are pushed out grouped by sector when it is full (each touched sector read-modify-written once).
 S2 'log'          demoted entries are APPENDED to an open 64-entry sector and written as one whole sector when full (no read before the write); an index in RAM (one word per key hash: sector and slot) says exactly where each key is, so a lookup needs no presence counter and no sector scan, and reads exactly one sector (none when the key is in the open sector); dead entries (promoted away) are reclaimed by compaction: when free sectors run low, the oldest sector is read and its live entries re-appended.
Times use the board figures: card read 0.6 ms, write 2.0 ms per 512-byte block (hexn_layer3_tiers_v1.py). Workload: Zipf(s) popularity over NK keys, 30 percent puts, the popular set drifts (shifts by a quarter of NK every STEPS/4). Everything synthetic; it compares strategies, it does not predict the real workload.
Usage: python3 tools/hexn_batch_model_v1.py [--nk 50000 --steps 60000 --fb 9 --ramb 12]"""
import argparse, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tier_ref_v3 as R
T_RD, T_WR = 0.6e-3, 2.0e-3
class S0(R.Tier3):
    name = "S0 one buffer"
    def stats(s): s.flush(); return s.n["sd_blk_rd"], s.n["sd_blk_wr"]
class S1(R.Tier3):
    name = "S1 write queue"
    def __init__(s, Q=1024, **k): super().__init__(**k); s.Q = Q; s.q = {}; s.qhit = 0
    def _ins_sd(s, h, v):
        s.n["demote_sd"] += 1; s.q[h] = v
        if len(s.q) >= s.Q: s._push()
    def _push(s):
        by = {}
        for h, v in s.q.items(): by.setdefault(R.top(h, s.SB, s.KW) & ((1 << s.SB) - 1), []).append((h, v))
        s.q = {}
        for sec in sorted(by):
            s._access(sec)
            for h, v in by[sec]:
                for i in range(s.SPS):
                    if s.buf[i] is None: s.buf[i] = (h, v); s.dirty = True; s._cnt(s._bucket(h), +1); break
                else: s.n["sd_full"] += 1
    def _locate(s, h, sl, sec, hb):
        e = s.sdram.get(sl)
        if e is not None and e[0] == h: del s.sdram[sl]; return e[1]
        if h in s.q: s.qhit += 1; return s.q.pop(h)
        return super()._locate_card(h, sec, hb) if False else R.Tier3._locate(s, h, sl, sec, hb)
    def stats(s): s._push(); s.flush(); return s.n["sd_blk_rd"], s.n["sd_blk_wr"]
class S2(R.Tier3):
    name = "S2 log + index"
    def __init__(s, L=2048, low=4, **k):
        super().__init__(**k); s.L = L; s.low = low; s.index = {}; s.sectors = {}; s.live = {}; s.open = []; s.open_id = 0; s.tail = 0; s.rd = 0; s.wr = 0; s.gc_rd = 0; s.gc_moved = 0; s.opened_hit = 0
    def _append(s, h, v):
        s.open.append((h, v)); s.index[h] = (s.open_id, len(s.open) - 1)
        if len(s.open) == s.SPS: s._close()
    def _close(s):
        s.sectors[s.open_id] = list(s.open); s.live[s.open_id] = sum(1 for i, (h, v) in enumerate(s.open) if s.index.get(h) == (s.open_id, i)); s.wr += 1
        s.open = []; s.open_id += 1
        while s.open_id - s.tail > s.L - s.low: s._gc()
    def _gc(s):
        sec = s.tail; s.tail += 1; ent = s.sectors.pop(sec); s.live.pop(sec, None)
        if any(s.index.get(h) == (sec, i) for i, (h, v) in enumerate(ent)): s.rd += 1; s.gc_rd += 1
        for i, (h, v) in enumerate(ent):
            if s.index.get(h) == (sec, i): del s.index[h]; s.gc_moved += 1; s._append(h, v)
    def _ins_sd(s, h, v):
        s.n["demote_sd"] += 1; s._append(h, v)
    def _locate(s, h, sl, sec, hb):
        e = s.sdram.get(sl)
        if e is not None and e[0] == h: del s.sdram[sl]; return e[1]
        loc = s.index.get(h)
        if loc is None: s.n["skip"] += 1; return None
        sid, i = loc
        if sid == s.open_id: v = s.open[i][1]; s.opened_hit += 1
        else: v = s.sectors[sid][i][1]; s.rd += 1
        del s.index[h]
        if sid != s.open_id: s.live[sid] -= 1
        return v
    def stats(s): return s.rd, s.wr
def workload(nk, steps, seed=3, zipf=1.0):
    rnd = random.Random(seed); w = [1.0 / (r + 1) ** zipf for r in range(nk)]; cum = []; t = 0.0
    for x in w: t += x; cum.append(t)
    import bisect
    for n in range(steps):
        shift = (n * 4 // steps) * (nk // 4)
        r = bisect.bisect_left(cum, rnd.random() * t); k = (r + shift) % nk
        yield n, ((k + 1) * 0x2545F491) & 0x3FFFF, rnd.random() < 0.3
def run(cls, nk, steps, fb, ramb, kw=18, **extra):
    t = cls(KW=kw, FB=fb, BMB=14, RAMB=ramb, SB=12, **extra)
    for n, key, put in workload(nk, steps):
        if put: t.put(key, n & 0x3FFFF)
        else: t.get(key)
    rd, wr = t.stats(); return t, rd, wr
def main():
    a = argparse.ArgumentParser(); a.add_argument("--nk", type=int, default=50000); a.add_argument("--steps", type=int, default=60000)
    a.add_argument("--fb", type=int, default=9); a.add_argument("--ramb", type=int, default=12); a = a.parse_args()
    print("keys %d, steps %d, fast slots %d, SDRAM slots %d (scaled down so the card is used)" % (a.nk, a.steps, 1 << a.fb, 1 << a.ramb))
    print("%-16s %9s %9s %12s %10s" % ("strategy", "reads", "writes", "card time s", "ms/op"))
    for cls, ex in ((S0, {}), (S1, dict(Q=1024)), (S1, dict(Q=8192)), (S2, dict(L=2048))):
        t, rd, wr = run(cls, a.nk, a.steps, a.fb, a.ramb, **ex)
        nm = cls.name + (" Q=%d" % ex["Q"] if "Q" in ex else "")
        tm = rd * T_RD + wr * T_WR; print("%-16s %9d %9d %12.1f %10.3f" % (nm, rd, wr, tm, 1000 * tm / a.steps))
        if cls is S2: print("   log: %d reads were compaction (%d entries moved), %d lookups answered from the open sector, live entries on card %d" % (t.gc_rd, t.gc_moved, t.opened_hit, len(t.index)))
if __name__ == "__main__": main()
