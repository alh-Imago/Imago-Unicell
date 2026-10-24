"""(v3; imports the strategies from hexn_noise_fb_v2.py, which is left untouched.) SIMILAR stored patterns. Python model only; plain compare-all store, not the real block.
500 stored 64-wire patterns in 25 families: each pattern = its family centre with SPREAD wires flipped, so siblings differ from each other by about 2 x SPREAD wires (spread 12: ~21, 6: ~11, 3: ~6). Looks as before (independent flips, probability p).
Query kinds: known; SIBLING = never stored but from a stored family (similar, not the same: the hard false-known case); RANDOM = a random pattern (must be unknown).
Strategies: A one look (fixed 0.75), D three looks majority (fixed 0.75), E two looks masked with the chance-level threshold, C2 = E-style with the noise estimate and a third look when p_hat > 0.12. Usage: python3 tools/hexn_noise_fb_v3.py [SEEDS]"""
import sys, numpy as np
from hexn_noise_fb_v2 import strategy, W
N, F = 500, 25
NAMES = ("A", "D", "E", "C2")
def run(seed, spread, noise, q=1500):
    rng = np.random.default_rng(seed); cen = rng.integers(0, 2, (F, W), dtype=np.uint8)
    def member():
        c = cen[int(rng.integers(0, F))].copy(); c[rng.choice(W, spread, replace=False)] ^= 1; return c
    pats = np.array([member() for _ in range(N)])
    out = {n: dict(right=0, wrong=0, unk=0, sib=0, rnd=0, nk=0, ns=0, nr=0) for n in NAMES}
    for k in range(3 * q):
        kind = ("known", "sibling", "random")[k % 3]
        if kind == "known": i = int(rng.integers(0, N)); base = pats[i]
        elif kind == "sibling": base = member()
        else: base = rng.integers(0, 2, W, dtype=np.uint8)
        looks = [base ^ (rng.random(W) < noise).astype(np.uint8) for _ in range(3)]
        for n in NAMES:
            got, _ = strategy(n, pats, looks); o = out[n]
            if kind == "known": o["nk"] += 1; o["right"] += got == i; o["wrong"] += got is not None and got != i; o["unk"] += got is None
            elif kind == "sibling": o["ns"] += 1; o["sib"] += got is not None
            else: o["nr"] += 1; o["rnd"] += got is not None
    return out
if __name__ == "__main__":
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"{N} stored patterns in {F} families, {seeds} seeds, 1,500 queries of each kind per setting. right/wrong/unknown = share of known; sibling and random = share called known")
    print("spread (sibling distance) | noise p | strategy | right | wrong | unknown | sibling called known | random called known")
    for spread, label in ((12, "12 (~21)"), (6, "6 (~11)"), (3, "3 (~6)")):
        for noise in (0.03, 0.08, 0.15):
            rs = [run(s, spread, noise) for s in range(seeds)]
            for n in NAMES:
                g = lambda key, den: np.mean([r[n][key] / r[n][den] for r in rs])
                print(f"{label:<25} | {noise} | {n:<2} | {g('right','nk'):.3f} | {g('wrong','nk'):.3f} | {g('unk','nk'):.3f} | {g('sib','ns'):.3f} | {g('rnd','nr'):.3f}")
