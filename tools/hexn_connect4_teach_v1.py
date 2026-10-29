"""hexn_connect4_teach_v1: LAYER 4 AS A SECOND TEACHER OF LAYER 3 (Python only; no RTL, nothing on a card).
Alan, 29 Oct 2026: as play continues, layer 4's chosen paths can help layer 3 as well, another level of reinforcement; layer 4 still takes care of a sudden random move.
Question: after layer 3 has been trained on games in which LAYER 4 played X, does layer 3 ALONE (no tree, no tactics, greedy, no layer 4) play better than a layer 3 that trained by its own play?
Method: ONE layer 3 (hexn_layer3_v2.Layer3R, as tools/hexn_connect4_l23_v1.py L3Agent: two channels, path up to 5, masks (1,1),(1,0), min_n 2). TEACHED: layer 4 (hexn_connect4_layer4_v3.Planner3, depth 4 + free plies at confidence .8, tree with layer 3 prediction) chooses X's moves, using this same layer 3 to predict O; every move goes into layer 3's path memory, and at the end of each game layer 3 is rewarded with the real result (+64 win, +16 draw, -32 loss) as in the baseline, so the entries along the teacher's path are reinforced. OWN: the baseline (the L23 harness, X plays its own learned choice, 10% random, same rewards). After N training games a COPY of layer 3 plays 100 greedy games alone as X against the same opponent [win / draw / loss]. Cost: tree positions per teacher move.
Limits: layer 3 contexts are move histories, not boards (it cannot see threats); small samples; one opponent type per table; the teacher learns while it teaches, so early games are the weakest; nothing tuned."""
import os, sys, copy, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_v2 as V2, hexn_connect4_v1 as C, hexn_connect4_l23_v1 as L23, hexn_connect4_layer4_v1 as L1, hexn_connect4_layer4_v3 as L3P
REW, START = L23.REW, 7
class Teacher(L3P.Planner3):
    def __init__(s, **kw):
        super().__init__(mode="tree3", theta=0.04, tactics=True, **kw)
        s.m = V2.Layer3R(nch=2, L=5, align=2, half=10 ** 9, masks=[(1, 1), (1, 0)], min_n=2)
    def start(s):
        s.m.hist = []; s.m.snap = [None, None]; s.m.used = []; s.t += 20; s.m.feed(s.t, 1, START); s.m.flush()
def teach_game(tc, opp, rnd):
    b = C.new(); tc.start(); turn = 1
    while True:
        c = tc.pick(b, rnd) if turn == 1 else opp(b, 2, rnd)
        C.drop(b, c, turn); tc.observe(turn, c); w = C.winner(b)
        if w: res = w; break
        if C.full(b): res = 0; break
        turn = 3 - turn
    tc.m.reward(REW[res]); return res
def student(m, t):
    ag = L23.L3Agent(5); ag.m = copy.deepcopy(m); ag.t = t; return ag
def run_teach(opp, games, seed, check, n_eval, **kw):
    rnd = random.Random(seed); tc = Teacher(**kw); out = []
    for g in range(1, games + 1):
        teach_game(tc, opp, rnd)
        if g in check: out.append(L23.evaluate(student(tc.m, tc.t), opp, random.Random(seed + 99), n_eval))
    return out, tc.created / max(tc.moves, 1)
def main(seeds=2, games=600, n_eval=100):
    check = (games // 6, games // 2, games)
    for oname, opp in (("BLOCKER opponent", C.opp_blocker), ("lookahead(2) opponent", C.make_lookahead(2))):
        print("\n%s: layer 3 ALONE plays X greedily after N training games [win / draw / loss], %d games, mean of %d seeds" % (oname, n_eval, seeds)); print("%-40s %s" % ("", "".join("%-26s" % ("after %d" % c) for c in check)))
        res = [L23.run(lambda: L23.L3Agent(5), opp, games, s, check, n_eval) for s in range(seeds)]
        print("%-40s %s" % ("trained by its own play", "".join("%-26s" % ("%.2f / %.2f / %.2f" % tuple(sum(r[i][k] for r in res) / seeds for k in range(3))) for i in range(3))), flush=True)
        rt = [run_teach(opp, games, s, check, n_eval, dmax=4, conf=0.8) for s in range(seeds)]
        print("%-40s %s" % ("taught by layer 4 (depth 4 + free plies)", "".join("%-26s" % ("%.2f / %.2f / %.2f" % tuple(sum(r[0][i][k] for r in rt) / seeds for k in range(3))) for i in range(3))), "  tree positions per teacher move %.0f" % (sum(r[1] for r in rt) / seeds), flush=True)
if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]; main(*a)
