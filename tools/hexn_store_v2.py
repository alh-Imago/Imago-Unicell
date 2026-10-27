"""hexn_store_v2: BIT-TRUE model of the layer 2 store (the reference that rtl/hexn_store_v1.v is checked against; clone of hexn_store_v1's design with the rules fixed so that hardware and model cannot differ). New file; hexn_store_v1.py is untouched.
Differences from hexn_store_v1 (all so the hardware rule is exact):
 - events are classes 0..7 (code 12..19 minus 12); history is the last 3 events; the first event after clear only enters the history;
 - slots, not dictionaries: KNOWN has KCAP slots and CAND has CCAP slots; a new entry goes to the LOWEST free slot; a full table overwrites the weakest slot (KNOWN: lowest seen; CAND: lowest count, then OLDEST by age = (t - start) mod 65536, so it stays right when the 16-bit clock wraps); ties go to the lowest slot number;
 - tumbling window only (count + start time; a sighting at least W after the start restarts the count); time is a 16-bit value from the host and differences wrap at 65536;
 - seen and contra are 8-bit saturating counts; candidate count is at most 15 (N is 1 to 15);
 - retrieve: best next event = highest seen at the longest known context, ties to the LOWEST event number (v1 left ties to Python set order);
 - the update looks each pair up afresh at each context length (a promotion at one length can evict an entry needed at the next).
Commands (same as the RTL): CLR, OBS (observe: predict, self-check, update store), LOAD (host load: every pair added or seen+1, no verdict, no candidates), RD (retrieve only).
Verdict codes: 0 ok, 1 contradiction, 2 novel (no context known), 3 start (no history yet).
Usage: python3 tools/hexn_store_v2.py   (self-test on the real runs)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
CLR, OBS, LOAD, RD = 0, 1, 2, 3
class StoreV2:
    def __init__(s, N=3, W=80, KCAP=128, CCAP=32):
        assert 1 <= N <= 15
        s.N, s.W, s.KCAP, s.CCAP = N, W, KCAP, CCAP
        s.k = [None] * KCAP      # [key, seen, contra]; key = (len, ctx tuple, ev)
        s.c = [None] * CCAP      # [key, count, start]
        s.hist = []; s.promoted = s.dropk = s.dropc = 0
    @property
    def n_known(s): return sum(1 for e in s.k if e)
    @property
    def n_cand(s): return sum(1 for e in s.c if e)
    def _ctx(s, j): return tuple(s.hist[-j:])
    def _scan(s, ev):
        r = {}
        for j in (1, 2, 3):
            if len(s.hist) < j: continue
            ctx = s._ctx(j); es = [e for e in s.k if e and e[0][0] == j and e[0][1] == ctx]
            if not es: continue
            best = min(es, key=lambda e: (-e[1], e[0][2]))
            r[j] = dict(tot=sum(e[1] for e in es), bseen=best[1], bev=best[0][2], ex=any(e[0][2] == ev for e in es))
        return r
    def _klook(s, key):
        hit = next((i for i, e in enumerate(s.k) if e and e[0] == key), None)
        free = next((i for i, e in enumerate(s.k) if e is None), None)
        vic = None
        for i, e in enumerate(s.k):
            if e and (vic is None or e[1] < s.k[vic][1]): vic = i
        return hit, free, vic
    def _addk(s, key, seen, free, vic):
        if free is not None: s.k[free] = [key, seen, 0]
        else: s.k[vic] = [key, seen, 0]; s.dropk += 1
    def step(s, cmd, ev=0, t=0):
        t &= 0xFFFF
        out = dict(verdict=3, vlevel=0, plevel=0, pbest=0, pbest_seen=0, ptotal=0)
        if cmd == CLR: s.hist = []; return out
        if cmd in (OBS, LOAD) and not s.hist:
            s.hist = [ev]; return out
        r = s._scan(ev); lv = max(r) if r else 0
        if lv: out.update(plevel=lv, pbest=r[lv]["bev"], pbest_seen=r[lv]["bseen"], ptotal=r[lv]["tot"])
        out.update(vlevel=lv, verdict=(2 if not lv else (0 if r[lv]["ex"] else 1)))
        if cmd == RD: return out
        if cmd == OBS and out["verdict"] == 1:
            ctx = s._ctx(lv)
            for e in s.k:
                if e and e[0][0] == lv and e[0][1] == ctx: e[2] = min(255, e[2] + 1)
        for j in (1, 2, 3):
            if len(s.hist) < j: continue
            key = (j, s._ctx(j), ev); hit, free, vic = s._klook(key)
            if hit is not None: s.k[hit][1] = min(255, s.k[hit][1] + 1); continue
            if cmd == LOAD: s._addk(key, 1, free, vic); continue
            ch = next((i for i, e in enumerate(s.c) if e and e[0] == key), None)
            exp = ch is not None and ((t - s.c[ch][2]) & 0xFFFF) >= s.W
            cnt = s.c[ch][1] + 1 if (ch is not None and not exp) else 1
            st = s.c[ch][2] if (ch is not None and not exp) else t
            if cnt >= s.N:
                if ch is not None: s.c[ch] = None
                s._addk(key, cnt, free, vic); s.promoted += 1
            elif ch is not None: s.c[ch][1], s.c[ch][2] = cnt, st
            else:
                cf = next((i for i, e in enumerate(s.c) if e is None), None)
                if cf is not None: s.c[cf] = [key, 1, t]
                else:
                    cv = min((i for i, e in enumerate(s.c)), key=lambda i: (s.c[i][1], -((t - s.c[i][2]) & 0xFFFF), i)); s.c[cv] = [key, 1, t]; s.dropc += 1
        s.hist = (s.hist + [ev])[-3:]
        return out
def key_bits(key):
    j, ctx, ev = key; c = 0
    for n, x in enumerate(reversed(ctx)): c |= x << (3 * n)      # newest event in the low bits
    return (j << 12) | (c << 3) | ev
def main():
    import hexn_layer2_v2 as V
    V.R = V.runs(); runs = [[k - 12 for k, _ in r] for r in V.R]
    st = StoreV2(N=3, W=80)
    for r in runs[:2]:
        st.step(CLR)
        for x in r: st.step(LOAD, x, 0)
    st.step(CLR); flags = []
    for i, x in enumerate(runs[2]):
        o = st.step(OBS, x, 1000 + i)
        if o["verdict"] in (1, 2): flags.append(i + 1)
    print("trained on runs 1 and 2 (host load), run 3 online: flagged events", flags, "| known", st.n_known, "| candidates", st.n_cand)
if __name__ == "__main__": main()
