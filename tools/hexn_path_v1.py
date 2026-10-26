"""hexn_path_v1: LEVEL 2, first toy world (ABSTRACT TABLE MODEL, not cells; Python only; new file).
Level 1 is assumed to hand over a stream of recognised patterns (tokens 0..5), each mis-recognised with probability p. A route is a short token sequence that ends in a goal (0, 1 or 2); other sequences lead nowhere (right answer = 'none').
The system sees the stream, and at the END of a sequence it must answer a goal or 'none'. Reward arrives only then (right +1, wrong -0.5), with no label of the true route. The learner keeps, for each key = the last k tokens, a running value for each answer, explores with chance 0.1, and learns from that end reward only.
Question this answers: how much of the recent past does level 2 have to keep (k = 1, 2, 3) when the same token means different things after different earlier tokens, and several routes reach the same goal? ASSUMPTION: the sequence end is marked; one answer per sequence; no choice of actions on the way (this is recognising routes, not yet steering).
Usage: python3 tools/hexn_path_v1.py seeds episodes"""
import sys, random
ROUTES = {(0, 1): 0, (3, 1): 0, (5, 5): 0,           # three routes to goal 0
          (0, 2): 1, (4, 1): 1,                       # (4,1) ends in 1 like (0,1) and (3,1) end in 0: the last token alone is ambiguous
          (0, 1, 3): 2, (2, 1, 3): 0, (4, 1, 3): 1}   # length 3: after (1,3) the earlier token decides; (0,1) -> goal 0 at length 2 but (0,1,3) -> goal 2 at length 3
NTOK, NANS = 6, 4                                     # answers 0..2 = goal, 3 = none
def episode(rnd, p):
    if rnd.random() < 0.75: seq = rnd.choice(list(ROUTES)); y = ROUTES[seq]
    else:
        while True:
            seq = tuple(rnd.randrange(NTOK) for _ in range(rnd.choice((2, 3))))
            if seq not in ROUTES: break
        y = 3
    seen = tuple(t if rnd.random() >= p else rnd.randrange(NTOK) for t in seq)
    return seen, y
def run(seed, k, p, episodes):
    rnd = random.Random(seed); V = {}; n = {}; hits = []
    for _ in range(episodes):
        seen, y = episode(rnd, p); key = seen[-k:]; v = V.setdefault(key, [0.0] * NANS); c = n.setdefault(key, [0] * NANS)
        a = rnd.randrange(NANS) if rnd.random() < 0.1 else max(range(NANS), key=lambda j: v[j])
        r = 1.0 if a == y else -0.5; c[a] += 1; v[a] += (r - v[a]) / c[a]; hits.append(a == y)
    last = hits[-500:]; return sum(last) / len(last)
if __name__ == "__main__":
    seeds, episodes = int(sys.argv[1]), int(sys.argv[2])
    print(f"{len(ROUTES)} routes to 3 goals, 25 percent of sequences lead nowhere; {seeds} seeds, {episodes} episodes, accuracy over the last 500 (answer = right goal or right 'none'); chance about 0.25")
    print("window k |  token noise p = 0.0  0.1  0.2")
    for k in (1, 2, 3):
        print(f"   {k}     |  " + "  ".join(f"{sum(run(s, k, p, episodes) for s in range(seeds)) / seeds:.2f}" for p in (0.0, 0.1, 0.2)))
