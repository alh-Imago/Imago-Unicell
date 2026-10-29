"""hexn_connect4_layer4_v1: FIRST MODEL OF LAYER 4, THE STRATEGIST, in Connect Four (Python only; no RTL, nothing on a card; layers 2 is not used).
Alan, 29 Oct 2026: layer 4 plans the possible choices as a tree and builds a path to the goal (a win); layer 3 builds a predictive model from the moves played and predicts ahead; layer 4 varies the depth of each branch by the predicted branch confidence, so short paths cost little but stay available; the tree is pruned at each point.
What this model does (every setting below is a first guess, not a tuned value):
 - It SEES the board now (the game's state) and the possible next positions; layer 3 (tools/hexn_layer3_v1.py Layer3, unchanged, two channels: 0 = X's columns, 1 = O's columns, path memory 5 snapshots, masks (1,1) and (1,0)) sees only the stream of columns, learns it as the games go, and is asked for the likely replies of O.
 - At X's turn: (1) FORCED replies are computed by layer 4 itself from the board: win now; else block O's win now. (2) Otherwise a TREE: X chooses (maximum), O's reply is an EXPECTATION over a distribution. The distribution comes from layer 3's predicted columns (weights), with the unseen mass spread evenly over the legal columns; with `tactics` on, a forced reply of O (win now, else block X's win now) takes 0.8 of the mass. A branch is followed while its path probability (the product of the predicted probabilities of O's replies on it) is at least `theta`, up to `dmax` plies; at the end of a branch the position is valued by the open-lines score (tools/hexn_connect4_v1.py `score`), squashed to -1..+1; a win is +1, a loss -1. Branches below `theta` are pruned (valued at once, not expanded). X plays the column with the best value; ties at random.
 - Layer 3 learns every move of every game (both sides), prediction is made BEFORE the move is learned.
Variants: forced only (no tree); tree with a uniform opponent model (the same cut rule); tree with layer 3's prediction; tree with layer 3's prediction but without the tactics prior.
Measured per variant and opponent: win / draw / loss share of the games (online, as the games go, first half and second half), and the mean number of tree nodes per move (the cost).
Limits: Python search on a fixed game, small sample, layer 3 contexts are move histories, nothing tuned, X is always first."""
import os, sys, copy, random, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_v1 as V1, hexn_connect4_v1 as C
COLS, ROWS, START = C.COLS, C.ROWS, 7
ORDER = C.ORDER
def lands(b, c): return sum(1 for v in b[c] if v)
def wins_at(b, c, r, who):
    """does a counter of `who` at (c, r) (already placed) make four?"""
    for dc, dr in ((1, 0), (0, 1), (1, 1), (1, -1)):
        n = 1
        for sgn in (1, -1):
            x, y = c + sgn * dc, r + sgn * dr
            while 0 <= x < COLS and 0 <= y < ROWS and b[x][y] == who: n += 1; x += sgn * dc; y += sgn * dr
        if n >= 4: return True
    return False
def can_win(b, who):
    out = []
    for c in range(COLS):
        r = lands(b, c)
        if r < ROWS:
            b[c][r] = who; w = wins_at(b, c, r, who); b[c][r] = 0
            if w: out.append(c)
    return out
def l3_cols(m, hist, snap, cache):
    """predicted columns of O (channel 1) after the given (hist, snap): dict col -> weight, from layer 3's tables (read only)"""
    k = hist
    if k in cache: return cache[k]
    t = copy.copy(m); t.hist = list(hist); t.snap = list(snap)
    v = dict(t.channel_view(1, top=10 ** 6)) if None not in snap else {}
    cache[k] = v; return v
class Planner:
    def __init__(s, mode, theta=0.04, dmax=6, tactics=True):
        s.mode, s.theta, s.dmax, s.tactics = mode, theta, dmax, tactics; s.nodes = 0; s.moves = 0
        s.m = V1.Layer3(nch=2, L=5, align=2, half=10 ** 9, masks=[(1, 1), (1, 0)]); s.t = 0
    def start(s):
        s.m.hist = []; s.m.snap = [None, None]; s.t += 20; s.m.feed(s.t, 1, START); s.m.flush()
    def observe(s, who, c): s.t += 5; s.m.feed(s.t, 0 if who == 1 else 1, c); s.m.flush()
    # ---- opponent model ----
    def odist(s, b, hist, snap, legal_, cache):
        n = len(legal_); base = {c: 1.0 / n for c in legal_}
        if s.mode in ("tree3", "tree3_nt"):
            v = l3_cols(s.m, hist, snap, cache); tot = 0.0; d = {c: 0.0 for c in legal_}
            for c, w in v.items():
                if c in d: d[c] += w; tot += w
            rem = max(0.0, 1.0 - tot)
            base = {c: d[c] + rem / n for c in legal_}
        if s.tactics and s.mode != "tree3_nt":
            f = can_win(b, 2) or can_win(b, 1)
            f = [c for c in f if c in legal_]
            if f: base = {c: 0.2 * base[c] + (0.8 / len(f) if c in f else 0.0) for c in legal_}
        return base
    def leaf(s, b): return math.tanh(C.score(b, 1) / 40.0)
    def value(s, b, turn, d, p, hist, snap, cache):
        s.nodes += 1
        legal_ = [c for c in ORDER if b[c][ROWS - 1] == 0]
        if not legal_: return 0.0
        if d == 0 or p < s.theta: return s.leaf(b)
        if turn == 1:
            best = -2.0
            for c in legal_:
                r = lands(b, c); b[c][r] = 1
                if wins_at(b, c, r, 1): v = 1.0
                else:
                    sn = list(snap); sn[0] = c; v = s.value(b, 2, d - 1, p, (hist + (tuple(sn),))[-5:], sn, cache) if False else s.value(b, 2, d - 1, p, (hist + (tuple(sn),))[-5:], sn, cache)
                b[c][r] = 0; best = max(best, v)
                if best >= 1.0: break
            return best
        dist = s.odist(b, hist, snap, legal_, cache); tot = 0.0
        for c in legal_:
            pc = dist[c]
            if pc <= 0: continue
            r = lands(b, c); b[c][r] = 2
            if wins_at(b, c, r, 2): v = -1.0
            else:
                sn = list(snap); sn[1] = c; v = s.value(b, 1, d - 1, p * pc, (hist + (tuple(sn),))[-5:], sn, cache)
            b[c][r] = 0; tot += pc * v
        return tot
    def pick(s, b, rnd):
        legal_ = C.legal(b); s.moves += 1
        w = can_win(b, 1)
        if w: return w[0]
        bl = can_win(b, 2)
        if bl: return bl[0]
        if s.mode == "forced": return rnd.choice(legal_)
        cache = {}; best, bc = -3.0, []
        for c in [c for c in ORDER if c in legal_]:
            r = lands(b, c); b[c][r] = 1; sn = list(s.m.snap); sn[0] = c
            v = s.value(b, 2, s.dmax - 1, 1.0, (tuple(s.m.hist) + (tuple(sn),))[-5:], sn, cache)
            b[c][r] = 0
            if v > best + 1e-9: best, bc = v, [c]
            elif abs(v - best) <= 1e-9: bc.append(c)
        return rnd.choice(bc)
def game(pl, opp, rnd):
    b = C.new(); pl.start(); turn = 1
    while True:
        c = pl.pick(b, rnd) if turn == 1 else opp(b, 2, rnd)
        C.drop(b, c, turn); pl.observe(turn, c)
        w = C.winner(b)
        if w: return w
        if C.full(b): return 0
        turn = 3 - turn
def run(mode, opp, games, seed, **kw):
    rnd = random.Random(seed); pl = Planner(mode, **kw); res = []
    for g in range(games): res.append(game(pl, opp, rnd))
    return res, pl.nodes / max(pl.moves, 1)
VARIANTS = [("forced only (win/block, else random)", "forced", {}), ("tree, uniform opponent, theta .04", "tree_u", dict(theta=0.04)), ("tree, layer 3 prediction, theta .04", "tree3", dict(theta=0.04)),
            ("tree, layer 3, no tactics prior", "tree3_nt", dict(theta=0.04)), ("tree, layer 3, theta .01 (deeper)", "tree3", dict(theta=0.01))]
def main(games=200, seeds=2):
    h = games // 2
    for oname, opp in (("RANDOM opponent", C.opp_random), ("BLOCKER opponent", C.opp_blocker), ("lookahead(2) opponent", C.make_lookahead(2))):
        print("\n%s: X (planner) plays first; online share of wins / draws / losses, games 1-%d and %d-%d, mean of %d seeds; nodes per move" % (oname, h, h + 1, games, seeds))
        for name, mode, kw in VARIANTS:
            rs = [run(mode, opp, games, sd, **kw) for sd in range(seeds)]
            def sh(a, bb): n = sum(bb - a for _ in rs); return [sum(sum(1 for x in r[0][a:bb] if x == k) for r in rs) / n for k in (1, 0, 2)]
            f, l = sh(0, h), sh(h, games)
            print("%-42s %.2f / %.2f / %.2f   %.2f / %.2f / %.2f   nodes %.0f" % (name, f[0], f[1], f[2], l[0], l[1], l[2], sum(r[1] for r in rs) / seeds), flush=True)
if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]; main(*a)
