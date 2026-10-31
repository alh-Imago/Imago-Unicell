"""hexn_helper_judge_v4: A JUDGE TRAINED ON POSITIONS FROM BOTH COLOURS (Python + numpy; model only; new file 31 Oct 2026; v1 to v3 untouched).
Why: the 31 Oct whole-stack test (docs/hex-n/HEXN_DESIGN.md) showed the v3 judge as leaf plays as well as the hand score when it is the FIRST player (0.89 / 0.91 against 0.85 / 0.89, plain depth 3 / 4 against lookahead(2) + 20% random) but much worse as the SECOND player (0.49 / 0.62 against 0.75 / 0.80): v3 was trained only on leaves seen from the first player's tree. v4 trains the same network (127 inputs, H hidden, tanh output, value for the FIRST player) on positions from games between mixed players, every position labelled by a DEPTH-6 alpha-beta search with the hand score from the first player's view (a win or loss in sight = +1 / -1, otherwise tanh(score / 40)); positions are taken from both colours' play and from one random move off the game line.
Usage: python3 tools/hexn_helper_judge_v4.py gen GAMES SEED OUT.npz   |   python3 tools/hexn_helper_judge_v4.py train OUT.json H EPOCHS data1.npz [data2.npz ...]  (train is tools/hexn_helper_judge_v1.py train).
Limits: Connect Four only; the teacher is the hand score searched six plies; positions are not the search's own leaves; held-out games are used only to report error."""
import os, sys, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_helper_judge_v1 as J
def label(b):
    n = sum(1 for col in b for v in col if v); turn = 1 if n % 2 == 0 else 2
    if C.winner(b): return 1.0 if C.winner(b) == 1 else -1.0
    v = C.search(b, 1, turn, 6, -10 ** 9, 10 ** 9)
    if abs(v) > 5000: return 1.0 if v > 0 else -1.0
    return float(np.tanh(v / 40.0))
def gen(games, seed, out, per_game=14):
    rnd = random.Random(seed); F = []; Y = []; G = []
    mix = [C.make_lookahead(2), C.make_lookahead(3), C.opp_blocker, C.opp_random, C.make_lookahead(1)]
    for g in range(games):
        b = C.new(); who = 1; pl = {1: rnd.choice(mix), 2: rnd.choice(mix)}; seen = []
        while True:
            c = rnd.choice(C.legal(b)) if rnd.random() < 0.12 else pl[who](b, who, rnd); C.drop(b, c, who)
            if C.winner(b) or C.full(b): break
            seen.append([col[:] for col in b]); who = 3 - who
        rnd.shuffle(seen)
        for b in seen[:per_game]:
            if rnd.random() < 0.3:
                c = rnd.choice(C.legal(b)); C.drop(b, c, 1 if sum(1 for col in b for v in col if v) % 2 == 0 else 2)
            F.append(J.feats(b)); Y.append(label(b)); G.append(seed * 100000 + g)
    np.savez_compressed(out, F=np.array(F), Y=np.array(Y, dtype=np.float32), G=np.array(G)); print("wrote", out, len(Y), "positions from", games, "games")
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "gen": gen(int(a[1]), int(a[2]), a[3])
    else: J.train(a[1], int(a[2]), int(a[3]), a[4:])
