"""Hex-N cluster v18 (new file): (1) a reward that gives NO credit to an output that does not vary with the input, and (2) a HOMEOSTATIC OFFSET on each cell's threshold.
Same cluster, layout, classes, noise, samples, learner and search as v16 (old 'easy' start, no pruning).
1. Reward per output group k: 0 if group k fires for every training sample or for none; otherwise the balanced accuracy 'fires exactly when the sample is class k' (0..15). Summed over the four groups.
   (v16 gave a constant output 8 of 15, which is the flat plateau the searches got stuck on.)
2. Homeostasis (Alan, 20 Oct): effective threshold = trained thr + bias + off, off in [-M, +M], floor 0.  At each window end: if the cell reached, hi += 1 and lo = 0, else lo += 1 and hi = 0;
   hi >= RUN: off += 1 (harder to fire), lo >= RUN: off -= 1 (easier); the run counter then restarts.  The offset and counters PERSIST from one sample to the next within an evaluation (start at 0 each evaluation);
   samples are shown in a fixed shuffled order.  M = 0 is the plain cell (isolates the reward change).  --fb adds a second push from the feedback total (see code).
Usage: python3 tools/hexn_cluster_v18.py [--M m] [--run r] [--gate 0|1] [--tries T] [--runs N] [--first S] [--noise Q] [--diag]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
c15 = load("hexn_cluster_v15"); mc = c15.mc; N, P, PL = c15.N, c15.P, c15.PL


class HomeoCell(mc.MixCell):
    def __init__(self, cfg, M, run, prev=None):
        super().__init__(*cfg); self.M, self.run = M, run
        self.off, self.hi, self.lo = (prev.off, prev.hi, prev.lo) if prev else (0, 0, 0)

    def clock(self, rx, phase, ph_start, win_end):
        if win_end and phase:
            base = self.thr; self.thr = max(0, base + self.off)          # effective threshold for this window end
            super().clock(rx, phase, ph_start, win_end); self.thr = base
            if self.M:
                if self.reach_r: self.hi += 1; self.lo = 0
                else: self.lo += 1; self.hi = 0
                if self.hi >= self.run: self.off = min(self.off + 1, self.M); self.hi = 0
                if self.lo >= self.run: self.off = max(self.off - 1, -self.M); self.lo = 0
        else:
            super().clock(rx, phase, ph_start, win_end)


def sample_counts(topo, cells, bits):
    nc = len(cells); counts = [0] * 4; ins = {}
    for j, (i, lane) in enumerate(topo.inputs): ins[(i, lane)] = j
    for w in range(topo.W):
        for phase in (0, 1):
            for t in range(PL):
                tx = [c.tx(phase) for c in cells]
                if w == topo.W - 1:
                    for g in range(4): counts[g] += sum(tx[i][lane] for (i, lane) in topo.outputs[g])
                for i, c in enumerate(cells):
                    rx = [0] * N
                    for f in range(6):
                        nb = topo.nbr[i][f]
                        if nb is not None:
                            src = tx[nb]; o = ((f + 3) % 6) * P
                            for p in range(P): rx[f * P + p] = src[o + p]
                    for (ii, lane), j in ins.items():
                        if ii == i: rx[lane] = bits[j]
                    c.clock(rx, phase, int(t == 0), int(phase == 1 and t == PL - 1))
    return counts


def run_all(topo, cfgs, data, M, run):
    """Counts per sample, in data order; offsets persist from sample to sample."""
    prev = None; out = []
    for bits, y in data:
        cells = [HomeoCell(cfgs[i], M, run, prev[i] if prev else None) for i in range(len(cfgs))]
        out.append(sample_counts(topo, cells, bits)); prev = cells
    return out


def rewards(topo, cfgs, data, M, run, gate, bits=4):
    g = run_all(topo, cfgs, data, M, run); top = (1 << bits) - 1; tot = 0
    for k in range(4):
        pos = [x for (_, y), x in zip(data, g) if y == k]; neg = [x for (_, y), x in zip(data, g) if y != k]
        tp = sum(x[k] > 0 for x in pos); tn = sum(not x[k] > 0 for x in neg)
        fired = tp + (len(neg) - tn)
        if gate and fired in (0, len(data)): continue
        tot += round(top * (tp / len(pos) + tn / len(neg)) / 2)
    return tot


def accuracy(topo, cfgs, data, M, run):
    g = run_all(topo, cfgs, data, M, run); ok = 0
    for (_, y), x in zip(data, g):
        m = max(x); ok += (m > 0 and x.count(m) == 1 and x.index(m) == y)
    return ok / len(data)


def one(seed, R, q, tries, S, M, run, gate, warm=100, diag=False):
    topo = c15.Topo(R); rnd = random.Random(seed); tpl = c15.v12.make_templates(rnd, 4)
    train = [(c15.v12.sample(rnd, tpl[y], q), y) for y in range(4) for _ in range(S)]
    test = [(c15.v12.sample(rnd, tpl[y], q), y) for y in range(4) for _ in range(50)]
    sh = random.Random(seed + 5); sh.shuffle(train); sh.shuffle(test)
    lf = c15.v6.Lfsr(seed + 77); n = len(topo.cells); best = None; br = -1
    for _ in range(warm):
        c = [c15.easy(lf) for _ in range(n)]; r = rewards(topo, c, train, M, run, gate)
        if r > br: best, br = c, r
    cur, cr = best, br; hist = [cr]
    for t in range(tries - warm):
        nxt = list(cur)
        for _ in range(1 + lf.randrange(3)):
            j = lf.randrange(n); nxt[j] = c15.mutate(nxt[j], lf)
        r = rewards(topo, nxt, train, M, run, gate)
        if r >= cr: cur, cr = nxt, r
        if (t + 1) % 100 == 0: hist.append(cr)
    if diag: print("   reward history", hist)
    return accuracy(topo, cur, test, M, run), c15.v12.template_rule(tpl, test)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--radius", type=int, default=1); ap.add_argument("--noise", type=float, default=0.15)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); ap.add_argument("--tries", type=int, default=600)
    ap.add_argument("--per-class", type=int, default=16); ap.add_argument("--M", type=int, default=0); ap.add_argument("--run", type=int, default=2)
    ap.add_argument("--gate", type=int, default=1); ap.add_argument("--diag", action="store_true"); a = ap.parse_args()
    print(f"hex cluster radius {a.radius}, variation-gated reward {a.gate}, homeostasis M={a.M} run={a.run}, noise {a.noise}, {a.tries} tries")
    print(f"{'seed':>4} {'learned':>8} {'template-rule':>13}")
    tot = 0
    for s in range(a.first, a.first + a.runs):
        l, t = one(s, a.radius, a.noise, a.tries, a.per_class, a.M, a.run, a.gate, diag=a.diag); tot += l
        print(f"{s:>4} {l:>8.2f} {t:>13.2f}", flush=True)
    print(f"mean learned {tot / a.runs:.2f}")
