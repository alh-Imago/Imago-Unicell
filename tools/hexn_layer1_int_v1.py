"""hexn_layer1_int_v1: THE LAYER 1 JUDGE AND ITS LEARNING RULE IN WHOLE NUMBERS (Python; model only; new file 31 Oct 2026). Alan, 12:06: 'then move into the whole number'.
Everything the neural does is an integer operation, so a cell can hold it as it stands:
 inputs  x_i = the layer 1 counts (pure lines holding 1, 2, 3 counters for X, then for O: six small integers) and 8 x parity (so every input has the scale of a count);
 weights Wq_i, bias Bq: signed integers with WB fractional bits (WB = 14: 'Q14'; the float weight on counts/8 is 8 x Wq / 2^WB);
 forward  a = sum(Wq_i x_i) + Bq (a wide integer); index = (a >> (WB-6)) + 256 clipped to 0..511; output o = LUT[index] (512 entries, tanh over [-4,4) in steps of 1/64, scaled by 256: a signed 9-bit number);
 learning err = o - t (t = the teacher's value scaled by 256 and rounded); gain = 256 - (o*o >> 8); delta_i = (5 * err * gain * x_i * m + round) >> (29 - WB); Wq_i -= delta_i; the bias uses x = 8; m = 1 (2 when a surprise doubles the step). The constant 5 >> 29 reproduces the float rule lr = 0.02 to within 2.3%.
Same Connect Four stack as hexn_layer1_module_v2.py (layer 1 counts -> neural; teaching module = layer 2 stores (feed A gate, feed B step doubling) + layer 3 history model + layer 4 search), only the neural and its update are integer.
Usage: python3 tools/hexn_layer1_int_v1.py OPP MODE START ARM GAMES SEED WB   (MODE G|GB). Reports: the score in blocks of 100 games, the final integer weights, the largest absolute accumulator seen (bits needed) and the largest absolute weight."""
import os, sys, math, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_blend_v2 as B, hexn_layer1_judge_v1 as L, hexn_layer1_module_v2 as M2
LUT = [int(round(256 * math.tanh((i - 256 + 0.5) / 64.0))) for i in range(512)]
def xint(b):
    f = L.l1(b); x = [int(round(v * 8)) for v in f[:6]]; x.append(8 * int(f[6])); return x
class OnlineInt:
    def __init__(s, start, arm, WB=14, lr=0.02):
        s.WB, s.arm, s.lr = WB, arm, lr; s.W = [0] * 7; s.Bq = 0; s.rec = []; s.amax = 0; s.wmax = 0
        if start == "hand":
            for i, v in enumerate((.2, .8, 1.8, -.2, -.8, -1.8)): s.W[i] = int(round(v * (1 << WB) / 8))
        s.w = np.array(s.W, dtype=float) * 8 / (1 << WB); s.bias = 0.0
    def out(s, x):
        a = sum(w * v for w, v in zip(s.W, x)) + s.Bq; s.amax = max(s.amax, abs(a)); i = (a >> (s.WB - 6)) + 256
        return LUT[0 if i < 0 else 511 if i > 511 else i]
    def value(s, b): return s.out(xint(b)) / 256.0
    def update(s, pos, t, m=1):
        x = xint(pos); o = s.out(x); err = o - int(round(max(-1.0, min(1.0, t)) * 256)); gain = 256 - ((o * o) >> 8); sh = 29 - s.WB; rnd = 1 << (sh - 1)
        for i in range(7): s.W[i] -= (5 * err * gain * x[i] * m + rnd) >> sh
        s.Bq -= (5 * err * gain * 8 * m + rnd) >> sh
        s.wmax = max(s.wmax, max(abs(w) for w in s.W), abs(s.Bq)); s.w = np.array(s.W, dtype=float) * 8 / (1 << s.WB); s.bias = s.Bq / (1 << s.WB)
class ModInt(M2.Mod2):
    def __init__(s, mode, start, arm, WB=14):
        super().__init__(mode, start, arm); s.j = OnlineInt(start, arm, WB); B.JUDGE["o"] = s.j; s.J = s.j
    def learn(s, r):
        j = s.j
        if j.arm == "none": j.rec = []; return
        n = len(j.rec)
        for k, e in enumerate(j.rec):
            sb = e[2] if len(e) > 2 else False; t = j.rec[k + 1][1] if k + 1 < n else r
            j.update(e[0], t, 2 if (s.mode2 == "GB" and sb) else 1)
        j.rec = []
def run(opp, mode, start, arm, games, seed, WB):
    rnd = random.Random(seed); op = B.opponent(opp); me = ModInt(mode, start, arm, WB); sc = 0.0
    print("opponent %s mode %s start %s arm %s seed %d WB %d (integer)" % (opp, mode, start, arm, seed, WB), flush=True)
    for i in range(games):
        if i % 2 == 0: w = B.game(me, op, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = r
        else: w = B.game(op, me, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = -r
        me.learn(r); sc += (mine + 1) / 2
        if (i + 1) % 100 == 0: print("games %4d  score of the last 100: %.2f   Wq %s Bq %d   max|acc| %d (%d bits) max|W| %d (%d bits)" % (i + 1, sc / 100, me.j.W, me.j.Bq, me.j.amax, me.j.amax.bit_length() + 1, me.j.wmax, me.j.wmax.bit_length() + 1), flush=True); sc = 0.0
if __name__ == "__main__":
    a = sys.argv[1:]; run(a[0], a[1], a[2], a[3], int(a[4]), int(a[5]), int(a[6]))
