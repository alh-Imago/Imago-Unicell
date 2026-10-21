"""Hex-N cluster v22 (new file): the decision-table cell with a STATE MACHINE (tally with a commit threshold) on every table row, instead of the random keep-or-undo search (Alan, 21 Oct 2026; Tsetlin-style).
Same cells, layout (one cell per output group), reward-free: no train-set score is used after the warm start.  Rule, applied after EACH training sample (online, local):
  outcome  = good if the right output group fires strictly more than the others, else bad  (one bit, broadcast to every cell: the 'feedback')
  every table row a cell LOOKED UP while handling the sample (row = the 6-bit combination of faces with input, 0 excluded) has a tally t in [-T, +T]:
      good: t = min(T, t + 1)      bad: t = t - 1
      when t <= -T (the row has failed T times more than it succeeded): the row is TRIED AGAIN: P randomly chosen faces of that row get a new random level 0..3, and t = 0.
  A row used in successes climbs to +T and stays; the commit threshold T is the dial (small = changes fast and noisy, large = slow and steady).
Budget parity with the search: warm start = best of 100 random tables (100 evaluations), then (tries - 100) passes over the training samples, each pass = one evaluation's worth of sample runs.  No undo.
Usage: python3 tools/hexn_cluster_v22.py [--T t] [--P p] [--tries 1000] [--first S] [--runs N] [--noise Q]"""
import argparse, importlib.util, os, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
v21 = load("hexn_cluster_v21"); v19 = v21.v19; m3 = v21.m3; c15 = v21.c15; F = m3.F


class UsedCell(m3.TableCell):
    """TableCell that also records which table rows it looked up (the eligibility trace)."""
    def __init__(self, *a):
        super().__init__(*a); self.used = []

    def clock(self, rx, phase, ph_start, win_end):
        super().clock(rx, phase, ph_start, win_end)
        if win_end and phase:
            combo = sum(b << f for f, b in enumerate(self.fin))
            if combo: self.used.append(combo)


def one(seed, R, q, tries, S, T, P, rand, warm=100):
    topo = c15.Topo(R); topo.outputs = v19.own_outputs(topo); rnd = random.Random(seed); tpl = c15.v12.make_templates(rnd, 4)
    train = [(c15.v12.sample(rnd, tpl[y], q), y) for y in range(4) for _ in range(S)]
    test = [(c15.v12.sample(rnd, tpl[y], q), y) for y in range(4) for _ in range(50)]
    sh = random.Random(seed + 5); sh.shuffle(train); sh.shuffle(test)
    lf = c15.v6.Lfsr(seed + 77); n = len(topo.cells); best = None; br = -1
    for _ in range(warm):
        c = [v21.new_cfg(lf, rand) for _ in range(n)]; r = v21.rewards(topo, c, train)
        if r > br: best, br = c, r
    cfgs = [(list(a), list(d), [list(x) for x in t]) for (a, d, t) in best]
    tally = [[0] * 64 for _ in range(n)]; order = list(range(len(train))); rr = random.Random(seed + 99)
    for _ in range(tries - warm):
        rr.shuffle(order)
        for k in order:
            bits, y = train[k]
            cells = [UsedCell(*cfgs[i]) for i in range(n)]
            x = v19.sample_counts(topo, cells, bits); m = max(x)
            good = m > 0 and x.count(m) == 1 and x.index(m) == y
            for i, c in enumerate(cells):
                for combo in set(c.used):
                    t = tally[i][combo]; t = min(T, t + 1) if good else t - 1
                    if t <= -T:
                        for f in rr.sample(range(F), min(P, F)): cfgs[i][2][combo][f] = rr.randint(0, 3)
                        t = 0
                    tally[i][combo] = t
    return v21.accuracy(topo, cfgs, test), c15.v12.template_rule(tpl, test)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--radius", type=int, default=1); ap.add_argument("--noise", type=float, default=0.15)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=5); ap.add_argument("--tries", type=int, default=1000)
    ap.add_argument("--per-class", type=int, default=16); ap.add_argument("--T", type=int, default=4); ap.add_argument("--P", type=int, default=1); ap.add_argument("--rand", type=float, default=0.2)
    a = ap.parse_args()
    print(f"hex cluster v22 (table + state machine) T={a.T} P={a.P}, radius {a.radius}, noise {a.noise}, {a.tries} tries-equivalent")
    print(f"{'seed':>4} {'learned':>8} {'template-rule':>13}")
    tot = 0
    for s in range(a.first, a.first + a.runs):
        l, t = one(s, a.radius, a.noise, a.tries, a.per_class, a.T, a.P, a.rand); tot += l
        print(f"{s:>4} {l:>8.2f} {t:>13.2f}", flush=True)
    print(f"mean learned {tot / a.runs:.2f}")
