"""hexn_scorer_quant_v1: HOW MUCH DOES WHOLE-NUMBER (int8) WEIGHTING COST? (Python + numpy + sklearn; new file 1 Nov 2026). Takes the River Exe task of hexn_real_exe_v1 (8 detectors x 12 bins, learn on 2022, test on all 2023),
builds the two-class table refresh in floating point, then quantises it the way the Tang scorer (fpga/verilog/hexn_scorer_v1.v) needs it: per sensor subtract the largest weight (the same constant for both classes, so the decision does not change),
multiply by a scale, round to a whole number, clip to -127..0 (8-bit). The int8 score is computed with the bit-exact reference hexn_scorer_ref_v1.score. Reports AUC float vs int8 for several scales, and how often the two decisions differ.
Usage: python3 tools/hexn_scorer_quant_v1.py"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_real_exe_v1 as E, hexn_real_ocean_v2 as O, hexn_scorer_ref_v1 as R
def quantise(W, scale):
    Wq = W - W.max(axis=(0, 2), keepdims=True)                 # per sensor, the same shift for both classes
    return np.clip(np.round(Wq * scale), -127, 0).astype(int)
def run():
    X, y, el, yr, t, T = E.build(); i22 = np.where(el & (yr == 2022))[0]; i23 = np.where(el & (yr == 2023))[0]; d = X.shape[1]
    lo, hi = np.percentile(X[i22], 1, axis=0), np.percentile(X[i22], 99, axis=0); B = O.bins(X, lo, hi); assert d == R.NS and O.NB == 12
    Tb = O.Tab(2, d, lo, hi, 0.0)
    for i in i22: Tb.add(int(y[i]), X[i])
    W = Tb.weights(); ar = np.arange(d)[None, :]
    sf = W[1][ar, B[i23]].sum(1) - W[0][ar, B[i23]].sum(1)
    rng = (W - W.max(axis=(0, 2), keepdims=True)).min()
    print("task: River Exe, learn 2022 (%d rows), test 2023 (%d rows, %d high-flow crossings); weight spread after the per-sensor shift: %.1f nats" % (len(i22), len(i23), y[i23].sum(), -rng))
    print("float table            AUC %.4f" % E.auc(sf, y[i23]))
    for scale in (2, 4, 8, 12, 16):
        Wq = quantise(W, scale); sc = np.array([R.score(Wq, 0, B[i])[1:3] for i in i23]); si = sc[:, 1] - sc[:, 0]
        sat = np.mean((np.round((W - W.max(axis=(0, 2), keepdims=True)) * scale) < -127))
        print("int8 scale %2d (1 step = %.3f nats): AUC %.4f | table entries clipped %.1f%% | largest |score| %d" % (scale, 1 / scale, E.auc(si, y[i23]), 100 * sat, np.abs(sc).max()))
    return W
if __name__ == "__main__": run()
