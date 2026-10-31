"""hexn_layer1_int_v2: CLONE of hexn_layer1_int_v1.py (v1 untouched) adding STOCHASTIC ROUNDING of the learning step (31 Oct 2026; Alan, 12:58: 'proceed through those steps'; step 1 = settle the habit-opponent gap of the whole-number learner).
Why: with a fixed rounding offset a step smaller than one unit is lost every time and a small bias builds up; stochastic rounding adds a random number in [0, 2^shift) before the shift, so the AVERAGE step is right (in hardware: a free-running LFSR of `shift` bits; here Python's random with a fixed seed stands in for it).
Usage: python3 tools/hexn_layer1_int_v2.py OPP MODE START ARM GAMES SEED WB SR   (SR 0 = as v1, 1 = stochastic rounding). Prints the same blocks as v1."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_blend_v2 as B, hexn_layer1_int_v1 as I
class OnlineIntSR(I.OnlineInt):
    def __init__(s, start, arm, WB=14, SR=1): super().__init__(start, arm, WB); s.SR = SR; s.lfsr = random.Random(12345)
    def update(s, pos, t, m=1):
        if not s.SR: return super().update(pos, t, m)
        x = I.xint(pos); o = s.out(x); err = o - int(round(max(-1.0, min(1.0, t)) * 256)); gain = 256 - ((o * o) >> 8); sh = 29 - s.WB
        for i in range(7): s.W[i] -= (5 * err * gain * x[i] * m + s.lfsr.getrandbits(sh)) >> sh
        s.Bq -= (5 * err * gain * 8 * m + s.lfsr.getrandbits(sh)) >> sh
        s.wmax = max(s.wmax, max(abs(w) for w in s.W), abs(s.Bq))
        import numpy as np; s.w = np.array(s.W, dtype=float) * 8 / (1 << s.WB); s.bias = s.Bq / (1 << s.WB)
class ModIntSR(I.ModInt):
    def __init__(s, mode, start, arm, WB=14, SR=1):
        super().__init__(mode, start, arm, WB); s.j = OnlineIntSR(start, arm, WB, SR); B.JUDGE["o"] = s.j; s.J = s.j
def run(opp, mode, start, arm, games, seed, WB, SR):
    rnd = random.Random(seed); op = B.opponent(opp); me = ModIntSR(mode, start, arm, WB, SR); sc = 0.0
    print("opponent %s mode %s start %s arm %s seed %d WB %d SR %d (integer)" % (opp, mode, start, arm, seed, WB, SR), flush=True)
    for i in range(games):
        if i % 2 == 0: w = B.game(me, op, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = r
        else: w = B.game(op, me, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = -r
        me.learn(r); sc += (mine + 1) / 2
        if (i + 1) % 100 == 0: print("games %4d  score of the last 100: %.2f   Wq %s Bq %d   max|acc| %d (%d bits) max|W| %d (%d bits)" % (i + 1, sc / 100, me.j.W, me.j.Bq, me.j.amax, me.j.amax.bit_length() + 1, me.j.wmax, me.j.wmax.bit_length() + 1), flush=True); sc = 0.0
if __name__ == "__main__":
    a = sys.argv[1:]; run(a[0], a[1], a[2], a[3], int(a[4]), int(a[5]), int(a[6]), int(a[7]))
