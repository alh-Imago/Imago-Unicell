"""hexn_encode_v1: how to turn the ESP32's analog readings into the bank's 18 on/off wires (Python model of the bank only; no RTL; new file; uses hexn_tang_script_v1.make_model/classify unchanged).
Data: the recordings in docs/hex-n/data (27 Oct 2026, 200 per second): light (a36) in three conditions (lamp on, light off, daylight only) and the pot (a35) from the sweep. Classes = light condition x pot zone: 3 x 2 = 6 states (pot zone low = under 1365, high = over 2730; the middle third is left out).
ASSUMPTION: the two channels were recorded separately, so a sample of a state is a light sample of that condition paired with a pot sample of that zone, drawn independently (the pot cannot change the light; true unless the wiring couples them, not checked). Pot samples are drawn evenly over 100-count bins so the long stops at 0 and 4095 do not dominate. Light values are the mean of two consecutive samples (5 ms apart: cancels the lamp flicker, see the 200 per second row of HEXN_DESIGN.md) unless 'raw' is asked for.
Codings of one 12-bit reading into B wires: gap = thermometer with thresholds in the biggest gaps between neighbouring training readings of the pooled channel (no labels; fewer than B wires are used when there are fewer gaps of 150 counts or more); therm = thermometer, bit i = value >= (i+1)*4096/(B+1); quant = thermometer with thresholds at quantiles of the training values; binary = the top B bits; gray = those bits Gray-coded. Wires: pot on wires 0..B-1, light on B..2B-1, the rest stay 0 (thermistor later).
The bank learns from 16 samples per class (training noise = what was recorded) and is tested on 40 fresh samples per class; extra noise = Gaussian counts added to each reading of the TEST samples only. Accuracy = share classified as the right class (no answer or a tie counts as wrong).
Usage: python3 tools/hexn_encode_v1.py [seeds]"""
import sys, os, csv, random, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_script_v1 as S1
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "hex-n", "data")
def load(fn, col):
    return [int(r[col]) for r in csv.reader(l for l in open(os.path.join(D, fn)) if not l.startswith("#")) if len(r) == 8 and r[0].isdigit()]
def pairs(v): return [(v[2 * k] + v[2 * k + 1]) / 2 for k in range(len(v) // 2)]
LIGHT = {"lamp": "esp_run_20261027_200hz_light_on.csv", "dark": "esp_run_20261027_200hz_light_off.csv", "day": "esp_run_20261027_200hz_daylight_only.csv"}
def sources(raw):
    light = {k: (load(f, 4) if raw and k == "lamp" else pairs(load(f, 4))) for k, f in LIGHT.items()}
    pot = load("esp_run_20261027_200hz_pot_sweep.csv", 3); zones = {"lo": [x for x in pot if x < 1365], "hi": [x for x in pot if x > 2730]}
    bins = {z: {} for z in zones}
    for z, xs in zones.items():
        for x in xs: bins[z].setdefault(x // 100, []).append(x)
    return light, bins
def draw_pot(bins, z, r): b = r.choice(list(bins[z])); return r.choice(bins[z][b])
STATES = [(l, z) for l in ("lamp", "dark", "day") for z in ("lo", "hi")]
def encode(pot, light, kind, B, q):
    out = []
    for v, ch in ((pot, 0), (light, 1)):
        if kind == "gap": bits = [int(v >= t) for t in q[ch]]
        elif kind == "therm": th = [(i + 1) * 4096 / (B + 1) for i in range(B)]; bits = [int(v >= t) for t in th]
        elif kind == "quant": bits = [int(v >= t) for t in q[ch]]
        else:
            n = min(4095, max(0, int(v))) >> (12 - B)
            if kind == "gray": n ^= n >> 1
            bits = [(n >> (B - 1 - k)) & 1 for k in range(B)]
        out += bits
    return out + [0] * (18 - len(out))
def gaps(train, B, mingap=150):
    """thresholds in the (up to) B biggest gaps of at least mingap counts between neighbouring values of the POOLED training readings of each channel; no labels are used. mingap is a hand-made choice (several times the recorded noise)."""
    out = []
    for ch in (0, 1):
        v = sorted(s[ch] for s in train); g = sorted(((b - a, (a + b) / 2) for a, b in zip(v, v[1:]) if b - a >= mingap), reverse=True)[:B]
        out.append(sorted(t for _, t in g))
    return out
def quantiles(train, B):
    out = []
    for ch in (0, 1):
        v = sorted(s[ch] for s in train); out.append([v[int(len(v) * (i + 1) / (B + 1))] for i in range(B)])
    return out
def run(kind, B, sigma, raw, seed, d0, light, bins, ntr=16, nte=40):
    r = random.Random(seed)
    def make(n, noise):
        s = []
        for y, (l, z) in enumerate(STATES):
            for _ in range(n): s.append((draw_pot(bins, z, r) + (r.gauss(0, noise) if noise else 0), r.choice(light[l]) + (r.gauss(0, noise) if noise else 0), y))
        return s
    tr = make(ntr, 0); te = make(nte, sigma); q = quantiles(tr, B) if kind == "quant" else gaps(tr, B) if kind == "gap" else None; r.shuffle(tr)
    d = dict(d0); d["classes"] = len(STATES); d["wires"] = 18
    d["train"] = [(encode(p, l, kind, B, q), y) for p, l, y in tr]; d["test"] = []
    m = S1.make_model(d, 16)
    return sum(S1.classify(m, encode(p, l, kind, B, q))[0] == y for p, l, y in te) / len(te)
def main():
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    d0 = S1.parse_script(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "hex-n", "frontend", "example_sensors_script_v1.txt")).read())
    light, bins = sources(False); lraw, _ = sources(True)
    print("6 states (3 light x 2 pot zones), %d seeds; accuracy on fresh test samples; added test noise sigma in counts\n" % seeds)
    print("coding   B |  sigma 0   50  100   150   300   600")
    for kind in ("gap", "therm", "quant", "gray", "binary"):
        for B in ((2, 4, 9) if kind == "gap" else (2, 3, 4, 6, 8, 9)):
            row = [st.mean(run(kind, B, s, False, sd, d0, light, bins) for sd in range(seeds)) for s in (0, 50, 100, 150, 300, 600)]
            print("%-7s %2d |        " % (kind, B) + "  ".join("%.2f" % x for x in row))
    print("\nlamp light WITHOUT pair averaging (raw samples), therm:")
    for B in (4, 9):
        row = [st.mean(run("therm", B, s, True, sd, d0, lraw, bins) for sd in range(seeds)) for s in (0, 50, 100, 150, 300, 600)]
        print("therm   %2d raw |    " % B + "  ".join("%.2f" % x for x in row))
if __name__ == "__main__": main()
