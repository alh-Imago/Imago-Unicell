"""hexn_connect4_cand_v2: TWO CONTROLS FOR cand_v1 (Python only; no RTL, nothing on a card; imports tools/hexn_connect4_cand_v1.py unchanged).
cand_v1 (30 Oct 2026) showed that mixing a flat spread into layer 3's reply improves layer 4 against lookahead(2) + 20% random moves, all the way to an empty model. Two questions: (1) is the cause the tree's CUTOFFS (theta .04 prunes replies below 4%; free plies at conf .8) rather than the model being wrong? (2) what does the same mixing cost against the plain, non-random lookahead(2), where the learned model was essential on 29 Oct?
Usage: python3 tools/hexn_connect4_cand_v2.py VARIANT LAM THETA CONF OPP [GAMES] [SEEDS]   OPP = noisy (lookahead(2) + 20% random) or plain (lookahead(2)). CONF 2.0 = no free plies.
Measured as in cand_v1. Limits as cand_v1."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_layer4_v1 as L1, hexn_connect4_stale_v2 as S2, hexn_connect4_cand_v1 as X
def run(variant, lam, theta, conf, opp_name, games, seed):
    rnd = random.Random(seed); opp = S2.noisy(C.make_lookahead(2), 0.2) if opp_name == "noisy" else C.make_lookahead(2)
    pl = X.P(variant, lam, mode="tree3", theta=theta, tactics=True, dmax=4, conf=conf)
    return [L1.game(pl, opp, rnd) for _ in range(games)]
def main(variant, lam, theta, conf, opp_name, games=100, seeds=6):
    h = games // 2; rs = [run(variant, lam, theta, conf, opp_name, games, sd) for sd in range(seeds)]
    def sh(a, b): n = len(rs) * (b - a); return [sum(sum(1 for x in r[a:b] if x == k) for r in rs) / n for k in (1, 0, 2)]
    f, l = sh(0, h), sh(h, games)
    print("%-6s lam %.2f theta %.2f conf %.1f %-5s  %.2f / %.2f / %.2f    %.2f / %.2f / %.2f" % (variant, lam, theta, conf, opp_name, f[0], f[1], f[2], l[0], l[1], l[2]), flush=True)
if __name__ == "__main__":
    a = sys.argv[1:]; main(a[0], float(a[1]), float(a[2]), float(a[3]), a[4], *(int(x) for x in a[5:]))
