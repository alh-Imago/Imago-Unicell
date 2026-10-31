"""hexn_draughts_hex_v2: CLONE of hexn_draughts_hex_v1.py (v1 untouched) adding the CONFIDENCE BLEND of the layer 4 decision 2 (Alan, 31 Oct 02:36): at each opponent node the value is c * (expectation under layer 3's learned replies, renormalised over the legal moves it knows) + (1 - c) * (worst case = minimum over all replies), where c = the share of probability layer 3 puts on legal moves (its 'something not seen' share is 1 - c). mode 'learn' = v1 behaviour (learned spread plus a flat share for the unseen part); 'flat' = no model; 'minimax' = c is 0 (worst case only, no pruning by probability: the control that should play like the plain search); 'blend' = the proposal. Child path probability = p * max(c * q_i, 1 - c). Original v1 text follows.
hexn_draughts_hex_v1: THE HEX-N STACK ON DRAUGHTS, FIRST VERSION (Python only; no RTL, nothing on a card; stage 3a of the draughts plan, 30 Oct 2026). Imports the rules engine (hexn_draughts_v1) and the plain baseline's score (hexn_draughts_plain_v1) unchanged, and the Layer 3 model (hexn_layer3_v1) unchanged.
What it is (the same shape as the Connect Four layer 4 of tools/hexn_connect4_layer4_v3.py, without the confidence-chosen depth rule, which Connect Four did not show to help): an EXPECTIMAX search of depth `depth`. My moves: the maximum. The opponent's replies: an expectation over the probabilities from LAYER 3, a two-channel layer 3 (channel 0 = my moves, channel 1 = the opponent's moves, contexts of up to 5 snapshots, masks (1,1) and (1,0)) that learns every move of every game it sees, on move histories. A move's key is its path (the squares it visits). Replies layer 3 does not name share the remaining weight equally. Branches whose path probability falls under `theta` (.04) are scored at once. Leaf = tanh(score / 150) with the SAME hand score as the plain baseline (mine minus theirs); a side with no move loses (-1 / +1). Captures are searched on, up to 6 extra plies, as in the baseline.
`empty=True` is the control that has no learned model: the replies are a flat spread over the legal moves (as in the Connect Four 'empty' control).
The player keeps its layer 3 across games, so it LEARNS ONLINE as the games go. Methods: start(side), pick(game, rnd), observe(side, move). No teaching, no self-play, no judge yet (stage 3b).
Limits: draughts has forced captures, so many nodes have one legal move; the first version is not tuned; no alpha-beta at the opponent nodes; Python speed."""
import os, sys, math, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_draughts_v1 as D, hexn_draughts_plain_v1 as P, hexn_layer3_v1 as V1
START = ("start",)
def l3_keys(m, hist, snap, cache):
    """predicted moves of the opponent (channel 1) after the given (hist, snap): dict key -> weight, read only"""
    if hist in cache: return cache[hist]
    t = copy.copy(m); t.hist = list(hist); t.snap = list(snap)
    v = dict(t.channel_view(1, top=10 ** 6)) if None not in snap else {}
    cache[hist] = v; return v
class Hex:
    def __init__(s, depth, theta=0.04, empty=False, mode=None):
        s.mode = mode or ("flat" if empty else "learn"); empty = empty or s.mode == "flat"
        s.depth, s.theta, s.empty = depth, theta, empty; s.t = 0; s.nodes = 0; s.moves = 0; s.me = 1
        s.m = V1.Layer3(nch=2, L=5, align=2, half=10 ** 9, masks=[(1, 1), (1, 0)])
    def feed(s, ch, key): s.t += 5; s.m.feed(s.t, ch, key); s.m.flush()
    def start(s, side):
        s.me = side; m = s.m; m.hist = []; m.snap = [None, None]; s.t += 20; m.feed(s.t, 1, START); m.flush()
    def observe(s, side, mv): s.feed(0 if side == s.me else 1, mv[0])
    def leaf(s, b): return math.tanh(P.score(b, s.me) / 150.0)
    def dist(s, legal, hist, snap, cache):
        n = len(legal); base = {mv[0]: 1.0 / n for mv in legal}
        if not s.empty:
            v = l3_keys(s.m, hist, snap, cache); d = {mv[0]: 0.0 for mv in legal}; tot = 0.0
            for k, w in v.items():
                if k in d: d[k] += w; tot += w
            rem = max(0.0, 1.0 - tot); base = {k: d[k] + rem / n for k in d}
        return base
    def val(s, b, turn, depth, p, hist, snap, cache, ext):
        s.nodes += 1; mv = D.moves(b, turn)
        if not mv: return -1.0 if turn == s.me else 1.0
        forced = bool(mv[0][1])
        if p < s.theta or (depth <= 0 and not (forced and ext < 6)): return s.leaf(b)
        if depth <= 0: ext += 1
        if turn == s.me:
            best = -2.0
            for m in mv:
                sn = list(snap); sn[0] = m[0]; rec = D.apply(b, m)
                v = s.val(b, 3 - turn, depth - 1, p, (hist + (tuple(sn),))[-5:], sn, cache, ext); D.undo(b, m, rec)
                if v > best: best = v
            return best
        if s.mode in ("minimax", "blend"):
            lv = l3_keys(s.m, hist, snap, cache) if (s.mode == "blend" and None not in snap) else {}
            w = {m[0]: lv.get(m[0], 0.0) for m in mv}; c = min(1.0, sum(w.values())) if s.mode == "blend" else 0.0
            vals = []; ev = 0.0
            for m in mv:
                qi = (w[m[0]] / sum(w.values())) if c > 0 else 0.0; pc = max(c * qi, 1.0 - c)
                sn = list(snap); sn[1] = m[0]; rec = D.apply(b, m)
                v = s.val(b, 3 - turn, depth - 1, p * pc, (hist + (tuple(sn),))[-5:], sn, cache, ext); D.undo(b, m, rec); vals.append(v); ev += c * qi * v
            return ev + (1.0 - c) * min(vals)
        d = s.dist(mv, hist, snap, cache); tot = 0.0
        for m in mv:
            pc = d[m[0]]
            if pc <= 0: continue
            sn = list(snap); sn[1] = m[0]; rec = D.apply(b, m)
            v = s.val(b, 3 - turn, depth - 1, p * pc, (hist + (tuple(sn),))[-5:], sn, cache, ext); D.undo(b, m, rec); tot += pc * v
        return tot
    def pick(s, g, rnd):
        s.moves += 1; mv = g.legal()
        if len(mv) == 1: return mv[0]
        cache = {}; hist = tuple(s.m.hist[-5:]); snap = list(s.m.snap); best, bm = -9.0, []
        for m in mv:
            sn = list(snap); sn[0] = m[0]; rec = D.apply(g.b, m)
            v = s.val(g.b, 3 - g.turn, s.depth - 1, 1.0, (hist + (tuple(sn),))[-5:], sn, cache, 0); D.undo(g.b, m, rec)
            if v > best + 1e-12: best, bm = v, [m]
            elif abs(v - best) <= 1e-12: bm.append(m)
        return rnd.choice(bm)
def play(a, b, rnd, open_random=2):
    """a is X (moves first), b is O. Returns the result (1 X won, 2 O won, 3 draw)."""
    g = D.Game()
    for side, pl in ((1, a), (2, b)):
        if hasattr(pl, "start"): pl.start(side)
    while not g.result():
        side = g.turn
        mv = rnd.choice(g.legal()) if g.plies < open_random else (a if side == 1 else b).pick(g, rnd)
        for s_, pl in ((1, a), (2, b)):
            if hasattr(pl, "observe"): pl.observe(side, mv)
        g.play(mv)
    return g.result()
