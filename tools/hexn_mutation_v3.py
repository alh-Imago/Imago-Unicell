"""Hex-N mutation experiment v3 (clone of v2; v1 and v2 left as they were).

Change from v2: a phase where BOTH the goal and the cell are silent no longer counts as a perfect match (v2 gave such cells a free 500 on the feedback half). v3 leaves that phase out and re-weights the other one; if both phases are silent in both, the score is 0 (nothing was matched).
A phase where the goal is silent but the cell is active still scores 0 for that phase.

--- v2 text follows ---
Hex-N mutation experiment v2 (clone of v1; v1 left as it was).

Change from v1: the score is GRADED. v1 counted exact tx-bit matches, so a nearly right cell scored the same as a silent one.
v2 counts, for every (window, phase, lane), HOW MANY clocks the lane was high (the burst length, A3) and scores closeness:
   closeness = 1 - sum|a-b| / sum max(a,b)     (1 = identical, 0 = no overlap; silent-vs-silent lanes are skipped)
It is computed separately for the forward phase and the feedback phase, then combined:  score = (1-FB)*forward + FB*feedback
FB (--fb) is the weight of the feedback phase; --fb 0 means forward only, --fb 0.5 means the feedback lines count as much as the forward ones.
Same seeds, same stimuli and same random-best control as v1, so the tables compare directly.
Usage: python3 tools/hexn_mutation_v3.py [--runs N] [--tries T] [--fb W]"""
import argparse, importlib.util, os, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("hexn_v1", os.path.join(ROOT, "tools", "hexn_mutation_v1.py"))
v1 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v1)
Cell, N, PL = v1.Cell, v1.N, v1.PL


def bursts(cfg, stim):
    """per (window, phase) a list of N counts: clocks the lane was high in that phase"""
    c = Cell(*cfg); fw, fb = [], []; acc = [0] * N
    for k, (rx, phase, ps, we) in enumerate(stim):
        if ps: acc = [0] * N
        acc = [a + b for a, b in zip(acc, c.tx(phase))]
        c.clock(rx, phase, ps, we)
        if k % PL == PL - 1: (fb if phase else fw).append(list(acc))
    return fw, fb


def closeness(a, b):
    num = den = 0
    for x, y in zip(a, b):
        for p, q in zip(x, y):
            num += abs(p - q); den += max(p, q)
    return None if den == 0 else 1 - num / den


def score(cfg, stim, goal_b, w):
    fw, fb = bursts(cfg, stim)
    parts = [(1 - w, closeness(fw, goal_b[0])), (w, closeness(fb, goal_b[1]))]
    parts = [(wt, c) for wt, c in parts if c is not None and wt > 0]
    tot = sum(wt for wt, _ in parts)
    return 0 if tot == 0 else round(1000 * sum(wt * c for wt, c in parts) / tot)


def train(seed, tries, w):
    rnd = random.Random(seed)
    stim = v1.make_stimuli(rnd); goal_cfg = v1.rand_cfg(rnd); gb = bursts(goal_cfg, stim)
    ones = sum(map(sum, gb[0])) + sum(map(sum, gb[1]))
    cur = v1.rand_cfg(rnd); cs = score(cur, stim, gb, w); start = cs; kept = 0
    for _ in range(tries):
        nxt = v1.mutate(cur, rnd); ns = score(nxt, stim, gb, w)
        if ns >= cs:
            kept += ns > cs; cur, cs = nxt, ns
    rr = random.Random(seed + 1); best = max(score(v1.rand_cfg(rr), stim, gb, w) for _ in range(tries))
    return ones, start, cs, best, kept, [cur[1].count(k) for k in range(4)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--runs", type=int, default=8); ap.add_argument("--tries", type=int, default=300)
    ap.add_argument("--fb", type=float, default=0.5); a = ap.parse_args()
    print(f"score 0..1000 = closeness of burst lengths (forward {1-a.fb:.2f}, feedback {a.fb:.2f}); 0 = no overlap with the goal")
    print(f"{'seed':>4} {'goal-clk':>8} {'start':>6} {'mutated':>7} {'random-best':>11} {'improving':>9}  lanes per direction code 0/1/2/3")
    for s in range(a.runs):
        ones, st, en, rb, kept, dc = train(s, a.tries, a.fb)
        print(f"{s:>4} {ones:>8} {st:>6} {en:>7} {rb:>11} {kept:>9}  {dc}")
