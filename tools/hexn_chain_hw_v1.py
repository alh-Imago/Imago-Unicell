"""hexn_chain_hw_v1 (10 Nov 2026): the speech chain (window detectors -> count/log-probability store -> decision) in EXACT HARDWARE ARITHMETIC, the reference for rtl/hexn_speech_chain_v1.v. Alan 23:14 ('place the full path into the Kintex, then run some tests'). Direction doc section 63. Python model; the RTL is cross-checked against this file bit for bit (tests/vm/test_hexn_speech_chain_v1.py).
Differences from tools/hexn_chain_v1.py (floating point), all forced by the hardware form:
 - EVENT-DRIVEN BANK: a window of STEPS time steps x NLINES lines is not held as 192 parallel wires; each event (step-in-window s, line l) reads ONE word of ternary weights for all 10 detectors, WROM[w][s*NLINES + l], and adds them to 10 accumulators. Same sum as the parallel bank with PL = 1 (the built detector multiplies by PL = 10, a scale only).
 - Window end w: margin[c] = acc[c] - THR[w][c] (integer thresholds: floor(midpoint of the mean own-class and other-class net on training half A + 0.5)); class = largest margin (lowest index on a tie) if it is > 0 else NONE = 10; msum[c] += margin[c].
 - Store: LP[d][w][prev][cls] = clip(round(16 ln p), -127, 0), p from add-one counts of training half B (context 1: prev = NONE at window 0). pathq[d] += LP[d][w][prev][cls].
 - Score S[d] = pathq[d] + SH(msum[d], code_w): code 0 = off, 1 = right shift 1, 2 = x1, 3 = x2, ... 10 = x256 (shifts only, no multiplier); the code per window is chosen on a validation part of half B.
 - Per window end the unit reports: the class, pred = argmax S (lowest index on a tie), gap = best msum - second best msum, stop = (gap >= GAP).
All arithmetic below is on Python ints with the widths the RTL uses noted in comments; the checks assert they hold.
Usage: python3 tools/hexn_chain_hw_v1.py DIR     (evaluates on the 300 test recordings)"""
import sys, os, math, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

NC = 10; NONE = 10; A = 11


class Params:
    def __init__(s, nwin, steps, nlines, wrom, thr, lp, code, gap):
        s.nwin, s.steps, s.nlines = nwin, steps, nlines
        s.wrom = wrom        # [nwin][steps*nlines] -> tuple of NC ternary weights
        s.thr = thr          # [nwin][NC] ints
        s.lp = lp            # [NC][nwin][A][A] ints -127..0
        s.code = code        # [nwin] 0..10
        s.gap = gap          # int


def shift(v, code):
    if code == 0: return 0
    e = code - 2
    return (v >> 1) if e == -1 else (v << e)


def argmax_first(v):
    b = 0
    for i in range(1, len(v)):
        if v[i] > v[b]: b = i
    return b


def run_recording(P, events):
    """events: [(step, line)] with step in 0..nwin*steps-1 -> list per window of dict(cls, pred, gap, stop)"""
    acc_all = [[0] * NC for _ in range(P.nwin)]
    for st, ln in events:
        w, s = divmod(st, P.steps); wt = P.wrom[w][s * P.nlines + ln]
        for c in range(NC): acc_all[w][c] += wt[c]
    msum = [0] * NC; pathq = [0] * NC; prev = NONE; out = []
    for w in range(P.nwin):
        acc = acc_all[w]; assert all(-128 <= a <= 127 for a in acc)
        margin = [acc[c] - P.thr[w][c] for c in range(NC)]
        mx = argmax_first(margin); cls = mx if margin[mx] > 0 else NONE
        for c in range(NC): msum[c] += margin[c]; pathq[c] += P.lp[c][w][prev][cls]
        S = [pathq[c] + shift(msum[c], P.code[w]) for c in range(NC)]
        pred = argmax_first(S); srt = sorted(msum, reverse=True); gap = srt[0] - srt[1]
        out.append(dict(cls=cls, pred=pred, gap=gap, stop=int(gap >= P.gap), msum=list(msum), S=list(S)))
        prev = cls
    return out


def decide(res, use_stop):
    """final digit and windows used"""
    if use_stop:
        for w, r in enumerate(res):
            if r["stop"]: return r["pred"], w + 1
    return res[-1]["pred"], len(res)


# ---------------------------------------------------------------- training on real data (numpy)
def train(Xtr3, ytr, nwin, nlines, gap, seed=1):
    """Xtr3: (N, nsteps, nlines) 0/1 ; returns Params, trained as in hexn_chain_v1 (halves A for banks, B for the store)"""
    import hexn_det_shd_v1 as D, hexn_chain_v1 as C
    nsteps = Xtr3.shape[1]; steps = nsteps // nwin
    rs = np.random.RandomState(1); half = np.zeros(len(ytr), dtype=bool)
    for c in range(NC): idx = np.where(ytr == c)[0]; half[rs.permutation(idx)[:len(idx) // 2]] = True
    def win(X, w): return X[:, w * steps:(w + 1) * steps, :].reshape(len(X), -1).astype(np.int32)
    wrom = []; thr = []
    for w in range(nwin):
        Xa, ya = win(Xtr3[half], w), ytr[half]; Wt = D.train_bank(Xa, ya, len(ya) // NC); net = Xa @ Wt.T
        thr.append([int(math.floor((net[ya == k, k].mean() + net[ya != k, k].mean()) / 2 + 0.5)) for k in range(NC)])
        wrom.append([tuple(int(x) for x in Wt[:, j]) for j in range(Wt.shape[1])])
    P = Params(nwin, steps, nlines, wrom, thr, None, [0] * nwin, gap)
    # window classes of half B through the bank
    def classes(X):
        rows = []
        for x in X:
            ev = [(st, ln) for st, ln in zip(*np.nonzero(x))]; acc = [[0] * NC for _ in range(nwin)]
            for st, ln in ev:
                w, s = divmod(int(st), steps); wt = wrom[w][s * nlines + int(ln)]
                for c in range(NC): acc[w][c] += wt[c]
            cl = []
            for w in range(nwin):
                m = [acc[w][c] - thr[w][c] for c in range(NC)]; mx = argmax_first(m); cl.append(mx if m[mx] > 0 else NONE)
            rows.append(cl)
        return np.array(rows)
    XB = Xtr3[~half]; yB = ytr[~half]; cB = classes(XB); vs = np.random.RandomState(2).rand(len(yB)) < 0.2
    def lpq(cnt): return np.clip(np.round(16 * np.log(cnt / cnt.sum(axis=-1, keepdims=True))), -127, 0).astype(int)
    P.lp = lpq(C.build_store(cB, yB, nwin, 1))
    Pv = Params(nwin, steps, nlines, wrom, thr, lpq(C.build_store(cB[~vs], yB[~vs], nwin, 1)), [0] * nwin, gap)
    evs = [[(int(a), int(b)) for a, b in zip(*np.nonzero(x))] for x in XB[vs]]; yv = yB[vs]
    for w in range(nwin):                                                     # choose the shift code of window w on validation (earlier windows already fixed)
        best = (-1, 0)
        for code in range(11):
            Pv.code[w] = code; acc = np.mean([run_recording(Pv, e)[w]["pred"] == y for e, y in zip(evs, yv)])
            if acc > best[0] + 1e-9: best = (acc, code)
        Pv.code[w] = best[1]
    P.code = list(Pv.code); return P


def events_of(x): return [(int(a), int(b)) for a, b in zip(*np.nonzero(x))]


def main(d):
    import hexn_det_shd_v1 as D, hexn_det_net_v1 as N
    nwin = 5; Xtr3, ytr, Xte3, yte, new = D.build(d, N.NIN, N.NBINS, N.TOPN)
    P = train(Xtr3, ytr, nwin, N.NIN, gap=10)
    r0 = random.Random(0); pick = []
    for c in range(NC): pick += r0.sample([i for i in range(len(yte)) if yte[i] == c], 30)
    pick = np.array(pick); y = yte[pick]; is_new = np.isin(pick, new); res = [run_recording(P, events_of(Xte3[i])) for i in pick]
    print("hardware-arithmetic chain, %d windows of %d steps; shift codes per window %s; chain accuracy on the 300 test recordings (all | unheard speakers)" % (nwin, P.steps, P.code))
    for p in range(nwin):
        pr = np.array([r[p]["pred"] for r in res]); cl = np.array([r[p]["cls"] for r in res]); print("  after %d windows: %.1f | %.1f   (share of recordings whose window %d is reported NONE: %.0f%%)" % (p + 1, 100 * np.mean(pr == y), 100 * np.mean(pr[is_new] == y[is_new]), p + 1, 100 * np.mean(cl == NONE)))
    for g in (5, 10, 20, 40, 80):
        P.gap = g; rr = [run_recording(P, events_of(Xte3[i])) for i in pick]; dw = [decide(r, True) for r in rr]
        print("  stop at gap >= %-3d: mean windows %.2f, accuracy %.1f" % (g, np.mean([w for _, w in dw]), 100 * np.mean([p for p, _ in dw] == y)))
    print("  largest |msum| seen: %d ; largest |S|: %d (the RTL holds msum in 16 bits and S in 24)" % (max(abs(v) for r in res for q in r for v in q["msum"]), max(abs(v) for r in res for q in r for v in q["S"])))
    return P


if __name__ == "__main__":
    main(sys.argv[1])
