"""hexn_connect4_blend_v2: CLONE of hexn_connect4_blend_v1.py (v1 untouched) adding the NEURAL CORE'S JUDGE as the leaf (31 Oct 03:31). Names: a trailing j = integer judge (tools/hexn_judge_int_v1.py, S1 = S2 = 6), f = float judge, none = hand score; plainJD = alpha-beta with the integer judge as leaf (separates what the judge gives from what the Hex-N search gives); hexM/hexH/hex/hexE + depth + j/f. The judge value is for X (side 1) and is negated for O. Original v1 text follows.
hexn_connect4_blend_v1: THE LAYER 4 CONFIDENCE BLEND IN CONNECT FOUR, AGAINST OPPONENTS WITH HABITS (Python only; no RTL, nothing on a card; new file 31 Oct 2026).
Alan, 31 Oct 03:15: 'Yes if you can, at least it matches' = test the blend where positions DO recur and the opponent has habits, to see whether the learned part ever earns its place. Draughts gave only 'equal' (09:40 row).
Players: plainD = tools/hexn_connect4_v1.py make_lookahead(D) (alpha-beta, random tie-break, no learning). Hex players (same shape as tools/hexn_draughts_hex_v3.py): expectimax of depth D; my moves maximise; at opponent nodes: 'minimax' = worst case only; 'blendH' = c * expectation under layer 3's replies (renormalised over the legal moves it knows) + (1 - c) * minimum, c = (probability mass on legal moves) x (layer 3's running hit rate, step 1/10, start 0); 'learn' = learned spread plus a flat share for the unseen part (v1 style); 'flat' = flat spread. Layer 3 = hexn_layer3_v1.Layer3 (2 channels, 5 snapshots, masks (1,1) and (1,0)), kept across the games of a seed, key 7 = new game. Leaf = tanh(hand score / 20), win +1, loss -1.
Opponents: noisy2 = lookahead(2) with 20 percent random moves (the layer 4 test opponent of 21:20); habit2 = lookahead(2) with a FIXED tie-break (first best column in the centre-first order), so the same position always gets the same reply; habit3 = the same at depth 3; habitN = habit2 with 10 percent random moves.
Usage: python3 tools/hexn_connect4_blend_v1.py OPPONENT CANDIDATE... [--games N] [--seeds S]  e.g. habit2 plain3 hexM3 hexH3 hex3 hexE3. Score = (wins + half the draws) / games; first player alternates; learner fresh per seed.
Limits: one hand score; 6 ladder-free openings by chance only; Python speed; nothing tuned; small samples (standard error about 0.045 at 120 games)."""
import os, sys, math, copy, random, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_layer3_v1 as V1, hexn_judge_int_v1 as JI
JUDGE = {}
def judge(kind):
    if kind not in JUDGE: path = os.environ.get('HEXN_JUDGE') or JI.WPATH; JUDGE[kind] = JI.JudgeInt(6, 6, path=path) if kind == 'j' else JI.JudgeFloat(path)
    return JUDGE[kind]
ORDER = C.ORDER; NEW = 7
def fixed(depth):
    def play(b, who, rnd):
        best, bc = None, None
        for c in [c for c in ORDER if b[c][C.ROWS - 1] == 0]:
            C.drop(b, c, who); v = C.search(b, who, 3 - who, depth - 1, -10 ** 9, 10 ** 9); C.undo(b, c)
            if best is None or v > best: best, bc = v, c
        return bc
    return play
def noisy(pl, p): return lambda b, who, rnd: rnd.choice(C.legal(b)) if rnd.random() < p else pl(b, who, rnd)
def l3_keys(m, hist, snap, cache):
    if hist in cache: return cache[hist]
    t = copy.copy(m); t.hist = list(hist); t.snap = list(snap)
    v = dict(t.channel_view(1, top=10 ** 6)) if None not in snap else {}
    cache[hist] = v; return v
class Hex:
    def __init__(s, depth, mode="blendH", theta=0.04, leafkind=None):
        s.leafkind = leafkind; s.J = judge(leafkind) if leafkind else None
        s.depth, s.mode, s.theta = depth, mode, theta; s.t = 0; s.nodes = 0; s.moves = 0; s.me = 1; s.hit = 0.0
        s.m = V1.Layer3(nch=2, L=5, align=2, half=10 ** 9, masks=[(1, 1), (1, 0)])
    def feed(s, ch, key): s.t += 5; s.m.feed(s.t, ch, key); s.m.flush()
    def start(s, side):
        s.me = side; m = s.m; m.hist = []; m.snap = [None, None]; s.t += 20; m.feed(s.t, 1, NEW); m.flush()
    def observe(s, side, c):
        if side != s.me and s.mode == "blendH" and None not in s.m.snap:
            v = s.m.channel_view(1, top=1); s.hit += 0.1 * ((1.0 if (v and v[0][0] == c) else 0.0) - s.hit)
        s.feed(0 if side == s.me else 1, c)
    def leaf(s, b):
        if s.J is None: return math.tanh(C.score(b, s.me) / 20.0)
        v = s.J.value(b); return v if s.me == 1 else -v
    def val(s, b, turn, depth, p, hist, snap, cache):
        s.nodes += 1; w = C.winner(b)
        if w: return 1.0 if w == s.me else -1.0
        mv = [c for c in ORDER if b[c][C.ROWS - 1] == 0]
        if not mv: return 0.0
        if depth <= 0 or p < s.theta: return s.leaf(b)
        if turn == s.me:
            best = -2.0
            for c in mv:
                sn = list(snap); sn[0] = c; C.drop(b, c, turn)
                v = s.val(b, 3 - turn, depth - 1, p, (hist + (tuple(sn),))[-5:], sn, cache); C.undo(b, c); best = max(best, v)
            return best
        lv = l3_keys(s.m, hist, snap, cache) if (s.mode != "minimax" and None not in snap) else {}
        w_ = {c: lv.get(c, 0.0) for c in mv}; tot = sum(w_.values())
        if s.mode in ("minimax", "blendH"):
            c_ = 0.0 if s.mode == "minimax" else min(1.0, tot) * s.hit; vals = []; ev = 0.0
            for c in mv:
                qi = (w_[c] / tot) if (c_ > 0 and tot > 0) else 0.0; pc = max(c_ * qi, 1.0 - c_)
                sn = list(snap); sn[1] = c; C.drop(b, c, turn)
                v = s.val(b, 3 - turn, depth - 1, p * pc, (hist + (tuple(sn),))[-5:], sn, cache); C.undo(b, c); vals.append(v); ev += c_ * qi * v
            return ev + (1.0 - c_) * min(vals)
        n = len(mv); d = {c: 1.0 / n for c in mv}
        if s.mode == "learn": rem = max(0.0, 1.0 - tot); d = {c: w_[c] + rem / n for c in mv}
        tv = 0.0
        for c in mv:
            if d[c] <= 0: continue
            sn = list(snap); sn[1] = c; C.drop(b, c, turn)
            v = s.val(b, 3 - turn, depth - 1, p * d[c], (hist + (tuple(sn),))[-5:], sn, cache); C.undo(b, c); tv += d[c] * v
        return tv
    def __call__(s, b, who, rnd):
        s.moves += 1; cache = {}; hist = tuple(s.m.hist[-5:]); snap = list(s.m.snap); best, bc = -9.0, []
        for c in [c for c in ORDER if b[c][C.ROWS - 1] == 0]:
            sn = list(snap); sn[0] = c; C.drop(b, c, who)
            v = s.val(b, 3 - who, s.depth - 1, 1.0, (hist + (tuple(sn),))[-5:], sn, cache); C.undo(b, c)
            if v > best + 1e-12: best, bc = v, [c]
            elif abs(v - best) <= 1e-12: bc.append(c)
        return rnd.choice(bc)
def game(x, o, rnd):
    """x moves first. Returns winner 0/1/2."""
    b = C.new(); who = 1; pl = {1: x, 2: o}
    for side in (1, 2):
        if hasattr(pl[side], "start"): pl[side].start(side)
    while True:
        c = pl[who](b, who, rnd)
        for side in (1, 2):
            if hasattr(pl[side], "observe"): pl[side].observe(who, c)
        C.drop(b, c, who); w = C.winner(b)
        if w: return w
        if C.full(b): return 0
        who = 3 - who
def search_j(b, me, turn, depth, alpha, beta, J):
    w = C.winner(b)
    if w: return (10000 + depth) if w == me else -(10000 + depth)
    mv = [c for c in ORDER if b[c][C.ROWS - 1] == 0]
    if not mv: return 0
    if depth == 0: v = J.value(b); return 1000 * (v if me == 1 else -v)
    if turn == me:
        best = -10 ** 9
        for c in mv:
            C.drop(b, c, turn); best = max(best, search_j(b, me, 3 - turn, depth - 1, alpha, beta, J)); C.undo(b, c); alpha = max(alpha, best)
            if alpha >= beta: break
        return best
    best = 10 ** 9
    for c in mv:
        C.drop(b, c, turn); best = min(best, search_j(b, me, 3 - turn, depth - 1, alpha, beta, J)); C.undo(b, c); beta = min(beta, best)
        if alpha >= beta: break
    return best
def plain_j(depth, kind):
    J = judge(kind)
    def play(b, who, rnd):
        best, bc = None, []
        for c in [c for c in ORDER if b[c][C.ROWS - 1] == 0]:
            C.drop(b, c, who); v = search_j(b, who, 3 - who, depth - 1, -10 ** 9, 10 ** 9, J); C.undo(b, c)
            if best is None or v > best: best, bc = v, [c]
            elif v == best: bc.append(c)
        return rnd.choice(bc)
    return play
def make(name):
    kind = name[-1] if name[-1] in "jf" else None; core = name[:-1] if kind else name
    for pre, mode in (("hexM", "minimax"), ("hexH", "blendH"), ("hexE", "flat"), ("hex", "learn")):
        if core.startswith(pre) and core[len(pre):].isdigit(): return Hex(int(core[len(pre):]), mode, leafkind=kind)
    if core.startswith("plainJ"): return plain_j(int(core[6:]), kind or "j")
    if core.startswith("plain") and core[5:].isdigit(): return C.make_lookahead(int(core[5:]))
    raise SystemExit("unknown " + name)
def opponent(name):
    if name == "noisy2": return noisy(C.make_lookahead(2), 0.2)
    if name == "plain3": return C.make_lookahead(3)
    if name == "plain4": return C.make_lookahead(4)
    if name == "habit2": return fixed(2)
    if name == "habit3": return fixed(3)
    if name == "habitN": return noisy(fixed(2), 0.1)
    raise SystemExit("unknown opponent " + name)
def main(opp, cands, games, seeds):
    print("opponent %s; %d seeds x %d games, first player alternates" % (opp, seeds, games), flush=True)
    for cn in cands:
        w = d = l = 0; tm = 0.0; nm = 0; nodes = 0; hm = 0
        for sd in range(seeds):
            rnd = random.Random(sd); cand = make(cn); op = opponent(opp)
            for i in range(games):
                t0 = time.time()
                if i % 2 == 0: r = game(cand, op, rnd); w += r == 1; l += r == 2
                else: r = game(op, cand, rnd); w += r == 2; l += r == 1
                d += r == 0; tm += time.time() - t0
            if isinstance(cand, Hex): nodes += cand.nodes; hm += cand.moves
        n = seeds * games
        print("%-8s W %3d D %3d L %3d   score %.2f   %.1f s per game%s" % (cn, w, d, l, (w + 0.5 * d) / n, tm / n, ("   nodes/move %.0f" % (nodes / hm)) if hm else ""), flush=True)
if __name__ == "__main__":
    a = sys.argv[1:]; games, seeds = 40, 3
    if "--games" in a: i = a.index("--games"); games = int(a[i + 1]); del a[i:i + 2]
    if "--seeds" in a: i = a.index("--seeds"); seeds = int(a[i + 1]); del a[i:i + 2]
    main(a[0], a[1:], games, seeds)
