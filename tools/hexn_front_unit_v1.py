#!/usr/bin/env python3
"""hexn_front_unit_v1: FROM A DATA FILE TO THE OPEN UNIT (new file 1 Nov 2026; host side). The front end's new step: take the same files and task as the intake and analysis engine (tools/hexn_intake_v1.py, untouched, whose loading and features it reuses),
learn the counted-detector table on the training part, FIT it to the unit (the scorer has 8 detector slots x 12 bins, two classes, whole-number weights), send it, stream the test rows through the unit as raw words and VERIFY every result against the bit-exact reference.
FITTING: the detectors are ranked on the TRAINING part only (each alone, AUC), the best 8 are kept (fewer if the file has fewer; unused slots get zero weights), the weights are made whole numbers (per detector the largest weight is subtracted, times a scale, rounded, clipped to -127..0; scale 4 costs nothing on River Exe, see hexn_scorer_quant_v1.py).
Two classes only (the scorer has two). With --bias-b the same weights also go into judge B with that bias: every row then gets two answers (an early-warning and a strict setting from one pass).
PACKAGE (--out file.json): task text, the chosen detectors with their names and bin edges (the host or the ESP32 turns a raw reading into a bin with them), the table words, the scale, AUC float against whole numbers on the test part.
Usage: python3 tools/hexn_front_unit_v1.py FILE [FILE ...] (--future SENSOR --q 0.9 --hours 6 | --rule EXPR | --label COL) [--port /dev/ttyUSB0 | --emulate] [--max-rows 1000] [--bias-b -40] [--out pkg.json]"""
import sys, os, json, argparse
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_intake_v1 as I, hexn_real_ocean_v2 as O, hexn_scorer_ref_v1 as R, hexn_scorer_quant_v1 as Q
def derive_task(d, Rl, a):
    """same three ways to get a label as the intake engine's analysis (label column, stated rule, future crossing)"""
    sens = [c for c in d.columns if Rl.get(c) == "sensor" and c in d]; t = d["_t"] if "_t" in d else None; step = float(t.diff().dt.total_seconds().median()) if t is not None else 1.0
    elig = np.ones(len(d), bool)
    if a.label: lab = d[a.label]; classes = sorted(lab.unique().tolist()); y = lab.map({c: i for i, c in enumerate(classes)}).values; sens = [c for c in sens if c != a.label]; how = "label column %s" % a.label
    elif a.rule: y = d.eval(a.rule).astype(int).values; classes = [0, 1]; how = "stated rule: %s" % a.rule
    elif a.future:
        x = d[a.future].astype(float).values; H = int(round(a.hours * 3600 / step)); T = np.nanpercentile(x[:int(0.6 * len(x))], a.q * 100)
        fut = np.array([x[i + 1:i + 1 + H].max() if i + H < len(x) else np.nan for i in range(len(x))]); elig = (x < T) & ~np.isnan(fut); y = (fut >= T).astype(int); classes = [0, 1]
        how = "future: %s crosses %.4g (the %g percentile of the first 60 per cent) within %g h; rows already above the line are left out" % (a.future, T, a.q * 100, a.hours)
    else: raise SystemExit("No task chosen: give --label COL, --rule EXPR or --future SENSOR [--q 0.9 --hours 6].")
    if len(classes) != 2: raise SystemExit("The unit's scorer has two classes; this task has %d." % len(classes))
    return sens, t, step, elig, y, how
def fit(files, a, max_det=8, scale=4):
    """returns (package dict, test rows as list of 8-bin lists, test labels)"""
    d, infos, Rl = I.load(files); sens, t, step, elig, y, how = derive_task(d, Rl, a)
    kind = a.features if a.features != "auto" else ("dynamic" if t is not None else "current"); F = I.features(d, sens, kind, step); Xv = F.values; names = list(F.columns); idx = np.where(elig)[0]
    if t is not None: cut = idx[int(0.6 * len(idx))]; tr, te = idx[idx < cut], idx[idx >= cut]
    else: p = np.random.default_rng(0).permutation(idx); tr, te = p[:int(0.6 * len(p))], p[int(0.6 * len(p)):]
    lo, hi = np.nanpercentile(Xv[tr], 1, axis=0), np.nanpercentile(Xv[tr], 99, axis=0); Xv = np.nan_to_num(Xv); B = O.bins(Xv, lo, hi); dd = Xv.shape[1]
    Tb = O.Tab(2, dd, lo, hi, 0.0)
    for i in tr: Tb.add(int(y[i]), Xv[i])
    W = Tb.weights()
    alone = [(I.auc(W[1][f][B[tr, f]] - W[0][f][B[tr, f]], y[tr]), f) for f in range(dd)]
    keep = [f for v, f in sorted([(v if v == v else -1, f) for v, f in alone], reverse=True)[:max_det]]
    Ws = W[:, keep, :]; Wq = Q.quantise(Ws, scale); n = len(keep)
    W8 = np.zeros((2, 8, 16), dtype=int); W8[:, :n, :12] = Wq
    ar = np.arange(n)[None, :]; sf = Ws[1][ar, B[te][:, keep]].sum(1) - Ws[0][ar, B[te][:, keep]].sum(1)
    bin_rows = [[int(B[i, f]) for f in keep] + [0] * (8 - n) for i in te]
    exp = [R.score(W8, 0, b)[0] for b in bin_rows]; si = np.array([R.unpack(w)[2] - R.unpack(w)[1] for w in exp])
    pkg = {"task": how, "classes": [0, 1], "scale": scale, "detectors": [{"slot": k, "name": names[f], "lo": float(lo[f]), "hi": float(hi[f])} for k, f in enumerate(keep)],
           "table_words": ["%08x" % R.w_load(c, s, b, W8[c][s][b]) for c in range(2) for s in range(8) for b in range(12)], "bias": 0,
           "training_rows": int(len(tr)), "test_rows": int(len(te)), "test_positives": int(y[te].sum()), "auc_float_selected": I.auc(sf, y[te]), "auc_whole_numbers": I.auc(si, y[te]), "detectors_available": dd}
    return pkg, bin_rows, [int(v) for v in y[te]], exp
def evenly(n_total, n):
    return np.linspace(0, n_total - 1, min(n, n_total)).astype(int)
def send_and_verify(unit, pkg, bin_rows, labels, exp, max_rows=1000, bias_b=None):
    pick = evenly(len(bin_rows), max_rows); rows = [bin_rows[i] for i in pick]; lab = [labels[i] for i in pick]; ex = [exp[i] for i in pick]
    unit.preset(4 if bias_b is not None else 3)
    table = [int(w, 16) for w in pkg["table_words"]]
    if bias_b is not None: unit.load_judges(table, 0, bias_b)
    else: unit.stream(table + [R.w_bias(0)])
    res = unit.stream([R.w_score(b) for b in rows]); k = 2 if bias_b is not None else 1
    A = res[0::k]; Bj = res[1::k] if k == 2 else None; wrong = sum(1 for r, e in zip(A, ex) if r != e)
    def counts(rs):
        c = {"caught": 0, "missed": 0, "false_alarms": 0, "correct_quiet": 0}
        for r, l in zip(rs, lab):
            p = r >> 31
            if l: c["caught" if p else "missed"] += 1
            else: c["false_alarms" if p else "correct_quiet"] += 1
        return c
    out = {"rows_sent": len(rows), "positives": int(sum(lab)), "judge_A_wrong_vs_reference": wrong, "judge_A": counts(A)}
    sA = np.array([R.unpack(r)[2] - R.unpack(r)[1] for r in A]); out["auc_from_unit_results_A"] = I.auc(sA, np.array(lab))
    if Bj is not None: out["judge_B_bias"] = bias_b; out["judge_B"] = counts(Bj)
    return out
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("files", nargs="+"); ap.add_argument("--label"); ap.add_argument("--rule"); ap.add_argument("--future"); ap.add_argument("--q", type=float, default=0.9); ap.add_argument("--hours", type=float, default=6.0)
    ap.add_argument("--features", default="auto"); ap.add_argument("--port"); ap.add_argument("--emulate", action="store_true"); ap.add_argument("--max-rows", type=int, default=1000); ap.add_argument("--bias-b", type=int); ap.add_argument("--out"); a = ap.parse_args()
    pkg, rows, lab, exp = fit(a.files, a); print("TASK:", pkg["task"]); print("training rows %d, test rows %d (%d positive); detectors available %d, kept %d:" % (pkg["training_rows"], pkg["test_rows"], pkg["test_positives"], pkg["detectors_available"], len(pkg["detectors"])))
    print("  " + ", ".join(x["name"] for x in pkg["detectors"])); print("AUC on the test part: float (kept detectors) %.4f, whole-number table %.4f" % (pkg["auc_float_selected"], pkg["auc_whole_numbers"]))
    if a.out: json.dump(pkg, open(a.out, "w"), indent=1); print("package written:", a.out)
    if a.port or a.emulate:
        import hexn_open_host_v1 as H
        if a.emulate: import hexn_open_emu_v1 as E; link = E.EmuLink()
        else: link = H.SerialLink(a.port)
        u = H.OpenUnit(link); u.id(); r = send_and_verify(u, pkg, rows, lab, exp, a.max_rows, a.bias_b)
        print("UNIT%s: %d rows streamed (%d positive); judge A result words wrong against the reference: %d (want 0)" % (" (MODEL, not hardware)" if a.emulate else "", r["rows_sent"], r["positives"], r["judge_A_wrong_vs_reference"]))
        print("  AUC from the unit's own results: %.4f | judge A: %s" % (r["auc_from_unit_results_A"], r["judge_A"]))
        if "judge_B" in r: print("  judge B (bias %d): %s" % (r["judge_B_bias"], r["judge_B"]))
