"""hexn_draughts_v1: RULES ENGINE FOR ENGLISH DRAUGHTS (8x8, 12 men each, Python only; no RTL, nothing on a card). The second game after Connect Four (Alan, 29 and 30 Oct 2026: draughts is the better test; Hex-N to be tested against a plain search of the same style on it).
Rules implemented (English draughts / American checkers): dark squares only; men move one step diagonally forward, kings one step in any of the four directions (no flying kings); capturing is MANDATORY and a jump is made over an adjacent enemy piece onto the empty square behind it; a jumping piece must keep jumping while it can (multi-jump), may not jump the same piece twice and ends its move if a man reaches the far row (it is crowned and stops); a player with no legal move loses. X moves first and moves UP the board (towards row 0); O moves down. Draw: 80 plies in a row without a capture or a man move (kings only), or 400 plies in all (a safety limit, not a rule).
Squares: 0..31, row = i // 4 (row 0 is O's back row), column = 2 * (i % 4) + (1 if row is even else 0). Pieces: 0 empty, 1 X man, 2 X king, 3 O man, 4 O king. Start: O on squares 0..11, X on 20..31.
A move is (path, captured): path = the squares the piece visits, from its start to its end; captured = the squares of the pieces it jumps. Two jump routes that end on the same square are two moves.
Correctness is checked in tests/test_hexn_draughts_v1.py by perft (the number of move sequences of a given length from the start): 7, 49, 302, 1469, 7361, 36768, 179740 for depths 1 to 7, the values published for English draughts, which I recalled from memory and did not look up in this session; the match of seven numbers is strong evidence but the list itself is from memory.
Limits: no repetition rule; evaluation and search are NOT here."""
ROWS = 8
DIRS = ((-1, -1), (-1, 1), (1, -1), (1, 1))
def _rc(i): r = i // 4; return r, 2 * (i % 4) + (1 if r % 2 == 0 else 0)
SQ = {_rc(i): i for i in range(32)}
ADJ = [[-1] * 4 for _ in range(32)]; JMP = [[-1] * 4 for _ in range(32)]
for _i in range(32):
    _r, _c = _rc(_i)
    for _d, (_dr, _dc) in enumerate(DIRS):
        ADJ[_i][_d] = SQ.get((_r + _dr, _c + _dc), -1); JMP[_i][_d] = SQ.get((_r + 2 * _dr, _c + 2 * _dc), -1)
X_DIRS, O_DIRS, K_DIRS = (0, 1), (2, 3), (0, 1, 2, 3)
def side(p): return 1 if p in (1, 2) else 2 if p in (3, 4) else 0
def dirs_of(p): return K_DIRS if p in (2, 4) else (X_DIRS if p == 1 else O_DIRS)
def new():
    b = [0] * 32
    for i in range(12): b[i] = 3
    for i in range(20, 32): b[i] = 1
    return b
def _king_row(p, sq): return (p == 1 and sq < 4) or (p == 3 and sq >= 28)
def _jumps(b, sq, p, turn, captured, path, origin, out):
    found = False
    for d in dirs_of(p):
        over, land = ADJ[sq][d], JMP[sq][d]
        if over < 0 or land < 0 or over in captured or side(b[over]) != 3 - turn or b[land] != 0: continue
        found = True; np_ = p + 1 if (p in (1, 3) and _king_row(p, land)) else p
        if np_ != p: out.append((path + (land,), captured + (over,)))          # crowned: the move ends
        else: _jumps(b, land, p, turn, captured + (over,), path + (land,), origin, out)
    if not found and len(path) > 1: out.append((path, captured))
def moves(b, turn):
    caps = []
    for sq in range(32):
        p = b[sq]
        if side(p) != turn: continue
        b[sq] = 0; _jumps(b, sq, p, turn, (), (sq,), sq, caps); b[sq] = p
    if caps: return caps
    out = []
    for sq in range(32):
        p = b[sq]
        if side(p) != turn: continue
        for d in dirs_of(p):
            t = ADJ[sq][d]
            if t >= 0 and b[t] == 0: out.append(((sq, t), ()))
    return out
def apply(b, mv):
    path, cap = mv; p = b[path[0]]; rec = (p, [(c, b[c]) for c in cap])
    b[path[0]] = 0
    for c in cap: b[c] = 0
    end = path[-1]; b[end] = p + 1 if (p in (1, 3) and _king_row(p, end)) else p
    return rec
def undo(b, mv, rec):
    path, cap = mv; p, caps = rec; b[path[-1]] = 0; b[path[0]] = p
    for c, v in caps: b[c] = v
def perft(b, turn, depth):
    if depth == 0: return 1
    n = 0
    for mv in moves(b, turn):
        rec = apply(b, mv); n += perft(b, 3 - turn, depth - 1) if depth > 1 else 1; undo(b, mv, rec)
    return n
class Game:
    """board + side to move + draw counters; result(): 0 running, 1 X won, 2 O won, 3 draw"""
    def __init__(s): s.b = new(); s.turn = 1; s.quiet = 0; s.plies = 0
    def legal(s): return moves(s.b, s.turn)
    def play(s, mv):
        reset = bool(mv[1]) or s.b[mv[0][0]] in (1, 3)
        apply(s.b, mv); s.turn = 3 - s.turn; s.plies += 1; s.quiet = 0 if reset else s.quiet + 1
    def result(s):
        if not s.legal(): return 3 - s.turn
        if s.quiet >= 80 or s.plies >= 400: return 3
        return 0
def show(b):
    rows = []
    for r in range(8):
        line = ""
        for c in range(8):
            i = SQ.get((r, c)); line += "." if i is None else ".xXoO"[b[i]] if b[i] else "-"
        rows.append(line)
    return "\n".join(rows)
