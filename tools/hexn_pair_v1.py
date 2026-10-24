"""Two small noise-tolerant front ends feeding one larger EXACT model, against one large noisy model. Python model only; nothing here has run on a board.
Objects are PAIRS (a, b): a and b are each one of V stored 64-wire codes (so halves repeat), N pairs are stored out of V x V possible. A cue is a noisy copy of the pair (FLIPS wrong wires in EACH half).
PAIR: each front end finds the nearest of its V stored codes (limit THR, a tie for nearest means unknown), giving a clean code id or 'unknown'. The big model then looks up the id pair EXACTLY (no distance, no noise handling); unknown from either half means unknown.
SINGLE: one model holds the N 128-wire patterns in the hashed RAM tier (T=3 tables, K=11, B=4, limit 2*THR) and finds the nearest one under noise.
Codes are random (SPREAD=32 flips from a shared centre means no structure) or clustered: SPREAD=s flips from one of 20 centres, so many codes are alike (the hard case, like real similar data).
Queries: known pairs; UNSEEN COMBOS (both halves known codes but the pair never stored: must be unknown); and fully new pairs (new halves: must be unknown).
Costs (controller cycles, read together 9.9 + 2.22 x (T-1) MEASURED; the front ends are either read from RAM in parallel (RAM) or held in a fast compare-all block (1 cycle ASSUMED, needs V slots); the exact big lookup is ONE bucket read, 9.9 measured). Bits stored are counted directly. Usage: python3 tools/hexn_pair_v1.py [SEEDS]"""
import sys, numpy as np
THR, T, K, B, N, V = 8, 3, 11, 4, 4000, 200
def codes(rng, spread):
    if spread >= 32: return rng.integers(0, 2, (V, 64), dtype=np.uint8)
    cen = rng.integers(0, 2, (20, 64), dtype=np.uint8); c = cen[rng.integers(0, 20, V)].copy()
    for r in c: r[rng.choice(64, spread, replace=False)] ^= 1
    return c
def front(code, cue):
    d = (code != cue).sum(1); o = np.argsort(d); return int(o[0]) if d[o[0]] <= THR and d[o[1]] > d[o[0]] else None
def run(seed, spread, flips, q=1500):
    rng = np.random.default_rng(seed); C = codes(rng, spread); A = rng.integers(0, V, N * 2); Bb = rng.integers(0, V, N * 2)
    pairs = []; seen = set()
    for a, b in zip(A, Bb):
        if (a, b) not in seen: seen.add((a, b)); pairs.append((int(a), int(b)))
        if len(pairs) == N: break
    pat = np.array([np.concatenate([C[a], C[b]]) for a, b in pairs]); W = 128
    wires = [rng.choice(W, K, replace=False) for _ in range(T)]; pw = 1 << np.arange(K); tab = -np.ones((T, 1 << K, B), dtype=np.int32); ptr = np.zeros((T, 1 << K), dtype=np.int32)
    for i in range(N):
        for t in range(T): a = int(pat[i][wires[t]] @ pw); tab[t, a, ptr[t, a] % B] = i; ptr[t, a] += 1
    exact = {p: i for i, p in enumerate(pairs)}
    def noisy(x):
        x = x.copy(); x[rng.choice(64, flips, replace=False)] ^= 1; return x
    res = {}
    def count(kind, truth, ps, ss):
        r = res.setdefault(kind, dict(n=0, p_right=0, p_wrong=0, p_unk=0, s_right=0, s_wrong=0, s_unk=0)); r["n"] += 1
        for tag, ans in (("p", ps), ("s", ss)):
            if ans is None: r[tag + "_unk"] += 1
            elif ans == truth: r[tag + "_right"] += 1
            else: r[tag + "_wrong"] += 1
    for k in range(3 * q):
        kind = ("known", "unseen_combo", "new_pair")[k % 3]
        if kind == "known": i = int(rng.integers(0, N)); a, b = pairs[i]; ca, cb = C[a], C[b]; truth = i
        elif kind == "unseen_combo":
            while True:
                a, b = int(rng.integers(0, V)), int(rng.integers(0, V))
                if (a, b) not in exact: break
            ca, cb = C[a], C[b]; truth = None
        else: ca, cb = rng.integers(0, 2, 64, dtype=np.uint8), rng.integers(0, 2, 64, dtype=np.uint8); truth = None
        na, nb = noisy(ca), noisy(cb); fa, fb = front(C, na), front(C, nb)
        ps = None if fa is None or fb is None else exact.get((fa, fb))
        cue = np.concatenate([na, nb]); cand = set()
        for t in range(T): cand.update(tab[t, int(cue[wires[t]] @ pw)].tolist())
        cand.discard(-1); ss = None
        if cand:
            c = np.array(sorted(cand)); d = (pat[c] != cue).sum(1); j = int(d.argmin())
            if d[j] <= 2 * THR: ss = int(c[j])
        count(kind, truth, ps, ss)
    return res
if __name__ == "__main__":
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"{N} stored pairs of {V} codes, {seeds} seeds. For each query kind: right / wrong / unknown, as share of that kind. PAIR = two front ends + exact big lookup, SINGLE = one noisy 128-wire model.")
    print("codes | flips per half | kind | PAIR right wrong unk | SINGLE right wrong unk")
    for spread in (32, 12, 6):
        for flips in (2, 4):
            rs = [run(s, spread, flips) for s in range(seeds)]
            for kind in ("known", "unseen_combo", "new_pair"):
                g = lambda tag: [np.mean([r[kind][tag + x] / r[kind]["n"] for r in rs]) for x in ("_right", "_wrong", "_unk")]
                p, s = g("p"), g("s")
                print(f"{'random' if spread >= 32 else 'clustered, spread %d' % spread:<20} | {flips} | {kind:<12} | {p[0]:.3f} {p[1]:.3f} {p[2]:.3f} | {s[0]:.3f} {s[1]:.3f} {s[2]:.3f}")
    print("bits stored: SINGLE", N * 128, "| PAIR", V * 64 * 2, "(codes, two front ends) +", N * 2 * int(np.ceil(np.log2(V))), "(id pairs in the big model) =", V * 64 * 2 + N * 2 * int(np.ceil(np.log2(V))))
    print("cycles per lookup: SINGLE", round(9.9 + 2.22 * (T - 1), 1), "| PAIR with front ends in RAM", round(9.9 + 2.22 * (T - 1) + 9.9, 1), "(front ends in parallel, then one exact read) | PAIR with front ends in a fast block", round(1 + 9.9, 1))
