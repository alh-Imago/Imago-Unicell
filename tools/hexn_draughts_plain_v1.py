"""hexn_draughts_plain_v1: THE PLAIN BASELINE FOR DRAUGHTS (Python only; no RTL, nothing on a card; stage 2 of the draughts plan, 30 Oct 2026). An alpha-beta (negamax) player with a hand-written score and no learning, the draughts counterpart of tools/hexn_connect4_v1.py make_lookahead. Imports tools/hexn_draughts_v1.py (the rules engine) unchanged.
Score (from the side to move): man 100 + 3 per row advanced; king 160 + a small bonus for the centre; mine minus theirs. A side with no legal move loses (-10000 minus the remaining depth, so a quicker loss is worse). Captures are searched on past the depth limit for up to 6 extra plies, so the search does not stop in the middle of an exchange. Captures are mandatory so the move list is already forced there. Ties between equal moves are broken at random.
`match(a, b, games, seed, open_random)`: plays `games` games, colours alternating, with the first `open_random` plies chosen at random so games differ; returns the results as (a wins, draws, b wins). Players are objects with `pick(game, rnd)`.
Limits: a first, simple score; no transposition table, no iterative deepening; Python speed; the draw rule is the engine's (80 quiet plies / 400 plies)."""
import os, sys, random, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_draughts_v1 as D
CENTER = {D.SQ[(r, c)] for r in (2, 3, 4, 5) for c in (2, 3, 4, 5) if (r, c) in D.SQ}
def score(b, turn):
    s = 0
    for i, p in enumerate(b):
        if not p: continue
        if p == 1: v = 100 + 3 * (7 - i // 4)
        elif p == 3: v = 100 + 3 * (i // 4)
        else: v = 160 + (4 if i in CENTER else 0)
        s += v if D.side(p) == turn else -v
    return s
def search(b, turn, depth, alpha, beta, ext=0):
    mv = D.moves(b, turn)
    if not mv: return -(10000 + depth)
    if depth <= 0 and not (mv[0][1] and ext < 6): return score(b, turn)
    if depth <= 0: ext += 1
    best = -10 ** 9
    for m in mv:
        rec = D.apply(b, m); v = -search(b, 3 - turn, depth - 1, -beta, -alpha, ext); D.undo(b, m, rec)
        if v > best: best = v
        if best > alpha: alpha = best
        if alpha >= beta: break
    return best
class Plain:
    def __init__(s, depth): s.depth = depth; s.nodes = 0
    def pick(s, g, rnd):
        mv = g.legal(); best, bm = -10 ** 9, []
        for m in mv:
            rec = D.apply(g.b, m); v = -search(g.b, 3 - g.turn, s.depth - 1, -10 ** 9, 10 ** 9); D.undo(g.b, m, rec)
            if v > best: best, bm = v, [m]
            elif v == best: bm.append(m)
        return rnd.choice(bm)
class Rand:
    def pick(s, g, rnd): return rnd.choice(g.legal())
def game(px, po, rnd, open_random=2):
    g = D.Game()
    while not g.result():
        if g.plies < open_random: g.play(rnd.choice(g.legal()))
        else: g.play((px if g.turn == 1 else po).pick(g, rnd))
    return g.result()
def match(a, b, games, seed, open_random=2):
    rnd = random.Random(seed); aw = dr = bw = 0
    for i in range(games):
        if i % 2 == 0: r = game(a, b, rnd, open_random); aw += r == 1; bw += r == 2
        else: r = game(b, a, rnd, open_random); aw += r == 2; bw += r == 1
        dr += r == 3
    return aw, dr, bw
if __name__ == "__main__":
    a = sys.argv[1:]; da, db, n = int(a[0]), int(a[1]), int(a[2])
    pa = Rand() if da == 0 else Plain(da); pb = Rand() if db == 0 else Plain(db); t = time.time()
    r = match(pa, pb, n, 0); print("depth %d (wins %d) vs depth %d (wins %d), draws %d, %d games, %.1f s" % (da, r[0], db, r[2], r[1], n, time.time() - t))
