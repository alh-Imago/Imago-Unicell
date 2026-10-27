"""hexn_reward_v1: the REWARD-DRIVEN GOAL READ for layer 2 (Alan, 27 Oct 2026: store and retrieve first, then the reward side). ABSTRACT MODEL on the store's keys, not cells; Python only; no RTL; new file.
Idea: each stored sequence entry (context of 1 to 3 events, next event) gets a VALUE next to its counts: the average reward of the routines that went through it. The reward is a teacher signal given only when a routine ends in a goal (desired goal +1, any other goal -0.5, as in hexn_path_v1); there is no label of the right route. The goal read is: at a decision point, among the keys that can come next, take the one whose entry has the highest value (explore a random one with chance eps). The desired goal is a HOST setting, so changing it later must re-steer the system.
World: the four routines of the real runs, A = 1 2 3 -> 7, B = 4 2 3 -> 8, C = 1 5 6 -> 8, D = 4 5 6 -> 7. Two real decisions per routine: the first key (1 or 4) and the second (2 or 5); the goal depends on both (7 for 1-2 and 4-5, 8 for 1-5 and 4-2). The history the store sees is continuous across routines (the last 3 events can include the end of the previous routine), as in the real store.
Phases: 40 routines of passive learning (the operator presses at random), then the system chooses (epsilon-greedy, eps 0.1) for the rest. Measured: share of routines that end in the desired goal over the last 50 routines (a random chooser gets 0.5), and the routines needed to reach 0.9.
Variants: context length k used for the value (1, 2, 3); key recognition error p (the sensor misreads a key as a random key, so the history and the learned entries are wrong, the world is not); teacher error q (the reward sign is flipped); goal change at routine 300 (7 -> 8) with the value kept as a running mean 1/n ('mean') or a constant step 0.1 ('step').
Limits: abstract table; the system knows which keys are possible next (from its stored entries after the passive phase); two decisions per routine; reward only at the end; no cost of keys; synthetic world built from the real routine design.
Usage: python3 tools/hexn_reward_v1.py"""
import random, collections
TREE = {(): (1, 4), (1,): (2, 5), (4,): (2, 5), (1, 2): (3,), (4, 2): (3,), (1, 5): (6,), (4, 5): (6,), (1, 2, 3): (7,), (4, 2, 3): (8,), (1, 5, 6): (8,), (4, 5, 6): (7,)}
class Agent:
    def __init__(s, k, mode, rnd, eps=0.1, alpha=0.1):
        s.k, s.mode, s.rnd, s.eps, s.alpha = k, mode, rnd, eps, alpha
        s.q = {}; s.hist = []                   # q[(ctx, ev)] = [value, n]; ctx = last k observed events
    def key(s, ev): return (tuple(s.hist[-s.k:]), ev)
    def value(s, ev): return s.q.get(s.key(ev), [0.0, 0])[0]
    def choose(s, options, greedy_allowed=True):
        if s.rnd.random() < s.eps or not greedy_allowed: return s.rnd.choice(options)
        best = max(s.value(e) for e in options); return s.rnd.choice([e for e in options if s.value(e) == best])
    def update(s, used, r):
        for key in used:
            v = s.q.setdefault(key, [0.0, 0]); v[1] += 1; v[0] += (r - v[0]) / v[1] if s.mode == "mean" else s.alpha * (r - v[0])
def episode(ag, rnd, p, q, want, passive):
    """one routine; returns True if it ended in the desired goal"""
    pref = (); used = []
    while pref in TREE:
        opts = TREE[pref]
        e = rnd.choice(opts) if (passive or len(opts) == 1) else ag.choose(list(opts))
        obs = e if rnd.random() >= p else rnd.randrange(1, 9)       # what the sensor reports
        used.append(ag.key(obs)); ag.hist.append(obs); pref = pref + (e,)
    goal = pref[-1]; r = 1.0 if goal == want else -0.5
    if rnd.random() < q: r = -0.5 if r > 0 else 1.0
    ag.update(used, r); return goal == want
def run(k, mode, p=0.0, q=0.0, n=800, flip=None, seed=0, alpha=0.1):
    rnd = random.Random(seed); ag = Agent(k, mode, rnd, alpha=alpha); want = 7; hist = []
    for i in range(n):
        if flip and i == flip: want = 8
        hist.append(episode(ag, rnd, p, q, want, passive=(i < 40)))
    return hist
def curve(h, lo, hi): return sum(h[lo:hi]) / (hi - lo)
def first_reach(h, start, thr=0.9, w=50):
    for i in range(start + w, len(h) + 1):
        if sum(h[i - w:i]) / w >= thr: return i - start
    return None
def main(seeds=30):
    print("A. CONTEXT LENGTH k and recognition error p (teacher error 0, 800 routines, goal 7, %d seeds): share reaching the desired goal in routines 700-800; routines (after the 40 passive ones) needed to reach 0.9" % seeds)
    print("   k | p=0.0 final / needed | p=0.1 final / needed | p=0.2 final / needed")
    for k in (1, 2, 3):
        row = []
        for p in (0.0, 0.1, 0.2):
            hs = [run(k, "mean", p, 0.0, seed=s) for s in range(seeds)]; fin = sum(curve(h, 700, 800) for h in hs) / seeds
            nd = [first_reach(h, 40) for h in hs]; ok = [x for x in nd if x is not None]
            row.append("%.3f / %s" % (fin, ("%.0f (%d/%d)" % (sum(ok) / len(ok), len(ok), seeds)) if ok else "never"))
        print("   %d | %s" % (k, " | ".join(row)))
    print("\nB. TEACHER ERROR q (reward sign flipped), k=1, p=0: final share in routines 700-800")
    for q in (0.0, 0.2, 0.4, 0.5, 0.6): print("   q=%.1f: %.3f" % (q, sum(curve(run(1, "mean", 0.0, q, seed=s), 700, 800) for s in range(seeds)) / seeds))
    print("\nC. GOAL CHANGE at routine 300 (7 -> 8), k=1, p=0, q=0: share reaching the NEW desired goal in routines 300-400 / 400-500 / 700-800, and routines after the change to reach 0.9")
    for mode, al in (("mean", 0), ("step", 0.1), ("step", 0.3)):
        hs = [run(1, mode, 0.0, 0.0, n=800, flip=300, seed=s, alpha=al) for s in range(seeds)]
        nd = [first_reach(h, 300) for h in hs]; ok = [x for x in nd if x is not None]
        print("   %-5s %-4s: %.3f / %.3f / %.3f | needed %s" % (mode, ("" if mode == "mean" else "a=%.1f" % al), sum(curve(h, 300, 400) for h in hs) / seeds, sum(curve(h, 400, 500) for h in hs) / seeds, sum(curve(h, 700, 800) for h in hs) / seeds, ("%.0f (%d/%d)" % (sum(ok) / len(ok), len(ok), seeds)) if ok else "never"))
    def base(sd):
        rnd = random.Random(sd); ag = Agent(1, "mean", rnd); return sum(episode(ag, rnd, 0.0, 0.0, 7, True) for _ in range(800)) / 800
    print("\nD. RANDOM CHOOSER (the operator pressing at random, no steering): %.3f (should be 0.5)" % (sum(base(sd) for sd in range(seeds)) / seeds))
    print("\nThe reward flips the order of the two choices only when the teacher is wrong more than half the time: with rewards +1 / -0.5 and error q the right choice averages 1-1.5q against -0.5+1.5q for the wrong one, equal at q = 0.5.")
if __name__ == "__main__": main()
