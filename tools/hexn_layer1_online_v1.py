"""hexn_layer1_online_v1: A LAYER 1 JUDGE THAT LEARNS WHILE IT PLAYS, NO HOST AND NO STORED DATA (Python + numpy; model only; new file 31 Oct 2026). Alan, 10:41: yes to the online test; layers 2 to 4 'do real work ... they become a training module'.
The judge is the linear layer 1 judge of hexn_layer1_judge_v1 (7 detector counts -> 8 weights -> tanh), value for X. It plays Connect Four at depth 3 (5% random moves) against a fixed opponent and after EVERY game nudges its weights, one small step per position it created, with plain gradient steps on the tanh squared error (lr 0.02). The three ways of getting the target (the 'training module'):
  MC  = the game result only (what the outside world says; no layer 4 help)
  TD  = layer 4's own search: the target for the position after my move is the value the depth-3 search found at my NEXT turn (the last position gets the result)
  MIX = the average of the two.
Starts: 'blank' = all weights 0 (knows nothing); 'hand' = the hand score's weights (1,4,9 -> 0.2, 0.8, 1.8 for own, minus for the opponent). 'fixed' = hand weights, never updated (the baseline).
Usage: python3 tools/hexn_layer1_online_v1.py OPP START ARM GAMES [SEED]   (ARM = MC | TD | MIX | none) - prints the learner's score per block of 100 games and the final weights.
Limits: Connect Four only; float arithmetic (whole-number update rule not yet tried); one opponent per run; learning stays on during the scored blocks, so scores include the cost of learning."""
import os, sys, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_blend_v2 as B, hexn_layer1_judge_v1 as L
class Online:
    def __init__(s, start, arm, lr=0.02, depth=3, eps=0.05):
        s.w = np.zeros(7); s.bias = 0.0
        if start == "hand": s.w[:3] = [.2, .8, 1.8]; s.w[3:6] = [-.2, -.8, -1.8]
        s.arm, s.lr, s.depth, s.eps = arm, lr, depth, eps; s.rec = []
    def value(s, b): return float(np.tanh(L.l1(b) @ s.w + s.bias))
    def __call__(s, b, who, rnd):
        best, bc = None, []
        for c in [c for c in B.ORDER if b[c][C.ROWS - 1] == 0]:
            C.drop(b, c, who); v = B.search_j(b, who, 3 - who, s.depth - 1, -10 ** 9, 10 ** 9, s); C.undo(b, c)
            if best is None or v > best: best, bc = v, [c]
            elif v == best: bc.append(c)
        c = rnd.choice(C.legal(b)) if rnd.random() < s.eps else rnd.choice(bc)
        vx = max(-1.0, min(1.0, best / 1000.0 if abs(best) < 5000 else (1.0 if best > 0 else -1.0))); vx = vx if who == 1 else -vx
        C.drop(b, c, who); s.rec.append(([col[:] for col in b], vx)); C.undo(b, c); return c
    def learn(s, r):
        if s.arm == "none": s.rec = []; return
        n = len(s.rec)
        for k, (pos, v) in enumerate(s.rec):
            nxt = s.rec[k + 1][1] if k + 1 < n else r
            t = r if s.arm == "MC" else nxt if s.arm == "TD" else 0.5 * (r + nxt)
            x = L.l1(pos); o = np.tanh(x @ s.w + s.bias); d = 2 * (o - t) * (1 - o * o)
            s.w -= s.lr * d * x; s.bias -= s.lr * d
        s.rec = []
def run(opp, start, arm, games, seed):
    rnd = random.Random(seed); op = B.opponent(opp); me = Online(start, arm); sc = 0.0; tot = 0.0
    print("opponent %s start %s arm %s seed %d" % (opp, start, arm, seed), flush=True)
    for i in range(games):
        if i % 2 == 0: w = B.game(me, op, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = r
        else: w = B.game(op, me, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = -r
        me.learn(r); sc += (mine + 1) / 2; tot += (mine + 1) / 2
        if (i + 1) % 100 == 0: print("games %4d  score of the last 100: %.2f   weights %s bias %.2f" % (i + 1, sc / 100, np.round(me.w, 2).tolist(), me.bias), flush=True); sc = 0.0
if __name__ == "__main__":
    a = sys.argv[1:]; run(a[0], a[1], a[2], int(a[3]), int(a[4]) if len(a) > 4 else 0)
