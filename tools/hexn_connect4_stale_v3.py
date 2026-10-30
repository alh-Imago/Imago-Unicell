"""hexn_connect4_stale_v3: CHECK OF A SURPRISE IN stale_v2 (Python only; no RTL, nothing on a card). In tools/hexn_connect4_stale_v2.py the policy 'every50' read an EMPTY copy of layer 3 for games 1-50 (the copy was taken at game 1, before anything was learned) and won 0.98 against lookahead(2) + 20% random moves, against 0.74 for the live layer 3. This file runs the planner with an empty copy for ALL games ('empty': layer 4 sees no learned opponent model, only the tactics prior and a uniform spread) beside the live one, on both opponents with 20% random moves, 6 seeds x 100 games. stale_v2 is imported unchanged. Limits as v2."""
import os, sys, copy, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_layer4_v1 as L1
import hexn_connect4_stale_v2 as S2
class EmptyPlanner(S2.StalePlanner):
    def start(s):
        had = s.games == 0
        super().start()
        if had: s.mread = copy.deepcopy(s.m)       # taken at game 1, never refreshed (policy 'live' leaves it None afterwards, so force it)
    def odist(s, b, hist, snap, legal_, cache):
        return super().odist(b, hist, snap, legal_, cache)
def run(opp, games, seed, policy):
    rnd = random.Random(seed)
    pl = EmptyPlanner(policy="frozen" if policy == "empty" else "live", mode="tree3", theta=0.04, tactics=True, dmax=4, conf=0.8)
    if policy == "empty": pl.policy = "none"      # no scheduled refresh: keeps the game-1 copy
    return [L1.game(pl, opp, rnd) for _ in range(games)]
def main(games=100, seeds=6):
    h = games // 2
    for oname, opp in (("lookahead(2) + 20% random", S2.noisy(C.make_lookahead(2), 0.2)), ("blocker + 20% random", S2.noisy(C.opp_blocker, 0.2))):
        print("\n%s: X = layer 4 planner; online [win / draw / loss], games 1-%d and %d-%d; %d seeds x %d games" % (oname, h, h + 1, games, seeds, games), flush=True)
        for p in ("live", "empty"):
            rs = [run(opp, games, sd, p) for sd in range(seeds)]
            def sh(a, b): n = len(rs) * (b - a); return [sum(sum(1 for x in r[a:b] if x == k) for r in rs) / n for k in (1, 0, 2)]
            f, l = sh(0, h), sh(h, games)
            print("%-6s %.2f / %.2f / %.2f    %.2f / %.2f / %.2f" % (p, f[0], f[1], f[2], l[0], l[1], l[2]), flush=True)
if __name__ == "__main__": main()
