"""hexn_intake_v1: FRONT-END INTAKE AND ANALYSIS ENGINE, FIRST PROTOTYPE (Python + numpy + pandas + scikit-learn; host side; model only; new file 31 Oct 2026). Alan, 17:16: 'this is the kind of data the frontend needs to accept, and then there is the things you want highlighted, almost an analysis engine'.
STEP 1 INTAKE: reads one or more CSV (or .csv.gz) files in any of the layouts seen so far (header or none; '#' comment lines; long format with a repeated measure column; a GeoJSON position column; text, counter or date-time time columns; digital 0/1 columns), works out each column's ROLE (time, counter, position, label, sensor, digital, meta, constant), and merges files on time (inner join, the author's own rule for the ocean set).
STEP 2 HIGHLIGHTS (no learning, no label needed): cadence and gaps; per sensor: stuck runs, spikes (beyond 8 median absolute deviations), missing, quality flags ('Estimated', 'Suspect'); redundant pairs (|r| > 0.97); drift (median in the second half against the first, in units of the spread); label balance and episodes. Lines are ranked and written in plain words.
STEP 3 TASK MENU: what can be tested with this file: a label column if present; otherwise a derived one the user must state (--rule 'expr', --future SENSOR --q 0.9 --hours 6).
STEP 4 ANALYSIS (when a label is given or derived): counted detectors (12 bins over the loaded 1st to 99th percentile range of the training part, readings and statistics clipped), table refresh (tools/hexn_real_data_v1.py idea, two or more classes), learning curve against nearest class mean and logistic regression, chronological train/test when a time column exists (first 60 per cent train), and WHICH DETECTORS CARRY THE SIGNAL (each sensor's own table score, AUC alone).
Usage: python3 tools/hexn_intake_v1.py FILE [FILE ...] [--label COL] [--rule EXPR] [--future SENSOR --q 0.9 --hours 6] [--features current|dynamic]"""
import sys, os, re, json, gzip, argparse, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_real_ocean_v2 as O
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
NB = O.NB
def read_any(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt") as f: head = [next(f, "") for _ in range(40)]
    rows = [l for l in head if l.strip() and not l.startswith("#")]; first = next(iter(rows), "")
    try: [float(v) for v in first.strip().split(",")]; hdr = None
    except ValueError: hdr = 0
    d = pd.read_csv(path, comment="#", header=hdr)
    if hdr is None: d.columns = ["col%d" % i for i in range(d.shape[1])]
    return d
def roles(d):
    R = {}
    for c in d.columns:
        s = d[c]; nm = c.lower()
        if s.nunique(dropna=True) <= 1: R[c] = "constant"; continue
        if not pd.api.types.is_numeric_dtype(s):
            smp = s.dropna().astype(str).head(200)
            if smp.str.startswith("{").mean() > 0.9 and smp.str.contains("oordinates").mean() > 0.9: R[c] = "position"; continue
            try: pd.to_datetime(smp); R[c] = "time"; continue
            except Exception: pass
            R[c] = "meta" if re.search(r"quality|qcode|complete|measure", nm) or s.nunique() > 12 else "label"; continue
        if re.search(r"quality|qcode|complete", nm): R[c] = "meta"; continue
        if re.search(r"label|class|target|status|^type$", nm) and s.nunique() <= 12: R[c] = "label"; continue
        if s.is_monotonic_increasing and s.nunique() > 0.99 * len(s): R[c] = "counter"; continue
        R[c] = "digital" if s.nunique() <= 2 else "sensor"
    return R
def short_stems(paths):
    st = [re.sub(r"^[0-9a-f]{8}-", "", os.path.basename(p).replace(".csv.gz", "").replace(".csv", "")) for p in paths]
    if len(st) < 2: return st
    pre = os.path.commonprefix(st); suf = os.path.commonprefix([x[::-1] for x in st])[::-1]; out = [x[len(pre):len(x) - len(suf)] or x for x in st]; return out
def load(paths):
    parts = []; stems = short_stems(paths)
    for p, stem in zip(paths, stems):
        d = read_any(p); R = roles(d); tc = [c for c in d.columns if R[c] == "time"]
        if tc: d["_t"] = pd.to_datetime(d[tc[0]]).dt.tz_localize(None) if pd.to_datetime(d[tc[0]]).dt.tz is not None else pd.to_datetime(d[tc[0]])
        sens = [c for c, r in R.items() if r in ("sensor", "digital")]
        ren = {c: (stem if c == "value" else c) for c in sens}; d = d.rename(columns=ren); R = {ren.get(c, c): r for c, r in R.items()}
        info = {"path": p, "rows": len(d), "roles": R}; parts.append((d, info))
    if len(parts) == 1: return parts[0][0], [parts[0][1]], parts[0][1]["roles"]
    base = None
    for d, info in parts:
        cols = ["_t"] + [c for c, r in info["roles"].items() if r in ("sensor", "digital")]; x = d[cols]
        base = x if base is None else base.merge(x, on="_t", how="inner")
    roles_all = {c: "sensor" for c in base.columns if c != "_t"}; return base, [i for _, i in parts], roles_all
def episodes(b): b = np.asarray(b).astype(int); return int(((b[1:] - b[:-1]) == 1).sum() + (1 if len(b) and b[0] else 0))
def highlights(d, R, infos):
    H = []; t = d["_t"] if "_t" in d else None; sens = [c for c in d.columns if R.get(c) in ("sensor", "digital") and c in d]
    if t is not None:
        dt = t.diff().dt.total_seconds().dropna(); med = float(dt.median()); gaps = int((dt > 1.5 * med).sum()); H.append((1, "time: %d rows from %s to %s, one reading every %g s; %d gap(s) longer than 1.5 steps" % (len(d), t.min(), t.max(), med, gaps)))
    if t is None:
        for c, r in R.items():
            m = re.search(r"_(us|ms|s)$", c.lower())
            if r == "counter" and m and c in d:
                u = {"us": 1e-6, "ms": 1e-3, "s": 1.0}[m.group(1)]; dt = d[c].diff().dropna() * u; med = float(dt.median()); H.append((1, "time (%s, a counter): %d rows over %.1f s, median step %.4g s, %d step(s) longer than 1.5 x median" % (c, len(d), (d[c].iloc[-1] - d[c].iloc[0]) * u, med, int((dt > 1.5 * med).sum())))); break
    for c, r in R.items():
        if r == "constant" and c in d.columns: H.append((2, "%s never changes (always %s): not used, check the wiring or the sensor" % (c, d[c].dropna().iloc[0] if d[c].notna().any() else "empty")))
    for c in sens:
        x = d[c].astype(float).values; med = np.nanmedian(x); mad = np.nanmedian(np.abs(x - med)) + 1e-12; sp = np.sum(np.abs(x - med) > 8 * 1.4826 * mad)
        run = (pd.Series(x).diff() == 0).astype(int); longest = int(run.groupby((run == 0).cumsum()).sum().max()) if len(run) else 0
        if np.isnan(x).mean() > 0.001: H.append((2, "%s: %.1f per cent missing" % (c, 100 * np.isnan(x).mean())))
        if sp and sp < 0.03 * len(x): H.append((3, "%s: %d spike readings beyond 8 median deviations (largest %.4g against median %.4g)" % (c, sp, np.nanmax(np.abs(x - med)) + med, med)))
        if longest > 0.2 * len(x) and R.get(c) == "sensor": H.append((3, "%s: stuck: the same value repeats for %d readings in a row" % (c, longest)))
        h = len(x) // 2; q = np.nanpercentile(x, [25, 75]); iqr = (q[1] - q[0]) + 1e-12; sh = (np.nanmedian(x[h:]) - np.nanmedian(x[:h])) / iqr
        if abs(sh) > 0.5 and R.get(c) == "sensor": H.append((3, "%s: DRIFT, the second half sits %.1f spreads %s the first half" % (c, abs(sh), "above" if sh > 0 else "below")))
    for p in infos:
        pass
    S = d[[c for c in sens if R.get(c) == "sensor"]]
    if S.shape[1] > 1:
        C = S.corr().abs().values; names = S.columns
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                if C[i, j] > 0.97: H.append((2, "%s and %s carry almost the same information (|r| %.2f): one is redundant" % (names[i], names[j], C[i, j])))
    lab = [c for c in d.columns if R.get(c) == "label" and c in d]
    for c in lab:
        vc = d[c].value_counts(); H.append((2, "label %s: %s; rarest class %.1f per cent" % (c, ", ".join("%s %d" % (k, v) for k, v in vc.items()), 100 * vc.min() / len(d))))
    return sorted(H, key=lambda h: -h[0])
def features(d, sens, kind, step_s):
    X = {}; k1, k3 = max(1, int(round(3600 / step_s))), max(1, int(round(10800 / step_s)))
    for c in sens:
        x = d[c].astype(float).values; X[c] = x
        if kind == "dynamic":
            lag = lambda n: np.concatenate([np.full(n, x[0]), x[:-n]]); X[c + "_d1h"] = x - lag(k1); X[c + "_d3h"] = x - lag(k3); X[c + "_s1h"] = np.convolve(x, np.ones(k1), "full")[:len(x)]
    return pd.DataFrame(X)
def auc(s, y): return roc_auc_score(y, s) if 0 < y.sum() < len(y) else float("nan")
def analyse(d, R, a):
    sens = [c for c in d.columns if R.get(c) == "sensor" and c in d]; t = d["_t"] if "_t" in d else None; step = float(t.diff().dt.total_seconds().median()) if t is not None else 1.0
    elig = np.ones(len(d), bool)
    if a.label: lab = d[a.label]; classes = sorted(lab.unique().tolist()); y = lab.map({c: i for i, c in enumerate(classes)}).values; sens = [c for c in sens if c != a.label]; how = "label column %s" % a.label
    elif a.rule: y = d.eval(a.rule).astype(int).values; classes = [0, 1]; how = "stated rule: %s" % a.rule
    elif a.future:
        x = d[a.future].astype(float).values; H = int(round(a.hours * 3600 / step)); T = np.nanpercentile(x[:int(0.6 * len(x))], a.q * 100); fut = np.array([x[i + 1:i + 1 + H].max() if i + H < len(x) else np.nan for i in range(len(x))]); elig = (x < T) & ~np.isnan(fut); y = (fut >= T).astype(int); classes = [0, 1]
        how = "future: %s crosses %.4g (the %g percentile of the first 60 per cent) within %g h; rows already above the line are left out" % (a.future, T, a.q * 100, a.hours)
    else: return ["No task chosen: give --label COL, --rule EXPR or --future SENSOR [--q 0.9 --hours 6]."]
    kind = a.features if a.features != "auto" else ("dynamic" if t is not None else "current"); F = features(d, sens, kind, step); Xv = F.values; names = list(F.columns); idx = np.where(elig)[0]
    cut = idx[int(0.6 * len(idx))] if t is not None else None
    if t is not None: tr, te = idx[idx < cut], idx[idx >= cut]
    else: p = np.random.default_rng(0).permutation(idx); tr, te = p[:int(0.6 * len(p))], p[int(0.6 * len(p)):]
    K = len(classes); lo, hi = np.nanpercentile(Xv[tr], 1, axis=0), np.nanpercentile(Xv[tr], 99, axis=0); Xv = np.nan_to_num(Xv); B = O.bins(Xv, lo, hi); Xs = np.clip((Xv - lo) / (hi - lo + 1e-9), 0, 1); dd = Xv.shape[1]; ar = np.arange(dd)[None, :]
    out = ["TASK: %s" % how, "  classes %s; training rows %d (positives/each class %s), test rows %d (%s); split: %s; detectors: %d (%s)" % (classes, len(tr), np.bincount(y[tr], minlength=K).tolist(), len(te), np.bincount(y[te], minlength=K).tolist(), "chronological, first 60 per cent trains" if t is not None else "random 60/40", dd, kind)]
    if K == 2: out.append("  episodes of the rarer class: train %d, test %d%s" % (episodes(y[tr] == 1), episodes(y[te] == 1), "  (FEW: treat every number below as rough)" if episodes(y[te] == 1) < 10 else ""))
    def sc(T, ii, fs=None):
        W = T.weights(); fi = ar if fs is None else np.array([fs])[None, :]; S = np.stack([W[k][fi, B[ii][:, fs if fs is not None else slice(None)]].sum(1) if fs is None else W[k][fs][B[ii][:, fs]] for k in range(K)]); return S
    def metric(S, ii): return auc(S[1] - S[0], y[ii]) if K == 2 else float(np.mean(S.argmax(0) == y[ii]))
    ns = sorted({n for n in (50, 200, 1000, 5000, len(tr)) if n <= len(tr)}); T = O.Tab(K, dd, lo, hi, 0.0); done = 0; mname = "AUC" if K == 2 else "accuracy"; rows = {"table refresh": [], "logistic regression": [], "nearest class mean": []}
    cs = np.zeros((K, dd)); cn = np.zeros(K)
    for n in ns:
        for i in tr[done:n]: T.add(int(y[i]), Xv[i]); cs[y[i]] += Xs[i]; cn[y[i]] += 1
        done = n; rows["table refresh"].append(metric(sc(T, te), te))
        if len(set(y[tr[:n]])) == K and np.bincount(y[tr[:n]]).min() >= 2:
            m = LogisticRegression(max_iter=300, class_weight="balanced").fit(Xs[tr[:n]], y[tr[:n]]); p = m.decision_function(Xs[te]) if K == 2 else m.predict(Xs[te]); rows["logistic regression"].append(auc(p, y[te]) if K == 2 else float(np.mean(p == y[te])))
        else: rows["logistic regression"].append(float("nan"))
        if cn.min() > 0: cm = cs / cn[:, None]; dist = ((Xs[te][:, None, :] - cm[None]) ** 2).sum(2); rows["nearest class mean"].append(auc(dist[:, 0] - dist[:, 1], y[te]) if K == 2 else float(np.mean(dist.argmin(1) == y[te])))
        else: rows["nearest class mean"].append(float("nan"))
    out.append("  %s on the test part after n training rows:   n = %s" % (mname, "  ".join("%6d" % n for n in ns)))
    for k, r in rows.items(): out.append("    %-20s %s" % (k, "  ".join("%6.3f" % v if v == v else "     -" for v in r)))
    imp = []
    for f in range(dd):
        W = T.weights()
        if K == 2: s = W[1][f][B[te, f]] - W[0][f][B[te, f]]; imp.append((auc(s, y[te]), names[f]))
        else: s = np.stack([W[k][f][B[te, f]] for k in range(K)]); imp.append((float(np.mean(s.argmax(0) == y[te])), names[f]))
    imp.sort(reverse=True); out.append("  WHAT CARRIES THE SIGNAL (each detector alone, %s): %s" % (mname, "; ".join("%s %.3f" % (n, v) for v, n in imp[:6])))
    return out
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("files", nargs="+"); ap.add_argument("--label"); ap.add_argument("--rule"); ap.add_argument("--future"); ap.add_argument("--q", type=float, default=0.9); ap.add_argument("--hours", type=float, default=6.0); ap.add_argument("--features", default="auto"); a = ap.parse_args()
    d, infos, R = load(a.files); print("INTAKE: %d file(s) -> %d rows x %d columns" % (len(a.files), len(d), d.shape[1]))
    for i in infos:
        if len(infos) == 1 or True: print("  %s: %d rows; roles: %s" % (os.path.basename(i["path"]), i["rows"], ", ".join("%s=%s" % (c, r) for c, r in i["roles"].items() if r != "constant")[:400]))
    print("HIGHLIGHTS (most important first):"); [print("  [%d] %s" % h) for h in highlights(d, R, infos)]
    print("ANALYSIS:"); [print(l) for l in analyse(d, R, a)]
