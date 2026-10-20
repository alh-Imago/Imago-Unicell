"""Hex-N mutation experiment v1 (VM side, one cell, nothing in RTL).

Question: can a cell with a stored GOAL and seeded one-setting MUTATION with KEEP-OR-UNDO move towards the goal?
The goal is the output (tx) pattern a hidden 'teacher' cell produces for a fixed set of stimuli.
The cell under training starts from a different random setting. Score = number of tx bits equal to the goal
over all windows. Uses the Cell class that the RTL test pins (assumptions A1..A7 unchanged).
Everything is seeded; the same seed gives the same run.  Usage: python3 tools/hexn_mutation_v1.py [--runs N] [--tries T]"""
import argparse, importlib.util, os, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("hexn_t", os.path.join(ROOT, "tests", "test_hexn_cell_v1.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
Cell, F, P, N, PL = m.Cell, m.F, m.P, m.N, m.PL


def make_stimuli(rnd, windows=4):
    seq = []
    for w in range(windows):
        for phase in (0, 1):
            for t in range(PL):
                seq.append(([int(rnd.random() < 0.55) for _ in range(N)], phase, int(t == 0), int(phase == 1 and t == PL - 1)))
    return seq


def run(cfg, stim):
    c = Cell(*cfg); out = []
    for rx, phase, ps, we in stim:
        out.extend(c.tx(phase)); c.clock(rx, phase, ps, we)
    return out


def rand_cfg(rnd):
    return ([int(rnd.random() < 0.85) for _ in range(N)], [rnd.randint(0, 3) for _ in range(N)],
            [rnd.randint(0, 3) for _ in range(N)], [rnd.randint(0, 5) for _ in range(F)], rnd.choice([0, 0, 0, 1, 2]))


def mutate(cfg, rnd):
    a, d, c, t, b = [list(x) if isinstance(x, list) else x for x in cfg]
    k = rnd.randrange(5)
    if k == 0: i = rnd.randrange(N); a[i] ^= 1
    elif k == 1: i = rnd.randrange(N); d[i] = rnd.randint(0, 3)
    elif k == 2: i = rnd.randrange(N); c[i] = rnd.randint(0, 3)
    elif k == 3: i = rnd.randrange(F); t[i] = max(0, min(7, t[i] + rnd.choice([-1, 1])))
    else: b = max(0, min(3, b + rnd.choice([-1, 1])))
    return (a, d, c, t, b)


def score(cfg, stim, goal):
    """Balanced: a matched 1 counts as much as all the matched 0s together (goals are mostly 0s, so plain matching is fooled by an all-silent cell)."""
    out = run(cfg, stim); ones = sum(goal) or 1; zeros = (len(goal) - sum(goal)) or 1
    tp = sum(1 for x, y in zip(out, goal) if y and x); tn = sum(1 for x, y in zip(out, goal) if not y and not x)
    return round(1000 * (tp / ones + tn / zeros) / 2)


def train(seed, tries):
    rnd = random.Random(seed)
    stim = make_stimuli(rnd); goal = run(rand_cfg(rnd), stim)
    ones = sum(goal)
    cur = rand_cfg(rnd); cs = score(cur, stim, goal); start = cs; kept = 0
    for _ in range(tries):
        nxt = mutate(cur, rnd); ns = score(nxt, stim, goal)
        if ns >= cs:                       # keep if not worse; otherwise undo (cur unchanged)
            kept += ns > cs; cur, cs = nxt, ns
    # control: same number of tries, no keep/undo, best of random settings
    rr = random.Random(seed + 1); best = max(score(rand_cfg(rr), stim, goal) for _ in range(tries))
    dc = [cur[1].count(k) for k in range(4)]
    return len(goal), ones, start, cs, best, kept, dc


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--runs", type=int, default=8); ap.add_argument("--tries", type=int, default=300)
    a = ap.parse_args()
    print("score is 0..1000 (balanced accuracy x 1000; 500 = a silent or random cell)")
    print(f"{'seed':>4} {'bits':>5} {'goal1s':>6} {'start':>6} {'mutated':>7} {'random-best':>11} {'improving':>9}  lanes per direction code 0/1/2/3")
    for s in range(a.runs):
        n, ones, st, en, rb, kept, dc = train(s, a.tries)
        print(f"{s:>4} {n:>5} {ones:>6} {st:>6} {en:>7} {rb:>11} {kept:>9}  {dc}")
