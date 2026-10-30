"""Hex-N counted detector vs SIMPLE TRAINED CLASSIFIERS, PYTHON MODEL ONLY (new file, 30 Oct 2026; no RTL, nothing on a card).
Alan, 30 Oct 22:14: 'start with the baseline' = the missing comparison of layer 1 (the counted detector) against a simple trained
classifier on the same samples. Same data for every arm (random binary patterns, minimum pattern distance 4, wires flipped with
probability q, S training samples per class, 100 fresh test samples per class, 25 seeds). A tie or silence counts as WRONG for every arm.
Arms: detector = the counted detector bank of tools/hexn_ring_v1.py (AW 7); tmpl = per-class majority-vote template, nearest by
Hamming distance; nbayes = Bernoulli naive Bayes (Laplace +1, log-likelihood); knn1 = nearest single training sample (Hamming);
rule = nearest TRUE template (the data's own ceiling, uses information no trainer has)."""
import argparse, importlib.util, math, os, random, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("ring", os.path.join(ROOT, "tools", "hexn_ring_v1.py")); R = importlib.util.module_from_spec(sp); sp.loader.exec_module(R)
R.AW = 7

def uniq_min(d):
    m = min(d); return d.index(m) if d.count(m) == 1 else -1
def uniq_max(d):
    m = max(d); return d.index(m) if d.count(m) == 1 else -1

def one(seed, K, nb, q, S, D=4, per_test=100):
    rnd = random.Random(seed); tpl = R.templates(rnd, K, nb, D)
    tr = [(R.sample(rnd, tpl[c], q), c) for c in range(K) for _ in range(S)]; random.Random(seed + 5).shuffle(tr)
    te = [(R.sample(rnd, tpl[c], q), c) for c in range(K) for _ in range(per_test)]
    X = [x for x, _ in tr]; y = [c for _, c in tr]; res = {}
    m = R.train_bank(X, y, K, R.AW, S); res["detector"] = sum(R.answer(R.bursts(m, x)) == c for x, c in te) / len(te)
    mean = [[sum(x[j] for x, c in tr if c == k) / S for j in range(nb)] for k in range(K)]
    tm = [[1 if v >= 0.5 else 0 for v in row] for row in mean]
    res["tmpl"] = sum(uniq_min([sum(a != b for a, b in zip(x, tm[k])) for k in range(K)]) == c for x, c in te) / len(te)
    lp = [[math.log((sum(x[j] for x, c in tr if c == k) + 1) / (S + 2)) for j in range(nb)] for k in range(K)]
    ln = [[math.log(1 - (sum(x[j] for x, c in tr if c == k) + 1) / (S + 2)) for j in range(nb)] for k in range(K)]
    res["nbayes"] = sum(uniq_max([sum(lp[k][j] if x[j] else ln[k][j] for j in range(nb)) for k in range(K)]) == c for x, c in te) / len(te)
    def knn(x):
        d = [sum(a != b for a, b in zip(x, t)) for t, _ in tr]; i = uniq_min(d); return y[i] if i >= 0 else -1
    res["knn1"] = sum(knn(x) == c for x, c in te) / len(te)
    res["rule"] = sum(uniq_min([sum(a != b for a, b in zip(x, tpl[k])) for k in range(K)]) == c for x, c in te) / len(te)
    return res

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=25); a = ap.parse_args()
    arms = ("detector", "tmpl", "nbayes", "knn1", "rule")
    print(f"{a.seeds} seeds, 100 test samples per class; mean accuracy; in brackets: paired difference arm minus detector (mean, wins/losses over seeds)")
    print("K  wires noise S/class | " + " | ".join(f"{x:^22s}" for x in arms))
    for K, nb in ((4, 12), (8, 18), (16, 18)):
        for q in (0.15, 0.25):
            for S in (16, 4, 2):
                rs = [one(s, K, nb, q, S) for s in range(a.seeds)]; line = []
                for arm in arms:
                    mu = st.mean(r[arm] for r in rs)
                    if arm == "detector": line.append(f"{mu:.3f}".center(22))
                    else:
                        d = [r[arm] - r["detector"] for r in rs]; line.append(f"{mu:.3f} ({st.mean(d):+.3f}, {sum(v>0.005 for v in d)}/{sum(v<-0.005 for v in d)})".center(22))
                print(f"{K:<2d} {nb:<5d} {q:<5} {S:<7d} | " + " | ".join(line), flush=True)
