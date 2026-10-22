"""Model of the cell's accumulator leak (no RTL). Question: if the same scene is seen in several windows in a row (each window a fresh noisy copy), does an accumulator that keeps a decayed share of the previous window's total decide better than one that clears every window?
Setup: the trained detector bank of a script (tools/hexn_tang_script_v1.py) gives each window's burst lengths (0..7 per detector, unique-maximum rules unchanged). One accumulator per class, class g counting only detector g's burst (one lane, +1 per clock of the burst, as the full cell does), total clamped 0..2^AW-1.
At the start of each window the previous total is changed by the leak rule: clear (what hexn_cell_v2/v3 does), none (keep, saturating), sub1 / sub2 (subtract 1 or 2, floor 0), half (shift right 1), keep3q (x3/4). After n windows the answer is the class with the UNIQUE highest total (a tie counts as wrong, as for the detectors).
Usage: python3 tools/hexn_leak_model_v1.py SCRIPT [NOISE] [TRIALS_PER_CLASS]"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_script_v1 as S1
d = S1.parse_script(open(sys.argv[1]).read()); noise = float(sys.argv[2]) if len(sys.argv) > 2 else 0.2; per = int(sys.argv[3]) if len(sys.argv) > 3 else 60
K, AW = d["classes"], d["aw"]; m = S1.make_model(d, 16); top = (1 << AW) - 1
tpl = {}
for bits, y in d["train"] + d["test"]: tpl.setdefault(y, []).append(bits)
LEAK = {"clear": lambda a: 0, "none": lambda a: a, "sub1": lambda a: max(0, a - 1), "sub2": lambda a: max(0, a - 2), "half": lambda a: a >> 1, "keep3q": lambda a: (a * 3) >> 2}
NW = (1, 2, 3, 4, 6, 8)
print("script %s, %d classes, noise %.2f, %d scenes per class; share of scenes where the unique highest total is the true class after n windows" % (os.path.basename(sys.argv[1]), K, noise, per))
print("%-8s" % "leak" + "".join("  n=%d  " % n for n in NW))
res = {k: [0] * len(NW) for k in LEAK}; tot = 0
r = random.Random(7)
for y in range(K):
    for _ in range(per):
        base = r.choice(tpl[y]); frames = [S1.classify(m, [b ^ (1 if r.random() < noise else 0) for b in base])[1] for _ in range(max(NW))]; tot += 1
        for name, f in LEAK.items():
            acc = [0] * K
            for w in range(max(NW)):
                acc = [min(top, f(a) + frames[w][g]) for g, a in enumerate(acc)]
                if (w + 1) in NW:
                    mx = max(acc); res[name][NW.index(w + 1)] += (acc.count(mx) == 1 and acc[y] == mx and mx > 0)
for name in LEAK: print("%-8s" % name + "".join(" %.3f " % (v / tot) for v in res[name]))
