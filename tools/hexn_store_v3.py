"""hexn_store_v3: bit-true model of the layer 2 store WITH REWARD VALUES (the reference for rtl/hexn_store_v3.v). Standalone copy of the hexn_store_v2.StoreV2 rules (that file is untouched). Reward side of Alan's plan (27 Oct 2026); design from tools/hexn_reward_v1.py (value per stored entry, constant step, goal read).
Additions to v2:
 - every KNOWN entry has a VALUE, signed 8 bit (reward 1.0 = +64, -0.5 = -32), 0 when the entry is created;
 - a QUEUE of the last 32 known slots that OBS used (a hit, or a pair just promoted); LOAD does not queue; the queue is a ring (the oldest is overwritten when full);
 - command REW (4) with a signed 8-bit reward r: for every queued slot, oldest first, value += step(r - value) with d = r - value: d >= 1: (d + 2^s - 1) >> s (rounded UP), d <= 0: d >> s (arithmetic shift, rounded DOWN), so the value always reaches the reward exactly in both directions (a plain arithmetic shift stalls early for rises and falls to the end for drops; the first draft did that); s = vshift, step 2^-s, s = 3 is 0.125, the slot is skipped if it has since been emptied; then the queue is emptied. The reward is the teacher's signal at the end of a routine.
 - GOAL READ: with the history after the last command, among the successors stored at the longest known context of length <= glvl (host setting 1..3), the entry with the highest value (ties: higher seen, then lower event) -> gbest (event) and gval (its value); gbest/gval are given by every OBS and RD (computed on the history BEFORE that event is added, as the prediction is).
Limits: queued slots may have been overwritten since (a full table); reward granularity 1/64; one reward per routine, not a trace; as v2.
Usage: python3 tools/hexn_store_v3.py (self-test)"""
import os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_store_v2 as M2    # only for key_bits
CLR, OBS, LOAD, RD, REW = 0, 1, 2, 3, 4
class StoreV3:
    """Same store as hexn_store_v2.StoreV2 (rules copied, v2 untouched) plus values, the used-slot queue, REW and the goal read."""
    def __init__(s, N=3, W=80, KCAP=128, CCAP=32, vshift=3, glvl=1):
        assert 1 <= N <= 15
        s.N, s.W, s.KCAP, s.CCAP, s.vshift, s.glvl = N, W, KCAP, CCAP, vshift, glvl
        s.k = [None] * KCAP; s.val = [0] * KCAP; s.c = [None] * CCAP; s.q = collections.deque(maxlen=32)
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
            ctx = s._ctx(j); es = [(i, e) for i, e in enumerate(s.k) if e and e[0][0] == j and e[0][1] == ctx]
            if not es: continue
            bi, best = min(es, key=lambda ie: (-ie[1][1], ie[1][0][2]))
            bv = min(es, key=lambda ie: (-s.val[ie[0]], -ie[1][1], ie[1][0][2]))
            r[j] = dict(tot=sum(e[1] for _, e in es), bseen=best[1], bev=best[0][2], ex=any(e[0][2] == ev for _, e in es), vev=bv[1][0][2], vval=s.val[bv[0]])
        return r
    def _klook(s, key):
        hit = next((i for i, e in enumerate(s.k) if e and e[0] == key), None)
        free = next((i for i, e in enumerate(s.k) if e is None), None)
        vic = None
        for i, e in enumerate(s.k):
            if e and (vic is None or e[1] < s.k[vic][1]): vic = i
        return hit, free, vic
    def _addk(s, key, seen, free, vic):
        i = free if free is not None else vic
        if free is None: s.dropk += 1
        s.k[i] = [key, seen, 0]; s.val[i] = 0; return i
    def step(s, cmd, ev=0, t=0, r=0):
        t &= 0xFFFF
        out = dict(verdict=3, vlevel=0, plevel=0, pbest=0, pbest_seen=0, ptotal=0, gbest=0, gval=0)
        if cmd == CLR: s.hist = []; return out
        if cmd == REW:
            for i in s.q:
                if s.k[i]: d = r - s.val[i]; s.val[i] += ((d + (1 << s.vshift) - 1) >> s.vshift) if d > 0 else (d >> s.vshift)
            s.q.clear(); return out
        if cmd in (OBS, LOAD) and not s.hist:
            s.hist = [ev]; return out
        sc = s._scan(ev); lv = max(sc) if sc else 0
        if lv: out.update(plevel=lv, pbest=sc[lv]["bev"], pbest_seen=sc[lv]["bseen"], ptotal=sc[lv]["tot"])
        gl = max((j for j in sc if j <= s.glvl), default=0)
        if gl: out.update(gbest=sc[gl]["vev"], gval=sc[gl]["vval"])
        out.update(vlevel=lv, verdict=(2 if not lv else (0 if sc[lv]["ex"] else 1)))
        if cmd == RD: return out
        if cmd == OBS and out["verdict"] == 1:
            ctx = s._ctx(lv)
            for e in s.k:
                if e and e[0][0] == lv and e[0][1] == ctx: e[2] = min(255, e[2] + 1)
        for j in (1, 2, 3):
            if len(s.hist) < j: continue
            key = (j, s._ctx(j), ev); hit, free, vic = s._klook(key)
            if hit is not None:
                s.k[hit][1] = min(255, s.k[hit][1] + 1)
                if cmd == OBS: s.q.append(hit)
                continue
            if cmd == LOAD: s._addk(key, 1, free, vic); continue
            ch = next((i for i, e in enumerate(s.c) if e and e[0] == key), None)
            exp = ch is not None and ((t - s.c[ch][2]) & 0xFFFF) >= s.W
            cnt = s.c[ch][1] + 1 if (ch is not None and not exp) else 1
            st = s.c[ch][2] if (ch is not None and not exp) else t
            if cnt >= s.N:
                if ch is not None: s.c[ch] = None
                i = s._addk(key, cnt, free, vic); s.promoted += 1; s.q.append(i)
            elif ch is not None: s.c[ch][1], s.c[ch][2] = cnt, st
            else:
                cf = next((i for i, e in enumerate(s.c) if e is None), None)
                if cf is not None: s.c[cf] = [key, 1, t]
                else:
                    cv = min((i for i, e in enumerate(s.c)), key=lambda i: (s.c[i][1], -((t - s.c[i][2]) & 0xFFFF), i)); s.c[cv] = [key, 1, t]; s.dropc += 1
        s.hist = (s.hist + [ev])[-3:]
        return out
def val_bits(v): return v & 0xFF
def main():
    import hexn_layer2_v2 as V
    V.R = V.runs(); runs = [[k - 12 for k, _ in r] for r in V.R]
    st = StoreV3(N=3, W=80)
    for r in runs[:2]:
        st.step(CLR)
        for x in r: st.step(LOAD, x, 0)
    st.step(CLR); out = None
    for i, x in enumerate(runs[2][:12]): out = st.step(OBS, x, 1000 + i)
    st.step(REW, r=64); print("queued slots rewarded; values now:", sorted(v for v in st.val if v)[:8], "| goal read after the last event:", st.step(RD, 0, 2000))
if __name__ == "__main__": main()
