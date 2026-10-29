"""hexn_connect4_v1: CONNECT FOUR as the test world for layer 4, the strategist (Python only; no RTL, nothing on a card; layers 2 and 3 are not used in this file).
Alan, 29 Oct 2026: expand the game to Connect Four: a larger grid and gravity (a counter drops to the lowest free place in its column), so that winning needs planning and strategy.
The same view of the world as the tic-tac-toe test (tools/hexn_ttt_v1.py): the machine sees only a stream of moves as numbers: column 0..6 is key 0..6 and 7 is 'new game'. That is 8 classes, which is exactly the 3-bit events of the chip's layer 2 store (tic-tac-toe needed 10 and showed that limit). The board, the gravity and the four-in-a-row rule exist only here, in the world; the player sees keys and an outcome.
Board: 7 columns x 6 rows, b[c][r] with r = 0 the bottom; 0 empty, 1 = first player (X), 2 = second (O). Reference players: random; blocker (wins if it can, else blocks the other's win, else random); lookahead(depth) = alpha-beta search, depth in moves (plies), with a simple centre-first order and a count of open lines as the score at the horizon; it is the stand-in for 'a strategist' to measure how much room planning has."""
import random
COLS, ROWS = 7, 6
LINES = []
for c in range(COLS):
    for r in range(ROWS):
        for dc, dr in ((1, 0), (0, 1), (1, 1), (1, -1)):
            cells = [(c + k * dc, r + k * dr) for k in range(4)]
            if all(0 <= x < COLS and 0 <= y < ROWS for x, y in cells): LINES.append(cells)
def new(): return [[0] * ROWS for _ in range(COLS)]
def height(b, c): return sum(1 for v in b[c] if v)
def legal(b): return [c for c in range(COLS) if b[c][ROWS - 1] == 0]
def drop(b, c, who):
    """put a counter in column c; returns the row it landed in"""
    r = height(b, c); b[c][r] = who; return r
def undo(b, c): b[c][height(b, c) - 1] = 0
def winner(b):
    for cells in LINES:
        v = b[cells[0][0]][cells[0][1]]
        if v and all(b[x][y] == v for x, y in cells): return v
    return 0
def full(b): return not legal(b)
def opp_random(b, who, rnd): return rnd.choice(legal(b))
def opp_blocker(b, who, rnd):
    for w in (who, 3 - who):
        for c in legal(b):
            drop(b, c, w); win = winner(b) == w; undo(b, c)
            if win: return c
    return rnd.choice(legal(b))
ORDER = [3, 2, 4, 1, 5, 0, 6]
def score(b, who):
    """open lines (no counter of the other side): +1 per own counter in them, squared, for who minus the other"""
    s = 0
    for cells in LINES:
        v = [b[x][y] for x, y in cells]; a, o = v.count(who), v.count(3 - who)
        if a and not o: s += a * a
        elif o and not a: s -= o * o
    return s
def search(b, me, turn, depth, alpha, beta):
    w = winner(b)
    if w: return (10000 + depth) if w == me else -(10000 + depth)
    mv = [c for c in ORDER if b[c][ROWS - 1] == 0]
    if not mv: return 0
    if depth == 0: return score(b, me)
    if turn == me:
        best = -10 ** 9
        for c in mv:
            drop(b, c, turn); best = max(best, search(b, me, 3 - turn, depth - 1, alpha, beta)); undo(b, c); alpha = max(alpha, best)
            if alpha >= beta: break
        return best
    best = 10 ** 9
    for c in mv:
        drop(b, c, turn); best = min(best, search(b, me, 3 - turn, depth - 1, alpha, beta)); undo(b, c); beta = min(beta, best)
        if alpha >= beta: break
    return best
def make_lookahead(depth):
    def play(b, who, rnd):
        best, bc = None, []
        for c in [c for c in ORDER if b[c][ROWS - 1] == 0]:
            drop(b, c, who); v = search(b, who, 3 - who, depth - 1, -10 ** 9, 10 ** 9); undo(b, c)
            if best is None or v > best: best, bc = v, [c]
            elif v == best: bc.append(c)
        return rnd.choice(bc)
    return play
def play_game(p1, p2, rnd, moves=None):
    """p1 is X (moves first). Returns (winner 0/1/2, list of columns played)."""
    b = new(); who = 1; seq = []
    while True:
        c = (p1 if who == 1 else p2)(b, who, rnd); drop(b, c, who); seq.append(c)
        w = winner(b)
        if w: return w, seq
        if full(b): return 0, seq
        who = 3 - who
def match(p1, p2, n, seed=0):
    """n games with p1 as X, n with p1 as O. Returns (wins, draws, losses) of p1 over 2n games and the mean game length."""
    rnd = random.Random(seed); w = d = l = 0; tot = 0
    for i in range(2 * n):
        if i < n: r, s = play_game(p1, p2, rnd); w += r == 1; l += r == 2
        else: r, s = play_game(p2, p1, rnd); w += r == 2; l += r == 1
        d += r == 0; tot += len(s)
    return w, d, l, tot / (2 * n)
if __name__ == "__main__":
    import sys, time
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    for name, a, b in (("blocker vs random", opp_blocker, opp_random), ("lookahead(2) vs random", make_lookahead(2), opp_random), ("lookahead(2) vs blocker", make_lookahead(2), opp_blocker),
                       ("lookahead(4) vs blocker", make_lookahead(4), opp_blocker), ("lookahead(4) vs lookahead(2)", make_lookahead(4), make_lookahead(2))):
        t = time.time(); w, d, l, m = match(a, b, n); print("%-30s win %3d draw %3d loss %3d of %d, mean length %.1f moves (%.0f s)" % (name, w, d, l, 2 * n, m, time.time() - t))
