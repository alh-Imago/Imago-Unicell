"""hexn_layer1_module_v2: THE TRAINING MODULE WITH LAYER 2 ADDED (Python + numpy; model only; new file 31 Oct 2026; v1 untouched). Alan, 12:06: 'add in the layer 2 sets of data, then move into the whole number'.
Layer 2 = tools/hexn_store_v7.py (StoreV7, the bit-true store model: N=2 sightings to store a pair, LMAX=3, look-back 3, LRU eviction), ONE STORE PER FEED, as in the design (one layer 2 per layer 1 feed):
  feed A = the OPPONENT's column stream (what the opponent did). Each opponent move is first READ (RD: verdict 0 expected / 1 contradiction = context known but this move never seen after it / 2 novel) then OBSERVED (OBS). Verdict 1 = SURPRISE.
  feed B = the judge's own verdict on my positions, in 5 buckets (what the neural thinks of the position after my move); the same RD/OBS pair; verdict 1 = SURPRISE.
Uses (the 'gate' form, the only harmless one found in the 31 Oct 05:10 row): mode G: when feed A reports a surprise on the opponent's last move, layer 4 trusts the layer 3 prediction at half weight for my next move (the hit rate is halved for that one search). Mode GB: G plus feed B: the judge's learning step is DOUBLED for a position whose feed B verdict was a surprise (the neural is told 'this was unexpected, learn more from it').
Usage: python3 tools/hexn_layer1_module_v2.py OPP MODE START ARM GAMES [SEED]   (MODE G|GB; START blank|hand; ARM TD|none). Prints the same blocks as v1 plus counts of A and B surprises."""
import os, sys, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_blend_v2 as B, hexn_layer1_online_v1 as O, hexn_layer1_judge_v1 as L, hexn_layer1_module_v1 as M1
import hexn_store_v7 as S7
def mk(): return S7.StoreV7(N=2, W=80, CCAP=32, EVB=3, IB=8, RB=7, LMAX=3, lookback=3)
class Mod2(M1.Mod):
    def __init__(s, mode, start, arm, **kw):
        super().__init__("H", start, arm, **kw); s.mode2 = mode; s.A = mk(); s.Bs = mk(); s.tt = 0; s.sA = False; s.base = 0.0; s.nA = s.nB = s.nev = 0
    def start(s, side):
        super().start(side); s.A.step(S7.CLR); s.Bs.step(S7.CLR); s.sA = False
    def observe(s, side, c):
        if side != s.me: s.hit = s.base
        super().observe(side, c)
        if side != s.me:
            s.base = s.hit; s.tt += 4; o = s.A.step(S7.RD, c, s.tt); s.A.step(S7.OBS, c, s.tt); s.nev += 1
            s.sA = o["verdict"] == 1; s.nA += s.sA
            if s.sA: s.hit = 0.5 * s.hit
    def __call__(s, b, who, rnd):
        c = super().__call__(b, who, rnd); pos, vx = s.j.rec[-1]; bk = min(4, int((vx + 1) * 2.5)); s.tt += 4
        o = s.Bs.step(S7.RD, bk, s.tt); s.Bs.step(S7.OBS, bk, s.tt); sb = o["verdict"] == 1; s.nB += sb; s.j.rec[-1] = (pos, vx, sb); return c
    def learn(s, r):
        j = s.j
        if j.arm == "none": j.rec = []; return
        n = len(j.rec)
        for k, e in enumerate(j.rec):
            pos, v = e[0], e[1]; sb = e[2] if len(e) > 2 else False
            nxt = j.rec[k + 1][1] if k + 1 < n else r; t = nxt
            x = L.l1(pos); o = np.tanh(x @ j.w + j.bias); d = 2 * (o - t) * (1 - o * o); lr = j.lr * (2.0 if (s.mode2 == "GB" and sb) else 1.0)
            j.w -= lr * d * x; j.bias -= lr * d
        j.rec = []
def run(opp, mode, start, arm, games, seed):
    rnd = random.Random(seed); op = B.opponent(opp); me = Mod2(mode, start, arm); sc = 0.0
    print("opponent %s mode %s start %s arm %s seed %d" % (opp, mode, start, arm, seed), flush=True)
    for i in range(games):
        if i % 2 == 0: w = B.game(me, op, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = r
        else: w = B.game(op, me, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = -r
        me.learn(r); sc += (mine + 1) / 2
        if (i + 1) % 100 == 0: print("games %4d  score of the last 100: %.2f   weights %s bias %.2f   A surprises %.2f per opp move, B %.2f per my move" % (i + 1, sc / 100, np.round(me.j.w, 2).tolist(), me.j.bias, me.nA / max(1, me.nev), me.nB / max(1, me.nev)), flush=True); sc = 0.0
if __name__ == "__main__":
    a = sys.argv[1:]; run(a[0], a[1], a[2], a[3], int(a[4]), int(a[5]) if len(a) > 5 else 0)
