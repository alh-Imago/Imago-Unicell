"""Hex-N mutation experiment v4: simulated annealing (new file; v1-v3 untouched). VM only.

Same cell, stimuli, goals, seeds and v3 score (silent phases left out) as v3, so the tables compare directly.
Change: a WORSE setting is sometimes kept, with probability exp(-drop/T). T starts at --t0 (score points, 0..1000 scale) and falls
in a straight line to 0 over the tries, so early on the search can step off a dead end and at the end it only climbs.
The result reported is the BEST setting seen during the run (what you would freeze), not the last one.
The columns 'keep-undo' and 'random-best' are the v3 method and the random control on the same seed and budget.
Usage: python3 tools/hexn_mutation_v4.py [--runs N] [--tries T] [--fb W] [--t0 T0]"""
import argparse, importlib.util, math, os, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("hexn_v3", os.path.join(ROOT, "tools", "hexn_mutation_v3.py"))
v3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v3)
v1, bursts, score = v3.v1, v3.bursts, v3.score


def anneal(cur, stim, gb, w, tries, t0, rnd):
    cs = score(cur, stim, gb, w); best, bs = cur, cs
    for k in range(tries):
        T = t0 * (1 - k / tries)
        nxt = v1.mutate(cur, rnd); ns = score(nxt, stim, gb, w)
        if ns >= cs or (T > 0 and rnd.random() < math.exp((ns - cs) / T)):
            cur, cs = nxt, ns
            if cs > bs: best, bs = cur, cs
    return bs


def one(seed, tries, w, t0):
    rnd = random.Random(seed)
    stim = v1.make_stimuli(rnd); goal_cfg = v1.rand_cfg(rnd); gb = bursts(goal_cfg, stim)
    start_cfg = v1.rand_cfg(rnd); start = score(start_cfg, stim, gb, w)
    cur = start_cfg; cs = start
    for _ in range(tries):                                  # v3 method: keep if not worse, else undo
        nxt = v1.mutate(cur, rnd); ns = score(nxt, stim, gb, w)
        if ns >= cs: cur, cs = nxt, ns
    ann = anneal(start_cfg, stim, gb, w, tries, t0, random.Random(seed + 1000))
    rr = random.Random(seed + 1); best = max(score(v1.rand_cfg(rr), stim, gb, w) for _ in range(tries))
    return start, cs, ann, best


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--runs", type=int, default=8); ap.add_argument("--tries", type=int, default=1500)
    ap.add_argument("--fb", type=float, default=0.5); ap.add_argument("--t0", type=float, default=60); a = ap.parse_args()
    print(f"score 0..1000, v3 score, feedback weight {a.fb}, anneal start temperature {a.t0}")
    print(f"{'seed':>4} {'start':>6} {'keep-undo':>9} {'anneal':>7} {'random-best':>11}")
    for s in range(a.runs):
        st, ku, an, rb = one(s, a.tries, a.fb, a.t0)
        print(f"{s:>4} {st:>6} {ku:>9} {an:>7} {rb:>11}")
