"""hexn_real_data_v1: THE SENSOR CELL ON REAL DATA IT HAS NEVER SEEN (Python + numpy + scikit-learn data only; model only; new file 31 Oct 2026). Alan, 16:09: 'find some random data and see if it can handle that'.
Real labelled data from scikit-learn's bundled sets: iris (4 measurements, 3 flowers), wine (13 chemical measures, 3 wines), breast cancer (30 measures, 2 classes), digits (64 pixels, 10 numbers).
The cell as designed: layer 1 turns each measurement into one counted detector (12 bins across a LOADED range = min to max of the data, count 1 each), so a sample is d counts (d x 12 inputs). The neural has one score per class over those inputs. Two ways to set the weights from nothing (no loaded table: broad prior of one pseudo-sample):
  refresh : per class and measurement a running count, mean and variance (Welford; the 19:10 row); weights = log-likelihood of the bin centre (spread floor 0.6 bin), rebuilt after every sample;
  grad    : whole-number gradient learning (tools/hexn_multiout_int_v1.py, blank start, rate 192/128).
References: nearest class mean (measurements scaled to 0..1), and scikit-learn Gaussian naive Bayes and logistic regression fed the same n samples (the best a standard method does with them). Accuracy on the held-out 40 per cent, after n labelled samples seen (training stream in random order), averaged over random 60/40 splits (20 for iris, wine, breast cancer; 3 for digits).
Usage: python3 tools/hexn_real_data_v1.py [DATASET ...]"""
import sys, os, warnings
import numpy as np
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_multiout_int_v1 as MO
from sklearn import datasets as DS
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
NB = 12
class Table:
    def __init__(s, K, d, lo, hi):
        s.K, s.d, s.lo, s.hi = K, d, lo, hi; rng = hi - lo + 1e-9; s.n = np.ones((K, d)); s.m = np.tile((lo + hi) / 2, (K, 1)); s.v = np.tile((rng / 3) ** 2, (K, 1)); s.bw = rng / NB; s.cen = lo[:, None] + (np.arange(NB) + 0.5) * s.bw[:, None]
    def add(s, k, x):
        s.n[k] += 1; g = 1.0 / s.n[k]; dd = x - s.m[k]; s.m[k] += g * dd; s.v[k] += g * (dd * dd - s.v[k])
    def weights(s):
        sd = np.maximum(np.sqrt(s.v), 0.6 * s.bw[None, :]); z = (s.cen[None, :, :] - s.m[:, :, None]) / sd[:, :, None]
        return np.maximum(-0.5 * z * z, -8.0) - np.log(sd)[:, :, None]          # K x d x NB
def bins(X, lo, hi): return np.clip(((X - lo) / (hi - lo + 1e-9) * NB).astype(int), 0, NB - 1)
def run(name, reps, ns):
    D = getattr(DS, "load_" + name)(); X = D.data.astype(float); y = D.target; K = len(set(y)); d = X.shape[1]; lo, hi = X.min(0), X.max(0); B = bins(X, lo, hi); Xs = (X - lo) / (hi - lo + 1e-9)
    arms = ["refresh", "grad", "nearest", "gnb", "logreg"]; acc = {a: np.full(len(ns), 0.0) for a in arms}; cnt = {a: np.zeros(len(ns)) for a in arms}
    for rep in range(reps):
        rng = np.random.default_rng(100 + rep); perm = rng.permutation(len(y)); cut = int(0.6 * len(y)); tr, te = perm[:cut], perm[cut:]
        T = Table(K, d, lo, hi); Wg = MO.MultiOutInt(np.zeros((K, d * NB), dtype=int).tolist(), 192); cs = np.zeros((K, d)); cn = np.zeros(K); done = 0
        for j, n in enumerate(ns):
            n = min(n, len(tr))
            for i in tr[done:n]:
                T.add(y[i], X[i]); x = [0] * (d * NB)
                for f in range(d): x[f * NB + B[i, f]] = 1
                Wg.learn(x, int(y[i])); cs[y[i]] += Xs[i]; cn[y[i]] += 1
            done = n
            Wr = T.weights(); fi = np.arange(d)[None, :] * NB
            def pred_w(Wm): return np.argmax(Wm[:, np.arange(d)[None, :], B[te]].sum(2), 0)
            acc["refresh"][j] += np.mean(pred_w(Wr) == y[te]); cnt["refresh"][j] += 1
            acc["grad"][j] += np.mean(pred_w(np.array(Wg.W, float).reshape(K, d, NB)) == y[te]); cnt["grad"][j] += 1
            cm = np.where(cn[:, None] > 0, cs / np.maximum(cn, 1)[:, None], 0.5); acc["nearest"][j] += np.mean(np.argmin(((Xs[te][:, None, :] - cm[None]) ** 2).sum(2), 1) == y[te]); cnt["nearest"][j] += 1
            if n >= 2 * K and len(set(y[tr[:n]])) == K:
                for nm, mdl in (("gnb", GaussianNB()), ("logreg", LogisticRegression(max_iter=300))):
                    try: mdl.fit(Xs[tr[:n]], y[tr[:n]]); acc[nm][j] += mdl.score(Xs[te], y[te]); cnt[nm][j] += 1
                    except Exception: pass
    print("%s: %d samples, %d measurements, %d classes, %d repeats; labelled samples seen:" % (name, len(y), d, K, reps), "  ".join("%5d" % n for n in ns), flush=True)
    for a in arms: print("  %-8s" % a, "  ".join(("%.3f" % (acc[a][j] / cnt[a][j])) if cnt[a][j] else "    -" for j in range(len(ns))), flush=True)
if __name__ == "__main__":
    which = sys.argv[1:] or ["iris", "wine", "breast_cancer", "digits"]
    cfg = {"iris": (20, (0, 3, 6, 10, 20, 40, 90)), "wine": (20, (0, 3, 6, 10, 20, 40, 106)), "breast_cancer": (20, (0, 4, 10, 20, 50, 100, 341)), "digits": (3, (0, 10, 30, 100, 300, 1078))}
    for w in which: run(w, *cfg[w])
