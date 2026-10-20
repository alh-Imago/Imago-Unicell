"""Hex-N cluster v19 (new file): the one-change-at-a-time LADDER (Alan, 20 Oct 2026).  A clone of v18; every new thing is a flag, all OFF by default, so with no flags v19 == v18 (checked).
Steps (each added alone on top of the best so far; the accept rule is fixed in advance, see hexn_ladder_compare_v1.py):
  --fbpush   step 2  the feedback total also votes on the threshold offset. Per window: fire vote = +1 if the cell reached else -1; feedback vote = +1 if it reached WITHOUT feedback agreeing (fb total 0),
                     -1 if it did not reach although feedback arrived, else 0.  Net vote > 0: 'hi' run grows, < 0: 'lo' run grows, = 0: both runs reset (opposing votes cancel).
  --score    step 3  the reward gets a readout term: share of training samples where the right group fires strictly more than every other group, scaled to 0..15 (the answer is read that way).
  --aim      step 4  half of the mutations pick a cell from the output cells of a group that is stuck (fires for every training sample or none) instead of a random cell.
  --decay    step 5  at the start of each sample an offset that did not move in the previous sample steps one toward zero.
  --fweights step 6  each cell has a weight 1..3 per face (default 1); a receiving lane adds +-weight of its face; mutation can change a weight. Trained only (fixed at run time).
Usage: python3 tools/hexn_cluster_v19.py --M 2 --run 3 [--fbpush] [--score] [--aim] [--decay] [--fweights] [--first S] [--runs N] [--tries T] [--noise Q]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
c15 = load("hexn_cluster_v15"); mc = c15.mc; N, P, PL = c15.N, c15.P, c15.PL
FLAGS = dict(fbpush=False, score=False, aim=False, decay=False, fweights=False)


class Cell(mc.MixCell):
    def __init__(self, cfg, M, run, prev=None):
        super().__init__(*cfg[:5]); self.M, self.run = M, run
        self.w = cfg[5] if len(cfg) > 5 else [1] * 6
        self.off, self.hi, self.lo, self.pushed = (prev.off, prev.hi, prev.lo, False) if prev else (0, 0, 0, False)
        if prev and FLAGS["decay"] and not prev.pushed and self.off:
            self.off += -1 if self.off > 0 else 1
        if FLAGS["fweights"]:
            self.rcv_w = {ph: [(i, self.w[i // P]) for i in self.rcv[ph]] for ph in (0, 1)}

    def clock(self, rx, phase, ph_start, win_end):
        if FLAGS["fweights"]:
            delta = 0; any_rx = 0
            for i, wt in self.rcv_w[phase]:
                if rx[i]:
                    any_rx = 1; delta += -wt if self.c[i] == 3 else wt
            cap = (1 << mc.AW) - 1
            if not phase:
                self.fwd = min(max((0 if ph_start else self.fwd) + delta, 0), cap)
                if ph_start: self.fb = 0; self.inany = any_rx
                else: self.inany |= any_rx
            else:
                self.fb = min(max(self.fb + delta, 0), cap)
            self.bc = 0 if ph_start else min(self.bc + 1, 7)
            if win_end and phase:
                te = self.thr + self.bias
                self.reach_r = int(self.fwd >= te); self.margin_r = max(min(self.fwd - te, 6), 0)
                self.fbok_r = int(self.fb != 0); self.inany_r = self.inany
        if win_end and phase:
            base = self.thr; self.thr = max(0, base + self.off)
            if FLAGS["fweights"]:
                te = self.thr + self.bias; self.reach_r = int(self.fwd >= te); self.margin_r = max(min(self.fwd - te, 6), 0)
            else:
                super().clock(rx, phase, ph_start, win_end)
            self.thr = base
            if self.M:
                v = 1 if self.reach_r else -1
                if FLAGS["fbpush"]:
                    if self.reach_r and not self.fbok_r: v += 1
                    elif not self.reach_r and self.fbok_r: v -= 1
                if v > 0: self.hi += 1; self.lo = 0
                elif v < 0: self.lo += 1; self.hi = 0
                else: self.hi = self.lo = 0
                if self.hi >= self.run: self.off = min(self.off + 1, self.M); self.hi = 0; self.pushed = True
                if self.lo >= self.run: self.off = max(self.off - 1, -self.M); self.lo = 0; self.pushed = True
        elif not FLAGS["fweights"]:
            super().clock(rx, phase, ph_start, win_end)


def sample_counts(topo, cells, bits):
    counts = [0] * 4; ins = {}
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
    prev = None; out = []
    for bits, y in data:
        cells = [Cell(cfgs[i], M, run, prev[i] if prev else None) for i in range(len(cfgs))]
        out.append(sample_counts(topo, cells, bits)); prev = cells
    return out


def rewards(topo, cfgs, data, M, run, bits=4):
    g = run_all(topo, cfgs, data, M, run); top = (1 << bits) - 1; tot = 0; stuck = []
    for k in range(4):
        pos = [x for (_, y), x in zip(data, g) if y == k]; neg = [x for (_, y), x in zip(data, g) if y != k]
        tp = sum(x[k] > 0 for x in pos); tn = sum(not x[k] > 0 for x in neg); fired = tp + (len(neg) - tn)
        if fired in (0, len(data)): stuck.append(k); continue
        tot += round(top * (tp / len(pos) + tn / len(neg)) / 2)
    if FLAGS["score"]:
        ok = sum((max(x) > 0 and x.count(max(x)) == 1 and x.index(max(x)) == y) for (_, y), x in zip(data, g))
        tot += round(top * ok / len(data))
    return tot, stuck


def accuracy(topo, cfgs, data, M, run):
    g = run_all(topo, cfgs, data, M, run)
    return sum((max(x) > 0 and x.count(max(x)) == 1 and x.index(max(x)) == y) for (_, y), x in zip(data, g)) / len(data)


def mutate(cfg, r):
    if FLAGS["fweights"] and r.randrange(6) == 0:
        w = list(cfg[5]) if len(cfg) > 5 else [1] * 6; f = r.randrange(6); w[f] = max(1, min(3, w[f] + r.choice([-1, 1])))
        return tuple(cfg[:5]) + (w,)
    return tuple(c15.mutate(cfg[:5], r)) + tuple(cfg[5:])


def one(seed, R, q, tries, S, M, run, warm=100):
    topo = c15.Topo(R); rnd = random.Random(seed); tpl = c15.v12.make_templates(rnd, 4)
    train = [(c15.v12.sample(rnd, tpl[y], q), y) for y in range(4) for _ in range(S)]
    test = [(c15.v12.sample(rnd, tpl[y], q), y) for y in range(4) for _ in range(50)]
    sh = random.Random(seed + 5); sh.shuffle(train); sh.shuffle(test)
    lf = c15.v6.Lfsr(seed + 77); n = len(topo.cells); best = None; br = -1
    for _ in range(warm):
        c = [c15.easy(lf) for _ in range(n)]; r, st = rewards(topo, c, train, M, run)
        if r > br: best, br, bst = c, r, st
    cur, cr, cst = best, br, bst
    for t in range(tries - warm):
        nxt = list(cur)
        for _ in range(1 + lf.randrange(3)):
            if FLAGS["aim"] and cst and lf.randrange(2):
                cand = sorted({ci for k in cst for (ci, _) in topo.outputs[k]}); j = cand[lf.randrange(len(cand))]
            else: j = lf.randrange(n)
            nxt[j] = mutate(nxt[j], lf)
        r, st = rewards(topo, nxt, train, M, run)
        if r >= cr: cur, cr, cst = nxt, r, st
    return accuracy(topo, cur, test, M, run), c15.v12.template_rule(tpl, test)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--radius", type=int, default=1); ap.add_argument("--noise", type=float, default=0.15)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); ap.add_argument("--tries", type=int, default=600)
    ap.add_argument("--per-class", type=int, default=16); ap.add_argument("--M", type=int, default=2); ap.add_argument("--run", type=int, default=3)
    for f in FLAGS: ap.add_argument("--" + f, action="store_true")
    a = ap.parse_args()
    for f in FLAGS: FLAGS[f] = getattr(a, f)
    print(f"hex cluster v19 radius {a.radius}, M={a.M} run={a.run}, flags {[f for f in FLAGS if FLAGS[f]]}, noise {a.noise}, {a.tries} tries")
    print(f"{'seed':>4} {'learned':>8} {'template-rule':>13}")
    tot = 0
    for s in range(a.first, a.first + a.runs):
        l, t = one(s, a.radius, a.noise, a.tries, a.per_class, a.M, a.run); tot += l
        print(f"{s:>4} {l:>8.2f} {t:>13.2f}", flush=True)
    print(f"mean learned {tot / a.runs:.2f}")
