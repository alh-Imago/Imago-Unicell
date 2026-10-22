"""Pattern recall (associative memory) model, no RTL. Question (Alan, 22 Oct): the leaky accumulators hold a pattern for a while and then lose it; can a stored copy be brought back when a PARTIAL cue arrives?
Setup: N lanes (the class cells; 7 or 19), a pattern = a set of Kact lanes that are active together (each a token burst). M patterns are stored. A cue = a random PART of one stored pattern (Kcue of its Kact lanes), each cue lane dropped with probability pdrop, plus each other lane falsely active with probability pfalse. Score = the completed set equals the stored pattern exactly.
Methods: none (the cue as it is: never complete by construction when Kcue < Kact), lookup (a small store of the M patterns; recall = the stored pattern with the largest overlap with the cue, ties = failure; that is a content-addressable memory), cells (NO store: lane weights set once by a clipped Hebbian rule, W_ij = sign(sum over patterns of (2a_i-1)(2a_j-1)) in {-1,0,+1}, the three settings a cell lane has; each cell i fires when sum_j W_ij x_j > t; one step; t is the best single value for the whole run, chosen on a separate sample).
Usage: python3 tools/hexn_recall_model_v1.py [N] [Kact] [Kcue] [pdrop] [pfalse] [TRIALS]"""
import sys, random
N = int(sys.argv[1]) if len(sys.argv) > 1 else 19; Kact = int(sys.argv[2]) if len(sys.argv) > 2 else 5; Kcue = int(sys.argv[3]) if len(sys.argv) > 3 else 3
pdrop = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0; pfalse = float(sys.argv[5]) if len(sys.argv) > 5 else 0.02; T = int(sys.argv[6]) if len(sys.argv) > 6 else 400
def sgn(v): return (v > 0) - (v < 0)
def trial(r, pats, W, t):
    p = r.choice(pats); part = r.sample(sorted(p), Kcue); cue = {i for i in part if r.random() >= pdrop} | {i for i in range(N) if i not in p and r.random() < pfalse}
    best = max(len(cue & q) - 0 * len(cue - q) for q in pats); winners = [q for q in pats if len(cue & q) == best]
    look = (len(winners) == 1 and winners[0] == p)
    out = {i for i in range(N) if sum(W[i][j] for j in cue if j != i) > t}
    return look, out == set(p), out
print("N=%d lanes, %d active per pattern, cue = %d of them, drop %.2f, false %.2f, %d trials per row" % (N, Kact, Kcue, pdrop, pfalse, T))
print("stored | lookup | cells (best threshold t)")
for M in (1, 2, 4, 8, 12, 16, 24):
    r = random.Random(M); pats = []
    while len(pats) < M:
        q = frozenset(r.sample(range(N), Kact))
        if q not in pats: pats.append(q)
    W = [[0] * N for _ in range(N)]
    for i in range(N):
        for j in range(N):
            if i != j: W[i][j] = sgn(sum((2 * (i in q) - 1) * (2 * (j in q) - 1) for q in pats))
    bestc = (-1, None)
    for t in range(-2, 8):
        rr = random.Random(99); c = sum(trial(rr, pats, W, t)[1] for _ in range(150))
        if c > bestc[0]: bestc = (c, t)
    t = bestc[1]; rr = random.Random(5); lk = ce = 0
    for _ in range(T): a, b, _o = trial(rr, pats, W, t); lk += a; ce += b
    print("%6d | %.3f | %.3f (t=%d)" % (M, lk / T, ce / T, t))
