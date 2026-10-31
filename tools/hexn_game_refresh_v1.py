"""hexn_game_refresh_v1: THE TABLE REFRESH ON THE GAME SIDE (Python + numpy; float model; new file 31 Oct 2026). Alan, 16:05: 'i was going to suggest applying the same to the game side as well' (the running average set the sensor neural's weights, 19:10 and 19:30 rows).
Mapping: the sensor kept a running mean and spread of the height per animal and rebuilt the weights from them. The game judge is a two-class case (will this position win or lose for me?). Its inputs x are the 7 layer 1 numbers. From the SAME teaching targets the gradient rule uses (t = the next search value, or the game result at the end), every recorded position adds to two running tables with weights p = (1+t)/2 for 'winning' and 1-p for 'losing': weight sum, sum of x, sum of x*x. After each game: mean_w, mean_l, pooled within-class variance per input; log-odds weight Wstat_i = (mean_w - mean_l)_i / var_i; judge weight a = c * Wstat / 2 (value = P(win) - P(loss) = tanh(logodds / 2)), bias = -sum(a_i * (mean_w + mean_l)_i / 2). The hand weights count as N0 pseudo-positions: W = (N0*hand + N*stat) / (N0 + N). c (default 0.5) lowers the overconfidence of treating the 7 inputs as independent. No gradient step, no learning rate.
Arms: fixed (worst-case search, hand weights never updated), learn (the 14:10 module: blendH, gate G, gradient learning), ref (same module and gate, refresh in place of the gradient). Hand start, depth 3, as in the earlier rows.
Usage: python3 tools/hexn_game_refresh_v1.py OPP ARM GAMES SEED [C] [N0]"""
import os, sys, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_blend_v2 as B, hexn_layer1_judge_v1 as L, hexn_layer1_module_v2 as M2
class ModRef(M2.Mod2):
    def __init__(s, c=0.5, n0=300.0):
        super().__init__("G", "hand", "TD"); s.c = c; s.n0 = n0; s.hand = s.j.w.copy(); s.hb = float(s.j.bias)
        s.S = np.zeros(2); s.M = np.zeros((2, 7)); s.Q = np.zeros((2, 7))
    def learn(s, r):
        j = s.j; n = len(j.rec)
        for k, e in enumerate(j.rec):
            t = j.rec[k + 1][1] if k + 1 < n else r; p = (1 + max(-1.0, min(1.0, t))) / 2; x = L.l1(e[0])
            for c, w in ((0, p), (1, 1 - p)): s.S[c] += w; s.M[c] += w * x; s.Q[c] += w * x * x
        j.rec = []
        if s.S.min() < 1e-6: return
        mu = s.M / s.S[:, None]; N = s.S.sum(); var = ((s.Q[0] - s.M[0] ** 2 / s.S[0]) + (s.Q[1] - s.M[1] ** 2 / s.S[1])) / N + 1e-3
        a = s.c * (mu[0] - mu[1]) / var / 2; b = -float(np.sum(a * (mu[0] + mu[1]) / 2)); k = N / (N + s.n0)
        j.w = (1 - k) * s.hand + k * a; j.bias = (1 - k) * s.hb + k * b
def make(arm, c, n0):
    if arm == "ref": m = ModRef(c, n0)
    else: m = M2.Mod2("G", "hand", "TD")
    m.mode = "minimax" if arm == "fixed" else "blendH"; m.j.arm = "none" if arm == "fixed" else "TD"; return m
def run(opp, arm, games, seed, c=0.5, n0=300.0):
    rnd = random.Random(seed); op = B.opponent(opp); me = make(arm, c, n0); sc = 0.0; out = []
    for i in range(games):
        if i % 2 == 0: w = B.game(me, op, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = r
        else: w = B.game(op, me, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = -r
        me.learn(r); sc += (mine + 1) / 2
        if (i + 1) % 100 == 0: out.append(sc / 100); sc = 0.0
    print("RESULT %s %s c=%g n0=%g seed %d blocks %s weights %s bias %.2f" % (opp, arm, c, n0, seed, " ".join("%.2f" % v for v in out), np.round(me.j.w, 2).tolist(), me.j.bias), flush=True)
if __name__ == "__main__":
    a = sys.argv[1:]; run(a[0], a[1], int(a[2]), int(a[3]), float(a[4]) if len(a) > 4 else 0.5, float(a[5]) if len(a) > 5 else 300.0)
