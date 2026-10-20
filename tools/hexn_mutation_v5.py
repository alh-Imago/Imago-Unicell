"""Hex-N mutation experiment v5: better starting point and bigger steps (new file; v1-v4 untouched). VM only.

Same cell, stimuli, goals, seeds and v3 score as v3/v4. Four ways to spend the SAME budget of tries, plus the random control:
  plain   : v3 keep-or-undo from a random start, one setting changed per try
  warm    : first WARM tries sample random settings and the best becomes the start; the rest is keep-or-undo (total tries equal)
  multi   : keep-or-undo, but each try changes 1, 2 or 3 settings at once
  both    : warm start and multi-setting steps
  random  : best of all the tries as independent random settings (the control)
Usage: python3 tools/hexn_mutation_v5.py [--first S] [--runs N] [--tries T] [--warm K] [--fb W] [--salt S]
--salt S changes only the random stream used for the mutations (not the goals, stimuli or starts), to measure run-to-run noise"""
import argparse, importlib.util, os, random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("hexn_v3", os.path.join(ROOT, "tools", "hexn_mutation_v3.py"))
v3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v3)
v1, bursts, score = v3.v1, v3.bursts, v3.score


def climb(cfg, stim, gb, w, tries, rnd, multi):
    cs = score(cfg, stim, gb, w)
    for _ in range(tries):
        nxt = cfg
        for _ in range(rnd.randint(1, 3) if multi else 1): nxt = v1.mutate(nxt, rnd)
        ns = score(nxt, stim, gb, w)
        if ns >= cs: cfg, cs = nxt, ns
    return cs


def warm_start(stim, gb, w, k, rnd):
    best = max((v1.rand_cfg(rnd) for _ in range(k)), key=lambda c: score(c, stim, gb, w))
    return best


def one(seed, tries, w, k, salt=0):
    rnd = random.Random(seed)
    stim = v1.make_stimuli(rnd); gb = bursts(v1.rand_cfg(rnd), stim)
    start = v1.rand_cfg(rnd)
    plain = climb(start, stim, gb, w, tries, random.Random(seed + 2000 + salt * 7919), False)
    multi = climb(start, stim, gb, w, tries, random.Random(seed + 3000 + salt * 7919), True)
    ws = warm_start(stim, gb, w, k, random.Random(seed + 4000 + salt * 7919))
    warm = climb(ws, stim, gb, w, tries - k, random.Random(seed + 5000 + salt * 7919), False)
    both = climb(ws, stim, gb, w, tries - k, random.Random(seed + 6000 + salt * 7919), True)
    rr = random.Random(seed + 1); rb = max(score(v1.rand_cfg(rr), stim, gb, w) for _ in range(tries))
    return plain, warm, multi, both, rb


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=8)
    ap.add_argument("--tries", type=int, default=1500); ap.add_argument("--warm", type=int, default=100); ap.add_argument("--fb", type=float, default=0.5); ap.add_argument("--salt", type=int, default=0)
    a = ap.parse_args()
    print(f"score 0..1000, v3 score, feedback weight {a.fb}, {a.tries} tries each, warm start uses {a.warm} of them")
    print(f"{'seed':>4} {'plain':>6} {'warm':>6} {'multi':>6} {'both':>6} {'random-best':>11}")
    for s in range(a.first, a.first + a.runs):
        print(f"{s:>4} " + " ".join(f"{x:>6}" for x in one(s, a.tries, a.fb, a.warm, a.salt)), flush=True)
