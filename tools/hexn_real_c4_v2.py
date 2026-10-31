"""hexn_real_c4_v2: THE BIAS STEP FOR THE TABLE REFRESH (Python + numpy + scikit-learn; float model; new file 31 Oct 2026; clone of tools/hexn_real_c4_v1.py, which is unchanged). Alan, 16:40: 'no add the bias step'. v1 showed the refresh sets the six weights well (AUC .897) but 'v > 0 means win' is right only .808 of the time, because the first player's edge (66 per cent wins) is not in the bias.
Three bias steps on top of the refreshed weights w (all use only labelled positions and running sums):
  prior  : add the class prior term to the bias, 0.5 ln(win weight / loss weight) (the proper discriminant bias, from two running counts);
  bgrad  : one pass of a gradient step on the bias ONLY, v = tanh(w.x + b), lr 0.02 (one number, the same rule as the weights use, weights held);
  bthr   : layer 1 style tally: 32 score bins, a count of wins and of losses in each (draws left out); the bias puts the decision point where 'wins above, losses below' is right most often on the tallies;
  bmean  : closed form, b = running mean of (atanh(0.9 t) - w.x) over the labelled positions (t = +1, 0, -1), no learning rate.
Same data, splits and metrics as v1 (AUC is unchanged by a bias, so accuracy of v > 0 on win/loss positions and correlation are reported; always-win = .728).
Usage: python3 tools/hexn_real_c4_v2.py [SPLITS]"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_real_c4_v1 as V1
HAND = V1.HAND
def run(splits=5, ns=(0, 10, 30, 100, 300, 1000, 5000, 20000, 54045)):
    F, Y, C = V1.load(); arms = ["refresh", "prior", "bgrad", "bmean", "bthr", "grad_h"]; R = {a: np.zeros((len(ns), 3)) for a in arms}; cnt = len(ns) * [0]
    for sp in range(splits):
        rng = np.random.default_rng(300 + sp); perm = rng.permutation(len(Y)); cut = int(0.8 * len(Y)); tr, te = perm[:cut], perm[cut:]; Xt, Yt = F[te], Y[te]
        for j, n in enumerate(ns):
            n = min(n, len(tr)); i = tr[:n]; X, y = F[i], Y[i]; out = {}
            w, b = V1.refresh(X, y); out["refresh"] = np.tanh(Xt @ w + b)
            p = (y + 1) / 2.0; sw, sl = p.sum(), (1 - p).sum(); bp = b + (0.5 * np.log((sw + 1) / (sl + 1)) * (n / (n + 300.0)))
            out["prior"] = np.tanh(Xt @ w + bp)
            bg = b
            for x, t in zip(X, y): o = np.tanh(x @ w + bg); bg -= 0.02 * 2 * (o - t) * (1 - o * o)
            out["bgrad"] = np.tanh(Xt @ w + bg)
            bm = b if n == 0 else float(np.mean(np.arctanh(0.9 * y) - X @ w)); k = n / (n + 30.0); out["bmean"] = np.tanh(Xt @ w + (1 - k) * b + k * bm)
            wl = y != 0; sc = X @ w
            if wl.sum() >= 4 and len(set(y[wl])) == 2:
                edges = np.linspace(sc[wl].min() - 1e-6, sc[wl].max() + 1e-6, 33); hw = np.histogram(sc[wl & (y > 0)], edges)[0]; hl = np.histogram(sc[wl & (y < 0)], edges)[0]
                acc_ = [(hl[:q].sum() + hw[q:].sum()) for q in range(33)]; q = int(np.argmax(acc_)); thr = edges[min(q, 32)] if q < 33 else edges[-1]; bt = -thr
            else: bt = b
            out["bthr"] = np.tanh(Xt @ w + bt)
            w2, b2 = V1.grad(HAND, 0.0, X, y); out["grad_h"] = np.tanh(Xt @ w2 + b2)
            for a, v in out.items(): R[a][j] += V1.metrics(v, Yt)
            cnt[j] += 1
    for k, nm in ((1, "accuracy v>0 = win, win/loss positions (always-win .728)"), (2, "correlation with target (all)")):
        print("%s; labelled positions seen:" % nm, "  ".join("%6d" % n for n in ns))
        for a in arms: print("  %-8s" % a, "  ".join("%.3f " % (R[a][j][k] / cnt[j]) for j in range(len(ns))), flush=True)
if __name__ == "__main__": run(*[int(v) for v in sys.argv[1:]])
