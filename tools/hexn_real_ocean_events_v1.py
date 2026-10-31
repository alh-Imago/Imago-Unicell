"""hexn_real_ocean_events_v1: STATED-RULE ANOMALY TEST ON THE OCEAN LOG (Python + numpy + pandas + scikit-learn; float model; new file 31 Oct 2026). Alan, 17:00: 'start with 1' (labels from a stated rule), the author's own page (RoLA v2) being about online anomaly detection under drift.
THE RULE, fixed before any run (from the quantiles of the data): a minute is UNUSUAL if ANY of: turbidity > 10 (normal about 1.2), conductivity < 5 (normal about 5.7), flow < 5 (normal about 12.9), salinity < 30 (normal about 33.9). It marks 31 of 4,315 minutes (0.7 per cent) in 4 episodes: 2 minutes at 10:03 on 28 Oct, 25 minutes at 12:15 on 28 Oct, 2 at 10:06 on 30 Oct, 2 at 22:11 on 30 Oct. The label is therefore a function of four of the nine sensors: the test shows whether the cell can LEARN a stated rule from almost nothing, not that it finds real faults.
Variant A: the cell sees all nine sensors. Variant B: the four sensors in the rule are HIDDEN; the cell must see the event in the other five (two temperatures, three oxygen numbers) = cross-sensor evidence.
Cell as designed: counted detectors (12 bins over the loaded 1st to 99th percentile range, readings and statistics clipped to it), table-based scores:
  table_unsup : NO LABELS AT ALL: one running table (mean and spread per sensor) over every minute that has been seen; anomaly score = - sum of the per-sensor log-likelihoods of the bins (a minute far from the usual scores high);
  table_2class: the 19:10 table refresh with the stated-rule labels (normal and unusual tables); score = log-likelihood ratio.
References: scikit-learn IsolationForest (no labels), logistic regression with balanced classes (labels, needs 2 unusual minutes).
Metrics on the test minutes: AUC (unusual against normal), and with the alarm threshold set from the training minutes only so that 1 per cent of the normal minutes seen would alarm: recall (share of unusual test minutes that alarm) and false alarm rate.
Protocols: RANDOM (60/40 split, 30 repeats; about 19 unusual minutes in training, 12 in test: noisy) and CHRONO (minutes seen in time order from the start of day 1 and tested on days 2 and 3, which hold 4 unusual minutes: nothing firm can be said; shown anyway).
Usage: python3 tools/hexn_real_ocean_events_v1.py"""
import sys, os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_real_ocean_v2 as O
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
NB = O.NB
def auc(s, y): return roc_auc_score(y, s) if 0 < y.sum() < len(y) else np.nan
def run(name, X, y, proto, ns, reps):
    d = X.shape[1]; lo, hi = np.percentile(X, 1, axis=0), np.percentile(X, 99, axis=0); B = O.bins(X, lo, hi); Xs = np.clip((X - lo) / (hi - lo + 1e-9), 0, 1); ar = np.arange(d)[None, :]
    arms = ["table_unsup", "table_2class", "isoforest", "logreg"]; R = {a: np.full((len(ns), 3, reps), np.nan) for a in arms}
    for rep in range(reps):
        if proto == "RANDOM": perm = np.random.default_rng(70 + rep).permutation(len(y)); cut = int(0.6 * len(y)); tr, te = perm[:cut], perm[cut:]
        else: tr, te = np.arange(0, 1440), np.arange(1440, len(y))
        Tu = O.Tab(1, d, lo, hi, 0.0); T2 = O.Tab(2, d, lo, hi, 0.0); done = 0
        for j, n in enumerate(ns):
            n = min(n, len(tr))
            for i in tr[done:n]: Tu.add(0, X[i]); T2.add(int(y[i]), X[i])
            done = n; idx = tr[:n]; yt = y[te]; norm = idx[y[idx] == 0]
            def ev(a, st, sr):                                    # st: scores of training minutes seen, sr: scores of test minutes
                thr = np.percentile(st[y[idx] == 0], 99) if (y[idx] == 0).sum() >= 5 else np.inf; R[a][j, 0, rep] = auc(sr, yt)
                R[a][j, 1, rep] = np.mean(sr[yt == 1] > thr) if yt.sum() else np.nan; R[a][j, 2, rep] = np.mean(sr[yt == 0] > thr)
            if n >= 5:
                W = Tu.weights(); ev("table_unsup", -W[0][ar, B[idx]].sum(1), -W[0][ar, B[te]].sum(1))
                if (y[idx] == 1).sum() >= 1 and (y[idx] == 0).sum() >= 1:
                    W = T2.weights(); f = lambda ii: W[1][ar, B[ii]].sum(1) - W[0][ar, B[ii]].sum(1); ev("table_2class", f(idx), f(te))
                m = IsolationForest(n_estimators=100, random_state=rep).fit(Xs[idx]); ev("isoforest", -m.score_samples(Xs[idx]), -m.score_samples(Xs[te]))
                if (y[idx] == 1).sum() >= 2: m = LogisticRegression(max_iter=500, class_weight="balanced").fit(Xs[idx], y[idx]); ev("logreg", m.decision_function(Xs[idx]), m.decision_function(Xs[te]))
    npos = "(unusual minutes in the test part: %d)" % y[te].sum() if proto == "CHRONO" else "(about %d unusual test minutes per split)" % round(0.4 * y.sum())
    print("%s, %s %s; minutes seen:" % (name, proto, npos), "  ".join("%5d" % n for n in ns))
    for k, nm in ((0, "AUC"), (1, "recall at 1 per cent false-alarm threshold"), (2, "false alarm rate")):
        print("  " + nm)
        for a in arms: print("    %-13s" % a, "  ".join(("%.3f" % np.nanmean(R[a][j, k])) if np.isfinite(R[a][j, k]).any() else "    -" for j in range(len(ns))), flush=True)
if __name__ == "__main__":
    d = O.load(); cols = [c for c in d.columns if c not in ("Timestamp", "t", "lon", "lat", "elev")]
    y = ((d.C3_Turbidity > 10) | (d.SEB45_Conductivity < 5) | (d.Flow_Flow < 5) | (d.SEB45_Salinity < 30)).values.astype(int); print("unusual minutes by the stated rule: %d of %d" % (y.sum(), len(y)))
    hidden = ["C3_Turbidity", "SEB45_Conductivity", "Flow_Flow", "SEB45_Salinity"]
    for name, cs in (("A (all nine sensors)", cols), ("B (rule sensors hidden)", [c for c in cols if c not in hidden])):
        X = d[cs].values.astype(float); print("== variant %s: %s" % (name, ", ".join(cs)))
        run(name, X, y, "RANDOM", (30, 100, 300, 1000, 2589), 30); run(name, X, y, "CHRONO", (100, 300, 720, 1440), 1)
