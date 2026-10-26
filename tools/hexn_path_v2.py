"""hexn_path_v2: TWO CHANNELS + A COMBINING LEVEL 3 (ABSTRACT TABLE MODEL, not cells; Python only; new file; imports hexn_path_v1.py, left untouched).
A hidden SITUATION s (0..5) is seen through two sensors. Each channel has its own token stream (level 1 output, each token mis-recognised with chance p) and its own level 2 (a table keyed on the last k=3 tokens, learned from ITS OWN end reward: the right goal of that channel, as in hexn_path_v1).
Channel A's goal for situation s is GA[s], channel B's is GB[s]. Each channel's goal alone is ambiguous (each goal value belongs to two situations); the pair of goals identifies the situation.
Level 3 = a table keyed on the two level-2 answers (greedy answers of the level-2 tables at that moment), learned from the end reward of guessing the situation (right +1, wrong -0.5; explores 10 percent). 
Compared: level 3 hearing channel A only, channel B only, both, and both with channel B missing 30 percent of the time (its answer replaced by a 'missing' marker).
ASSUMPTIONS: each channel has its own goal teacher for level 2 (the reward for the right channel goal); the sequence end is marked; the two channels are independent given the situation; hand-built world.
Usage: python3 tools/hexn_path_v2.py seeds episodes"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_path_v1 as P1
GA = [0, 0, 1, 1, 2, 2]; GB = [0, 1, 1, 2, 2, 0]          # situation -> goal of channel A, of channel B; pairs (0,0),(0,1),(1,1),(1,2),(2,2),(2,0) are all different
ROUTES_BY_GOAL = {}
for r, g in P1.ROUTES.items(): ROUTES_BY_GOAL.setdefault(g, []).append(r)
def seq_for(rnd, goal, shift, p):
    r = rnd.choice(ROUTES_BY_GOAL[goal]); r = tuple((t + shift) % P1.NTOK for t in r)
    return tuple(t if rnd.random() >= p else rnd.randrange(P1.NTOK) for t in r)
class Table:
    def __init__(s, nans): s.V = {}; s.n = {}; s.nans = nans
    def answer(s, key, rnd, explore=0.1):
        v = s.V.setdefault(key, [0.0] * s.nans)
        return rnd.randrange(s.nans) if rnd.random() < explore else max(range(s.nans), key=lambda j: v[j])
    def greedy(s, key): v = s.V.setdefault(key, [0.0] * s.nans); return max(range(s.nans), key=lambda j: v[j])
    def learn(s, key, a, r):
        c = s.n.setdefault(key, [0] * s.nans); v = s.V.setdefault(key, [0.0] * s.nans); c[a] += 1; v[a] += (r - v[a]) / c[a]
def run(seed, mode, p, episodes, drop=0.0, k=3):
    rnd = random.Random(seed); LA = Table(3); LB = Table(3); L3 = Table(6); hits = []
    for _ in range(episodes):
        s = rnd.randrange(6); sa = seq_for(rnd, GA[s], 0, p); sb = seq_for(rnd, GB[s], 2, p); missing = rnd.random() < drop
        ka, kb = sa[-k:], sb[-k:]
        aa = LA.answer(ka, rnd); ab = LB.answer(kb, rnd)                     # level 2 answers (explore as in v1)
        LA.learn(ka, aa, 1.0 if aa == GA[s] else -0.5); LB.learn(kb, ab, 1.0 if ab == GB[s] else -0.5)
        ga, gb = LA.greedy(ka), LB.greedy(kb)                                # level 3 hears the greedy level-2 answers
        key = {"A": (ga,), "B": (gb,), "AB": (ga, 3 if missing else gb)}[mode]
        a3 = L3.answer(key, rnd); L3.learn(key, a3, 1.0 if a3 == s else -0.5); hits.append(a3 == s)
    last = hits[-500:]; return sum(last) / len(last)
if __name__ == "__main__":
    seeds, episodes = int(sys.argv[1]), int(sys.argv[2])
    print(f"6 situations, two channels, level 3 guesses the situation; {seeds} seeds, {episodes} episodes, accuracy over the last 500 (exploration included, ceiling about 0.92); chance 0.17")
    print("token noise p |  A only  B only  both   both, B missing 30%")
    for p in (0.0, 0.1, 0.2):
        f = lambda mode, drop=0.0: sum(run(s, mode, p, episodes, drop) for s in range(seeds)) / seeds
        print(f"    {p:.1f}      |   {f('A'):.2f}    {f('B'):.2f}    {f('AB'):.2f}      {f('AB', 0.3):.2f}")
