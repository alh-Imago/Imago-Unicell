"""hexn_player_detect_v1: CAN THE OPPONENT'S STYLE BE TOLD FROM WHAT THE UNIT ALREADY SEES? (Python; model only; new file 31 Oct 2026). Alan, 13:00: 'on the different styles of play, can they be detected ... a player detector, allowing the system to switch out approaches as it runs?'
A fixed player (the module of hexn_layer1_module_v2 with fixed hand weights, no learning, worst-case plus gate as in mode G) plays game after game against one opponent while an OBSERVER collects, from the opponent's moves only, four numbers that need no extra knowledge of the opponent:
  hit   = the share of opponent moves the layer 3 model ranked first (cumulative);
  surp  = the share of opponent moves that were a layer 2 feed A surprise (verdict 1);
  miss  = the share of the opponent's chances (an immediate win for it, or an immediate win of mine to block) that it did NOT take;
  ctr   = the share of opponent moves in the centre column.
Snapshots are taken after 20, 50, 100, 200, 400 opponent moves (features keep accumulating across games, as a unit would). Opponents: habitN, noisy2, plain3, plain4. Seeds 0 to 7 for each.
Then: nearest-centroid classification (features scaled by their spread), trained on the even seeds and tested on the odd seeds and the reverse; reported as four-way and as the three groups that matter for the choice of approach (habit / noisy / strong = plain3 and plain4).
Usage: python3 tools/hexn_player_detect_v1.py collect OUT.json SEEDS | analyse OUT.json"""
import os, sys, json, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_blend_v2 as B, hexn_layer1_module_v2 as M2
SNAPS = (20, 50, 100, 200, 400); OPPS = ("habitN", "noisy2", "plain3", "plain4")
class Obs(M2.Mod2):
    def __init__(s): super().__init__("G", "hand", "none"); s.lastb = C.new(); s.nopp = s.hits = s.miss = s.chances = s.ctr = 0; s.snaps = {}
    def start(s, side): super().start(side); s.lastb = C.new()
    def __call__(s, b, who, rnd):
        c = super().__call__(b, who, rnd); s.lastb = [col[:] for col in b]; C.drop(s.lastb, c, who); return c
    def observe(s, side, c):
        if side != s.me:
            b = s.lastb; opp = side; legal = C.legal(b)
            def wins(w): return [x for x in legal if (C.drop(b, x, w), C.winner(b) == w, C.undo(b, x))[1]]
            mine = wins(opp); theirs = wins(3 - opp)
            if mine: s.chances += 1; s.miss += c not in mine
            elif theirs: s.chances += 1; s.miss += c not in theirs
            v = s.m.channel_view(1, top=1) if None not in s.m.snap else None
            s.hits += bool(v and v[0][0] == c); s.ctr += c == 3
            super().observe(side, c); s.nopp += 1
            if s.nopp in SNAPS: s.snaps[s.nopp] = [s.hits / s.nopp, s.nA / max(1, s.nev), s.miss / max(1, s.chances) if s.chances else 0.0, s.ctr / s.nopp]
        else: super().observe(side, c)
def collect(out, seeds):
    res = {}
    for o in OPPS:
        for sd in range(seeds):
            rnd = random.Random(100 + sd); op = B.opponent(o); me = Obs(); g = 0
            while me.nopp < SNAPS[-1]:
                if g % 2 == 0: B.game(me, op, rnd)
                else: B.game(op, me, rnd)
                g += 1
            res.setdefault(o, {})[sd] = {str(k): v for k, v in me.snaps.items()}; print(o, sd, "games", g, flush=True)
    json.dump(res, open(out, "w"))
def analyse(path):
    R = json.load(open(path)); seeds = sorted(R[OPPS[0]], key=int); names = ["hit", "surp", "miss", "ctr"]
    grp = {"habitN": "habit", "noisy2": "noisy", "plain3": "strong", "plain4": "strong"}
    for n in SNAPS:
        X = []; y = []; sdl = []
        for o in OPPS:
            for sd in seeds: X.append(R[o][sd][str(n)]); y.append(o); sdl.append(int(sd))
        X = np.array(X); y = np.array(y); sdl = np.array(sdl)
        if n == 100:
            print("feature means at 100 opponent moves (mean +- spread over seeds):")
            for o in OPPS: m = X[y == o]; print("  %-7s" % o, "  ".join("%s %.2f+-%.2f" % (k, m[:, i].mean(), m[:, i].std()) for i, k in enumerate(names)))
        acc4 = []; acc3 = []
        for par in (0, 1):
            tr = sdl % 2 == par; te = ~tr; sc = X[tr].std(0) + 1e-6
            cen = {o: (X[tr & (y == o)] / sc).mean(0) for o in OPPS}
            for i in np.where(te)[0]:
                d = {o: np.linalg.norm(X[i] / sc - cen[o]) for o in OPPS}; p = min(d, key=d.get); acc4.append(p == y[i]); acc3.append(grp[p] == grp[y[i]])
        print("after %3d opponent moves: four-way accuracy %.2f   three-group accuracy %.2f" % (n, np.mean(acc4), np.mean(acc3)))
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "collect": collect(a[1], int(a[2]))
    else: analyse(a[1])
