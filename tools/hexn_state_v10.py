"""Hex-N state-latch experiment v10 (new file; v1-v9 untouched). VM only. Single cell.

Question: does a small WRITABLE memory in the cell win back the score lost to delay (v9: 833 at delay 0 -> 443 at delay 3)?
Model of the memory (an assumption made here, not a decision): the cell keeps an M-bit shift register. At the end of every window the bit
'face MSRC received any input this window' is shifted in (newest bit = 1 window ago, next = 2 windows ago, ...). MSRC (which face to
watch) is a trained setting. Each face also has a trained TAP (0 = ignore the memory, k = use bit k-1 of the register). Where a TAP is set:
  AND  lane gate: also requires the tapped bit to be 1          (memory AND the three registered conditions)
  XOR  lane gate: steers on the tapped bit instead of 'input arrived' (even lane when set, odd when clear)
--live adds a second change: the AND gate uses 'input has arrived so far in THIS window' instead of the previous window's result.
M = 0 is the plain cell (taps ignored), so M = 0 reproduces v9.  The register shifts one bit per window, so M bits can only reach M windows
back: a rising score with M mostly tests whether the search can FIND and use the tap, not whether memory can exist.
Task, learner and control are v9's (delay D, 10 windows, teacher = plain cell fed the delayed stream, v6 learner with 4-bit reward).
Usage: python3 tools/hexn_state_v10.py --delay D --mem M [--live] [--first S] [--runs N] [--tries T]"""
import argparse, importlib.util, os, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(name):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", name + ".py"))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
v3, v6, v9 = load("hexn_mutation_v3"), load("hexn_learner_v6"), load("hexn_delay_v9")
v1, Cell, F, P, N, PL = v3.v1, v3.Cell, v3.v1.F, v3.v1.P, v3.N, v3.PL
WIN = 10
v9.WIN = WIN


class StateCell(Cell):
    def __init__(self, base, msrc, taps, M, live):
        super().__init__(*base); self.msrc, self.taps, self.M, self.live = msrc, taps, M, live; self.mem = [0] * M

    def tx(self, phase):
        out = []
        for f in range(F):
            tap = self.taps[f] if self.M else 0
            mb = self.mem[tap - 1] if tap else None
            for p in range(P):
                i = f * P + p; d, cd = self.d[i], self.c[i]
                sender = self.a[i] and ((d == 2) if phase else (d in (1, 3)))
                first = not any(self.a[f * P + q] and self.c[f * P + q] == 1 and self.d[f * P + q] != 0 for q in range(p))
                r, fo = self.reach_r[f], self.fbok_r[f]
                ia = self.inany_r[f]
                ia_and = (ia or self.inany[f]) if self.live else ia
                and_ok = r and fo and ia_and and (mb if mb is not None else 1)
                xs = mb if mb is not None else ia
                pas = {0: and_ok, 1: r and first, 2: r and ((not xs) if p & 1 else xs), 3: False}[cd]
                out.append(int(bool(sender and pas and self.bc[i] < self.margin_r[f] + 1)))
        return out

    def clock(self, rx, phase, ph_start, win_end):
        super().clock(rx, phase, ph_start, win_end)
        if win_end and phase and self.M:
            self.mem = [int(bool(self.inany_r[self.msrc]))] + self.mem[:-1]


def rand_cfg(rnd, M):
    return (v1.rand_cfg(rnd), rnd.randrange(F), [rnd.randint(0, M) for _ in range(F)])


def mutate(cfg, rnd, M):
    base, msrc, taps = cfg
    if M == 0 or rnd.random() > 0.25: return (v1.mutate(base, rnd), msrc, taps)
    if rnd.random() < 0.3: return (base, rnd.randrange(F), taps)
    taps = list(taps); taps[rnd.randrange(F)] = rnd.randint(0, M); return (base, msrc, taps)


def bursts(cfg, stim, M, live):
    c = StateCell(cfg[0], cfg[1], cfg[2], M, live); fw, fb = [], []; acc = [0] * N
    for k, (rx, phase, ps, we) in enumerate(stim):
        if ps: acc = [0] * N
        acc = [a + b for a, b in zip(acc, c.tx(phase))]
        c.clock(rx, phase, ps, we)
        if k % PL == PL - 1: (fb if phase else fw).append(list(acc))
    return fw, fb


def score(cfg, stim, gb, w, M, live):
    fw, fb = bursts(cfg, stim, M, live)
    parts = [(1 - w, v3.closeness(fw, gb[0])), (w, v3.closeness(fb, gb[1]))]
    parts = [(x, c) for x, c in parts if c is not None and x > 0]; tot = sum(x for x, _ in parts)
    return 0 if tot == 0 else round(1000 * sum(x * c for x, c in parts) / tot)


def one(seed, d, M, live, tries, w, warm, bits, min_goal=20):
    rnd = random.Random(seed); stim = v1.make_stimuli(rnd, windows=WIN)
    for _ in range(500):
        gb = v3.bursts(v1.rand_cfg(rnd), v9.shifted(stim, d))
        if sum(map(sum, gb[0])) + sum(map(sum, gb[1])) >= min_goal: break
    q = lambda cf: score(cf, stim, gb, w, M, live) * ((1 << bits) - 1) // 1000
    lf = v6.Lfsr(seed + 77); best = None; br = -1
    for _ in range(warm):
        c = rand_cfg(lf, M); r = q(c)
        if r > br: best, br = c, r
    cur, cr = best, br
    for _ in range(tries - warm):
        nxt = cur
        for _ in range(1 + lf.randrange(3)): nxt = mutate(nxt, lf, M)
        r = q(nxt)
        if r >= cr: cur, cr = nxt, r
    rr = random.Random(seed + 1); rb = max(score(rand_cfg(rr, M), stim, gb, w, M, live) for _ in range(tries))
    return score(cur, stim, gb, w, M, live), rb


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--delay", type=int, default=0); ap.add_argument("--mem", type=int, default=0)
    ap.add_argument("--live", action="store_true"); ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=20)
    ap.add_argument("--tries", type=int, default=1500); ap.add_argument("--warm", type=int, default=100)
    ap.add_argument("--bits", type=int, default=4); ap.add_argument("--fb", type=float, default=0.5); a = ap.parse_args()
    print(f"delay {a.delay}, memory {a.mem} bits, live-AND {a.live}, {WIN} windows, {a.tries} tries")
    print(f"{'seed':>4} {'learned':>8} {'random-best':>11}")
    for s in range(a.first, a.first + a.runs):
        l, rb = one(s, a.delay, a.mem, a.live, a.tries, a.fb, a.warm, a.bits); print(f"{s:>4} {l:>8} {rb:>11}", flush=True)
