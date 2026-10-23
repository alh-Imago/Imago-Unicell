"""Two tiers (Python model only, nothing on a board): the existing fast block as a BUFFER in front of the hashed RAM tier.
v1 (hexn_ram_tier_v1.py) is left untouched. Hot tier = S slots compared at once (about 1 cycle), least-recently-used replaced.
Cold tier = hashed RAM (T tables, K hash wires, bucket B), master copy of everything, so no write-back is needed in this model.
Lookup: compare the cue with the hot slots; hit if within THR wires. Miss: read the RAM, and copy the answer into the hot tier.
Workload: n objects, Zipf popularity (few objects asked about often), the popular set CHANGES half way through, cues have FLIPS noisy wires.
NOT modelled: the +-7 counters (plain binary patterns), writes/updates, RAM latency is ASSUMED (10 or 30 cycles), not measured.
Usage: python3 tools/hexn_ram_tier_v2.py [--seeds 3]"""
import argparse, numpy as np
import hexn_ram_tier_v1 as R

def run(seed, W=64, T=3, K=11, B=4, n=5000, S=8, zipf=1.0, flips=2, q=6000, L=10, par=False):
    rng = np.random.default_rng(seed)
    objs, wires, pw, tab = R.build(rng, W, T, K, B, n)
    thr = max(3, W // 8)
    p = 1.0 / np.arange(1, n + 1) ** zipf; p /= p.sum()
    rank_to_obj = [rng.permutation(n), rng.permutation(n)]            # popularity order, reshuffled half way
    hot = []                                                          # list of object ids, most recent last
    hits = ok = wrong = miss = 0; cycles = 0
    ram_cost = (L + B - 1) * (1 if par else T)
    for k in range(q):
        i = rank_to_obj[0 if k < q // 2 else 1][rng.choice(n, p=p)]
        cue = objs[i].copy()
        if flips: cue[rng.choice(W, flips, replace=False)] ^= 1
        cycles += 1                                                   # the compare against the hot slots
        if hot:
            d = (objs[hot] != cue).sum(1); j = d.argmin()
            if d[j] <= thr:
                hits += 1; got = hot.pop(j) if False else hot[j]; hot.append(hot.pop(j))
                ok += (got == i); wrong += (got != i); continue
        cycles += ram_cost
        cand = set()
        for t in range(T): cand.update(tab[t, cue[wires[t]] @ pw].tolist())
        cand.discard(-1)
        if not cand: miss += 1; continue
        c = np.array(sorted(cand)); d = (objs[c] != cue).sum(1); j = d.argmin()
        if d[j] > thr: miss += 1; continue
        got = int(c[j]); ok += (got == i); wrong += (got != i)
        if S > 0:
            if got in hot: hot.remove(got)
            hot.append(got)
            if len(hot) > S: hot.pop(0)                               # least recently used leaves
    return hits / q, ok / q, wrong / q, miss / q, cycles / q

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=3); a = ap.parse_args()
    print("n=5000 objects, W=64, RAM tier T=3 K=11 B=4 (24,576 entries, fits the assumed 8 Mbit), 2 noisy wires per cue, popular set changes half way")
    print("hot slots | zipf | RAM latency | tables | hot hit rate | right | wrong | miss | mean cycles per lookup")
    for S in (0, 8, 32, 128):
        for zipf in (0.8, 1.0, 1.3):
            for L, par in ((10, False), (30, False), (30, True)):
                r = np.mean([run(s, S=S, zipf=zipf, L=L, par=par) for s in range(a.seeds)], axis=0)
                print(f"{S:<9} | {zipf} | {L:<11} | {'parallel' if par else 'serial':<8} | {r[0]:.2f} | {r[1]:.2f} | {r[2]:.3f} | {r[3]:.2f} | {r[4]:.1f}")
if __name__ == "__main__": main()
