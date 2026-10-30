"""hexn_connect4_cand_v3: cand_v2 WITH THE SEARCH DEPTH AS AN ARGUMENT (Python only; no RTL, nothing on a card; imports cand_v1 and stale_v2 unchanged).
Reason (30 Oct 2026, 15:05): the same EMPTY model (tactics prior and flat spread only) won 10 of 10 games at depth 4 and lost 10 of 10 at depth 6 against plain lookahead(2); the 29 Oct 'uniform model lost 0/100' was depth 6. Question: is the advantage of the empty model over the learned one on the noisy opponent specific to depth 4?
Usage: python3 tools/hexn_connect4_cand_v3.py VARIANT LAM DMAX [GAMES] [SEEDS]   opponent = lookahead(2) + 20% random moves; theta .04; conf .8."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_layer4_v1 as L1, hexn_connect4_stale_v2 as S2, hexn_connect4_cand_v1 as X
def run(variant, lam, dmax, games, seed):
    rnd = random.Random(seed); opp = S2.noisy(C.make_lookahead(2), 0.2)
    pl = X.P(variant, lam, mode="tree3", theta=0.04, tactics=True, dmax=dmax, conf=0.8)
    return [L1.game(pl, opp, rnd) for _ in range(games)]
def main(variant, lam, dmax, games=50, seeds=4):
    h = games // 2; rs = [run(variant, lam, dmax, games, sd) for sd in range(seeds)]
    def sh(a, b): n = len(rs) * (b - a); return [sum(sum(1 for x in r[a:b] if x == k) for r in rs) / n for k in (1, 0, 2)]
    f, l = sh(0, h), sh(h, games)
    print("%-6s lam %.2f dmax %d noisy  %.2f / %.2f / %.2f    %.2f / %.2f / %.2f   (%d seeds x %d games)" % (variant, lam, dmax, f[0], f[1], f[2], l[0], l[1], l[2], seeds, games), flush=True)
if __name__ == "__main__":
    a = sys.argv[1:]; main(a[0], float(a[1]), int(a[2]), *(int(x) for x in a[3:]))
