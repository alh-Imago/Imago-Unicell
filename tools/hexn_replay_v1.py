"""hexn_replay_v1: REPLAY of the three recorded sensor data sets (light, pot, thermistor) through the layer-1 banks IN TIME ORDER, sample by sample (Python model only; no RTL; new file; reuses hexn_layer1_v1 banks' rules, hexn_encode_v1, hexn_medfilt_v1 unchanged).
Each bank is trained once (seed 0, 16 samples per class, as in hexn_layer1_v1) on the first part of the data, then the whole stream is replayed. Reported per stream: samples, share right on the held-out part, share 'no answer or tie', output CHANGES against the changes the reference label makes (a steady input should give a steady output; extra changes = chatter), and the longest run of wrong answers.
Limits: the three sensors were recorded separately, so there is no joint recording; the light files are three separate steady recordings joined end to end (no real transitions inside the data); the reference label of the thermistor is the band of its centred-median trend (hand-made edges 1850 and 1990); the pot labels are the bands of the knob reading itself, so the pot test shows consistency, not independent truth.
(Training samples are shuffled, as in hexn_layer1_v1: a first draft here left them class-ordered, which biases the saturating counters and gave pot 0.589; discarded.)
Usage: python3 tools/hexn_replay_v1.py"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer1_v1 as L, hexn_encode_v1 as E, hexn_medfilt_v1 as M, hexn_tang_script_v1 as S1
def report(name, bits, ref, ntrain, m, note=""):
    out = [S1.classify(m, b)[0] for b in bits]; n = len(out); h = range(ntrain, n)
    right = sum(out[i] == ref[i] for i in h) / len(h); none = sum(out[i] == -1 for i in h) / len(h)
    chg = sum(out[i] != out[i - 1] for i in range(1, n)); rchg = sum(ref[i] != ref[i - 1] for i in range(1, n))
    run = best = 0
    for i in h:
        run = run + 1 if out[i] != ref[i] else 0; best = max(best, run)
    print("%-11s | %5d samples (held-out %5d) | right %.3f | no answer/tie %.3f | output changes %4d vs reference changes %3d | longest wrong run %3d samples (%.2f s) %s" % (name, n, len(h), right, none, chg, rchg, best, best / 200.0, note))
def light():
    r = random.Random(0); names = ["lamp", "dark", "day"]; src, _ = E.sources(False); tr = {k: L.split(src[k], 0.6)[0] for k in names}
    pool = sorted(r.choice(tr[k]) for k in names for _ in range(16)); v = sorted(pool)
    th = sorted(t for _, t in sorted(((b - a, (a + b) / 2) for a, b in zip(v, v[1:]) if b - a >= 400), reverse=True)[:4])
    tt = [(L.pad(L.therm(r.choice(tr[k]), th)), y) for y, k in enumerate(names) for _ in range(16)]; r.shuffle(tt); m = L.bank(tt, 3)
    bits = []; ref = []; ntr = 0
    for y, k in enumerate(names):
        a, b = L.split(src[k], 0.6); bits += [L.pad(L.therm(x, th)) for x in a]; ref += [y] * len(a)
    ntr = len(bits)
    for y, k in enumerate(names):
        a, b = L.split(src[k], 0.6); bits += [L.pad(L.therm(x, th)) for x in b]; ref += [y] * len(b)
    # time order: per file train part then held-out part; held-out evaluated as the tail block
    report("light", bits, ref, ntr, m, "(pair-averaged samples at 100/s; replayed as train parts then held-out parts)")
def pot():
    r = random.Random(0); v = E.load("esp_run_20261027_200hz_pot_sweep.csv", 3); a, b = L.split(v, 0.5); th = [1024, 2048, 3072]
    band = lambda x: sum(x >= t for t in th); by = {c: [x for x in a if band(x) == c] for c in range(4)}
    tt = [(L.pad(L.therm(r.choice(by[c]), th)), c) for c in range(4) for _ in range(16)]; r.shuffle(tt); m = L.bank(tt, 4)
    report("pot", [L.pad(L.therm(x, th)) for x in v], [band(x) for x in v], len(a), m, "(no filter)")
def therm():
    r = random.Random(0); th = [1850, 1990]; band = lambda x: sum(x >= t for t in th)
    f = E.load("esp_run_20261027_200hz_thermistor_finger.csv", 5); c2 = E.load("esp_run_20261027_200hz_thermistor_run2.csv", 5)
    ff, fe = L.split(f, 0.5); ref = M.centred_median(f)
    pool = [(x, band(x)) for x in M.causal_median(ff, 9)] + [(x, band(x)) for x in M.causal_median(c2, 9)]
    by = {c: [x for x, y in pool if y == c] for c in range(3)}
    tt = [(L.pad(L.therm(r.choice(by[c]), th)), c) for c in range(3) for _ in range(16) if by[c]]; r.shuffle(tt); m = L.bank(tt, 3)
    for nm, xs in (("therm raw", f), ("therm med9", M.causal_median(f, 9))):
        report(nm, [L.pad(L.therm(x, th)) for x in xs], [band(x) for x in ref], len(ff), m, "(reference = centred-median band)")
def main():
    print("REPLAY of the recorded data through layer 1, in time order\n"); light(); pot(); therm()
if __name__ == "__main__": main()
