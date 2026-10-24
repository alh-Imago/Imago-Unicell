"""(v2, clone of hexn_noise_fb_v1.py which is left untouched.) v1 showed that dropping disagreeing wires recovers detection but lets never-seen objects through (up to 64 percent for C), because with fewer known wires a chance match passes more easily. v2 adds E and C2 whose threshold is bounded BELOW by the chance level for the number of known wires k: 0.5 + 4.2 x 0.5 / sqrt(k) (about 4.2 sigma, for ~500 candidates); C2 = C plus that floor, E = two looks, mask, threshold = the chance floor only.
Two looks at the same sensor as a noise measurement that is fed back. Python model only; nothing here has run on a board; the store is a plain compare-all memory standing in for the Hex-N memory block, NOT the real block (no counters, no 8-slot limit).
N=500 stored 64-wire patterns. A look = the stored pattern with each wire flipped independently with probability p (the noise), a new independent draw per look. Query kinds: known objects, and never-seen random objects (must be unknown).
Recall, as the host policy does it: compare only over KNOWN wires; familiar when best match >= fam_t x known wires AND the best is strictly ahead of the second best.
Strategies (looks used in brackets):
 A  one look, fixed fam_t=0.75 (the current way) [1]
 B  two looks; a wire where they DISAGREE is made unknown, the rest taken as seen; fixed fam_t [2]
 C  as B, and the disagreement rate is turned into a noise estimate p_hat = (1-sqrt(1-2D))/2; fam_t is set from it (1 - p_hat - 3 sigma on the known count, never below 0.60); if p_hat is high (> 0.12) a third look is taken and the cue becomes the majority of the three on every wire [2 or 3]
 D  three looks, majority per wire, fixed fam_t (the odd-looks reference) [3]
Noise settings: fixed p, and a MIX where each lookup is quiet (p=0.03) or noisy (p=0.18) with equal chance and the system is not told which. Not modelled: a real change between the two looks (it would look like noise), and noise that is the same in both looks. Usage: python3 tools/hexn_noise_fb_v1.py [SEEDS]"""
import sys, numpy as np
N, W = 500, 64
NAMES = ("A", "B", "C", "C2", "D", "E")
def recall(pats, cue, known, fam_t):
    k = int(known.sum())
    if k < 8: return None
    s = ((pats == cue) & known).sum(1); o = np.argsort(-s); b, sec = s[o[0]], s[o[1]]
    return int(o[0]) if b >= fam_t * k and b > sec else None
def estimate(D): return (1 - np.sqrt(max(0.0, 1 - 2 * D))) / 2
def chance(k): return 0.5 + 4.2 * 0.5 / np.sqrt(max(1, k))
def strategy(name, pats, looks, fam_t=0.75):
    if name == "A": return recall(pats, looks[0], np.ones(W, bool), fam_t), 1
    if name == "D": return recall(pats, (sum(looks[:3]) >= 2).astype(np.uint8), np.ones(W, bool), fam_t), 3
    agree = looks[0] == looks[1]
    if name == "B": return recall(pats, looks[0], agree, fam_t), 2
    if name == "E": return recall(pats, looks[0], agree, chance(int(agree.sum()))), 2
    D = 1 - agree.mean(); ph = estimate(D); n = 2
    if ph > 0.12: cue, known, n = (sum(looks[:3]) >= 2).astype(np.uint8), np.ones(W, bool), 3
    else: cue, known = looks[0], agree
    k = max(1, int(known.sum())); t = max(0.60, 1 - ph - 3 * np.sqrt(max(ph * (1 - ph), 1e-4) / k))
    if name == "C2": t = max(t, chance(k))
    return recall(pats, cue, known, t), n
def run(seed, noise, q=1500):
    rng = np.random.default_rng(seed); pats = rng.integers(0, 2, (N, W), dtype=np.uint8)
    out = {n: dict(right=0, wrong=0, unk=0, fk=0, looks=0, nk=0, nn=0) for n in NAMES}
    for k in range(2 * q):
        known = k % 2 == 0; p = rng.choice([0.03, 0.18]) if noise == "mix" else noise
        if known: i = int(rng.integers(0, N)); base = pats[i]
        else: base = rng.integers(0, 2, W, dtype=np.uint8)
        looks = [base ^ (rng.random(W) < p).astype(np.uint8) for _ in range(3)]
        for n in NAMES:
            got, nl = strategy(n, pats, looks); o = out[n]; o["looks"] += nl
            if known: o["nk"] += 1; o["right"] += got == i; o["wrong"] += got is not None and got != i; o["unk"] += got is None
            else: o["nn"] += 1; o["fk"] += got is not None
    return out
if __name__ == "__main__":
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"{N} stored 64-wire patterns, {seeds} seeds, 1,500 known and 1,500 never-seen lookups per setting. right/wrong/unknown = share of known lookups; false known = share of never-seen called known")
    print("noise p per wire | strategy | right | wrong | unknown | false known | looks per lookup")
    for noise in (0.03, 0.08, 0.15, 0.25, "mix"):
        rs = [run(s, noise) for s in range(seeds)]
        for n in NAMES:
            g = lambda key, den: np.mean([r[n][key] / r[n][den] for r in rs])
            print(f"{str(noise):<16} | {n} | {g('right','nk'):.3f} | {g('wrong','nk'):.3f} | {g('unk','nk'):.3f} | {g('fk','nn'):.3f} | {np.mean([r[n]['looks'] for r in rs]) / 3000:.2f}")
