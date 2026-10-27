"""hexn_ttt_v1: TIC-TAC-TOE as a test of layer 2 and layer 3 (Python only; uses hexn_store_v3 (layer 2 model) and hexn_layer3_v2 (layer 3 with reward) unchanged; no RTL).
Alan, 27 Oct 2026: simple test on both, tic-tac-toe, a limited number of moves and a stated goal.
The machine is given no rules and no board. It sees only a stream of moves as numbers (the interpretive layer is just 'cell 0..8 is key 0..8, 9 = new game') and the outcome as a reward: win +64, draw +16, loss -32 (signed bytes, as REW). It plays X (first) against an opponent. At each of its turns the options are the legal cells; it picks with its own goal read (highest learned value at the longest context that has been tried enough), otherwise at random; 10 percent of moves are random while training. After training it plays greedily (no random moves, learning off) and is scored.
 Layer 2 reading: one stream of moves (X and O interleaved), the layer 2 store model, goal read at context 1, 2 or 3 (the chip's longest is 3).
 Layer 3 reading: two channels, 0 = X's moves and 1 = O's moves, aligned into moments with snapshots (last X, last O), path memory up to 5 snapshots, reduced masks.
Opponents: RANDOM; BLOCKER (wins if it can, else blocks X's win, else random).
Reference: random X; a perfect player (minimax, never loses).
Limits: the layer 2 model is run with 10 key classes (cells 0-8 plus the start marker) while the chip's store has 3-bit events (8 classes): this test shows a limit of the chip's store, it is not a bit-true chip run. Contexts are move histories, not boards, so the same board reached by different move orders is learned separately (that is how a path memory works, and it is part of what is measured)."""
import os, sys, random, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_store_v3 as S, hexn_layer3_v2 as V2
LINES = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
def winner(b):
    for a, c, d in LINES:
        if b[a] and b[a] == b[c] == b[d]: return b[a]
    return 0
def legal(b): return [i for i in range(9) if not b[i]]
def opp_random(b, rnd): return rnd.choice(legal(b))
def opp_blocker(b, rnd):
    for who in (2, 1):
        for c in legal(b):
            b[c] = who; w = winner(b); b[c] = 0
            if w == who: return c
    return rnd.choice(legal(b))
def minimax(b, me, turn, memo):
    """value of the board for player `me` with `turn` to move, under best play by both; returns (value, best cell for the mover)"""
    k = (tuple(b), turn)
    if k in memo: return memo[k]
    w = winner(b)
    if w: r = (1 if w == me else -1, None)
    elif not legal(b): r = (0, None)
    else:
        vals = []
        for c in legal(b):
            b[c] = turn; sv = minimax(b, me, 3 - turn, memo)[0]; b[c] = 0; vals.append((sv, c))
        r = max(vals) if turn == me else min(vals)
    memo[k] = r; return r
_MEMO = {}
def perfect(b, rnd):
    v, c = minimax(b, 1, 1, _MEMO); good = []
    for cc in legal(b):
        b[cc] = 1; sv = minimax(b, 1, 2, _MEMO)[0]; b[cc] = 0
        if sv == v: good.append(cc)
    return rnd.choice(good)
REW = {1: 64, 0: 16, 2: -32}
class L2Agent:
    name = "layer 2"
    def __init__(s, glvl=2): s.st = S.StoreV3(N=2, W=1000, KCAP=4096, CCAP=64, vshift=3, glvl=glvl); s.t = 0
    def start(s): s.st.step(S.CLR); s.t += 1; s.st.step(S.OBS, 9, s.t)
    def pick(s, b, legal_, greedy):
        s.t += 1; g = s.st.step(S.RD, 0, s.t); return (g["gbest"] if g["gbest"] in legal_ and g["gval"] != 0 else None)
    def observe(s, who, c): s.t += 1; s.st.step(S.OBS, c, s.t)
    def end(s, res): s.st.step(S.REW, r=REW[res])
class L3Agent:
    name = "layer 3"
    def __init__(s, L=5): s.L = L; s.m = None; s.t = 0
    def start(s):
        s.m = s.m or V2.Layer3R(nch=2, L=s.L, align=2, half=10 ** 9, masks=[(1, 1), (1, 0)], min_n=2); m = s.m; m.hist = []; m.snap = [None, None]; m.used = []; s.t += 20; m.feed(s.t, 1, 9); m.flush()
    def pick(s, b, legal_, greedy):
        mo, lv = s.m.choose([((0, c),) for c in legal_]); return mo[0][1] if mo else None
    def observe(s, who, c): s.t += 5; s.m.feed(s.t, 0 if who == 1 else 1, c); s.m.flush()
    def end(s, res): s.m.reward(REW[res])
class Rand:
    name = "random"
    def start(s): pass
    def pick(s, b, l, g): return None
    def observe(s, w, c): pass
    def end(s, r): pass
def game(agent, opp, rnd, eps):
    b = [0] * 9; agent.start(); turn = 1
    while True:
        if turn == 1:
            lg = legal(b); c = None if rnd.random() < eps else agent.pick(b, lg, eps == 0)
            if c is None: c = rnd.choice(lg)
        else: c = opp(b, rnd)
        b[c] = turn; agent.observe(turn, c); w = winner(b)
        if w: return w
        if not legal(b): return 0
        turn = 3 - turn
def evaluate(agent, opp, rnd, n):
    """greedy play on a COPY of the agent (the copy learns nothing back): returns [win, draw, loss] shares"""
    import copy
    ag = copy.deepcopy(agent); c = [0, 0, 0]
    for _ in range(n): c[game(ag, opp, rnd, 0.0)] += 1
    return [c[1] / n, c[0] / n, c[2] / n]
def run(make, opp, games=3000, seed=0, check=(250, 1000, 3000), n_eval=400):
    rnd = random.Random(seed); ag = make(); out = []
    for g in range(1, games + 1):
        r = game(ag, opp, rnd, 0.1); ag.end(r)
        if g in check: out.append((g, evaluate(ag, opp, random.Random(seed + 99), n_eval)))
    return out
def main(seeds=3, games=3000):
    rows = [("random X", lambda: Rand()), ("layer 2, goal read context 1", lambda: L2Agent(1)), ("layer 2, goal read context 2", lambda: L2Agent(2)), ("layer 2, goal read context 3", lambda: L2Agent(3)), ("layer 3, path up to 5", lambda: L3Agent(5))]
    for oname, opp in (("RANDOM opponent", opp_random), ("BLOCKER opponent", opp_blocker)):
        print("\n%s: after N training games, greedy play of 400 games [win / draw / loss], mean of %d seeds" % (oname, seeds)); print("%-34s %s" % ("", "".join("%-26s" % ("after %d" % c) for c in (250, 1000, games))))
        for name, mk in rows:
            res = [run(mk, opp, games=games, seed=s, check=(250, 1000, games)) for s in range(seeds)] if name != "random X" else [[(c, evaluate(Rand(), opp, random.Random(s), 400)) for c in (250, 1000, games)] for s in range(seeds)]
            print("%-34s %s" % (name, "".join("%-26s" % ("%.2f / %.2f / %.2f" % tuple(sum(r[i][1][k] for r in res) / seeds for k in range(3))) for i in range(3))))
        pf = evaluate(type("P", (), {"start": lambda s: None, "pick": lambda s, b, l, g: perfect(b, random.Random(1)), "observe": lambda s, w, c: None, "end": lambda s, r: None})(), opp, random.Random(5), 400)
        print("%-34s %s" % ("perfect player (reference)", "%.2f / %.2f / %.2f" % tuple(pf)))
if __name__ == "__main__": main()
