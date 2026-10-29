"""hexn_connect4_selfplay_v1: THE SUGGESTION SYSTEM PLAYS ITSELF (Python only; no RTL, nothing on a card).
Alan, 29 Oct 2026, 23:50: 'how do I get it to play itself?'
Two copies of tools/hexn_connect4_suggest_v1.py System (layer 4 suggests, layer 3 chooses, results reward) play each other: A as X (moves first), B as O. Each copy is written for X, so B is shown a MIRRORED board (counters swapped 1 <-> 2) and its own moves are 'X' to it; the rival's moves arrive on channel 1 as before. Both learn: 30% of their non-forced moves follow their own layer 4 suggestion and 10% are random during training; the real result rewards every entry used (win +64, draw +16, loss -32 from each side's own view).
Measured: in blocks of games, A wins / draws / B wins; mean game length (plies); how many distinct opening sequences (first 4 plies) were played in the block (does it settle into repeating?); and after training, each side's copy plays 100 greedy games against the FIXED blocker and lookahead(2) (as the earlier tables; layer 3 chooses with layer 4 suggesting, X moves first for the copy of A; the copy of B plays X as well, using its own learning).
Limits: the two layer 3 instances per side (planner's predictor and the chooser) as in suggest_v1; small samples; nothing tuned; X's first-move advantage means A is expected to win more."""
import os, sys, copy, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_suggest_v1 as S
def mirror(b): return [[0 if v == 0 else 3 - v for v in col] for col in b]
def game(A, B, rnd, train=True):
    b = C.new(); A.start(); B.start(); turn = 1; seq = []
    while True:
        if turn == 1: c = A.x_move(b, rnd, train, True)
        else: c = B.x_move(mirror(b), rnd, train, True)
        C.drop(b, c, turn); seq.append(c)
        A.observe(1 if turn == 1 else 2, c); B.observe(1 if turn == 2 else 2, c)
        w = C.winner(b)
        if w: res = w; break
        if C.full(b): res = 0; break
        turn = 3 - turn
    if train:
        A.m.reward(S.REW[res]); B.m.reward(S.REW[{1: 2, 2: 1, 0: 0}[res]])
    return res, seq
def main(games=600, block=100, seed=0, n_eval=50):
    rnd = random.Random(seed); A = S.System(dmax=4, conf=0.8); B = S.System(dmax=4, conf=0.8)
    print("self-play: A is X (first), B is O; blocks of %d games: A wins / draws / B wins; mean plies; distinct 4-ply openings" % block)
    res = []; opens = set(); plies = 0
    for g in range(1, games + 1):
        r, seq = game(A, B, rnd); res.append(r); opens.add(tuple(seq[:4])); plies += len(seq)
        if g % block == 0:
            bl = res[-block:]; print("games %4d-%4d   %.2f / %.2f / %.2f   plies %.1f   openings %d of %d" % (g - block + 1, g, bl.count(1) / block, bl.count(0) / block, bl.count(2) / block, plies / block, len(opens), block), flush=True); opens = set(); plies = 0
    for name, ag in (("copy of A", A), ("copy of B", B)):
        for oname, opp in (("blocker", C.opp_blocker), ("lookahead(2)", C.make_lookahead(2))):
            wl, fo, no = S.evaluate(ag, opp, random.Random(seed + 99), n_eval, True)
            wa, fa, na = S.evaluate(ag, opp, random.Random(seed + 99), n_eval, False)
            print("%s vs %-13s with layer 4: %.2f / %.2f / %.2f (follow %.2f)   layer 3 alone: %.2f / %.2f / %.2f" % (name, oname, wl[0], wl[1], wl[2], fo, wa[0], wa[1], wa[2]), flush=True)
if __name__ == "__main__":
    a = [int(x) for x in sys.argv[1:]]; main(*a)
