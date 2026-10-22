"""Familiarity / novelty / deviation check on the counted detector bank (model only, no RTL; Alan, 22 Oct: 'have I seen this before, even partially, and how well does the stored pattern fit or deviate').
For the trained bank of a script: (1) FAMILIAR: a sample with noise q from a stored class: share where some detector fires (largest burst > 0); (2) NOVEL: a RANDOM 18-wire pattern never trained: share where some detector fires anyway (false familiarity); (3) FIT: the winner's burst length (0..7) against the true number of wires that differ from the stored template (Hamming distance, template = the training class centre = majority of the class's training samples). Prints a table by distance and by noise, and the novelty threshold trade-off (call it 'familiar' if the largest burst >= b).
Usage: python3 tools/hexn_familiar_model_v1.py SCRIPT"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_script_v1 as S1
d = S1.parse_script(open(sys.argv[1]).read()); K, NB = d["classes"], d["wires"]; m = S1.make_model(d, 16); r = random.Random(3)
cls = {}
for bits, y in d["train"]: cls.setdefault(y, []).append(bits)
cen = {y: [1 if 2 * sum(b[j] for b in cls[y]) > len(cls[y]) else 0 for j in range(NB)] for y in cls}
def burst(bits):
    pred, lens = S1.classify(m, bits); return pred, max(lens), lens
print("script %s: %d classes, %d wires" % (os.path.basename(sys.argv[1]), K, NB)); T = 400
print("noise | familiar (largest burst >= 1 / >= 2 / >= 3) | right class among those >= 1")
for q in (0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4):
    f = [0, 0, 0]; right = fired = 0
    for _ in range(T):
        y = r.randrange(K); b = [x ^ (1 if r.random() < q else 0) for x in cen[y]]; pred, mx, _l = burst(b)
        for i in range(3): f[i] += mx >= i + 1
        if mx >= 1: fired += 1; right += pred == y
    print("%5.2f | %.3f / %.3f / %.3f | %s" % (q, f[0] / T, f[1] / T, f[2] / T, ("%.3f" % (right / fired)) if fired else "-"))
f = [0, 0, 0]
for _ in range(2000):
    b = [r.randrange(2) for _ in range(NB)]; mx = burst(b)[1]
    for i in range(3): f[i] += mx >= i + 1
print("NOVEL (random 18-wire patterns, never trained), 2000 tried: false familiar at burst >= 1 / >= 2 / >= 3: %.3f / %.3f / %.3f" % tuple(x / 2000 for x in f))
print("FIT: mean winner burst by the number of wires that differ from the stored centre (cue = centre with exactly that many wires flipped, %d tries each)" % 200)
for h in (0, 1, 2, 3, 4, 5, 6, 8):
    s = n = 0
    for _ in range(200):
        y = r.randrange(K); b = list(cen[y])
        for j in r.sample(range(NB), h): b[j] ^= 1
        pred, mx, _l = burst(b); s += mx; n += 1
    print("  %d wires differ: mean largest burst %.2f" % (h, s / n))
