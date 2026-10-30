"""hexn_helper_judge_v1: MODEL OF THE NEURAL HELPER AS A POSITION JUDGE FOR LAYER 4 (Python + numpy only; no RTL, nothing on a card).
Alan, 30 Oct 2026, 16:22: model the helper first and see if it makes a real change. Design source: docs/hex-n/HEXN_DESIGN.md rows of 10:25 and 14:35 (job 1: score an unfinished position so the tree can stop early).
What this file does: (gen) plays games of layer 4 (tools/hexn_connect4_cand_v1.py P, 'empty' opponent model, depth 4, X plays a random column 15% of the time for variety) against lookahead(2) or the blocker, each with 20% random moves, and records EVERY position after every ply with the final result from X's side (+1 win, 0 draw, -1 loss); (train) fits a small network on them: input 127 = 42 squares x (empty, X, O) + the parity of the number of counters; one hidden layer of H relu units; one tanh output. Held out: 15% of the GAMES. Reports the mean squared error against the hand score tanh(score/40) that layer 4 uses now, and the same after the weights are rounded to 8 bits.
Seeds for training games are 1000 and up; tests (hexn_connect4_judge_v1.py) use seeds 0 to 5.
Usage: python3 tools/hexn_helper_judge_v1.py gen OPP GAMES SEED OUT.npz   (OPP = look or block)   |   python3 tools/hexn_helper_judge_v1.py train OUT.json H EPOCHS IN1.npz IN2.npz ...
Limits: Connect Four only; labels are the game result, not a value of the position; training and test opponents are the same families; the 8-bit check rounds the weights only (activations stay float)."""
import os, sys, json, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_connect4_layer4_v1 as L1, hexn_connect4_stale_v2 as S2, hexn_connect4_cand_v1 as X
COLS, ROWS = C.COLS, C.ROWS
def feats(b):
    f = np.zeros(COLS * ROWS * 3 + 1, dtype=np.float32); n = 0
    for c in range(COLS):
        for r in range(ROWS):
            v = b[c][r]; f[(c * ROWS + r) * 3 + v] = 1.0; n += v != 0
    f[-1] = n % 2; return f
def gen(opp_name, games, seed, out):
    rnd = random.Random(seed); opp = S2.noisy(C.make_lookahead(2) if opp_name == "look" else C.opp_blocker, 0.2)
    pl = X.P("empty", 0.0, mode="tree3", theta=0.04, tactics=True, dmax=4, conf=0.8); F = []; Y = []; G = []
    for g in range(games):
        b = C.new(); pl.start(); turn = 1; rec = []
        while True:
            c = pl.pick(b, rnd) if turn == 1 else opp(b, 2, rnd)
            if turn == 1 and rnd.random() < 0.15: c = rnd.choice(C.legal(b))
            C.drop(b, c, turn); pl.observe(turn, c); rec.append(feats(b)); w = C.winner(b)
            if w: res = 1 if w == 1 else -1; break
            if C.full(b): res = 0; break
            turn = 3 - turn
        for f in rec: F.append(f); Y.append(res); G.append(seed * 100000 + g)
    np.savez_compressed(out, F=np.array(F), Y=np.array(Y, dtype=np.float32), G=np.array(G)); print("wrote", out, len(Y), "positions from", games, "games")
def hand_scores(Fm):
    out = []
    for f in Fm:
        b = [[0] * ROWS for _ in range(COLS)]
        for c in range(COLS):
            for r in range(ROWS):
                i = (c * ROWS + r) * 3; b[c][r] = int(np.argmax(f[i:i + 3]))
        out.append(np.tanh(C.score(b, 1) / 40.0))
    return np.array(out, dtype=np.float32)
def train(out, H, epochs, paths):
    D = [np.load(p) for p in paths]; F = np.concatenate([d["F"] for d in D]); Y = np.concatenate([d["Y"] for d in D]); G = np.concatenate([d["G"] for d in D])
    ug = np.unique(G); rs = np.random.RandomState(0); rs.shuffle(ug); hold = set(ug[:max(1, int(0.15 * len(ug)))].tolist()); te = np.array([g in hold for g in G]); tr = ~te
    print("positions %d (train %d, held out %d from %d games)" % (len(Y), tr.sum(), te.sum(), len(hold)))
    hs = hand_scores(F[te]); print("hand score on held-out: MSE %.4f   correlation with result %.3f" % (np.mean((hs - Y[te]) ** 2), np.corrcoef(hs, Y[te])[0, 1]))
    print("constant 0: MSE %.4f" % np.mean(Y[te] ** 2))
    n_in = F.shape[1]; W1 = rs.randn(n_in, H).astype(np.float32) * 0.1; b1 = np.zeros(H, np.float32); W2 = rs.randn(H, 1).astype(np.float32) * 0.1; b2 = np.zeros(1, np.float32)
    P = [W1, b1, W2, b2]; M = [np.zeros_like(p) for p in P]; V = [np.zeros_like(p) for p in P]; t = 0; Ftr, Ytr = F[tr], Y[tr]
    def fwd(Fx):
        h = np.maximum(Fx @ W1 + b1, 0); o = np.tanh(h @ W2 + b2)[:, 0]; return h, o
    for ep in range(epochs):
        idx = rs.permutation(len(Ytr))
        for i in range(0, len(idx), 256):
            j = idx[i:i + 256]; x, y = Ftr[j], Ytr[j]; h, o = fwd(x); d = (2 * (o - y) * (1 - o ** 2) / len(j))[:, None]
            gW2 = h.T @ d; gb2 = d.sum(0); dh = (d @ W2.T) * (h > 0); gW1 = x.T @ dh; gb1 = dh.sum(0); t += 1
            for k, (p, g) in enumerate(zip(P, [gW1, gb1, gW2, gb2])):
                M[k] = 0.9 * M[k] + 0.1 * g; V[k] = 0.999 * V[k] + 0.001 * g * g; p -= 0.003 * (M[k] / (1 - 0.9 ** t)) / (np.sqrt(V[k] / (1 - 0.999 ** t)) + 1e-8)
        if ep % 5 == 4 or ep == epochs - 1:
            _, o = fwd(F[te]); print("epoch %2d  held-out MSE %.4f  correlation %.3f" % (ep + 1, np.mean((o - Y[te]) ** 2), np.corrcoef(o, Y[te])[0, 1]), flush=True)
    def q(p): s = np.abs(p).max() / 127.0 or 1.0; return np.round(p / s) * s
    Pq = [q(p) for p in P]; save = (W1.copy(), b1.copy(), W2.copy(), b2.copy())
    W1[:], b1[:], W2[:], b2[:] = Pq; _, oq = fwd(F[te]); print("after rounding the weights to 8 bits: held-out MSE %.4f  correlation %.3f" % (np.mean((oq - Y[te]) ** 2), np.corrcoef(oq, Y[te])[0, 1]))
    W1[:], b1[:], W2[:], b2[:] = save
    json.dump({"H": H, "n_in": n_in, "W1": W1.tolist(), "b1": b1.tolist(), "W2": W2.tolist(), "b2": b2.tolist(), "note": "hexn_helper_judge_v1, float weights; trained on %d positions" % len(Y)}, open(out, "w")); print("wrote", out)
if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "gen": gen(a[1], int(a[2]), int(a[3]), a[4])
    else: train(a[1], int(a[2]), int(a[3]), a[4:])
