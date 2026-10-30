"""hexn_helper_judge_v3: LEAF POSITIONS THE SEARCH REALLY REACHES, FOR A BETTER JUDGE (Python + numpy only; no RTL, nothing on a card; imports v1 and v2 of the judge unchanged).
Follows the 17:20 row of docs/hex-n/HEXN_DESIGN.md (first judge: no real change). Alan, 30 Oct 2026, 16:50: try the three improvements. This file does the first: instead of positions from the game itself, it records the positions the TREE of layer 4 (tools/hexn_connect4_cand_v1.py P, 'base' learned layer 3, hand-score leaf, theta .04, free plies conf .8) evaluates as leaves while it plays lookahead(2) or the blocker with 20% random moves. Duplicate boards within one game are kept once. The labels are then made by tools/hexn_helper_judge_v2.py relabel with a 6-ply teacher (second improvement); the network size is the argument H of hexn_helper_judge_v1.py train (third).
Usage: python3 tools/hexn_helper_judge_v3.py leaves OPP GAMES SEED DMAX MAXPER OUT.npz   (OPP = look or block; MAXPER = at most this many leaves kept per game, sampled)
Limits: Connect Four; leaves come from the hand-score planner."""
import os, sys, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_layer4_v1 as L1, hexn_connect4_stale_v2 as S2, hexn_connect4_cand_v1 as X, hexn_helper_judge_v1 as J
class Rec(X.P):
    def __init__(s, **kw): super().__init__("base", 0.0, **kw); s.seen = {}
    def leaf(s, b): s.seen[tuple(tuple(c) for c in b)] = 1; return super().leaf(b)
def leaves(opp_name, games, seed, dmax, maxper, out):
    rnd = random.Random(seed); opp = S2.noisy(C.make_lookahead(2) if opp_name == "look" else C.opp_blocker, 0.2)
    pl = Rec(mode="tree3", theta=0.04, tactics=True, dmax=dmax, conf=0.8); F = []; G = []
    for g in range(games):
        pl.seen = {}; b = C.new(); pl.start(); turn = 1; keep = {}
        while True:
            c = pl.pick(b, rnd) if turn == 1 else opp(b, 2, rnd); C.drop(b, c, turn); pl.observe(turn, c)
            for k in pl.seen: keep[k] = 1
            pl.seen = {}; w = C.winner(b)
            if w or C.full(b): break
            turn = 3 - turn
        ks = list(keep); rnd.shuffle(ks)
        for k in ks[:maxper]: F.append(J.feats([list(c) for c in k])); G.append(seed * 100000 + g)
    np.savez_compressed(out, F=np.array(F), Y=np.zeros(len(F), np.float32), G=np.array(G)); print("wrote", out, len(F), "leaf positions from", games, "games")
if __name__ == "__main__":
    a = sys.argv[1:]; leaves(a[1], int(a[2]), int(a[3]), int(a[4]), int(a[5]), a[6])
