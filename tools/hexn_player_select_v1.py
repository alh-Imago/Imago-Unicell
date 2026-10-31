"""hexn_player_select_v1: A SELECTOR DRIVEN BY THE PLAYER DETECTOR (Python; model only; new file 31 Oct 2026). Alan, 13:00: 'a player detector, allowing the system to switch out approaches as it runs'.
Arms (all start with the hand weights, depth 3, 5% random moves, as in the 13:30 and 14:10 rows):
  fixed  = worst-case search, hand weights never updated (the safe approach: best against noisy2 and plain3 in earlier rows);
  learn  = blend of layer 3 prediction with the layer 2 gate and the neural LEARNING from the search value (mode G, hand start; best against the habit opponent);
  select = starts as `fixed`; after 400 opponent moves the detector (hexn_player_detect_v1 features: hit, surp, miss, ctr; nearest centroid, centroids and scales taken from the 8-seed collection at 400 moves in the detect file) names the opponent's group; 'habit' switches to `learn`, anything else stays `fixed`. The decision is taken once.
Usage: python3 tools/hexn_player_select_v1.py OPP ARM GAMES SEED DETECT.json  (prints blocks of 100 games and, for select, the decision)."""
import os, sys, json, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_blend_v2 as B, hexn_player_detect_v1 as D
GROUP = {"habitN": "habit", "noisy2": "noisy", "plain3": "strong", "plain4": "strong"}
class Sel(D.Obs):
    def __init__(s, arm, det):
        super().__init__(); s.arm = arm; s.decided = None; s.to_learn()
        if arm != "learn": s.to_fixed()
        R = json.load(open(det)); X = {o: np.array([R[o][k]["400"] for k in R[o]]) for o in R}; allx = np.concatenate(list(X.values()))
        s.sc = allx.std(0) + 1e-6; s.cen = {o: (X[o] / s.sc).mean(0) for o in X}
    def to_fixed(s): s.mode = "minimax"; s.j.arm = "none"
    def to_learn(s): s.mode = "blendH"; s.j.arm = "TD"
    def observe(s, side, c):
        super().observe(side, c)
        if s.arm == "select" and side != s.me and s.nopp == 400 and s.decided is None:
            f = np.array(s.snaps[400]) / s.sc; d = {o: np.linalg.norm(f - s.cen[o]) for o in s.cen}; p = min(d, key=d.get); s.decided = GROUP[p]
            if s.decided == "habit": s.to_learn()
            else: s.to_fixed()
def run(opp, arm, games, seed, det):
    rnd = random.Random(seed); op = B.opponent(opp); me = Sel(arm, det); sc = 0.0
    print("opponent %s arm %s seed %d" % (opp, arm, seed), flush=True)
    for i in range(games):
        if i % 2 == 0: w = B.game(me, op, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = r
        else: w = B.game(op, me, rnd); r = 1 if w == 1 else -1 if w == 2 else 0; mine = -r
        me.learn(r); sc += (mine + 1) / 2
        if (i + 1) % 100 == 0: print("games %4d  score of the last 100: %.2f   mode %s  decided %s" % (i + 1, sc / 100, me.mode, me.decided), flush=True); sc = 0.0
if __name__ == "__main__":
    a = sys.argv[1:]; run(a[0], a[1], int(a[2]), int(a[3]), a[4])
