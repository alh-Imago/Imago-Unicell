"""hexn_connect4_suggest_v1: LAYER 4 SUGGESTS A STEP, LAYER 3 CHOOSES, THE RESULT REWARDS FOLLOWING (Python only; no RTL, nothing on a card).
Alan, 29 Oct 2026, 23:46: the step is a SUGGESTION, not an order; following it is rewarded when it works. This is the first version of goal passing (the goal read from layer 3's side, the planning from layer 4's).
Structure: LAYER 4 = tools/hexn_connect4_layer4_v3.py Planner3 (depth 4, free plies at confidence .8; tree with its own predictor of the opponent, a plain two-channel layer 3 fed only with the moves). LAYER 3 (the chooser) = hexn_layer3_v2.Layer3R with THREE channels: 0 = X's column, 1 = O's column, 2 = the GOAL (layer 4's suggested column 0..6, or 7 = none). Path up to 5 snapshots, masks (1,1,1), (1,0,1), (1,1,0), (1,0,0), min_n 2. Each X turn: (1) forced cases (win now, else block now) are played by layer 4 directly and no goal is sent (in the ALONE measurement this help is switched off too: layer 3 only); (2) otherwise layer 4 searches and sends its best column as a goal event (its own moment, before the choice); (3) layer 3 chooses among the legal columns from its learned values (contexts include the goal); if it has no opinion it plays RANDOM (never silently the suggestion); (4) the move and O's reply are fed in; (5) at the end of the game the real result rewards every entry used. Training exploration: 10% random move, and 30% of the time the move played is the suggestion (so that following can be tried and rewarded).
Measured after N training games, on a COPY, greedy, 100 games [win / draw / loss]: WITH suggestions (layer 4 still sending goals) and ALONE (goal = 7 none every turn: layer 3 without layer 4). Also: follow rate (X moves that equal the suggestion, among the non-forced moves), 'no opinion' rate (layer 3 had no value, played random), and layer 4 positions per search.
Limits: the layer 4 predictor and the chooser are two layer 3 instances (a simplification; one shared instance is what the design intends); goal = a column only; re-search every move (no plan reuse); small samples; nothing tuned."""
import os, sys, copy, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer3_v2 as V2, hexn_connect4_v1 as C, hexn_connect4_l23_v1 as L23, hexn_connect4_layer4_v1 as L1, hexn_connect4_layer4_v3 as L3P
REW, START, NONE = L23.REW, 7, 7
class System:
    def __init__(s, **kw):
        s.pl = L3P.Planner3(mode="tree3", theta=0.04, tactics=True, **kw)
        s.m = V2.Layer3R(nch=3, L=5, align=2, half=10 ** 9, masks=[(1, 1, 1), (1, 0, 1), (1, 1, 0), (1, 0, 0)], min_n=2); s.t = 0
        s.stats = dict(moves=0, followed=0, none=0, forced=0)
    def feed(s, ch, key): s.t += 5; s.m.feed(s.t, ch, key); s.m.flush()
    def start(s):
        s.pl.start(); m = s.m; m.hist = []; m.snap = [None, None, None]; m.used = []; s.t += 20; m.feed(s.t, 1, START); m.flush()
    def x_move(s, b, rnd, train, use_goal):
        """returns the column X plays"""
        lg = C.legal(b); s.stats["moves"] += 1
        f = (L1.can_win(b, 1) or L1.can_win(b, 2)) if use_goal else []      # ALONE mode: no tactical help at all, layer 3 only
        if f: s.stats["forced"] += 1; return f[0]
        g = s.pl.pick(b, rnd) if use_goal else NONE
        s.feed(2, g)
        if train and rnd.random() < 0.10: return rnd.choice(lg)
        if train and use_goal and rnd.random() < 0.30: return g
        mo, lv = s.m.choose([((0, c),) for c in lg])
        if mo is None: s.stats["none"] += 1; return rnd.choice(lg)
        c = mo[0][1]
        if use_goal and c == g: s.stats["followed"] += 1
        return c
    def observe(s, who, c): s.pl.observe(who, c); s.feed(0 if who == 1 else 1, c)
def play(sy, opp, rnd, train, use_goal=True):
    b = C.new(); sy.start(); turn = 1
    while True:
        c = sy.x_move(b, rnd, train, use_goal) if turn == 1 else opp(b, 2, rnd)
        C.drop(b, c, turn); sy.observe(turn, c); w = C.winner(b)
        if w: res = w; break
        if C.full(b): res = 0; break
        turn = 3 - turn
    if train: sy.m.reward(REW[res])
    return res
def evaluate(sy, opp, rnd, n, use_goal):
    ag = copy.deepcopy(sy); ag.stats = dict(moves=0, followed=0, none=0, forced=0); c = [0, 0, 0]
    for _ in range(n): c[play(ag, opp, rnd, False, use_goal)] += 1
    st = ag.stats; nf = max(st["moves"] - st["forced"], 1)
    return [c[1] / n, c[0] / n, c[2] / n], st["followed"] / nf, st["none"] / nf
def run(opp, games, seed, check, n_eval, **kw):
    rnd = random.Random(seed); sy = System(**kw); out = []
    for g in range(1, games + 1):
        play(sy, opp, rnd, True, True)
        if g in check: out.append((evaluate(sy, opp, random.Random(seed + 99), n_eval, True), evaluate(sy, opp, random.Random(seed + 99), n_eval, False)))
    return out, sy.pl.created / max(sy.pl.moves, 1)
def main(seeds=2, games=600, n_eval=100):
    check = (games // 6, games // 2, games)
    for oname, opp in (("BLOCKER opponent", C.opp_blocker), ("lookahead(2) opponent", C.make_lookahead(2))):
        print("\n%s: after N training games, greedy play of %d games on a copy [win / draw / loss]; follow rate / no-opinion rate among non-forced moves; mean of %d seeds" % (oname, n_eval, seeds))
        rs = [run(opp, games, s, check, n_eval, dmax=4, conf=0.8) for s in range(seeds)]
        for i, c in enumerate(check):
            for k, name in ((0, "layer 3 chooses, layer 4 suggests"), (1, "layer 3 alone (goal = none)")):
                wl = [sum(r[0][i][k][0][j] for r in rs) / seeds for j in range(3)]; fo = sum(r[0][i][k][1] for r in rs) / seeds; no = sum(r[0][i][k][2] for r in rs) / seeds
                print("after %-4d %-36s %.2f / %.2f / %.2f   follow %.2f  no-opinion %.2f" % (c, name, wl[0], wl[1], wl[2], fo, no), flush=True)
        print("layer 4 positions per search %.0f" % (sum(r[1] for r in rs) / seeds), flush=True)
if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]; main(*a)
