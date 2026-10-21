"""Hex-N two-round design v1 (new file).  Alan, 21 Oct 2026: train the detector bank first (round 1), FREEZE it, then train only a second stage on top (round 2); if the noise is too high the second stage is turned OFF, giving a variable-level setup.
Round 1 = exactly hexn_bank_v2 (4 summing cells, all 12 wires each, W=2 for the bank alone, 1,000 tries, same seeds): the result reproduces the bank's numbers.  Round 2 = 4 second-stage summing cells (one per class); face j of stage-2 cell k hears detector j's output face, lane for lane, as in
hexn_comb_v1 (W=4); searched alone (best of 100 random starts, then keep-or-undo to 1,000 tries) with the bank frozen.  Because the frozen detectors do not depend on stage 2, their output over time is worked out once per sample and replayed (a self-test checks this equals the full simulation).
Three answers are reported per seed on 200 fresh test samples: BANK (stage 2 off: the answer is the detector with most clocks), STAGE2 (stage 2 on), SWITCH (stage 2 on only if it scores strictly better than the bank on the TRAINING samples, else off: the automatic on/off setting).
Files: --out PREFIX writes PREFIX_bank.txt, PREFIX_stage2.txt, PREFIX_switch.txt (lines 'seed value template-rule', for hexn_ladder_compare_v1.py).  Usage: python3 tools/hexn_two_v1.py --out /tmp/x [--noise Q] [--first S] [--runs N] [--tries T]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
b2, c1 = load("hexn_bank_v2"), load("hexn_comb_v1")
b2.CELL = "sum"; b2.SEE = "all"; b2.WIRES = [b2.wires(k) for k in range(4)]
c1.CELL = "sum"; c1.SEE = "all"; c1.WIRES = [c1.wires(k) for k in range(4)]
mc, c15, v6, v12 = b2.mc, b2.c15, b2.v6, b2.v12
K, N, P, PL, W2 = 4, mc.N, mc.P, b2.PL, 4


def det_trace(dcfgs, bits):
    """Detector output lanes (12..15 of each detector) at every clock of a W2-window run, one list per clock."""
    cells = [mc.MixCell(*c) for c in dcfgs]; tr = []
    for w in range(W2):
        for phase in (0, 1):
            for t in range(PL):
                tx = [c.tx(phase) for c in cells]; tr.append([[tx[j][12 + p] for p in range(P)] for j in range(K)])
                rx = [0] * N
                for j in range(b2.NB): rx[j] = bits[j]
                for c in cells: c.clock(rx, phase, int(t == 0), int(phase == 1 and t == PL - 1))
    return tr


def stage2_counts(scfgs, tr):
    cells = [mc.MixCell(*c) for c in scfgs]; cnt = [0] * K; i = 0
    for w in range(W2):
        for phase in (0, 1):
            for t in range(PL):
                tx = [c.tx(phase) for c in cells]
                if w == W2 - 1:
                    for k in range(K): cnt[k] += sum(tx[k][16 + p] for p in range(P))
                rx = [0] * N
                for j in range(K):
                    for p in range(P): rx[j * P + p] = tr[i][j][p]
                for c in cells: c.clock(rx, phase, int(t == 0), int(phase == 1 and t == PL - 1))
                i += 1
    return cnt


def right(x, y): return max(x) > 0 and x.count(max(x)) == 1 and x.index(max(x)) == y


def s2_rewards(scfgs, traces, data, bits=4):
    g = [stage2_counts(scfgs, tr) for tr in traces]; top = (1 << bits) - 1; tot = 0
    for k in range(K):
        pos = [x for (_, y), x in zip(data, g) if y == k]; neg = [x for (_, y), x in zip(data, g) if y != k]
        tp = sum(x[k] > 0 for x in pos); tn = sum(not x[k] > 0 for x in neg); fired = tp + (len(neg) - tn)
        if fired in (0, len(data)): continue
        tot += round(top * (tp / len(pos) + tn / len(neg)) / 2)
    return tot + round(top * sum(right(x, y) for (_, y), x in zip(data, g)) / len(data))


def one(seed, q, tries, S, warm=100):
    rnd = random.Random(seed); tpl = v12.make_templates(rnd, K)
    train = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(S)]
    test = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(50)]
    sh = random.Random(seed + 5); sh.shuffle(train); sh.shuffle(test); lf = v6.Lfsr(seed + 77)
    # round 1: the bank, exactly as hexn_bank_v2 (W=2)
    best = None; br = -1
    for _ in range(warm):
        c = [b2.new_cfg(lf) for _ in range(K)]; r = b2.rewards(c, train, 2)
        if r > br: best, br = c, r
    cur, cr = best, br
    for _ in range(tries - warm):
        nxt = list(cur)
        for _ in range(1 + lf.randrange(3)):
            j = lf.randrange(K); nxt[j] = b2.mutate(nxt[j], lf)
        r = b2.rewards(nxt, train, 2)
        if r >= cr: cur, cr = nxt, r
    bank = cur
    bank_train = sum(right(x, y) for (_, y), x in zip(train, b2.run_all(bank, train, 2))) / len(train)
    bank_test = b2.accuracy(bank, test, 2)
    # round 2: stage 2 on the frozen bank (detector traces replayed)
    tr_train = [det_trace(bank, b) for b, _ in train]; tr_test = [det_trace(bank, b) for b, _ in test]
    best = None; br = -1
    for _ in range(warm):
        c = [b2.new_cfg(lf) for _ in range(K)]; r = s2_rewards(c, tr_train, train)
        if r > br: best, br = c, r
    cur, cr = best, br
    for _ in range(tries - warm):
        nxt = list(cur)
        for _ in range(1 + lf.randrange(3)):
            j = lf.randrange(K); nxt[j] = b2.mutate(nxt[j], lf)
        r = s2_rewards(nxt, tr_train, train)
        if r >= cr: cur, cr = nxt, r
    s2_train = sum(right(stage2_counts(cur, tr), y) for tr, (_, y) in zip(tr_train, train)) / len(train)
    s2_test = sum(right(stage2_counts(cur, tr), y) for tr, (_, y) in zip(tr_test, test)) / len(test)
    on = s2_train > bank_train
    return bank_test, s2_test, (s2_test if on else bank_test), on, v12.template_rule(tpl, test)


def selftest():
    r = random.Random(5); tpl = v12.make_templates(r, K); bits = v12.sample(r, tpl[0], 0.15); lf = v6.Lfsr(9)
    d = [b2.new_cfg(lf) for _ in range(K)]; s = [b2.new_cfg(lf) for _ in range(K)]
    full = c1.counts([mc.MixCell(*c) for c in d + s], bits, W2); cached = stage2_counts(s, det_trace(d, bits))
    assert full == cached, (full, cached)
    return full


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--noise", type=float, default=0.15)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); ap.add_argument("--tries", type=int, default=1000); ap.add_argument("--per-class", type=int, default=16)
    a = ap.parse_args(); print("self-test (cached replay equals full simulation):", selftest(), flush=True)
    fs = {n: open(f"{a.out}_{n}.txt", "a") for n in ("bank", "stage2", "switch")}; ons = 0
    for s in range(a.first, a.first + a.runs):
        b, t2, sw, on, tr = one(s, a.noise, a.tries, a.per_class); ons += on
        for n, v in (("bank", b), ("stage2", t2), ("switch", sw)): fs[n].write(f"{s:>4} {v:>8.2f} {tr:>13.2f}\n"); fs[n].flush()
        print(f"seed {s}: bank {b:.2f}  stage2 {t2:.2f}  switch {sw:.2f} ({'on' if on else 'off'})", flush=True)
    print(f"stage 2 switched on in {ons} of {a.runs} seeds")
