"""Hex-N layer 1: WHERE IS INFORMATION LOST IN THE WEIGHTS? PYTHON MODEL ONLY (new file, 30 Oct 2026; no RTL).
Alan, 30 Oct 22:30: after the margin rule (hexn_margin_v1.py) the counted detector is still behind a nearest-template classifier; look for
information lost in the weights (the 'dead band': lanes with a small count get weight 0 = ignored). Same data as hexn_baseline_v1.py,
margin answer rule (largest total minus threshold, ties to the lowest-numbered detector, always answers, margin unclamped), trainer
counters saturating at CAP (default 127).  A detector lane adds its weight when its wire is on; the total is Sum(w * x).
Variants (weights / total / threshold):
  V1  counted weights, dead band T = half the samples (max 16) / total clamped at 0 (the accumulator as modelled) / midpoint of own and other means
  V2  as V1 but the total is SIGNED (not clamped at 0; costs a sign bit)
  V3  counted weights with T = 1 (almost no dead band) / clamped / midpoint
  V4  T = 1 / signed / midpoint
  V5  sign of the count, no dead band (0 only when the count is exactly 0) / signed / midpoint
  V6  template weights (+1 where the class's majority bit is 1, -1 where 0) / signed / midpoint
  V7  template weights / signed / threshold = number of ones in the template (this IS the nearest-template classifier: sanity check)
  T2  nearest template, ties to the lowest (reference)
Also prints the share of lanes at weight 0 for V1."""
import argparse, importlib.util, os, random, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("ring", os.path.join(ROOT, "tools", "hexn_ring_v1.py")); R = importlib.util.module_from_spec(sp); sp.loader.exec_module(R)
R.AW = 7

def counters(X, y, K, cap):
    nb = len(X[0]); cnt = [[0] * nb for _ in range(K)]
    for x, c in zip(X, y):
        for k in range(K):
            d = (K - 1) if c == k else -1
            for j in range(nb):
                if x[j]: cnt[k][j] = max(-cap, min(cap, cnt[k][j] + d))
    return cnt

def total(w, x, signed, top=127):
    s = sum(a * b for a, b in zip(w, x)); return min(top, s) if signed else max(0, min(top, s))

def midpoint(W, X, y, K, signed):
    thr = []
    for k in range(K):
        pos = [total(W[k], x, signed) for x, c in zip(X, y) if c == k]; neg = [total(W[k], x, signed) for x, c in zip(X, y) if c != k]
        thr.append(round((sum(pos) / len(pos) + sum(neg) / len(neg)) / 2))
    return thr

def acc(W, thr, te, K, signed):
    ok = 0
    for x, c in te:
        mg = [total(W[k], x, signed) - thr[k] for k in range(K)]; ok += (mg.index(max(mg)) == c)
    return ok / len(te)

def one(seed, K, nb, q, S, cap=127, per_test=100):
    rnd = random.Random(seed); tpl = R.templates(rnd, K, nb, 4)
    tr = [(R.sample(rnd, tpl[c], q), c) for c in range(K) for _ in range(S)]; random.Random(seed + 5).shuffle(tr)
    te = [(R.sample(rnd, tpl[c], q), c) for c in range(K) for _ in range(per_test)]
    X = [x for x, _ in tr]; y = [c for _, c in tr]; cnt = counters(X, y, K, cap); T = max(1, min(R.TMAX, round(0.5 * S)))
    wT = [[(1 if v >= T else -1 if v <= -T else 0) for v in row] for row in cnt]
    w1 = [[(1 if v >= 1 else -1 if v <= -1 else 0) for v in row] for row in cnt]
    ws = [[(1 if v > 0 else -1 if v < 0 else 0) for v in row] for row in cnt]
    mean = [[sum(x[j] for x, c in tr if c == k) / S for j in range(nb)] for k in range(K)]; tm = [[1 if v >= 0.5 else 0 for v in row] for row in mean]
    wt = [[1 if b else -1 for b in row] for row in tm]; r = {}
    r["V1"] = acc(wT, midpoint(wT, X, y, K, False), te, K, False); r["V2"] = acc(wT, midpoint(wT, X, y, K, True), te, K, True)
    r["V3"] = acc(w1, midpoint(w1, X, y, K, False), te, K, False); r["V4"] = acc(w1, midpoint(w1, X, y, K, True), te, K, True)
    r["V5"] = acc(ws, midpoint(ws, X, y, K, True), te, K, True); r["V6"] = acc(wt, midpoint(wt, X, y, K, True), te, K, True)
    r["V7"] = acc(wt, [sum(row) for row in tm], te, K, True)
    r["T2"] = sum(min(range(K), key=lambda k: sum(a != b for a, b in zip(x, tm[k]))) == c for x, c in te) / len(te)
    r["zero"] = sum(w == 0 for row in wT for w in row) / (K * nb)
    return r

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=25); ap.add_argument("--cap", type=int, default=127); a = ap.parse_args()
    print(f"{a.seeds} seeds, counters saturate at {a.cap}; margin answer rule; accuracy")
    print("K  wires noise S  | V1 dead band | V2 +signed | V3 T=1 | V4 T=1,sgn | V5 sign | V6 template w | V7 tmpl w+thr=ones | T2 nearest tmpl | V1 zero lanes")
    for K, nb, q, S in ((4, 12, .15, 16), (8, 18, .15, 16), (16, 18, .15, 16), (16, 18, .25, 16), (8, 18, .15, 4), (8, 18, .15, 2), (8, 18, .25, 4)):
        rs = [one(s, K, nb, q, S, a.cap) for s in range(a.seeds)]; mu = lambda k: st.mean(r[k] for r in rs)
        print(f"{K:<2d} {nb:<5d} {q:<5} {S:<3d} | {mu('V1'):.3f}        | {mu('V2'):.3f}      | {mu('V3'):.3f}  | {mu('V4'):.3f}      | {mu('V5'):.3f}   | {mu('V6'):.3f}         | {mu('V7'):.3f}              | {mu('T2'):.3f}           | {mu('zero'):.2f}", flush=True)
