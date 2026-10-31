"""hexn_real_ocean_v2: CLONE of hexn_real_ocean_v1.py (v1 unchanged) WITH THE RUNNING STATISTICS CLIPPED TO THE LOADED RANGE (the same clip layer 1 already applies to its bins). v1 showed the refresh getting WORSE as it learned on random splits (.745 at 100 minutes to .661 at 2589) while plain methods reached .84 to .86: the outliers (turbidity spikes to 554, conductivity drops to 0.14) inflated the running mean and spread. ORIGINAL v1 DOCSTRING FOLLOWS.
 THE SENSOR CELL ON A REAL OCEAN-SENSOR LOG (Python + numpy + pandas + scikit-learn; float model; new file 31 Oct 2026). Alan, 16:54: attached nine sensor files and 'Labeled_PreProcessed_Dataset.csv' (4,315 readings, one per minute, 28 to 30 Oct 2021, a moving platform at about 14.3 to 18.2 N, 65.7 to 62.6 W): C3 temperature and turbidity, flow and flow temperature, optode oxygen concentration, saturation and temperature, SEB45 conductivity and salinity. The 'labelled' file has NO label column: only a timestamp and the nine sensors (checked).
Derived label (stated plainly: computed, not supplied): SUN UP or NOT. The sun's height above the horizon is worked out for every minute from the time and the platform's own position (positions from the raw saturation file, which carries coordinates); label 1 if the elevation is above 0 degrees. Question: from the nine water readings alone, can the cell tell whether the sun is up? (A real diurnal signal in oxygen and temperature is expected to be weak.)
Cell as designed: nine counted detectors (12 bins across a loaded range = 1st to 99th percentile of the data; a reading outside is put in the end bin), table refresh with true (derived) labels, tally-and-threshold bias (tools/hexn_real_c4_v2.py bthr idea: 32 score bins; here 2 classes of equal footing). Two protocols: RANDOM (random 60/40 split) and CHRONO (learn on day 1 in time order, test on days 2 and 3: real drift). Arms: refresh, refresh_f (forgets, step never below 1/200), nearest class mean (percentile scaled), Gaussian naive Bayes, logistic regression (the last two on n samples). Usage: python3 tools/hexn_real_ocean_v2.py"""
import sys, os, json, glob, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
HERE = os.path.dirname(os.path.abspath(__file__)); DD = os.path.join(HERE, "..", "docs", "hex-n", "data", "ocean_sensors"); NB = 12
def sun_elevation(t, lat, lon):
    d = t.dt.dayofyear.values + (t.dt.hour.values + t.dt.minute.values / 60.0) / 24.0; g = 2 * np.pi / 365.25 * (d - 1)
    decl = 0.006918 - 0.399912 * np.cos(g) + 0.070257 * np.sin(g) - 0.006758 * np.cos(2 * g) + 0.000907 * np.sin(2 * g) - 0.002697 * np.cos(3 * g) + 0.00148 * np.sin(3 * g)
    eqt = 229.18 * (0.000075 + 0.001868 * np.cos(g) - 0.032077 * np.sin(g) - 0.014615 * np.cos(2 * g) - 0.040849 * np.sin(2 * g))
    utc_min = t.dt.hour.values * 60 + t.dt.minute.values; ha = np.radians((utc_min + eqt + 4 * lon) / 4.0 - 180.0); la = np.radians(lat)
    return np.degrees(np.arcsin(np.sin(la) * np.sin(decl) + np.cos(la) * np.cos(decl) * np.cos(ha)))
def load():
    d = pd.read_csv(os.path.join(DD, "Labeled_PreProcessed_Dataset.csv")); d["t"] = pd.to_datetime(d["Timestamp"]).dt.tz_localize(None)
    r = pd.read_csv(os.path.join(DD, "Optode_Saturation_10-28_10-30_with_position.csv"), header=None); c = r[2].map(lambda s: json.loads(s)["Coordinates"])
    pos = pd.DataFrame({"t": pd.to_datetime(r[3]), "lon": c.map(lambda v: v[0]), "lat": c.map(lambda v: v[1])}); d = d.merge(pos, on="t", how="left"); d[["lon", "lat"]] = d[["lon", "lat"]].ffill().bfill()
    d["elev"] = sun_elevation(d["t"], d["lat"].values, d["lon"].values); return d
class Tab:
    def __init__(s, K, d, lo, hi, floor):
        s.K, s.d, s.lo, s.hi, s.floor = K, d, lo, hi, floor; rg = hi - lo + 1e-9; s.n = np.ones((K, d)); s.m = np.tile((lo + hi) / 2, (K, 1)); s.v = np.tile((rg / 3) ** 2, (K, 1)); s.bw = rg / NB; s.cen = lo[:, None] + (np.arange(NB) + 0.5) * s.bw[:, None]
    def add(s, k, x): x = np.clip(x, s.lo, s.hi); s.n[k] += 1; g = np.maximum(1.0 / s.n[k], s.floor); dd = x - s.m[k]; s.m[k] += g * dd; s.v[k] += g * (dd * dd - s.v[k])
    def weights(s): sd = np.maximum(np.sqrt(s.v), 0.6 * s.bw[None, :]); z = (s.cen[None] - s.m[:, :, None]) / sd[:, :, None]; return np.maximum(-0.5 * z * z, -8.0) - np.log(sd)[:, :, None]
def bins(X, lo, hi): return np.clip(((X - lo) / (hi - lo + 1e-9) * NB).astype(int), 0, NB - 1)
def run(proto, X, y, lo, hi, ns, reps):
    B = bins(X, lo, hi); Xs = np.clip((X - lo) / (hi - lo + 1e-9), 0, 1); d = X.shape[1]; arms = ["refresh", "refresh_f", "nearest", "gnb", "logreg"]; acc = {a: np.zeros(len(ns)) for a in arms}; cnt = {a: np.zeros(len(ns)) for a in arms}
    for rep in range(reps):
        if proto == "RANDOM": perm = np.random.default_rng(50 + rep).permutation(len(y)); cut = int(0.6 * len(y)); tr, te = perm[:cut], perm[cut:]
        else: tr, te = np.arange(0, 1440), np.arange(1440, len(y))
        Ts = {a: Tab(2, d, lo, hi, 0.0 if a == "refresh" else 1 / 200) for a in ("refresh", "refresh_f")}; cs = np.zeros((2, d)); cn = np.zeros(2); done = 0
        for j, n in enumerate(ns):
            n = min(n, len(tr))
            for i in tr[done:n]:
                for T in Ts.values(): T.add(y[i], X[i])
                cs[y[i]] += Xs[i]; cn[y[i]] += 1
            done = n
            for a in ("refresh", "refresh_f"):
                W = Ts[a].weights(); S = W[:, np.arange(d)[None, :], B[te]].sum(2); s = S[1] - S[0]
                if n >= 6 and len(set(y[tr[:n]])) == 2:                                   # tally-and-threshold bias on the training tallies
                    St = W[:, np.arange(d)[None, :], B[tr[:n]]].sum(2); st = St[1] - St[0]; ed = np.linspace(st.min() - 1e-6, st.max() + 1e-6, 33); h1 = np.histogram(st[y[tr[:n]] == 1], ed)[0]; h0 = np.histogram(st[y[tr[:n]] == 0], ed)[0]
                    q = int(np.argmax([h0[:q].sum() + h1[q:].sum() for q in range(33)])); s = s - ed[min(q, 32)]
                acc[a][j] += np.mean((s > 0) == (y[te] == 1)); cnt[a][j] += 1
            if cn.min() > 0: cm = cs / cn[:, None]; acc["nearest"][j] += np.mean(np.argmin(((Xs[te][:, None, :] - cm[None]) ** 2).sum(2), 1) == y[te]); cnt["nearest"][j] += 1
            if n >= 6 and len(set(y[tr[:n]])) == 2:
                for nm, mdl in (("gnb", GaussianNB()), ("logreg", LogisticRegression(max_iter=500))): mdl.fit(Xs[tr[:n]], y[tr[:n]]); acc[nm][j] += mdl.score(Xs[te], y[te]); cnt[nm][j] += 1
    print("%s protocol: day/night accuracy on the test part (always-majority %.3f); labelled minutes seen:" % (proto, max(np.mean(y[te] == 1), np.mean(y[te] == 0))), "  ".join("%5d" % n for n in ns), flush=True)
    for a in arms: print("  %-9s" % a, "  ".join(("%.3f" % (acc[a][j] / cnt[a][j])) if cnt[a][j] else "    -" for j in range(len(ns))), flush=True)
if __name__ == "__main__":
    d = load(); cols = [c for c in d.columns if c not in ("Timestamp", "t", "lon", "lat", "elev")]; X = d[cols].values.astype(float); y = (d["elev"].values > 0).astype(int)
    print("minutes %d, sun up %.1f per cent; elevation range %.0f to %.0f deg; sensors: %s" % (len(y), 100 * y.mean(), d.elev.min(), d.elev.max(), ", ".join(cols)))
    lo, hi = np.percentile(X, 1, axis=0), np.percentile(X, 99, axis=0)
    run("RANDOM", X, y, lo, hi, (0, 10, 30, 100, 300, 1000, 2589), 10); run("CHRONO", X, y, lo, hi, (0, 10, 30, 100, 300, 720, 1440), 1)
