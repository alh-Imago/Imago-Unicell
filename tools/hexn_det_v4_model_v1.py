"""Hex-N detector v4 (signed total and margin) in HARDWARE ARITHMETIC, PYTHON MODEL ONLY (new file, 30 Oct 2026; companion of rtl/hexn_det_v4.v).
The earlier models (hexn_margin_v1.py, hexn_deadband_v1.py) count a total in single lane steps. The RTL adds the lane sum on EVERY clock of a PL = 10 clock window, so with the
wires held for the window the total is PL x (lane sum), saturating at the accumulator width; thresholds and margins are in those units. This file redoes the comparison in them.
Arms (all trained by the counted rule with trainer counters saturating at CAP 31, as on the board, or CAP 127 where stated; midpoint thresholds in hardware units):
  H3   the detector as built (v3): total clamped at 0 and at 2^AW-1 (AW 7), margin 0..6 above the threshold, burst 1+margin, answer = unique strictly highest burst among detectors that fired
  H4_7 / H4_8 / H4_9   v4: signed total saturating at +-(2^AW - 1) for AW 7 / 8 / 9, answer = largest signed margin, ties to the lowest index
  H4_8w  as H4_8 with CAP 127 (8-bit trainer counters)
  T2   nearest template, ties to the lowest (reference)"""
import argparse, importlib.util, os, random, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("ring", os.path.join(ROOT, "tools", "hexn_ring_v1.py")); R = importlib.util.module_from_spec(sp); sp.loader.exec_module(R)
PL = 10

def weights(X, y, K, S, cap):
    nb = len(X[0]); cnt = [[0] * nb for _ in range(K)]
    for x, c in zip(X, y):
        for k in range(K):
            d = (K - 1) if c == k else -1
            for j in range(nb):
                if x[j]: cnt[k][j] = max(-cap, min(cap, cnt[k][j] + d))
    T = max(1, min(R.TMAX, round(0.5 * S)))
    return [[(1 if v >= T else -1 if v <= -T else 0) for v in row] for row in cnt]

def acc_hw(w, x, aw, signed):
    net = sum(a * b for a, b in zip(w, x)); mx = (1 << aw) - 1
    a = PL * net; a = max(-mx, min(mx, a)) if signed else max(0, min(mx, a)); return a

def midpoint(W, X, y, K, aw, signed):
    mx = (1 << aw) - 1; thr = []
    for k in range(K):
        pos = [acc_hw(W[k], x, aw, signed) for x, c in zip(X, y) if c == k]; neg = [acc_hw(W[k], x, aw, signed) for x, c in zip(X, y) if c != k]
        t = round((sum(pos) / len(pos) + sum(neg) / len(neg)) / 2); thr.append(max(-mx, min(mx, t)) if signed else max(0, min(mx, t)))
    return thr

def one(seed, K, nb, q, S, per_test=100):
    rnd = random.Random(seed); tpl = R.templates(rnd, K, nb, 4)
    tr = [(R.sample(rnd, tpl[c], q), c) for c in range(K) for _ in range(S)]; random.Random(seed + 5).shuffle(tr)
    te = [(R.sample(rnd, tpl[c], q), c) for c in range(K) for _ in range(per_test)]
    X = [x for x, _ in tr]; y = [c for _, c in tr]; r = {}
    W = weights(X, y, K, S, 31); W2 = weights(X, y, K, S, 127)
    thr = midpoint(W, X, y, K, 7, False); ok = 0
    for x, c in te:
        g = []
        for k in range(K):
            a = acc_hw(W[k], x, 7, False); g.append(1 + min(6, a - thr[k]) if a >= thr[k] and a > 0 else 0)
        mxg = max(g); ok += (mxg > 0 and g.count(mxg) == 1 and g.index(mxg) == c)
    r["H3"] = ok / len(te)
    for name, WW, aw in (("H4_7", W, 7), ("H4_8", W, 8), ("H4_9", W, 9), ("H4_8w", W2, 8)):
        thr = midpoint(WW, X, y, K, aw, True); ok = 0
        for x, c in te:
            mg = [acc_hw(WW[k], x, aw, True) - thr[k] for k in range(K)]; ok += (mg.index(max(mg)) == c)
        r[name] = ok / len(te)
    mean = [[sum(x[j] for x, c in tr if c == k) / S for j in range(nb)] for k in range(K)]; tm = [[1 if v >= .5 else 0 for v in row] for row in mean]
    r["T2"] = sum(min(range(K), key=lambda k: sum(a != b for a, b in zip(x, tm[k]))) == c for x, c in te) / len(te)
    return r

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=25); a = ap.parse_args()
    print(f"{a.seeds} seeds; hardware arithmetic (PL={PL}, wires held for the window); accuracy")
    print("K  wires noise S  | H3 as built | H4 AW7 | H4 AW8 | H4 AW9 | H4 AW8 +8-bit counters | T2 nearest template")
    for K, nb, q, S in ((4, 12, .15, 16), (8, 18, .15, 16), (16, 18, .15, 16), (16, 18, .25, 16), (8, 18, .15, 4), (8, 18, .15, 2), (8, 18, .25, 4)):
        rs = [one(s, K, nb, q, S) for s in range(a.seeds)]; mu = lambda k: st.mean(r[k] for r in rs)
        print(f"{K:<2d} {nb:<5d} {q:<5} {S:<3d} | {mu('H3'):.3f}       | {mu('H4_7'):.3f}  | {mu('H4_8'):.3f}  | {mu('H4_9'):.3f}  | {mu('H4_8w'):.3f}                  | {mu('T2'):.3f}", flush=True)
