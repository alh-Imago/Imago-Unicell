"""hexn_connect4_plainsearch_v1: THE CHEAP BASELINE FOR HEX-N AS A GAME ENGINE (Python only; no RTL, nothing on a card).
Alan, 30 Oct 2026, 20:14: and as a game engine? Baseline: a PLAIN alpha-beta minimax player with the hand score (tools/hexn_connect4_v1.py make_lookahead(depth), the same code the opponent uses), no learning at all, X moving first, against the same opponent as the layer 4 tests: lookahead(2) + 20% random moves. Same seeds 0 to 5, same game loop style.
Usage: python3 tools/hexn_connect4_plainsearch_v1.py DEPTH [GAMES] [SEEDS]. Output: online [win / draw / loss] over the first and second half of the games.
Limits: Connect Four; one opponent; hand score as the only knowledge."""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_stale_v2 as S2
def run(depth, games, seed):
    rnd = random.Random(seed); x = C.make_lookahead(depth); opp = S2.noisy(C.make_lookahead(2), 0.2)
    return [C.play_game(x, opp, rnd)[0] for _ in range(games)]
def main(depth, games=60, seeds=6):
    h = games // 2; rs = [run(depth, games, sd) for sd in range(seeds)]
    def sh(a, b): n = len(rs) * (b - a); return [sum(sum(1 for x in r[a:b] if x == k) for r in rs) / n for k in (1, 0, 2)]
    f, l = sh(0, h), sh(h, games)
    print("plain minimax depth %d  %.2f / %.2f / %.2f    %.2f / %.2f / %.2f   (%d seeds x %d games)" % (depth, f[0], f[1], f[2], l[0], l[1], l[2], seeds, games), flush=True)
if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]; main(*a)
