"""hexn_connect4_l23_v1: what do LAYER 2 and LAYER 3 manage alone in Connect Four, before any layer 4? (Python only; no RTL, nothing on a card.)
Alan, 29 Oct 2026: layer 3 has to be tested to see what it is capable of before layer 4 is planned; if layer 4 then shows a better improvement it becomes the next layer up. This is that baseline.
Same method as tools/hexn_ttt_v1.py (left untouched; its harness is cloned here for the 7 x 6 board of tools/hexn_connect4_v1.py): the machine is given no rules and no board, only a stream of moves as numbers (column 0..6 = key 0..6, 7 = new game) and the outcome as a reward (win +64, draw +16, loss -32). It plays X (first). Layer 2 = tools/hexn_store_v3.py (goal read at context 1, 2 or 3), layer 3 = tools/hexn_layer3_v2.py Layer3R (two channels: 0 = X's moves, 1 = O's moves, path memory of up to 5 snapshots) - both unchanged.
Opponents: RANDOM and BLOCKER (tools/hexn_connect4_v1.py). References: random X, and a search player lookahead(depth) as a stand-in for what planning could reach.
Limits: contexts are move histories, not boards (the same position reached by different move orders is learned separately, as in the tic-tac-toe test); games last 18 to 33 moves while the longest context is 3 (layer 2) or 5 snapshots (layer 3); the learners are not tuned for this world; sample sizes are small and printed."""
import os, sys, random, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_store_v3 as S, hexn_layer3_v2 as V2, hexn_connect4_v1 as C
REW = {1: 64, 0: 16, 2: -32}
START = 7
class L2Agent:
    def __init__(s, glvl=2): s.name = "layer 2, goal read context %d" % glvl; s.st = S.StoreV3(N=2, W=1000, KCAP=4096, CCAP=64, vshift=3, glvl=glvl); s.t = 0
    def start(s): s.st.step(S.CLR); s.t += 1; s.st.step(S.OBS, START, s.t)
    def pick(s, b, legal_, greedy):
        s.t += 1; g = s.st.step(S.RD, 0, s.t); return (g["gbest"] if g["gbest"] in legal_ and g["gval"] != 0 else None)
    def observe(s, who, c): s.t += 1; s.st.step(S.OBS, c, s.t)
    def end(s, res): s.st.step(S.REW, r=REW[res])
class L3Agent:
    def __init__(s, L=5): s.name = "layer 3, path up to %d" % L; s.L = L; s.m = None; s.t = 0
    def start(s):
        s.m = s.m or V2.Layer3R(nch=2, L=s.L, align=2, half=10 ** 9, masks=[(1, 1), (1, 0)], min_n=2); m = s.m; m.hist = []; m.snap = [None, None]; m.used = []; s.t += 20; m.feed(s.t, 1, START); m.flush()
    def pick(s, b, legal_, greedy):
        mo, lv = s.m.choose([((0, c),) for c in legal_]); return mo[0][1] if mo else None
    def observe(s, who, c): s.t += 5; s.m.feed(s.t, 0 if who == 1 else 1, c); s.m.flush()
    def end(s, res): s.m.reward(REW[res])
class Player:
    """a fixed player of tools/hexn_connect4_v1.py as an 'agent' (no learning)"""
    def __init__(s, name, fn): s.name = name; s.fn = fn; s.rnd = random.Random(7)
    def start(s): pass
    def pick(s, b, l, g): return s.fn(b, 1, s.rnd) if s.fn else None
    def observe(s, w, c): pass
    def end(s, r): pass
def game(agent, opp, rnd, eps):
    b = C.new(); agent.start(); turn = 1
    while True:
        if turn == 1:
            lg = C.legal(b); c = None if rnd.random() < eps else agent.pick(b, lg, eps == 0)
            if c is None: c = rnd.choice(lg)
        else: c = opp(b, 2, rnd)
        C.drop(b, c, turn); agent.observe(turn, c); w = C.winner(b)
        if w: return w
        if C.full(b): return 0
        turn = 3 - turn
def evaluate(agent, opp, rnd, n):
    """greedy play on a COPY of the agent (the copy learns nothing back): [win, draw, loss] shares"""
    ag = copy.deepcopy(agent); c = [0, 0, 0]
    for _ in range(n): c[game(ag, opp, rnd, 0.0)] += 1
    return [c[1] / n, c[0] / n, c[2] / n]
def run(make, opp, games, seed, check, n_eval):
    rnd = random.Random(seed); ag = make(); out = []
    for g in range(1, games + 1):
        r = game(ag, opp, rnd, 0.1); ag.end(r)
        if g in check: out.append(evaluate(ag, opp, random.Random(seed + 99), n_eval))
    return out
def main(seeds=2, games=1000, n_eval=100):
    check = (games // 4, games // 2, games)
    rows = [("random X", None), ("layer 2, goal read context 1", lambda: L2Agent(1)), ("layer 2, goal read context 2", lambda: L2Agent(2)), ("layer 2, goal read context 3", lambda: L2Agent(3)), ("layer 3, path up to 5", lambda: L3Agent(5))]
    for oname, opp in (("RANDOM opponent", C.opp_random), ("BLOCKER opponent", C.opp_blocker)):
        print("\n%s: greedy play of %d games after N training games [win / draw / loss], mean of %d seeds" % (oname, n_eval, seeds)); print("%-34s %s" % ("", "".join("%-26s" % ("after %d" % c) for c in check)))
        for name, mk in rows:
            if mk is None: res = [[evaluate(Player("r", None), opp, random.Random(s), n_eval)] * 3 for s in range(seeds)]
            else: res = [run(mk, opp, games, s, check, n_eval) for s in range(seeds)]
            print("%-34s %s" % (name, "".join("%-26s" % ("%.2f / %.2f / %.2f" % tuple(sum(r[i][k] for r in res) / seeds for k in range(3))) for i in range(3))), flush=True)
        for d in (2, 4):
            pf = evaluate(Player("lookahead", C.make_lookahead(d)), opp, random.Random(5), min(n_eval, 40)); print("%-34s %s" % ("lookahead(%d) (reference, %d games)" % (d, min(n_eval, 40)), "%.2f / %.2f / %.2f" % tuple(pf)), flush=True)
if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]; main(*a)
