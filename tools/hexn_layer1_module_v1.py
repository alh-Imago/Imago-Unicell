"""hexn_layer1_module_v1: THE TRAINING MODULE = LAYERS 2/3/4 TOGETHER TEACHING THE LAYER 1 JUDGE (Python + numpy; model only; new file 31 Oct 2026). Alan, 11:08: 'start there, so those layers come into one module: the design ends up with layer 1 the input, the training module and the neural'.
Build: layer 1 = the 7 detector counts; neural = the linear judge on them (hexn_layer1_online_v1.Online holds its weights and update rule); training module = the Hex player of tools/hexn_connect4_blend_v2.py (class Hex: its history model (the layer 3 model of hexn_layer3_v1, which learns the opponent's replies from the move stream) + layer 4's search) with the neural judge as its LEAF. After every move the module's search value (range -1..1, from the chosen move's root) is the teaching target for the position reached; after the game the last position gets the result. 'M' = module in worst-case mode (layer 4 search only, the layer 3 model unused, the same teacher as the 12:55 TD arm but with the Hex search); 'H' = module in blendH mode (layer 4 blends the layer 3 prediction of the opponent's reply by confidence x hit rate: layers 3 and 4 together).
HONEST SCOPE: the Layer3 object used here is the history-of-moves model; the layer 2 store (v5/v6/v7) is NOT in this loop (it is a separate component not yet wired to Connect Four).
Usage: python3 tools/hexn_layer1_module_v1.py OPP MODE START ARM GAMES [SEED]   (MODE M|H, START blank|hand, ARM TD|none)."""
import os, sys, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_blend_v2 as B, hexn_layer1_online_v1 as O
class Mod(B.Hex):
    def __init__(s, mode, start, arm, depth=3, eps=0.05):
        s.j = O.Online(start, arm); B.JUDGE["o"] = s.j; s.eps = eps
        super().__init__(depth, "minimax" if mode == "M" else "blendH", leafkind="o")
    def __call__(s, b, who, rnd):
        s.moves += 1; cache = {}; hist = tuple(s.m.hist[-5:]); snap = list(s.m.snap); best, bc = -9.0, []
        for c in [c for c in B.ORDER if b[c][C.ROWS - 1] == 0]:
            sn = list(snap); sn[0] = c; C.drop(b, c, who)
            v = s.val(b, 3 - who, s.depth - 1, 1.0, (hist + (tuple(sn),))[-5:], sn, cache); C.undo(b, c)
            if v > best + 1e-12: best, bc = v, [c]
            elif abs(v - best) <= 1e-12: bc.append(c)
        c = rnd.choice(C.legal(b)) if rnd.random() < s.eps else rnd.choice(bc)
        C.drop(b, c, who); s.j.rec.append(([col[:] for col in b], best if who == 1 else -best)); C.undo(b, c); return c
def run(opp, mode, start, arm, games, seed):
    rnd = random.Random(seed); op = B.opponent(opp); me = Mod(mode, start, arm); sc = 0.0
    print("opponent %s mode %s start %s arm %s seed %d" % (opp, mode, start, arm, seed), flush=True)
    for i in range(games):
        if i % 2 == 0: w = B.game(me, op, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = r
        else: w = B.game(op, me, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = -r
        me.j.learn(r); sc += (mine + 1) / 2
        if (i + 1) % 100 == 0: print("games %4d  score of the last 100: %.2f   weights %s bias %.2f" % (i + 1, sc / 100, np.round(me.j.w, 2).tolist(), me.j.bias), flush=True); sc = 0.0
if __name__ == "__main__":
    a = sys.argv[1:]; run(a[0], a[1], a[2], a[3], int(a[4]), int(a[5]) if len(a) > 5 else 0)
