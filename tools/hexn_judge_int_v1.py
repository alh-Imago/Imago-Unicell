"""hexn_judge_int_v1: THE NEURAL CORE'S JUDGE IN WHOLE-NUMBER ARITHMETIC (Python + numpy; model only; new file 31 Oct 2026). Alan, 31 Oct 03:31: 'yes' to implementing the neural core, Python whole-stack first, with whole numbers so it can go into hardware as it is.
The judge is the float network of tools/hexn_helper_judge_v3.py (127 inputs, 64 hidden units, one output; weights in docs/hex-n/data/judge_v3_h64_weights.json). Its input is ONE-HOT: for each of the 42 cells exactly one of three inputs (empty, X, O) is 1, plus one parity input, so the first layer is the SUM OF 43 ROWS of W1 (adds, no multiplies); then ReLU; then 64 multiply-adds with W2; then tanh.
Integer version: W1, b1 scaled by 2^S1 and rounded to integers; W2 scaled by 2^S2; hidden values are integers (scale 2^S1); the output accumulator is an integer of scale 2^(S1+S2); the final tanh is a lookup table of 512 entries over [-4, 4) (outputs scaled by 2^8, returned as a fraction). `JudgeInt(S1, S2)` gives value(board) in [-1, 1] for the side whose pieces are 1 (X) exactly like the float judge; `cost()` counts the operations of one evaluation and the memory in bits.
Run as a script: compares the integer judge with the float judge on positions from lookahead games (value error, sign agreement, which root move each prefers)."""
import os, sys, json, random
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_connect4_v1 as C, hexn_helper_judge_v1 as J
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WPATH = os.path.join(ROOT, "docs/hex-n/data/judge_v3_h64_weights.json")
class JudgeFloat:
    def __init__(s, path=WPATH):
        W = json.load(open(path)); s.W1, s.b1, s.W2, s.b2 = (np.array(W[k], dtype=np.float64) for k in ("W1", "b1", "W2", "b2"))
    def value(s, b): h = np.maximum(J.feats(b) @ s.W1 + s.b1, 0); return float(np.tanh(h @ s.W2 + s.b2)[0])
def active(b):
    idx = []
    for c in range(C.COLS):
        for r in range(C.ROWS): idx.append((c * C.ROWS + r) * 3 + b[c][r])
    n = sum(1 for c in range(C.COLS) for r in range(C.ROWS) if b[c][r]); 
    if n % 2: idx.append(C.COLS * C.ROWS * 3)
    return idx
class JudgeInt:
    def __init__(s, S1=6, S2=6, path=WPATH, TB=8):
        W = json.load(open(path)); s.S1, s.S2 = S1, S2
        s.W1 = np.rint(np.array(W["W1"]) * (1 << S1)).astype(np.int64); s.b1 = np.rint(np.array(W["b1"]) * (1 << S1)).astype(np.int64)
        s.W2 = np.rint(np.array(W["W2"])[:, 0] * (1 << S2)).astype(np.int64); s.b2 = int(round(float(np.array(W["b2"])[0]) * (1 << (S1 + S2))))
        s.TB = TB; xs = (np.arange(512) - 256 + 0.5) / 64.0; s.lut = np.rint(np.tanh(xs) * (1 << TB)).astype(np.int64)   # input range [-4, 4) in steps of 1/64
        s.cache = {}
    def acc(s, b):
        h = np.maximum(s.b1 + s.W1[active(b)].sum(axis=0), 0); return int(h @ s.W2) + s.b2          # scale 2^(S1+S2)
    def value(s, b):
        k = tuple(tuple(col) for col in b); v = s.cache.get(k)
        if v is None:
            a = s.acc(b); x = (a * 64) >> (s.S1 + s.S2)             # to 1/64 steps
            v = int(s.lut[max(0, min(511, x + 256))]) / float(1 << s.TB); s.cache[k] = v
        return v
    def cost(s):
        H = s.W1.shape[1]; w1max = int(np.abs(s.W1).max()); w2max = int(np.abs(s.W2).max())
        b1 = int(w1max).bit_length() + 1; b2 = int(w2max).bit_length() + 1
        return dict(adds_first_layer=43 * H, macs_second_layer=H, relu=H, lut_entries=512, W1_bits=s.W1.size * b1, W2_bits=s.W2.size * b2, bias_bits=(H + 1) * 16, weight_bits_total=s.W1.size * b1 + s.W2.size * b2 + (H + 1) * 16, W1_word=b1, W2_word=b2)
def positions(n, seed=1):
    rnd = random.Random(seed); out = []
    pl = [C.make_lookahead(2), C.opp_random]
    while len(out) < n:
        b = C.new(); who = 1; k = rnd.randrange(2); mv = 0
        while True:
            c = (C.make_lookahead(2) if rnd.random() < 0.7 else C.opp_random)(b, who, rnd); C.drop(b, c, who); mv += 1
            if C.winner(b) or C.full(b): break
            if mv >= 4 and rnd.random() < 0.25: out.append([col[:] for col in b])
            who = 3 - who
    return out[:n]
if __name__ == "__main__":
    P = positions(1500); F = JudgeFloat(); print("positions %d" % len(P))
    fv = np.array([F.value(b) for b in P])
    for S1, S2 in ((4, 4), (5, 5), (6, 6), (7, 7), (8, 8)):
        I = JudgeInt(S1, S2); iv = np.array([I.value(b) for b in P]); c = I.cost()
        print("S1=%d S2=%d: mean |error| %.4f, max %.3f, sign agreement %.3f (positions where the float value is beyond +-0.1), correlation %.4f, W1 word %d bits, W2 word %d bits, weights %.1f kbit" % (S1, S2, np.abs(fv - iv).mean(), np.abs(fv - iv).max(), np.mean(np.sign(fv[np.abs(fv) > 0.1]) == np.sign(iv[np.abs(fv) > 0.1])), np.corrcoef(fv, iv)[0, 1], c["W1_word"], c["W2_word"], c["weight_bits_total"] / 1000))
    # which root move does each prefer? 1-ply: drop each legal column, evaluate for the mover
    rnd = random.Random(5); same = tot = 0; I = JudgeInt(6, 6)
    for b in P[:400]:
        who = 1 if sum(1 for col in b for v in col if v) % 2 == 0 else 2
        mv = C.legal(b)
        if len(mv) < 2: continue
        def best(J_):
            vs = []
            for c in mv:
                C.drop(b, c, who); v = J_.value(b) * (1 if who == 1 else -1); C.undo(b, c); vs.append(v)
            return int(np.argmax(vs))
        tot += 1; same += best(F) == best(I)
    print("one-ply preferred move, float against integer (S1=S2=6): %d of %d the same" % (same, tot))
    print("cost per evaluation:", I.cost())
