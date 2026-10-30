"""hexn_connect4_stale_v1: DOES LAYER 4 PLAY AS WELL WHEN IT READS A STALE COPY OF LAYER 3 (Python only; no RTL, nothing on a card).
Alan, 30 Oct 2026, 10:37: use layer 3 twice, a live one for the current inputs and outputs and a second one, fed from the first, as the predictive model for layer 4. This is the cheap question from the design row of 10:45: does the planner lose strength when its copy lags behind the live layer 3?
Set-up: Planner3 (tools/hexn_connect4_layer4_v3.py, depth 4, free plies at confidence .8, tree3 with tactics) plays X online against an opponent. Its own layer 3 `m` (two channels) is the LIVE one: it learns every move as before. The tree reads the opponent's likely replies from `mread`, a deep copy of `m` taken on a schedule:
 live    - the tree reads `m` itself (the baseline, as in layer4_v3)
 every1  - copy taken at the START of every game (so it lags by the moves of the game in progress)
 every10 / every50 - copy taken at the start of every 10th / 50th game
 frozen  - one copy taken at the start of game 50, never refreshed
Measured: win / draw / loss of X over the first half and the second half of the games, summed over seeds. Limits: planner only (not the layer 3 chooser of suggest_v1), small samples, one depth setting, nothing tuned."""
import os, sys, copy, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_layer4_v1 as L1, hexn_connect4_layer4_v3 as L3P
class StalePlanner(L3P.Planner3):
    def __init__(s, policy="live", **kw):
        super().__init__(**kw); s.policy, s.mread, s.games = policy, None, 0
    def start(s):
        super().start(); s.games += 1; g = s.games - 1; p = s.policy
        if p == "live": s.mread = None
        elif p == "every1": s.mread = copy.deepcopy(s.m)
        elif p == "every10" and g % 10 == 0: s.mread = copy.deepcopy(s.m)
        elif p == "every50" and g % 50 == 0: s.mread = copy.deepcopy(s.m)
        elif p == "frozen" and g == 50: s.mread = copy.deepcopy(s.m)
    def odist(s, b, hist, snap, legal_, cache):
        live = s.m
        if s.mread is not None: s.m = s.mread
        try: return super().odist(b, hist, snap, legal_, cache)
        finally: s.m = live
POLICIES = ["live", "every1", "every10", "every50", "frozen"]
def run(opp, games, seed, policy):
    rnd = random.Random(seed); pl = StalePlanner(policy=policy, mode="tree3", theta=0.04, tactics=True, dmax=4, conf=0.8)
    return [L1.game(pl, opp, rnd) for _ in range(games)]
def main(games=100, seeds=3, only=0):
    h = games // 2
    for i, (oname, opp) in enumerate((("BLOCKER opponent", C.opp_blocker), ("lookahead(2) opponent", C.make_lookahead(2))), 1):
        if only not in (0, i): continue
        print("\n%s: X = layer 4 planner, depth 4, free plies conf .8; online [win / draw / loss], games 1-%d and %d-%d; %d seed(s) x %d games" % (oname, h, h + 1, games, seeds, games), flush=True)
        for p in POLICIES:
            rs = [run(opp, games, sd, p) for sd in range(seeds)]
            def sh(a, b): n = len(rs) * (b - a); return [sum(sum(1 for x in r[a:b] if x == k) for r in rs) / n for k in (1, 0, 2)]
            f, l = sh(0, h), sh(h, games)
            print("%-8s %.2f / %.2f / %.2f    %.2f / %.2f / %.2f" % (p, f[0], f[1], f[2], l[0], l[1], l[2]), flush=True)
if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]; main(*a)
