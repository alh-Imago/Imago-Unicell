"""(v2: clone of hexn_layer_v1.py, left untouched. FIX: in v1 a layer-2 cell heard hidden cell i on lane i*4, so hidden cell 5 landed on lane 20 = the output lane and overwrote its gate (that output cell could go silent), and 7 or more hidden cells ran off the end of the 24 lanes. v2 hears hidden cell i on lane i (i = 0..19; the output lane stays 20), so up to 20 hidden cells.)"""
"""hexn_layer_v1: a TWO-LAYER network of v2 cells (tools/hexn_cell_v2_model.py, MixCell; Python model only; new file). STEP 1: can a hand-wired network do the pattern task at all?
Layer 1: N1 cells, each hears the same 20 external input lanes (faces 1-5), every lane off / add / subtract (ternary: off, +, code 3 = negative), one threshold, ONE output lane (face 0 lane 0, gate CHOOSE).
Layer 2: N2 cells, one per class; cell j hears layer-1 cell i's output on its face i lane 0 (off / add / subtract), one threshold, one output lane (face 5 lane 0). The answer = the layer-2 cell with the most output clocks in the last two windows (a tie or silence = no answer).
Input: a pattern = 20 bits; each 1-bit drives its lane high for the first PULSE clocks of the forward phase of every window; a noisy presentation flips each bit with chance q. 4 windows per presentation (layer 1 decides after window 0, layer 2 after window 1).
ASSUMPTION (not checked here): the RTL cell v5 behaves as the v2 model."""
import sys, os, random, importlib.util
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("cm", os.path.join(ROOT, "tools", "hexn_cell_v2_model.py")); cm = importlib.util.module_from_spec(sp); sp.loader.exec_module(cm)
F, P, N = cm.F, cm.P, cm.N; PL = 10; NIN = 20; PULSE = 2; WIN = 4; OUT1 = 0; OUT2 = 5 * P
IN_LANES = list(range(P, N))                                   # faces 1..5, 20 lanes
def l1_cell(w, thr):                                          # w: 20 values in {0, 1, 2} = off, add, subtract
    act, dr, code = [0] * N, [0] * N, [0] * N; act[OUT1] = 1; dr[OUT1] = 1; code[OUT1] = 1
    for lane, s in zip(IN_LANES, w):
        if s: act[lane] = 1; code[lane] = 3 if s == 2 else 0
    return cm.MixCell(act, dr, code, [thr] * F, 0)
def l2_cell(w, thr):                                          # w: N1 values in {0, 1, 2}; sender i arrives on lane i
    act, dr, code = [0] * N, [0] * N, [0] * N; act[OUT2] = 1; dr[OUT2] = 1; code[OUT2] = 1
    for i, s in enumerate(w):
        if s: act[i] = 1; code[i] = 3 if s == 2 else 0
    return cm.MixCell(act, dr, code, [thr] * F, 0)
def present(net, bits):
    L1 = [l1_cell(w, t) for (w, t) in net["l1"]]; L2 = [l2_cell(w, t) for (w, t) in net["l2"]]; n1 = len(L1); out = [0] * len(L2)
    for win in range(WIN):
        for phase in (0, 1):
            for t in range(PL):
                ps, we = int(t == 0), int(phase == 1 and t == PL - 1)
                tx1 = [c.tx(phase) for c in L1]; tx2 = [c.tx(phase) for c in L2]
                for c in L1:
                    rx = [0] * N
                    if phase == 0 and t < PULSE:
                        for lane, b in zip(IN_LANES, bits): rx[lane] = b
                    c.clock(rx, phase, ps, we)
                for j, c in enumerate(L2):
                    rx = [0] * N
                    for i in range(n1): rx[i] = tx1[i][OUT1]
                    c.clock(rx, phase, ps, we)
                if win >= WIN - 2:
                    for j in range(len(L2)): out[j] += tx2[j][OUT2]
    return out
def answer(out):
    m = max(out); return out.index(m) if m > 0 and out.count(m) == 1 else -1
def hand_net(pats, thr1, thr2):                              # layer-1 cell i = template of pattern i (add on its 1-bits, subtract on its 0-bits); layer-2 cell j copies layer-1 cell j
    n = len(pats); l1 = [([1 if b else 2 for b in p], thr1) for p in pats]; l2 = [([1 if i == j else 0 for i in range(n)], thr2) for j in range(n)]; return {"l1": l1, "l2": l2}
def noisy(rnd, p, q): return [b ^ (rnd.random() < q) for b in p]
if __name__ == "__main__":
    import time
    rnd = random.Random(1); M = 3
    pats = [[int(rnd.random() < 0.5) for _ in range(NIN)] for _ in range(M)]
    print("hand-built network, %d patterns of %d bits (hamming distances %s); 40 noisy presentations per pattern" % (M, NIN, [sum(a != b for a, b in zip(pats[i], pats[j])) for i in range(M) for j in range(i)]))
    print("thr1 thr2 noise | right wrong none")
    t0 = time.time()
    for thr1, thr2 in ((6, 1), (10, 1), (14, 1)):
        net = hand_net(pats, thr1, thr2)
        for q in (0.0, 0.1, 0.2):
            r = w = nn = 0
            for y in range(M):
                for _ in range(40):
                    a = answer(present(net, noisy(rnd, pats[y], q))); r += a == y; w += a not in (y, -1); nn += a == -1
            tot = r + w + nn; print(f"{thr1:4d} {thr2:4d} {q:.2f} | {r/tot:.2f} {w/tot:.2f} {nn/tot:.2f}")
    print("seconds", round(time.time() - t0, 1))
