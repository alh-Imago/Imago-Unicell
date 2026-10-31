"""hexn_real_c4_v1: THE GAME JUDGE ON REAL LABELLED POSITIONS (Python + numpy + scikit-learn; float model; new file 31 Oct 2026). Alan, 16:37: attached the UCI Connect-4 opening database (John Tromp, 1995; 67,557 legal 8-ply positions, X to move, label = the game-theoretic result for X under perfect play: win 44,473, loss 16,635, draw 6,449). Data in docs/hex-n/data/connect4_uci/ (connect-4.data.Z, connect-4.names).
Question: do the layer 1 counts (6 pure-line counts + parity, tools/hexn_layer1_judge_v1.py l1) carry enough to judge REAL positions, and which way of setting the 8 weights does best?
Arms (judge value v = tanh(w.x + b), x = l1; targets win +1, draw 0, loss -1; all trained on the first n of a random 80 per cent, tested on the other 20 per cent; 5 random splits):
  hand    : the hand weights (.2 .8 1.8 -.2 -.8 -1.8), bias 0, never learning;
  grad_h  : gradient learning (tools/hexn_layer1_online_v1.py rule, lr 0.02, one pass, MSE on tanh) from the hand weights;  grad_0 : same from zero weights;
  refresh : the 19:10 table refresh with TRUE labels (p = 1, .5, 0 for win, draw, loss; class means and pooled spread; c 0.5; hand weights as 300 pseudo-positions);
  logreg7 : scikit-learn logistic regression (win vs loss) on the same 7 numbers = the best a linear judge on layer 1 can do;
  cells42 : scikit-learn gradient boosting on the raw 42 squares (n >= 5000 only) = what layer 1 throws away.
Metrics on the test positions: AUC of win against loss (draws left out; 0.5 = no skill, 1 = perfect), accuracy of 'v > 0 means win' on win and loss positions (the majority 'always win' scores .728), and correlation of v with the target on all.
Usage: python3 tools/hexn_real_c4_v1.py [SPLITS]"""
import sys, os, gzip, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer1_judge_v1 as L
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "..", "docs", "hex-n", "data", "connect4_uci", "connect-4.data.Z"); CACHE = os.environ.get("C4CACHE", "/tmp/hexn_c4_cache.npz")
def load():
    if os.path.exists(CACHE): z = np.load(CACHE); return z["F"], z["Y"], z["C"]
    txt = subprocess.run(["gzip", "-dc", DATA], capture_output=True, check=True).stdout.decode().split(); F = []; Y = []; C = []
    for line in txt:
        v = line.split(","); b = [[{"b": 0, "x": 1, "o": 2}[v[c * 6 + r]] for r in range(6)] for c in range(7)]; F.append(L.l1(b)); Y.append({"win": 1, "draw": 0, "loss": -1}[v[42]]); C.append([{"b": 0, "x": 1, "o": 2}[s] for s in v[:42]])
    F = np.array(F, dtype=float); Y = np.array(Y); C = np.array(C, dtype=np.int8); np.savez(CACHE, F=F, Y=Y, C=C); return F, Y, C
HAND = np.array([.2, .8, 1.8, -.2, -.8, -1.8, 0.0])
def grad(w, b, X, Y, lr=0.02):
    w = w.copy()
    for x, t in zip(X, Y):
        o = np.tanh(x @ w + b); d = 2 * (o - t) * (1 - o * o); w -= lr * d * x; b -= lr * d
    return w, b
def refresh(X, Y, c=0.5, n0=300.0):
    p = (Y + 1) / 2.0; S = np.array([p.sum(), (1 - p).sum()]); M = np.stack([p @ X, (1 - p) @ X]); Q = np.stack([p @ (X * X), (1 - p) @ (X * X)])
    if S.min() < 1e-6: return HAND.copy(), 0.0
    mu = M / S[:, None]; N = S.sum(); var = ((Q[0] - M[0] ** 2 / S[0]) + (Q[1] - M[1] ** 2 / S[1])) / N + 1e-3
    a = c * (mu[0] - mu[1]) / var / 2; bb = -float(np.sum(a * (mu[0] + mu[1]) / 2)); k = N / (N + n0); return (1 - k) * HAND + k * a, k * bb
def metrics(v, Y):
    wl = Y != 0; auc = roc_auc_score(Y[wl] > 0, v[wl]) if len(set(Y[wl])) == 2 and np.ptp(v[wl]) > 0 else 0.5
    return auc, np.mean((v[wl] > 0) == (Y[wl] > 0)), (np.corrcoef(v, Y)[0, 1] if np.ptp(v) > 0 else 0.0)
def run(splits=5, ns=(0, 10, 30, 100, 300, 1000, 5000, 20000, 54045)):
    F, Y, C = load(); arms = ["hand", "grad_h", "grad_0", "refresh", "logreg7", "cells42"]; R = {a: np.full((len(ns), 3), np.nan) for a in arms}; cnt = {a: np.zeros(len(ns)) for a in arms}
    for a in arms: R[a][:] = 0
    for sp in range(splits):
        rng = np.random.default_rng(300 + sp); perm = rng.permutation(len(Y)); cut = int(0.8 * len(Y)); tr, te = perm[:cut], perm[cut:]; Xt, Yt = F[te], Y[te]
        for j, n in enumerate(ns):
            n = min(n, len(tr)); i = tr[:n]; X, y = F[i], Y[i]; out = {}
            out["hand"] = np.tanh(Xt @ HAND)
            w, b = grad(HAND, 0.0, X, y); out["grad_h"] = np.tanh(Xt @ w + b)
            w, b = grad(np.zeros(7), 0.0, X, y); out["grad_0"] = np.tanh(Xt @ w + b)
            w, b = refresh(X, y); out["refresh"] = np.tanh(Xt @ w + b)
            wl = y != 0
            if n >= 10 and len(set(y[wl])) == 2:
                m = LogisticRegression(max_iter=500).fit(X[wl], y[wl] > 0); out["logreg7"] = m.decision_function(Xt)
            if n >= 5000: m = HistGradientBoostingClassifier(max_iter=150).fit(C[i][wl], y[wl] > 0); out["cells42"] = m.predict_proba(C[te])[:, 1] - 0.5
            for a, v in out.items(): R[a][j] += metrics(v, Yt); cnt[a][j] += 1
    wl = Y != 0; print("always-win accuracy on win/loss positions: %.3f" % np.mean(Y[wl] > 0))
    for k, nm in ((0, "AUC win vs loss"), (1, "accuracy v>0 = win, win/loss positions"), (2, "correlation with target (all)")):
        print("%s; labelled positions seen:" % nm, "  ".join("%6d" % n for n in ns))
        for a in arms: print("  %-8s" % a, "  ".join(("%.3f " % (R[a][j][k] / cnt[a][j])) if cnt[a][j] else "     - " for j in range(len(ns))), flush=True)
if __name__ == "__main__": run(*[int(v) for v in sys.argv[1:]])
