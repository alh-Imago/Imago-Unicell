"""hexn_scorer_ref_v1: bit-exact Python reference of fpga/verilog/hexn_scorer_v1.v (new file 1 Nov 2026) and the word encoders the ESP32 sketch must mirror."""
import numpy as np
NS = 8
def w_load(cls, sensor, b, wt): return (12 << 28) | (cls << 24) | (((sensor << 4) | b) << 16) | (int(wt) & 0xFF)
def w_bias(v): return (13 << 28) | (int(v) & 0xFFFF)
def w_score(bins):
    w = 0
    for i, b in enumerate(bins): assert 0 <= b < 12; w |= int(b) << (4 * i)
    return w
def table_words(W):
    """W[2][NS][16] int -> list of LOAD words"""
    return [w_load(c, s, b, W[c][s][b]) for c in range(2) for s in range(NS) for b in range(16)]
def score(W, bias, bins):
    s0 = sum(int(W[0][s][bins[s]]) for s in range(NS)); s1 = sum(int(W[1][s][bins[s]]) for s in range(NS))
    pred = 1 if (s1 + bias) > s0 else 0
    return (pred << 31) | ((s1 & 0xFFF) << 16) | (s0 & 0xFFF), s0, s1, pred
def unpack(w):
    s1 = (w >> 16) & 0xFFF; s0 = w & 0xFFF
    s1 -= 4096 if s1 & 0x800 else 0; s0 -= 4096 if s0 & 0x800 else 0
    return w >> 31, s0, s1
def make_vectors(seed=1, n=400):
    rng = np.random.default_rng(seed); W = rng.integers(-127, 128, size=(2, NS, 16)); bias = int(rng.integers(-300, 300))
    words = table_words(W) + [w_bias(bias)]; exp = []
    for k in range(n):
        if k == n // 2:                                  # re-load a few entries and the bias mid-stream
            for _ in range(5):
                c, s, b = int(rng.integers(0, 2)), int(rng.integers(0, NS)), int(rng.integers(0, 16)); W[c][s][b] = int(rng.integers(-127, 128)); words.append(w_load(c, s, b, W[c][s][b]))
            bias = int(rng.integers(-300, 300)); words.append(w_bias(bias))
        bins = rng.integers(0, 12, size=NS); words.append(w_score(bins)); exp.append(score(W, bias, bins)[0])
    return words, exp
if __name__ == "__main__":
    import sys
    words, exp = make_vectors(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    open("tests/hexn_scorer/in.hex", "w").write("\n".join("%08x" % w for w in words) + "\n")
    open("tests/hexn_scorer/exp.hex", "w").write("\n".join("%08x" % w for w in exp) + "\n")
    print(len(words), "input words,", len(exp), "expected results")
