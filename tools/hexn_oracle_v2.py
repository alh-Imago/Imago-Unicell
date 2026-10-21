"""Hex-N hand-set detector bank v2 (new file): the cell's OWN ceiling, no lane training.  Alan, 21 Oct 2026: is the 0.75 plateau of the trained bank a limit of the SEARCH or of the CELL?
For each class k the detector's 12 input lanes are all ACTIVE, receive-only (direction 0) and SIGNED BY THE TEMPLATE: gate code 1 (counts +1) where the class template bit is 1, code 3 (counts -1) where it is 0, so the forward total is
(agreeing ones) - (disagreeing ones) = a constant minus the Hamming distance to the template.  Lane 12 (face 3, lane 0) is the output (active, direction 1, code 1); every other lane is off.  Only the four detector THRESHOLDS are tuned,
by coordinate descent (3 passes, thresholds 0..63, bias 0) on the 64 TRAINING samples, scored by the strict-most-clocks answer; then the 200 fresh test samples are scored.  Same seeds, data, noise, W=2 and answer rule as the bank.
Hand-setting the lanes uses the true template, which a real trained cell would not have; this is an upper bound for what this cell can express, not a training result.  v2 (new file, clone of v1): adds --per-class S (training samples per class, default 16 = v1 exactly) so the ceiling can be measured with little training data (only the 4 thresholds use the training samples).
Usage: python3 tools/hexn_oracle_v2.py --out FILE [--per-class S] [--first S] [--runs N] [--noise Q]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
b = load("hexn_bank_v4"); b.CELL = "sum"; b.SEE = "all"; b.M = 1; K, N, NB = 4, b.N, b.NB; b.WIRES = [b.wires(k) for k in range(K)]
v12 = b.v12


def cfg(template, thr):
    a = [0] * N; d = [0] * N; c = [0] * N
    for j in range(NB): a[j] = 1; d[j] = 0; c[j] = 1 if template[j] else 3
    a[12] = 1; d[12] = 1; c[12] = 1
    return (a, d, c, [thr], 0)


def acc(cfgs, data, W=2):
    g = b.run_all(cfgs, data, W); return sum((max(x) > 0 and x.count(max(x)) == 1 and x.index(max(x)) == y) for (_, y), x in zip(data, g)) / len(data)


def one(seed, q, S=16, W=2):
    rnd = random.Random(seed); tpl = v12.make_templates(rnd, K)
    train = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(S)]
    test = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(50)]
    sh = random.Random(seed + 5); sh.shuffle(train); sh.shuffle(test)
    thr = [10 * max(1, round(0.7 * sum(t))) for t in tpl]; thr = [min(63, x) for x in thr]
    best = acc([cfg(tpl[k], thr[k]) for k in range(K)], train)
    for _ in range(3):
        for k in range(K):
            for t in range(64):
                trial = list(thr); trial[k] = t; r = acc([cfg(tpl[i], trial[i]) for i in range(K)], train)
                if r > best: best, thr = r, trial
    cfgs = [cfg(tpl[k], thr[k]) for k in range(K)]
    return acc(cfgs, test), best, v12.template_rule(tpl, test), thr


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--noise", type=float, default=0.15)
    ap.add_argument("--per-class", type=int, default=16); ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); a = ap.parse_args()
    for s in range(a.first, a.first + a.runs):
        t, tr, rule, thr = one(s, a.noise, a.per_class)
        with open(a.out, "a") as f: f.write(f"{s:>4} {t:>8.2f} {rule:>13.2f}\n")
        print(f"seed {s}: hand-set bank test {t:.2f} (train {tr:.2f}), template rule {rule:.2f}, thresholds {thr}", flush=True)
