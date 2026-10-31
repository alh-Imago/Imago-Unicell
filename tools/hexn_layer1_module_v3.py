"""hexn_layer1_module_v3: LAYER 2's PREDICTION AS A SECOND OPINION FOR LAYER 3 (Python; model only; new file 31 Oct 2026; module v2 untouched). Alan, 12:58: 'proceed through those steps' (step 2).
Mode GV = mode G of hexn_layer1_module_v2.py (feed A surprise halves the hit rate for the next search) plus: at the first opponent node of the search (the reply to each candidate move) the layer 2 feed A store is READ for its best predicted next opponent move (pbest, from the opponent's own last three moves) and compared with the top reply of the layer 3 model at that node. Agree: the hit rate is used as it is. Disagree: halved for that node's whole subtree. Layer 2 has no prediction: used as it is.
Usage: python3 tools/hexn_layer1_module_v3.py OPP MODE START ARM GAMES [SEED]   (MODE G|GV)."""
import os, sys, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_blend_v2 as B, hexn_layer1_module_v2 as M2, hexn_store_v7 as S7
class Mod3(M2.Mod2):
    def __init__(s, mode, start, arm): super().__init__("G", start, arm); s.v = mode == "GV"; s.p2 = None; s.nag = s.ndis = s.nnone = 0
    def __call__(s, b, who, rnd):
        o = s.A.step(S7.RD, 0, s.tt) if s.A.hist else {"plevel": 0, "pbest": 0}; s.p2 = o["pbest"] if o["plevel"] else None
        return super().__call__(b, who, rnd)
    def val(s, b, turn, depth, p, hist, snap, cache):
        if s.v and depth == s.depth - 1 and turn != s.me and None not in snap and C.winner(b) == 0:
            lv = B.l3_keys(s.m, hist, snap, cache); sv = s.hit
            if s.p2 is None or not lv: s.nnone += 1
            else:
                top = max(lv, key=lambda c: lv[c])
                if top == s.p2: s.nag += 1
                else: s.ndis += 1; s.hit = 0.5 * s.hit
            try: return super().val(b, turn, depth, p, hist, snap, cache)
            finally: s.hit = sv
        return super().val(b, turn, depth, p, hist, snap, cache)
def run(opp, mode, start, arm, games, seed):
    rnd = random.Random(seed); op = B.opponent(opp); me = Mod3(mode, start, arm); sc = 0.0
    print("opponent %s mode %s start %s arm %s seed %d" % (opp, mode, start, arm, seed), flush=True)
    for i in range(games):
        if i % 2 == 0: w = B.game(me, op, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = r
        else: w = B.game(op, me, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = -r
        me.learn(r); sc += (mine + 1) / 2
        if (i + 1) % 100 == 0: print("games %4d  score of the last 100: %.2f   weights %s bias %.2f   L2 vs L3 at first reply node: agree %d disagree %d none %d" % (i + 1, sc / 100, np.round(me.j.w, 2).tolist(), me.j.bias, me.nag, me.ndis, me.nnone), flush=True); sc = 0.0
if __name__ == "__main__":
    a = sys.argv[1:]; run(a[0], a[1], a[2], a[3], int(a[4]), int(a[5]) if len(a) > 5 else 0)
