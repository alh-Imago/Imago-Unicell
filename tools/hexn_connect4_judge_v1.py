"""hexn_connect4_judge_v1: DOES THE HELPER AS A POSITION JUDGE LET LAYER 4 SEARCH SHALLOWER (Python + numpy only; no RTL, nothing on a card).
Alan, 30 Oct 2026, 16:22: model the helper first and see if that makes a real change. The judge is docs/hex-n/data/judge_v2_weights.json (tools/hexn_helper_judge_v1.py train on positions relabelled by tools/hexn_helper_judge_v2.py: a one-look copy of a 4-ply search of the hand score; trained on seeds 1001 and 1002, tested here on seeds 0 and up).
Layer 4 = tools/hexn_connect4_cand_v1.py P ('base' = the plain learned layer 3 as the opponent model, theta .04, free plies conf .8). Only the LEAF changes: 'hand' = tanh(score/40) as before; 'judge' = the network's value of the board. Opponent: lookahead(2) + 20% random moves.
Usage: python3 tools/hexn_connect4_judge_v1.py LEAF DMAX [GAMES] [SEEDS]   LEAF = hand or judge. Measured: online [win / draw / loss] over games 1-half and half+1-end, and positions created per move.
Limits: Connect Four; the judge was trained on the opponent families it is tested on (different seeds); one noise level; the hand score and the judge are both used only at the leaves."""
import os, sys, json, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_layer4_v1 as L1, hexn_connect4_stale_v2 as S2, hexn_connect4_cand_v1 as X, hexn_helper_judge_v1 as J
W = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "hex-n", "data", "judge_v2_weights.json")))
W1, b1, W2, b2 = (np.array(W[k], dtype=np.float32) for k in ("W1", "b1", "W2", "b2"))
class PJ(X.P):
    def __init__(s, leaf="hand", **kw): super().__init__("base", 0.0, **kw); s.leafkind = leaf; s.lc = {}
    def leaf(s, b):
        if s.leafkind == "hand": return super().leaf(b)
        k = tuple(tuple(col) for col in b); v = s.lc.get(k)
        if v is None:
            h = np.maximum(J.feats(b) @ W1 + b1, 0); v = float(np.tanh(h @ W2 + b2)[0]); s.lc[k] = v
        return v
def run(leaf, dmax, games, seed):
    rnd = random.Random(seed); opp = S2.noisy(C.make_lookahead(2), 0.2)
    pl = PJ(leaf, mode="tree3", theta=0.04, tactics=True, dmax=dmax, conf=0.8)
    return [L1.game(pl, opp, rnd) for _ in range(games)], pl.created / max(pl.moves, 1)
def main(leaf, dmax, games=60, seeds=6):
    h = games // 2; rs = [run(leaf, dmax, games, sd) for sd in range(seeds)]
    def sh(a, b): n = len(rs) * (b - a); return [sum(sum(1 for x in r[0][a:b] if x == k) for r in rs) / n for k in (1, 0, 2)]
    f, l = sh(0, h), sh(h, games)
    print("%-5s dmax %d  %.2f / %.2f / %.2f    %.2f / %.2f / %.2f   positions per move %6.0f  (%d seeds x %d games)" % (leaf, dmax, f[0], f[1], f[2], l[0], l[1], l[2], sum(r[1] for r in rs) / seeds, seeds, games), flush=True)
if __name__ == "__main__":
    a = sys.argv[1:]; main(a[0], int(a[1]), *(int(x) for x in a[2:]))
