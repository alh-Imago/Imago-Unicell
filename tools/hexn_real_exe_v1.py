"""hexn_real_exe_v1: THE CELL ON A REAL RIVER, WITH A DRY YEAR THEN A WET YEAR (Python + numpy + pandas + scikit-learn; float model; new file 31 Oct 2026). Alan, 17:09: attached River Exe data (Environment Agency, OGL v3): flow and level at Thorverton and rain at Killerton Beare Farm and Tiverton, 15-minute readings for 2022 and 2023. Data in docs/hex-n/data/ea_exe/.
Task (the label is the FUTURE, not a function of the inputs): the river is now below its high-flow line T and will cross T within the next 6 hours. T = the 90th percentile of 2022 flow (33.5 m3/s), a loaded setting. Rows considered: those with flow below T. Positives: about 1.5 to 1.8 per cent of rows, in about 20 episodes a year (20 in 2022, 22 in 2023): few events, so the results are noisy. 2022 was DRY (median flow 3.7 m3/s) and 2023 WET (median 11.7): a real drift.
Layer 1 detectors (eight, 12 bins each over a loaded range = 1st to 99th percentile of the 2022 rows, readings and statistics clipped): log flow now; change in log flow over 1 h and over 3 h; sqrt of the rain in the last 1 h, 3 h and 6 h at Killerton; sqrt of the rain in the last 3 h and 12 h at Tiverton (upstream). (Level is not used: it is almost the same information as flow.)
PART 1, learning curve: stream the 2022 rows in time order into the labelled tables, test after n rows on ALL the 2023 rows. Arms: refresh (the 19:10 two-class table refresh), refresh_f (forgetting, step not below 1/3000), logistic regression (balanced), gradient boosting (balanced), and the single raw feature 'change in log flow over 1 h' (a rule with no learning). Metric: AUC (positives against the other rows).
PART 2, carrying on through 2023 as a live stream: score each day with the table as it stands, then (one day later, so each label is known) add the day's rows. Arms: frozen22 (the table at the end of 2022, never updated), keep (carry on, never forgets), keep_f (carry on, forgets, step not below 1/3000), scratch23 (a new table from nothing at 1 Jan 2023), logreg22 (logistic regression fitted on 2022, frozen). AUC by quarter and for the year.
Usage: python3 tools/hexn_real_exe_v1.py"""
import sys, os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_real_ocean_v2 as O
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
HERE = os.path.dirname(os.path.abspath(__file__)); DD = os.path.join(HERE, "..", "docs", "hex-n", "data", "ea_exe"); NB = O.NB
def rd(k): return pd.read_csv(os.path.join(DD, "thorverton_exe_%s_15min_2022_2023.csv.gz" % k))
def rollsum(a, n): c = np.cumsum(np.concatenate([np.zeros(n), a])); return c[n:] - c[:-n]
def build():
    f = rd("flow"); t = pd.to_datetime(f.dateTime); v = f.value.values; rk = rd("rain_killerton").value.values; rt = rd("rain_tiverton").value.values; lf = np.log(np.maximum(v, 0.05)); yr = t.dt.year.values
    lag = lambda a, n: np.concatenate([np.full(n, a[0]), a[:-n]])
    X = np.stack([lf, lf - lag(lf, 4), lf - lag(lf, 12), np.sqrt(rollsum(rk, 4)), np.sqrt(rollsum(rk, 12)), np.sqrt(rollsum(rk, 24)), np.sqrt(rollsum(rt, 12)), np.sqrt(rollsum(rt, 48))], 1)
    T = np.percentile(v[yr == 2022], 90); H = 24; fut = np.array([v[i + 1:i + 1 + H].max() if i + H < len(v) else np.nan for i in range(len(v))])
    el = (v < T) & ~np.isnan(fut); y = (fut >= T).astype(int); return X, y, el, yr, t, T
def auc(s, y): return roc_auc_score(y, s) if 0 < y.sum() < len(y) else np.nan
def run():
    X, y, el, yr, t, T = build(); i22 = np.where(el & (yr == 2022))[0]; i23 = np.where(el & (yr == 2023))[0]; lo, hi = np.percentile(X[i22], 1, axis=0), np.percentile(X[i22], 99, axis=0); B = O.bins(X, lo, hi); Xs = np.clip((X - lo) / (hi - lo + 1e-9), 0, 1); d = X.shape[1]; ar = np.arange(d)[None, :]
    print("high-flow line T = %.1f m3/s; rows 2022 %d (positives %d), 2023 %d (positives %d)" % (T, len(i22), y[i22].sum(), len(i23), y[i23].sum()))
    score = lambda Tb, idx: (lambda W: W[1][ar, B[idx]].sum(1) - W[0][ar, B[idx]].sum(1))(Tb.weights())
    ns = (500, 2000, 6000, 15000, len(i22)); Tr, Tf = O.Tab(2, d, lo, hi, 0.0), O.Tab(2, d, lo, hi, 1 / 3000); done = 0; res = {a: [] for a in ("refresh", "refresh_f", "logreg", "gbm", "rule_dlog1h")}
    for n in ns:
        for i in i22[done:n]: Tr.add(int(y[i]), X[i]); Tf.add(int(y[i]), X[i])
        done = n; tr = i22[:n]; res["refresh"].append(auc(score(Tr, i23), y[i23])); res["refresh_f"].append(auc(score(Tf, i23), y[i23])); res["rule_dlog1h"].append(auc(X[i23, 1], y[i23]))
        if y[tr].sum() >= 3:
            res["logreg"].append(auc(LogisticRegression(max_iter=500, class_weight="balanced").fit(Xs[tr], y[tr]).decision_function(Xs[i23]), y[i23])); res["gbm"].append(auc(HistGradientBoostingClassifier(max_iter=100, class_weight="balanced").fit(X[tr], y[tr]).decision_function(X[i23]) if hasattr(HistGradientBoostingClassifier, "decision_function") else HistGradientBoostingClassifier(max_iter=100, class_weight="balanced").fit(X[tr], y[tr]).predict_proba(X[i23])[:, 1], y[i23]))
        else: res["logreg"].append(np.nan); res["gbm"].append(np.nan)
    print("PART 1: learn on 2022 in time order, test on all of 2023 (AUC); 2022 rows seen:", "  ".join("%6d" % n for n in ns))
    for a, r in res.items(): print("  %-12s" % a, "  ".join("%.3f " % v for v in r))
    # PART 2
    days = (t.dt.dayofyear.values - 1); d23 = days[i23]; chunks = [i23[d23 == k] for k in range(365)]
    Tfz = O.Tab(2, d, lo, hi, 0.0)
    for i in i22: Tfz.add(int(y[i]), X[i])
    Tk, Tkf = O.Tab(2, d, lo, hi, 0.0), O.Tab(2, d, lo, hi, 1 / 3000)
    for i in i22: Tk.add(int(y[i]), X[i]); Tkf.add(int(y[i]), X[i])
    Ts = O.Tab(2, d, lo, hi, 0.0); lr22 = LogisticRegression(max_iter=500, class_weight="balanced").fit(Xs[i22], y[i22]); S = {a: np.zeros(len(i23)) for a in ("frozen22", "keep", "keep_f", "scratch23", "logreg22")}; pos = 0; prev = None; sc_ok = False
    for k, ch in enumerate(chunks):
        if len(ch) == 0: continue
        Ws = {"frozen22": Tfz, "keep": Tk, "keep_f": Tkf}
        for a, Tb in Ws.items(): S[a][pos:pos + len(ch)] = score(Tb, ch)
        S["scratch23"][pos:pos + len(ch)] = score(Ts, ch) if sc_ok else 0.0; S["logreg22"][pos:pos + len(ch)] = lr22.decision_function(Xs[ch])
        if prev is not None:
            for i in prev:
                Tk.add(int(y[i]), X[i]); Tkf.add(int(y[i]), X[i]); Ts.add(int(y[i]), X[i])
            sc_ok = y[np.concatenate([c for c in chunks[:k] if len(c)])].sum() >= 2
        prev = ch; pos += len(ch)
    q = (d23 // 91).clip(0, 3); print("PART 2: carrying on through 2023 as a live stream (AUC by quarter, then the year; positives per quarter: %s)" % [int(y[i23][q == j].sum()) for j in range(4)])
    for a in S: print("  %-10s" % a, "  ".join("%.3f " % auc(S[a][q == j], y[i23][q == j]) for j in range(4)), "  year %.3f" % auc(S[a], y[i23]))
if __name__ == "__main__": run()
