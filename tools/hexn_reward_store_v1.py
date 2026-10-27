"""hexn_reward_store_v1: the reward-driven goal read run on the STORE MODEL (tools/hexn_store_v3.py, the bit-true reference of rtl/hexn_store_v3.v) instead of the abstract table of hexn_reward_v1.py. Same world (the four routines, two decisions each, goal 7 or 8), same phases (40 passive routines, then the system chooses, 10 percent exploration), same measures, so the two can be compared. The store has to LEARN the pairs first (promotion at N sightings inside W events), values are 8-bit fixed point (reward +1 = +64, -0.5 = -32), the step is 2^-vshift, the goal read uses context length glvl.
Per routine: for each key pressed the host sends OBS with the key class (key - 1); at the routine's goal it sends REW with the teacher's reward (+64 desired goal, -32 other; sign flipped with chance q). The system's choice = the store's goal read (gbest) after the routine so far, or a random option with chance 0.1. Options not known to the store yet are chosen at random.
Measures: share of routines in 700-800 that end in the desired goal; routines (after the 40 passive) to reach 0.9 over 50; goal change 7 -> 8 at routine 300: routines after the change to reach 0.9.
Usage: python3 tools/hexn_reward_store_v1.py"""
import random
import hexn_store_v3 as S
from hexn_reward_v1 import TREE, curve, first_reach
def episode(st, rnd, p, q, want, passive, eps, t):
    pref = (); 
    while pref in TREE:
        opts = TREE[pref]
        if passive or len(opts) == 1 or rnd.random() < eps: e = rnd.choice(opts)
        else:
            g = st.step(S.RD, 0, t)["gbest"] + 1; e = g if g in opts else rnd.choice(opts)
        obs = e if rnd.random() >= p else rnd.randrange(1, 9)
        st.step(S.OBS, obs - 1, t); t += 1; pref = pref + (e,)
    goal = pref[-1]; r = 64 if goal == want else -32
    if rnd.random() < q: r = -32 if r > 0 else 64
    st.step(S.REW, r=r); return goal == want, t
def run(N=2, W=400, vshift=3, glvl=1, p=0.0, q=0.0, n=800, flip=None, seed=0):
    rnd = random.Random(seed); st = S.StoreV3(N=N, W=W, vshift=vshift, glvl=glvl); want = 7; h = []; t = 0
    for i in range(n):
        if flip and i == flip: want = 8
        ok, t = episode(st, rnd, p, q, want, i < 40, 0.1, t); h.append(ok)
    return h, st
def row(label, hs):
    ok = [x for x in (first_reach(h, 40) for h in hs) if x is not None]
    return "%s: final %.3f, to 0.9 in %s" % (label, sum(curve(h, 700, 800) for h in hs) / len(hs), ("%.0f (%d/%d)" % (sum(ok) / len(ok), len(ok), len(hs))) if ok else "never")
def main(seeds=20):
    print("A. clean world, N=2 W=400 step 2^-3, goal read at context 1/2/3")
    for gl in (1, 2, 3): print("  glvl %d  %s" % (gl, row("", [run(glvl=gl, seed=s)[0] for s in range(seeds)])))
    print("B. keys misread 10 and 20 percent (glvl 1 and 3)")
    for p in (0.1, 0.2):
        for gl in (1, 3): print("  p=%.1f glvl %d  %s" % (p, gl, row("", [run(glvl=gl, p=p, seed=s)[0] for s in range(seeds)])))
    print("C. teacher error q = 0.2, 0.4, 0.6 (glvl 1)")
    for q in (0.2, 0.4, 0.6): print("  q=%.1f  %s" % (q, row("", [run(q=q, seed=s)[0] for s in range(seeds)])))
    print("D. goal change at routine 300 (7 -> 8), glvl 1: step 2^-s for s = 2, 3, 5, 7")
    for sh in (2, 3, 5, 7):
        hs = [run(vshift=sh, n=800, flip=300, seed=s)[0] for s in range(seeds)]; ok = [x for x in (first_reach(h, 300) for h in hs) if x is not None]
        print("  s=%d: share correct 300-400 / 400-500 / 700-800: %.3f / %.3f / %.3f | to 0.9: %s" % (sh, sum(curve(h, 300, 400) for h in hs) / seeds, sum(curve(h, 400, 500) for h in hs) / seeds, sum(curve(h, 700, 800) for h in hs) / seeds, ("%.0f (%d/%d)" % (sum(ok) / len(ok), len(ok), seeds)) if ok else "never"))
if __name__ == "__main__": main()
