"""hexn_layer1_v1: LAYER 1 from the recorded ESP32 data: one bank (set of detectors trained by the bank's own learner) per sensor, each fed through its filter and coding (Python model only; no RTL; new file; uses hexn_tang_script_v1.make_model/classify, hexn_encode_v1, hexn_medfilt_v1, hexn_ir_decode_v1 unchanged).
Banks (each has its own 18 wires, as in 'one layer 1 per sensor'):
  light  : classes lamp on / light off / daylight only (the three 200 per second light recordings); pair-average of two samples, then thresholds in the gaps of the pooled training readings (min gap 400 counts, the hand-made choice of hexn_encode_v1).
  pot    : 4 position bands (under 1024, 1024-2047, 2048-3071, over 3071) from the pot sweep; thermometer with thresholds at the band edges (the labels define the bands, so the coding follows them). Trained on the first sweep, tested on the second.
  thermistor : 3 bands (warm under 1850, mid, cool 1990 or over; hand-made edges); 9-sample causal median in front. Trained on filtered samples from run_2 and the first half of the finger file, tested on the second half of the finger file, with the median and without (the label of each sample is the band of the file's 0.5 s centred-median trend). Thermometer at the band edges.
  ir     : the remote's 21 keys; the command byte as 8 wires, or the command plus its inverse as 16 wires; trained on the decoded frames, tested with random bit flips (probability p per wire).
Accuracy = share classified as the right class (no answer or a tie counts as wrong). Where a training pool is drawn at random, 16 samples per class (10 seeds).
Usage: python3 tools/hexn_layer1_v1.py"""
import sys, os, random, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_script_v1 as S1, hexn_encode_v1 as E, hexn_medfilt_v1 as M, hexn_ir_decode_v1 as IR
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "..", "docs", "hex-n", "data")
D0 = S1.parse_script(open(os.path.join(HERE, "..", "docs", "hex-n", "frontend", "example_sensors_script_v1.txt")).read())
def bank(train, K, NB=18):
    d = dict(D0); d["classes"] = K; d["wires"] = NB; d["train"] = train; d["test"] = []; return S1.make_model(d, 16)
def acc(m, test): return sum(S1.classify(m, b)[0] == y for b, y in test) / len(test)
def therm(v, ths): return [int(v >= t) for t in ths]
def pad(bits): return bits + [0] * (18 - len(bits))
def split(v, f): n = int(len(v) * f); return v[:n], v[n:]
def light_bank(seed):
    r = random.Random(seed); names = ["lamp", "dark", "day"]; src, _ = E.sources(False)
    tr = {k: split(src[k], 0.6)[0] for k in names}; te = {k: split(src[k], 0.6)[1] for k in names}
    pool = sorted(r.choice(tr[k]) for k in names for _ in range(16))
    v = sorted(pool); g = sorted(((b - a, (a + b) / 2) for a, b in zip(v, v[1:]) if b - a >= 400), reverse=True)[:4]; th = sorted(t for _, t in g)
    train = [(pad(therm(r.choice(tr[k]), th)), y) for y, k in enumerate(names) for _ in range(16)]; r.shuffle(train)
    m = bank(train, 3); test = [(pad(therm(x, th)), y) for y, k in enumerate(names) for x in te[k]]
    return acc(m, test), th
def pot_bank(seed):
    r = random.Random(seed); v = E.load("esp_run_20261027_200hz_pot_sweep.csv", 3); a, b = split(v, 0.5); th = [1024, 2048, 3072]
    band = lambda x: sum(x >= t for t in th); by = {c: [x for x in a if band(x) == c] for c in range(4)}
    train = [(pad(therm(r.choice(by[c]), th)), c) for c in range(4) for _ in range(16)]; r.shuffle(train)
    m = bank(train, 4); test = [(pad(therm(x, th)), band(x)) for x in b]
    return acc(m, test)
def therm_bank(seed):
    r = random.Random(seed); th = [1850, 1990]; band = lambda x: sum(x >= t for t in th)
    f = E.load("esp_run_20261027_200hz_thermistor_finger.csv", 5); c2 = E.load("esp_run_20261027_200hz_thermistor_run2.csv", 5)
    ff, fe = split(f, 0.5); ref = M.centred_median(f); reft = ref[len(ff):]
    pool = [(x, band(x)) for x in M.causal_median(ff, 9)] + [(x, band(x)) for x in M.causal_median(c2, 9)]
    by = {c: [x for x, y in pool if y == c] for c in range(3)}
    train = [(pad(therm(r.choice(by[c]), th)), c) for c in range(3) for _ in range(16) if by[c]]; r.shuffle(train)
    m = bank(train, 3); res = {}
    for name, xs in (("raw", fe), ("median9", M.causal_median(f, 9)[len(ff):])):
        res[name] = acc(m, [(pad(therm(x, th)), band(rf)) for x, rf in zip(xs, reft)])
    return res, {c: len(by[c]) for c in by}
def ir_keys(repeats):
    """codes of the decoded data frames; with repeats=True each press counts 1 + its repeat frames (a held key re-presents the same word every 108 ms)"""
    ps = IR.presses(IR.decode(IR.load(os.path.join(DATA, "esp_run_20261027_ir_all_keys_edges.csv"))))
    return [q["bytes"][2] for q in ps if q["kind"] == "data" for _ in range(1 + (q["repeats"] if repeats else 0))]
def spread_words(n, nb=18, seed=1):
    """n code words of nb bits chosen greedily to keep the smallest Hamming distance between any two as large as possible (random candidates, 400 per step)"""
    r = random.Random(seed); words = [r.getrandbits(nb)]
    while len(words) < n:
        c = [r.getrandbits(nb) for _ in range(400)]; words.append(max(c, key=lambda w: min(bin(w ^ x).count("1") for x in words)))
    return words
def ir_bank(seed, p, wires, repeats=True):
    r = random.Random(seed); table = [0x45, 0x46, 0x47, 0x44, 0x40, 0x43, 0x07, 0x15, 0x09, 0x16, 0x19, 0x0D, 0x0C, 0x18, 0x5E, 0x08, 0x1C, 0x5A, 0x42, 0x52, 0x4A]
    seen = ir_keys(repeats); idx = {c: i for i, c in enumerate(table)}
    words = spread_words(21)
    def bits(c):
        if wires == 18: w = words[idx[c]]; return [(w >> j) & 1 for j in range(18)]
        b = [(c >> j) & 1 for j in range(8)]; return b + [1 - x for x in b] if wires == 16 else b
    train = [(pad(bits(c)), idx[c]) for c in seen if c in idx]; r.shuffle(train)
    m = bank(train, 21); test = []
    for c in table:
        for _ in range(40): test.append((pad([x ^ (1 if r.random() < p else 0) for x in bits(c)]), idx[c]))
    return acc(m, test), len(train)
def main():
    print("LAYER 1 from the recorded data (10 seeds where a pool is drawn)\n")
    r = [light_bank(s) for s in range(10)]; print("light  (3 states, 3 thresholds from gaps %s): held-out accuracy %.3f" % ([round(t) for t in r[0][1]], st.mean(a for a, _ in r)))
    r = [pot_bank(s) for s in range(10)]; print("pot    (4 bands, thermometer at band edges): trained on sweep 1, tested on sweep 2: accuracy %.3f" % st.mean(r))
    r = [therm_bank(s) for s in range(10)]; print("thermistor (3 bands, edges 1850 and 1990), test = second half of the finger run: raw %.3f, with 9-sample median %.3f (training pool sizes per band %s)" % (st.mean(x[0]["raw"] for x in r), st.mean(x[0]["median9"] for x in r), r[0][1]))
    for rep in (False, True):
        print("\nir     (21 keys; training = %d samples: %s) accuracy against bit-flip probability per wire:" % (ir_bank(0, 0, 8, rep)[1], "the decoded data frames only" if not rep else "each press counted with its repeat frames"))
        print("  p      |  8 wires (command)  | 16 wires (command + inverse) | 18 wires (spread code words)")
        for p in (0.0, 0.02, 0.05, 0.1, 0.2):
            a8 = st.mean(ir_bank(s, p, 8, rep)[0] for s in range(10)); a16 = st.mean(ir_bank(s, p, 16, rep)[0] for s in range(10)); a18 = st.mean(ir_bank(s, p, 18, rep)[0] for s in range(10)); print("  %.2f   |       %.3f         |       %.3f                | %.3f" % (p, a8, a16, a18))
    t = [0x45, 0x46, 0x47, 0x44, 0x40, 0x43, 0x07, 0x15, 0x09, 0x16, 0x19, 0x0D, 0x0C, 0x18, 0x5E, 0x08, 0x1C, 0x5A, 0x42, 0x52, 0x4A]
    dd = sorted(bin(a ^ b).count("1") for i, a in enumerate(t) for b in t[:i]); print("\nsmallest Hamming distance between two key codes: 8 wires %d (%d pairs that close), 16 wires %d" % (dd[0], dd.count(dd[0]), 2 * dd[0]))
    w = spread_words(21); print("spread 18-bit code words: smallest distance %d" % min(bin(a ^ b).count("1") for i, a in enumerate(w) for b in w[:i]))
if __name__ == "__main__": main()
