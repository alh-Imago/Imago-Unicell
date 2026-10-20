"""Hex-N diagnostic (new file): for models trained on clean data (v20 settings, readout score on), report per class how often it is answered right, and per output group how often it fires on each true class.
Shows WHICH classes a model misses and whether the output group for a missing class is stuck on, stuck off, or just wrong.  Usage: python3 tools/hexn_diag_v1.py [--first S] [--runs N] [--tries T] [--noise Q]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("hexn_cluster_v20", os.path.join(ROOT, "tools", "hexn_cluster_v20.py"))
v20 = importlib.util.module_from_spec(sp); sp.loader.exec_module(v20); v19 = v20.v19; c15 = v19.c15
ap = argparse.ArgumentParser(); ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=4); ap.add_argument("--tries", type=int, default=600); ap.add_argument("--noise", type=float, default=0.0)
a = ap.parse_args(); v19.FLAGS["score"] = True
for s in range(a.first, a.first + a.runs):
    topo, tpl, cur = v20.train(s, 1, a.noise, a.tries, 16, 0, 3)
    rnd = random.Random(500 + s); test = [(c15.v12.sample(rnd, tpl[y], a.noise), y) for y in range(4) for _ in range(40)]
    g = v19.run_all(topo, cur, test, 0, 3); fire = [[0] * 4 for _ in range(4)]; right = [0] * 4
    for (_, y), x in zip(test, g):
        for k in range(4): fire[y][k] += x[k] > 0
        m = max(x); right[y] += (m > 0 and x.count(m) == 1 and x.index(m) == y)
    print(f"seed {s}: right per class (of 40) {right}")
    print("   fires of output group (cols) on true class (rows):")
    for y in range(4): print("    ", y, fire[y])
