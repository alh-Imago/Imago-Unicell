"""CONCEPT-LEVEL model of feedback roles on top of the leaky class accumulators (no RTL, not gate-accurate to the cell's feedback phase). Same scenes as tools/hexn_leak_model_v2.py (scene A for 8 windows, then scene B for 8 windows; also the static case = A only), leak a - (a >> 2).
Rules per window, acc = leak(acc) first, then:
  base      acc_g += len_g                                  (what hexn_cell_v4 does)
  wta1/wta2 acc_g += len_g - (max over other classes of len_h) >> s   (s = 1, 2; floor 0): competition, every class is told how strongly the best rival fired
  belief1/2 acc_g += len_g, and the class that led after the previous window (unique highest, > 0) gets +b (b = 1, 2): top-down reinforcement of the current belief
  wta+bel   both (s=2, b=1)
Answer = unique highest total (tie = wrong).  Usage: python3 tools/hexn_feedback_model_v1.py SCRIPT [NOISE] [SCENES_PER_CLASS]"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_script_v1 as S1
d = S1.parse_script(open(sys.argv[1]).read()); noise = float(sys.argv[2]) if len(sys.argv) > 2 else 0.15; per = int(sys.argv[3]) if len(sys.argv) > 3 else 60
K, AW = d["classes"], d["aw"]; m = S1.make_model(d, 16); top = (1 << AW) - 1; L = 8
tpl = {}
for bits, y in d["train"] + d["test"]: tpl.setdefault(y, []).append(bits)
def leak(a): return a - (a >> 2)
def lead(acc):
    mx = max(acc); return acc.index(mx) if mx > 0 and acc.count(mx) == 1 else None
def step(rule, acc, lens):
    prev = lead(acc); acc = [leak(a) for a in acc]; out = []
    for g in range(K):
        v = lens[g]
        if rule.startswith("wta") or rule == "wta+bel":
            s = {"wta1": 1, "wta2": 2, "wta+bel": 2}[rule]; v -= max(lens[h] for h in range(K) if h != g) >> s
        out.append(min(top, max(0, acc[g] + v)))
    b = {"belief1": 1, "belief2": 2, "wta+bel": 1}.get(rule, 0)
    if b and prev is not None: out[prev] = min(top, out[prev] + b)
    return out
RULES = ["base", "wta1", "wta2", "belief1", "belief2", "wta+bel"]; KS = (0, 1, 2, 4, 6, 8)
print("script %s, noise %.2f, %d scenes per class (model, leak a-(a>>2))" % (os.path.basename(sys.argv[1]), noise, per))
print("%-8s static after 1/4/8 windows | switch: last window of A, then k=1,2,4,6,8 after the switch" % "rule")
r = random.Random(5); eps = []
for ya in range(K):
    for _ in range(per):
        yb = r.choice([c for c in range(K) if c != ya]); ba = r.choice(tpl[ya]); bb = r.choice(tpl[yb]); eps.append((ya, yb, [S1.classify(m, [b ^ (1 if r.random() < noise else 0) for b in (ba if w < L else bb)])[1] for w in range(2 * L)]))
for rule in RULES:
    st = [0, 0, 0]; sw = [0] * len(KS)
    for ya, yb, fr in eps:
        acc = [0] * K
        for w in range(2 * L):
            acc = step(rule, acc, fr[w]); k = w + 1 - L; mx = max(acc); uniq = acc.count(mx) == 1 and mx > 0
            if w + 1 in (1, 4, 8): st[(1, 4, 8).index(w + 1)] += uniq and acc[ya] == mx
            if k in KS: sw[KS.index(k)] += uniq and acc[ya if k == 0 else yb] == mx
    n = len(eps); print("%-8s %.3f %.3f %.3f | " % (rule, *[x / n for x in st]) + " ".join("%.3f" % (x / n) for x in sw))
