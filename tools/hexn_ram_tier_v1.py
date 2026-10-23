"""Hashed RAM tier for the Hex-N memory: Python model only (nothing here has run on a board).
Idea (Alan, 23 Oct): keep patterns in the card RAM, address = hash of the pattern, check the bucket by compare.
Model: T hash tables, each addressed by K chosen wires of the W-wire key (so similar patterns share an address),
each address holds a bucket of B patterns (FIFO replace). Lookup reads the bucket in every table, takes the
closest stored pattern, accepts it if within THR wires. Cost model: each table read = L cycles for the first word
plus B-1 burst words; tables read one after another (PAR=1) or in parallel banks (PAR=T).
The fabric block today (8 slots, compared at once) is the baseline: about 1 cycle.
CAPACITY ASSUMPTION: 8 Mbit RAM, one entry = W wires x 4 bits (the +-7 counters) -> entries = 8e6 / (4*W).
Usage: python3 tools/hexn_ram_tier_v1.py [--seeds 3]"""
import argparse, numpy as np

def build(rng, W, T, K, B, n):
    wires = [rng.choice(W, K, replace=False) for _ in range(T)]
    pw = 1 << np.arange(K)
    objs = rng.integers(0, 2, (n, W), dtype=np.uint8)
    tab = -np.ones((T, 1 << K, B), dtype=np.int32); ptr = np.zeros((T, 1 << K), dtype=np.int32)
    for t in range(T):
        addr = objs[:, wires[t]] @ pw
        for i in range(n):
            a = addr[i]; tab[t, a, ptr[t, a] % B] = i; ptr[t, a] += 1
    return objs, wires, pw, tab

def trial(rng, W, T, K, B, n, flips, thr, q=1500):
    objs, wires, pw, tab = build(rng, W, T, K, B, n)
    ok = wrong = miss = 0
    for _ in range(q):
        i = rng.integers(0, n); cue = objs[i].copy()
        if flips: cue[rng.choice(W, flips, replace=False)] ^= 1
        cand = set()
        for t in range(T):
            cand.update(tab[t, cue[wires[t]] @ pw].tolist())
        cand.discard(-1)
        if not cand: miss += 1; continue
        c = np.array(sorted(cand)); d = (objs[c] != cue).sum(1); j = d.argmin()
        if d[j] > thr: miss += 1
        elif c[j] == i: ok += 1
        elif (objs[c[j]] == objs[i]).all(): ok += 1   # identical pattern stored twice: same answer
        else: wrong += 1
    return ok / q, wrong / q, miss / q

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=3); a = ap.parse_args()
    LAT = (10, 30)  # first-word latency in cycles to test (unknown for the real card: ASSUMED, to be measured)
    print("W=key wires, T=tables, K=hash wires, B=bucket, n=stored, flips=noise; ok/wrong/miss are fractions; cycles=lookup cost at RAM latency 10 / 30, serial tables | fabric block today ~1 cycle")
    print("W  | T | K  | B | entries used/cap | n     | flips | ok   | wrong | miss | cycles@10 | cycles@30")
    for W in (18, 64):
        cap = int(8e6 // (4 * W))
        for T, K, B in ((1, 10, 4), (2, 10, 4), (3, 10, 4), (3, 12, 4), (4, 12, 8)):
            if T * (1 << K) * B > cap * 4: continue          # allow a table set up to 4x capacity as a sizing probe
            for n in (1000, 20000, 100000):
                if n > cap: continue
                for flips in (0, 1, 2, 3):
                    r = np.mean([trial(np.random.default_rng(s), W, T, K, B, n, flips, thr=max(3, W // 8), q=600) for s in range(a.seeds)], axis=0)
                    cyc = lambda L: T * (L + B - 1)
                    print(f"{W:<2} | {T} | {K:<2} | {B} | {T*(1<<K)*B:>7}/{cap:<7} | {n:<6}| {flips}     | {r[0]:.2f} | {r[1]:.3f} | {r[2]:.2f} | {cyc(10):<9} | {cyc(30)}")
if __name__ == "__main__": main()
