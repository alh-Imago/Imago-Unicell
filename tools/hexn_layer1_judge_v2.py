"""hexn_layer1_judge_v2: CLONE of v1 (v1 untouched) with STRONGER training games: players lookahead 2, 3, 3, 4, 4, 5% random moves (v1: lookahead 1 to 3 + blocker, 12%). Reason: the v1 judges lost to the strong opponent (ledger 12:00). Original text of v1 follows.
hexn_layer1_judge_v1: LAYER 1 + JUDGE ONLY (Python + numpy; model only; new file 31 Oct 2026). Alan, 31 Oct 09:55: 'layers 1 to 4 are the choice makers and the judge acts on choice alone - try a small test of just 1 and judge, as most of the work, the initial step, is done in 1'.
Reading taken: layer 1 = the counted detectors. In Connect Four the detectors are the 69 lines of four cells; each line is 'pure' for a side when it holds only that side's counters, and the detector counts how many counters (1, 2 or 3). Layer 1 output = how many pure lines hold 1, 2, 3 counters for X, the same for O, plus the parity: 7 numbers, no board, no history, no layers 2 to 4. The judge sees ONLY these 7 numbers. (The hand score is the same 6 counts with fixed weights 1, 4, 9 - so this test asks whether a judge LEARNED from game results can read layer 1 better than the fixed weights.)
Judges compared (all trained on the same position set, label = actual result of the game seen from X, NOT a search value): 'lin' = tanh(w.x+b), 8 numbers; 'net' = 7 -> H relu -> tanh; 'raw' = the 127-input board judge (hexn_helper_judge_v1.train) as a control; hand score = tanh(score/40), untrained.
Usage: python3 tools/hexn_layer1_judge_v1.py gen GAMES SEED OUT.npz | train OUT_PREFIX H EPOCHS data.npz... | play OPP CAND... (CAND: plain3 hand score; L3 lin; N3 net; R3 raw, same with 4) [--games --seeds]
Limits: Connect Four only; mixed-strength players supply the games; outcome labels are noisy; judge weights are float."""
import os, sys, json, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_helper_judge_v1 as J, hexn_judge_int_v1 as JI
def l1(b):
    f = np.zeros(7, dtype=np.float32)
    for cells in C.LINES:
        v = [b[x][y] for x, y in cells]; x, o = v.count(1), v.count(2)
        if x and not o and x < 4: f[x - 1] += 1
        elif o and not x and o < 4: f[3 + o - 1] += 1
    f[:6] /= 8.0; f[6] = sum(1 for col in b for v in col if v) % 2; return f
def board(f):
    b = [[0] * C.ROWS for _ in range(C.COLS)]
    for c in range(C.COLS):
        for r in range(C.ROWS): i = (c * C.ROWS + r) * 3; b[c][r] = int(np.argmax(f[i:i + 3]))
    return b
def gen(games, seed, out, per_game=10):
    rnd = random.Random(seed); F = []; Y = []; G = []
    mix = [C.make_lookahead(2), C.make_lookahead(3), C.make_lookahead(3), C.make_lookahead(4), C.make_lookahead(4)]
    for g in range(games):
        b = C.new(); who = 1 if rnd.random() < .5 else 2; pl = {1: rnd.choice(mix), 2: rnd.choice(mix)}; seen = []; res = 0
        while True:
            c = rnd.choice(C.legal(b)) if rnd.random() < 0.05 else pl[who](b, who, rnd); C.drop(b, c, who); w = C.winner(b)
            if w: res = 1 if w == 1 else -1; break
            if C.full(b): break
            seen.append([col[:] for col in b]); who = 3 - who
        rnd.shuffle(seen)
        for b in seen[:per_game]: F.append(J.feats(b)); Y.append(res); G.append(seed * 100000 + g)
    np.savez_compressed(out, F=np.array(F), Y=np.array(Y, dtype=np.float32), G=np.array(G)); print("wrote", out, len(Y), "positions from", games, "games")
def fit(X, Y, H, epochs, rs):
    n = X.shape[1]
    if H: P = [rs.randn(n, H).astype(np.float32) * .3, np.zeros(H, np.float32), rs.randn(H, 1).astype(np.float32) * .3, np.zeros(1, np.float32)]
    else: P = [np.zeros((n, 1), np.float32), np.zeros(1, np.float32)]
    M = [np.zeros_like(p) for p in P]; V = [np.zeros_like(p) for p in P]; t = 0
    def fwd(x):
        if H: h = np.maximum(x @ P[0] + P[1], 0); return h, np.tanh(h @ P[2] + P[3])[:, 0]
        return None, np.tanh(x @ P[0] + P[1])[:, 0]
    for ep in range(epochs):
        idx = rs.permutation(len(Y))
        for i in range(0, len(idx), 128):
            j = idx[i:i + 128]; x, y = X[j], Y[j]; h, o = fwd(x); d = (2 * (o - y) * (1 - o ** 2) / len(j))[:, None]
            if H: g = [x.T @ ((d @ P[2].T) * (h > 0)), ((d @ P[2].T) * (h > 0)).sum(0), h.T @ d, d.sum(0)]
            else: g = [x.T @ d, d.sum(0)]
            t += 1
            for k, (p, gk) in enumerate(zip(P, g)):
                M[k] = .9 * M[k] + .1 * gk; V[k] = .999 * V[k] + .001 * gk * gk; p -= .01 * (M[k] / (1 - .9 ** t)) / (np.sqrt(V[k] / (1 - .999 ** t)) + 1e-8)
    return P, fwd
class L1Judge:
    def __init__(s, path): W = json.load(open(path)); s.P = [np.array(W[k], dtype=np.float64) for k in W["keys"]]; s.H = W["H"]
    def value(s, b):
        x = l1(b).astype(np.float64)
        if s.H: return float(np.tanh(np.maximum(x @ s.P[0] + s.P[1], 0) @ s.P[2] + s.P[3])[0])
        return float(np.tanh(x @ s.P[0] + s.P[1])[0])
def train(prefix, H, epochs, paths):
    D = [np.load(p) for p in paths]; F = np.concatenate([d["F"] for d in D]); Y = np.concatenate([d["Y"] for d in D]); G = np.concatenate([d["G"] for d in D])
    ug = np.unique(G); rs = np.random.RandomState(0); rs.shuffle(ug); hold = set(ug[:max(1, int(.15 * len(ug)))].tolist()); te = np.array([g in hold for g in G]); tr = ~te
    X = np.array([l1(board(f)) for f in F]); print("positions %d (train %d, held out %d), layer 1 inputs %d" % (len(Y), tr.sum(), te.sum(), X.shape[1]))
    hs = J.hand_scores(F[te]); print("hand score (fixed weights) held-out MSE %.4f corr %.3f   constant 0: %.4f" % (np.mean((hs - Y[te]) ** 2), np.corrcoef(hs, Y[te])[0, 1], np.mean(Y[te] ** 2)))
    for name, h in (("lin", 0), ("net", H)):
        P, fwd = fit(X[tr], Y[tr], h, epochs, rs); _, o = fwd(X[te])
        print("layer 1 judge %-3s held-out MSE %.4f corr %.3f" % (name, np.mean((o - Y[te]) ** 2), np.corrcoef(o, Y[te])[0, 1]))
        keys = ["W1", "b1", "W2", "b2"][:len(P)]; json.dump({"H": h, "keys": keys, **{k: p.tolist() for k, p in zip(keys, P)}}, open("%s_%s.json" % (prefix, name), "w"))
        if not h: print("  weights (1,2,3 own lines; 1,2,3 opponent lines; parity; bias):", np.round(P[0][:, 0], 2).tolist(), round(float(P[1][0]), 2))
    J.train(prefix + "_raw.json", 64, epochs, paths)
def play(opp, cands, games, seeds, prefix):
    import hexn_connect4_blend_v2 as B
    for k, nm in (("l", "lin"), ("n", "net")): B.JUDGE[k] = L1Judge("%s_%s.json" % (prefix, nm))
    B.JUDGE["r"] = JI.JudgeFloat("%s_raw.json" % prefix)
    old = B.make
    def make(name):
        if name[0] in "LNR" and name[1:].isdigit(): return B.plain_j(int(name[1:]), {"L": "l", "N": "n", "R": "r"}[name[0]])
        return old(name)
    B.make = make; B.main(opp, cands, games, seeds)
if __name__ == "__main__":
    a = sys.argv[1:]; games, seeds = 40, 3
    if "--games" in a: i = a.index("--games"); games = int(a[i + 1]); del a[i:i + 2]
    prefix = os.environ.get("L1PREFIX", "l1judge")
    if "--seeds" in a: i = a.index("--seeds"); seeds = int(a[i + 1]); del a[i:i + 2]
    if a[0] == "gen": gen(int(a[1]), int(a[2]), a[3])
    elif a[0] == "train": train(a[1], int(a[2]), int(a[3]), a[4:])
    elif a[0] == "play": play(a[1], a[2:], games, seeds, prefix)
