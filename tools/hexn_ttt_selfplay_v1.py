"""hexn_ttt_selfplay_v1: tic-tac-toe SELF-PLAY with a fixed budget (Python only; uses hexn_ttt_v1 unchanged).
Alan, 27 Oct 2026: after the opponent test, a self run, with a limited number of runs.
Two learners of the same kind play each other, one as X (moves first) and one as O, each with its own memory, learning only from win +64 / draw +16 / loss -32 and exploring 10 percent of its moves. BUDGET: 3,000 games per pair, 3 seeds, one pass; nothing is repeated or extended. Reported: the share of drawn games in games 2,501-3,000 of the self-play (exploration still on), the share of drawn games when both then play greedily (400 games, on copies), and how the trained X does as X against a random opponent and against the blocker (400 greedy games each) and the trained O's score as O against a random X. A perfect pair draws every game.
Limits: as hexn_ttt_v1 (layer 2 model with 10 key classes, which is wider than the chip's 3-bit events; move-history contexts)."""
import os, sys, random, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_ttt_v1 as T
REW_O = {2: 64, 0: 16, 1: -32}
class View:
    """wraps a learner so it can play either side: `me` is 1 (X) or 2 (O)"""
    def __init__(s, ag, me): s.ag = ag; s.me = me
def make(kind, me):
    ag = T.L2Agent(2) if kind == "l2" else T.L3Agent(5); ag.me = me
    if kind == "l3":
        orig = ag.observe
        def observe(who, c, ag=ag): ag.t += 5; ag.m.feed(ag.t, 0 if who == ag.me else 1, c); ag.m.flush()
        ag.observe = observe
    if me == 2:
        def end(res, ag=ag, kind=kind):
            r = T.REW[{1: 2, 2: 1, 0: 0}[res]]
            (ag.st.step(T.S.REW, r=r) if kind == "l2" else ag.m.reward(r))
        ag.end = end
    return ag
def play(ax, ao, rnd, eps):
    b = [0] * 9; ax.start(); ao.start(); turn = 1
    while True:
        ag = ax if turn == 1 else ao; lg = T.legal(b); c = None if rnd.random() < eps else ag.pick(b, lg, eps == 0)
        if c is None: c = rnd.choice(lg)
        b[c] = turn; ax.observe(turn, c); ao.observe(turn, c); w = T.winner(b)
        if w: return w
        if not T.legal(b): return 0
        turn = 3 - turn
def main(seeds=3, games=3000):
    for kind, name in (("l2", "layer 2 (goal read context 2)"), ("l3", "layer 3 (path up to 5)")):
        tot = dict(sp=0, greedy=0, vr=[0, 0, 0], vb=[0, 0, 0], o_vr=[0, 0, 0])
        for sd in range(seeds):
            rnd = random.Random(sd); ax, ao = make(kind, 1), make(kind, 2); res = []
            for g in range(games):
                r = play(ax, ao, rnd, 0.1); res.append(r); ax.end(r); ao.end(r)
            tot["sp"] += sum(1 for r in res[2500:] if r == 0) / 500 / seeds
            cx, co = copy.deepcopy(ax), copy.deepcopy(ao); gr = [play(cx, co, random.Random(100 + sd), 0.0) for _ in range(400)]; tot["greedy"] += sum(1 for r in gr if r == 0) / 400 / seeds
            for opp, key in ((T.opp_random, "vr"), (T.opp_blocker, "vb")):
                e = T.evaluate(ax, opp, random.Random(7 + sd), 400)
                for i in range(3): tot[key][i] += e[i] / seeds
            ev = [0, 0, 0]; cc = copy.deepcopy(ao); rr = random.Random(500 + sd)
            for _ in range(400):
                b = [0] * 9; cc.start(); turn = 1
                while True:
                    c = T.opp_random(b, rr) if turn == 1 else (lambda pk: rr.choice(T.legal(b)) if pk is None else pk)(cc.pick(b, T.legal(b), True))
                    b[c] = turn; cc.observe(turn, c); w = T.winner(b)
                    if w or not T.legal(b): ev[{2: 0, 0: 1, 1: 2}[w]] += 1; break
                    turn = 3 - turn
            for i in range(3): tot["o_vr"][i] += ev[i] / 400 / seeds
        f = lambda v: " / ".join("%.2f" % x for x in v)
        print("%s, %d games per pair, %d seeds:\n  drawn share in self-play games 2501-3000 (10%% random moves): %.2f\n  drawn share when both then play greedily: %.2f\n  trained X vs random [win/draw/loss]: %s | vs blocker: %s\n  trained O vs random X [win/draw/loss]: %s" % (name, games, seeds, tot["sp"], tot["greedy"], f(tot["vr"]), f(tot["vb"]), f(tot["o_vr"])))
if __name__ == "__main__": main()
