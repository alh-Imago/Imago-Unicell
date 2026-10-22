"""Model-level question for the multi-cell step: do the forward totals of NC cells (random lane settings) behind the glue buffer keep the class information the detectors found? Uses the trained model of a script (tools/hexn_tang_script_v1.py) and the clock-by-clock cell model (tools/hexn_cellbank_check_v1.py). No RTL. Nearest-centroid classifier on the cells' totals (centroids from noisy copies of the TRAINING samples), tested on noisy copies of the test samples; compared with the detectors' own answer. Usage: python3 tools/hexn_cells_separability_v1.py SCRIPT [NOISE] [SEEDS]"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_script_v1 as S1, hexn_cellbank_check_v1 as C1
d = S1.parse_script(open(sys.argv[1]).read()); noise = float(sys.argv[2]) if len(sys.argv) > 2 else 0.2; seeds = int(sys.argv[3]) if len(sys.argv) > 3 else 5
K = d["classes"]; m = S1.make_model(d, 16)
base = {}
for bits, y in d["train"] + d["test"]: base.setdefault(y, []).append(bits)
def noisy(r, b): return [x ^ (1 if r.random() < noise else 0) for x in b]
def feats(cells, lens): return [C1.cell_model(K, lens, cfg, 0)[0] for cfg in cells]
print("script %s, %d classes, input noise %.2f" % (os.path.basename(sys.argv[1]), K, noise))
print("cells | detectors-only answer | cell totals, nearest centroid (mean over %d random cell sets)" % seeds)
for NC in (1, 2, 3, 4, 6, 8, 12):
    accs = []; det = []
    for sd in range(seeds):
        r = random.Random(100 + sd); cells = [[r.choices([0, 1, 2], [0.3, 0.45, 0.25])[0] for _ in range(K)] for _ in range(NC)]
        cen = {}
        for y in range(K):
            fs = [feats(cells, S1.classify(m, noisy(r, b))[1]) for b in base[y] for _ in range(6)]; cen[y] = [sum(f[i] for f in fs) / len(fs) for i in range(NC)]
        ok = okd = n = 0
        for y in range(K):
            for b in base[y]:
                for _ in range(10):
                    pred, lens = S1.classify(m, noisy(r, b)); f = feats(cells, lens)
                    best = min(range(K), key=lambda c: sum((f[i] - cen[c][i]) ** 2 for i in range(NC))); ok += best == y; okd += pred == y; n += 1
        accs.append(ok / n); det.append(okd / n)
    print("%5d | %.3f | %.3f (min %.3f, max %.3f)" % (NC, sum(det) / len(det), sum(accs) / len(accs), min(accs), max(accs)))
