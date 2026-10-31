"""hexn_layer1_int_v4: CLONE of hexn_layer1_int_v1.py (v1 to v3 untouched) CORRECTING THE BIAS STEP (31 Oct 2026). A hand check of the units (done while looking for the cause of the whole-number learner's score gap) showed that in v1 the bias is learned 8 times too slowly: the float rule moves the bias by 0.04 x err x gain (it multiplies the error term by 1), but the weights act on counts that the float model divides by 8 and are stored divided by 8 again, so the integer step for a weight is 0.04/64 per count, and the bias must be stepped as if its input were 64, not 8. v1 used 8. Everything else is as v1. The check of 'one step integer against float' in the 12:58 row compared only six weights, not the bias, so it did not show this.
Usage: python3 tools/hexn_layer1_int_v4.py OPP MODE START ARM GAMES SEED WB"""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import hexn_connect4_blend_v2 as B, hexn_layer1_int_v1 as I
class OnlineInt4(I.OnlineInt):
    def update(s, pos, t, m=1):
        x = I.xint(pos); o = s.out(x); err = o - int(round(max(-1.0, min(1.0, t)) * 256)); gain = 256 - ((o * o) >> 8); sh = 29 - s.WB; rnd = 1 << (sh - 1)
        for i in range(7): s.W[i] -= (5 * err * gain * x[i] * m + rnd) >> sh
        s.Bq -= (5 * err * gain * 64 * m + rnd) >> sh
        s.wmax = max(s.wmax, max(abs(w) for w in s.W), abs(s.Bq)); s.w = np.array(s.W, dtype=float) * 8 / (1 << s.WB); s.bias = s.Bq / (1 << s.WB)
class ModInt4(I.ModInt):
    def __init__(s, mode, start, arm, WB=14):
        super().__init__(mode, start, arm, WB); s.j = OnlineInt4(start, arm, WB); B.JUDGE["o"] = s.j; s.J = s.j
if __name__ == "__main__":
    a = sys.argv[1:]; opp, mode, start, arm, games, seed, WB = a[0], a[1], a[2], a[3], int(a[4]), int(a[5]), int(a[6])
    rnd = random.Random(seed); op = B.opponent(opp); me = ModInt4(mode, start, arm, WB); sc = 0.0
    print("opponent %s mode %s start %s arm %s seed %d WB %d bias step x64" % (opp, mode, start, arm, seed, WB), flush=True)
    for i in range(games):
        if i % 2 == 0: w = B.game(me, op, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = r
        else: w = B.game(op, me, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = -r
        me.learn(r); sc += (mine + 1) / 2
        if (i + 1) % 100 == 0: print("games %4d  score of the last 100: %.2f   Wq %s Bq %d" % (i + 1, sc / 100, me.j.W, me.j.Bq), flush=True); sc = 0.0
