"""Hex-N detector bank v5 (new file; VM model only).  Alan, 21 Oct 2026: 'the multiple detectors seems to be the key'.
BANK = 4 independent cells, one per class; EVERY cell receives all 12 input wires (lanes 0..11 = faces 0,1,2) directly, with NO routing between cells; cell k's answer is the burst count on its own
output face (face 3, lanes 12..15) in the last window; the answer is the cell with strictly the most clocks (tie/silence wrong).  Same task, data, noise, search and reward as the 4-class cluster
(v21: best of 100 random starts, keep-or-undo, 1-3 changes per try, keep if >=, gated per-class reward + readout score), same seeds, so results compare with the cluster's 0.451 at 1,000 tries.
Arms: --cell sum (the v2 summing cell, hexn_cell_v2_model.MixCell) | table (the v3 decision-table cell, 64 rows).  W=2 windows (independent cells need no relay time).
NEW IN v5 (new file, clone of v4): --lanes weight. Alan, 21 Oct 2026: the hand-set bank reaches 0.859, the trained bank plateaus at 0.75, so the SEARCH is the limit. Trained detectors were using only 4-7 of 12 input lanes. In v2-v4 a lane move picked a random direction or gate code, which mostly breaks a lane (a receiving lane needs direction 0 and code 1 or 3). With --lanes weight the 12 INPUT lanes (0..11) are always receive-only (direction 0) and each has a 3-state WEIGHT: off, +1 (code 1), -1 (code 3); a mutation sets one input lane to a random weight (3 of 5 moves), steps the threshold (1 of 5, as v4's --thr-max/--thr-steps) or changes one OUTPUT-side lane 12..23 the old way (1 of 5: active flip, direction or code). The start (best of 100 random cells) uses random weights on the input lanes (a third each). This is the weight representation of a neuron (+, -, off), not a hard-wired path: the weights are still found by the search. Defaults (--lanes old) are v4 exactly.
NEW IN v4 (new file, clone of v3): --thr-max T and --thr-steps S for the SUMMING cell. Measured 21 Oct: each agreeing lane adds about 10 to the forward total (1 per clock x 10 clocks; accumulator cap 63) but v2/v3 only let the search set threshold 0..7 (+ bias 0..3), so a detector could only ask "did at least one lane agree?". v4 allows threshold 0..T (default 7 = v3 exactly) and threshold steps chosen from S (default "1" = +-1; "1,10" also allows +-10, one lane unit). Nothing else changes.
NEW IN v3 (new file, clone of v2): --dets M = M detectors PER CLASS (4M cells in all); the class score is the SUM of the burst counts on face 3 of its M detectors; every detector still sees all 12 wires; the search (keep-or-undo, 1-3 changes per try) picks among all 4M cells; reward unchanged (gated per-class + readout) on the class scores. M=1 is v2 exactly.
NEW IN v2: --see limits which of the 12 input wires each detector receives (fan-out cost): all (v1) | faces2 (detector k gets the 8 wires of faces k%3 and (k+1)%3) | face1 (detector k gets the 4 wires of face k%3; detector 3 repeats face 0) | half (detector k gets 6 wires: k even = wires 0,2,4..; k odd = wires 1,3,5.. of 12 -> every other wire).
Usage: python3 tools/hexn_bank_v5.py --cell table [--first S] [--runs N] [--tries T] [--W w]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
c15, m3, tri, v21 = load("hexn_cluster_v15"), load("hexn_cell_v3_model"), load("hexn_tri_v1"), load("hexn_cluster_v21")
v6, v12, mc = c15.v6, c15.v12, c15.mc
K, N, P, PL, NB = 4, mc.N, mc.P, c15.PL, c15.NB
CELL = "table"; SEE = "all"; M = 1; THR_MAX = 7; THR_STEPS = [1]; LANES = "old"


def wires(k):
    if SEE == "faces2": return [j for j in range(NB) if j // P in (k % 3, (k + 1) % 3)]
    if SEE == "face1": return [j for j in range(NB) if j // P == k % 3]
    if SEE == "half": return [j for j in range(NB) if j % 2 == k % 2]
    return list(range(NB))


def weight_lane(a, d, c, j, r):
    w = r.randrange(3); d[j] = 0
    if w == 0: a[j] = 0
    else: a[j] = 1; c[j] = 1 if w == 1 else 3


def new_cfg(r):
    if CELL == "sum" and LANES == "weight":
        a, d, c, t, bb = c15.easy(r); a, d, c = list(a), list(d), list(c)
        for j in range(NB): weight_lane(a, d, c, j, r)
        return (a, d, c, t, bb)
    if CELL == "sum": return c15.easy(r)
    a, d, t = tri.new_cfg(tri.Net("hex"), r); return (a, d, t)


def mutate(cfg, r):
    if CELL == "sum" and LANES == "weight":
        a, d, c, t, bb = [list(x) if isinstance(x, list) else x for x in cfg]; k = r.randrange(5)
        if k < 3: weight_lane(a, d, c, r.randrange(NB), r)
        elif k == 3: st = THR_STEPS[r.randrange(len(THR_STEPS))]; t[0] = max(0, min(THR_MAX, t[0] + (st if r.randrange(2) else -st)))
        else:
            i = NB + r.randrange(N - NB); m = r.randrange(3)
            if m == 0: a[i] ^= 1
            elif m == 1: d[i] = r.randint(0, 3)
            else: c[i] = r.randint(0, 3)
        return (a, d, c, t, bb)
    if CELL == "sum" and (THR_MAX != 7 or THR_STEPS != [1]):
        a, d, c, t, b = [list(x) if isinstance(x, list) else x for x in cfg]; k = r.randrange(5)
        if k == 0: i = r.randrange(N); a[i] ^= 1
        elif k == 1: i = r.randrange(N); d[i] = r.randint(0, 3)
        elif k == 2: i = r.randrange(N); c[i] = r.randint(0, 3)
        elif k == 3: st = THR_STEPS[r.randrange(len(THR_STEPS))]; t[0] = max(0, min(THR_MAX, t[0] + (st if r.randrange(2) else -st)))
        else: b = max(0, min(3, b + r.choice([-1, 1])))
        return (a, d, c, t, b)
    if CELL == "sum": return c15.mutate(cfg, r)
    return tri.mutate(tri.Net("hex"), cfg, r)


def make(cfg): return mc.MixCell(*cfg) if CELL == "sum" else tri.Cell(6, *cfg)


def counts(cells, bits, W):
    cnt = [0] * K
    for w in range(W):
        for phase in (0, 1):
            for t in range(PL):
                tx = [c.tx(phase) for c in cells]
                if w == W - 1:
                    for i in range(len(cells)): cnt[i // M] += sum(tx[i][12 + p] for p in range(P))
                for k, c in enumerate(cells):
                    rx = [0] * N
                    for j in WIRES[k % K]: rx[j] = bits[j]
                    c.clock(rx, phase, int(t == 0), int(phase == 1 and t == PL - 1))
    return cnt


def run_all(cfgs, data, W): return [counts([make(c) for c in cfgs], bits, W) for bits, y in data]


def rewards(cfgs, data, W, bits=4):
    g = run_all(cfgs, data, W); top = (1 << bits) - 1; tot = 0
    for k in range(K):
        pos = [x for (_, y), x in zip(data, g) if y == k]; neg = [x for (_, y), x in zip(data, g) if y != k]
        tp = sum(x[k] > 0 for x in pos); tn = sum(not x[k] > 0 for x in neg); fired = tp + (len(neg) - tn)
        if fired in (0, len(data)): continue
        tot += round(top * (tp / len(pos) + tn / len(neg)) / 2)
    ok = sum((max(x) > 0 and x.count(max(x)) == 1 and x.index(max(x)) == y) for (_, y), x in zip(data, g))
    return tot + round(top * ok / len(data))


def accuracy(cfgs, data, W):
    g = run_all(cfgs, data, W)
    return sum((max(x) > 0 and x.count(max(x)) == 1 and x.index(max(x)) == y) for (_, y), x in zip(data, g)) / len(data)


def one(seed, q, tries, S, W, warm=100):
    rnd = random.Random(seed); tpl = v12.make_templates(rnd, K)
    train = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(S)]
    test = [(v12.sample(rnd, tpl[y], q), y) for y in range(K) for _ in range(50)]
    sh = random.Random(seed + 5); sh.shuffle(train); sh.shuffle(test); lf = v6.Lfsr(seed + 77); best = None; br = -1
    for _ in range(warm):
        c = [new_cfg(lf) for _ in range(K * M)]; r = rewards(c, train, W)
        if r > br: best, br = c, r
    cur, cr = best, br
    for _ in range(tries - warm):
        nxt = list(cur)
        for _ in range(1 + lf.randrange(3)):
            j = lf.randrange(K * M); nxt[j] = mutate(nxt[j], lf)
        r = rewards(nxt, train, W)
        if r >= cr: cur, cr = nxt, r
    return accuracy(cur, test, W), v12.template_rule(tpl, test)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--cell", default="table"); ap.add_argument("--see", default="all"); ap.add_argument("--dets", type=int, default=1); ap.add_argument("--thr-max", type=int, default=7); ap.add_argument("--lanes", default="old"); ap.add_argument("--thr-steps", default="1"); ap.add_argument("--noise", type=float, default=0.15); ap.add_argument("--W", type=int, default=2)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); ap.add_argument("--tries", type=int, default=1000); ap.add_argument("--per-class", type=int, default=16)
    a = ap.parse_args(); CELL = a.cell; SEE = a.see; M = a.dets; THR_MAX = a.thr_max; LANES = a.lanes; THR_STEPS = [int(x) for x in a.thr_steps.split(",")]; WIRES = [wires(k) for k in range(K)]
    print(f"hex-n detector bank v1: cell {a.cell}, sees {a.see}, {a.dets} detector(s) per class, threshold 0..{a.thr_max} steps {a.thr_steps}, lanes {a.lanes}, 4 classes (chance 0.25), W {a.W}, noise {a.noise}, {a.tries} tries")
    print(f"{'seed':>4} {'learned':>8} {'template-rule':>13}"); tot = 0
    for s in range(a.first, a.first + a.runs):
        l, t = one(s, a.noise, a.tries, a.per_class, a.W); tot += l
        print(f"{s:>4} {l:>8.2f} {t:>13.2f}", flush=True)
    print(f"mean learned {tot / a.runs:.2f}")
