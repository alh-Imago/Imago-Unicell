"""Hex-N on-cell learner v6 (new file; v1-v5 untouched). VM model of what the silicon would have to do, with only hardware-sized parts.

What the learner may use (and nothing else):
  * a 32-bit LFSR for all random choices (deterministic from its seed, replayable, cheap in logic)
  * the teacher's REWARD: one number per trial, quantised to --bits bits (the feedback lines carry only this)
  * a shadow copy of the last good settings (keep-or-undo)
It never sees the goal pattern or the true score. The teacher (outside the cell) holds the goal and turns the cell's output
into the reward. The learning recipe is the best one from v5: warm start (best of K random settings by reward) then keep-or-undo
with 1-3 settings changed per try.  --bits 10 is almost the full score; --bits 1 is just 'better / not better' (a coarse good/bad).
Usage: python3 tools/hexn_learner_v6.py [--first S] [--runs N] [--tries T] [--warm K] [--bits B] [--fb W]"""
import argparse, importlib.util, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("hexn_v3", os.path.join(ROOT, "tools", "hexn_mutation_v3.py"))
v3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(v3)
v1, bursts, score = v3.v1, v3.bursts, v3.score


class Lfsr:
    """32-bit Galois LFSR (taps 32,22,2,1). Offers just the calls the Hex-N helpers use."""
    def __init__(self, seed): self.s = (seed * 2654435761 + 1) & 0xFFFFFFFF or 1
    def bit(self):
        lsb = self.s & 1; self.s >>= 1
        if lsb: self.s ^= 0x80200003
        return lsb
    def bits(self, n):
        v = 0
        for _ in range(n): v = (v << 1) | self.bit()
        return v
    def random(self): return self.bits(24) / (1 << 24)
    def randrange(self, n): return int(self.random() * n)
    def randint(self, a, b): return a + self.randrange(b - a + 1)
    def choice(self, seq): return seq[self.randrange(len(seq))]


class Teacher:
    """Outside the cell: holds the goal, returns the reward for a setting as a bits-wide number."""
    def __init__(self, stim, goal_b, w, bits): self.stim, self.gb, self.w, self.bits = stim, goal_b, w, bits
    def reward(self, cfg): return score(cfg, self.stim, self.gb, self.w) * ((1 << self.bits) - 1) // 1000


def learn(teacher, lf, tries, warm):
    best = None; br = -1
    for _ in range(warm):
        c = v1.rand_cfg(lf); r = teacher.reward(c)
        if r > br: best, br = c, r
    cur, cr = best, br
    for _ in range(tries - warm):
        nxt = cur
        for _ in range(1 + lf.randrange(3)): nxt = v1.mutate(nxt, lf)
        r = teacher.reward(nxt)
        if r >= cr: cur, cr = nxt, r
    return cur


def one(seed, tries, w, bits, warm):
    import random
    rnd = random.Random(seed)
    stim = v1.make_stimuli(rnd); gb = bursts(v1.rand_cfg(rnd), stim)
    t = Teacher(stim, gb, w, bits)
    cfg = learn(t, Lfsr(seed + 77), tries, warm)
    true = score(cfg, stim, gb, w)
    rr = random.Random(seed + 1); rb = max(score(v1.rand_cfg(rr), stim, gb, w) for _ in range(tries))
    return true, rb


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=30)
    ap.add_argument("--tries", type=int, default=1500); ap.add_argument("--warm", type=int, default=100)
    ap.add_argument("--bits", type=int, default=4); ap.add_argument("--fb", type=float, default=0.5); a = ap.parse_args()
    print(f"reward bits {a.bits}; true score 0..1000 of the setting the cell ends with; {a.tries} tries")
    print(f"{'seed':>4} {'learned':>8} {'random-best':>11}")
    for s in range(a.first, a.first + a.runs):
        l, rb = one(s, a.tries, a.fb, a.bits, a.warm); print(f"{s:>4} {l:>8} {rb:>11}", flush=True)
