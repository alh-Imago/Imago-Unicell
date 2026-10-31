"""hexn_layer1_int_v3: CLONE of hexn_layer1_int_v2.py (v1, v2 untouched) with a FINER TANH TABLE (31 Oct 2026; Alan, 12:58 step 1: why does the whole-number learner score about 0.06 to 0.09 below the float one against the habit opponent?).
Hypothesis tested here: the coarse table index (pre-activation steps of 1/64) is what costs the score. FINE = index steps of 1/256 (2048 entries over [-4, 4)), output still signed Q8 (so the learning rule is unchanged).
Usage: python3 tools/hexn_layer1_int_v3.py OPP MODE START ARM GAMES SEED WB   (the table is always the fine one)"""
import os, sys, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_blend_v2 as B, hexn_layer1_int_v1 as I, hexn_layer1_int_v2 as I2
LUT2 = [int(round(256 * math.tanh((i - 1024 + 0.5) / 256.0))) for i in range(2048)]
class OnlineIntFine(I.OnlineInt):
    def out(s, x):
        a = sum(w * v for w, v in zip(s.W, x)) + s.Bq; s.amax = max(s.amax, abs(a)); i = (a >> (s.WB - 8)) + 1024
        return LUT2[0 if i < 0 else 2047 if i > 2047 else i]
class ModIntFine(I.ModInt):
    def __init__(s, mode, start, arm, WB=14):
        super().__init__(mode, start, arm, WB); s.j = OnlineIntFine(start, arm, WB); B.JUDGE["o"] = s.j; s.J = s.j
if __name__ == "__main__":
    a = sys.argv[1:]; opp, mode, start, arm, games, seed, WB = a[0], a[1], a[2], a[3], int(a[4]), int(a[5]), int(a[6])
    rnd = random.Random(seed); op = B.opponent(opp); me = ModIntFine(mode, start, arm, WB); sc = 0.0
    print("opponent %s mode %s start %s arm %s seed %d WB %d fine table" % (opp, mode, start, arm, seed, WB), flush=True)
    for i in range(games):
        if i % 2 == 0: w = B.game(me, op, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = r
        else: w = B.game(op, me, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = -r
        me.learn(r); sc += (mine + 1) / 2
        if (i + 1) % 100 == 0: print("games %4d  score of the last 100: %.2f   Wq %s Bq %d" % (i + 1, sc / 100, me.j.W, me.j.Bq), flush=True); sc = 0.0
