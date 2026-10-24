"""NEAR TERM + LONG TERM with movement between them (Python model only; nothing here has run on a board).
Near term = a fast block of S slots (least recently used leaves), all slots compared at once: 1 cycle (assumed, controller-clock cycles).
Long term = the hashed RAM table (T tables x 2^K buckets x B patterns, 64-wire keys, closest wins within THR wires). The RAM keeps a copy of everything.
RAM costs, controller cycles: a read of the T tables issued together = 9.9 + 2.22 x (T-1) (MEASURED 23 Oct, designs hexn_ram probe); a WRITE is ASSUMED to cost the same (not measured).
Movement policies: PROMOTE = copy a pattern from RAM into the fast block ('first' = on the first RAM hit, 'second' = only on a second RAM hit, which keeps a one-time scan out of the fast block);
UPDATE = a hit sometimes changes the stored pattern (learning): 'through' = write the RAM copy at once, 'back' = mark it dirty and write the RAM copy when the pattern leaves the fast block.
A pattern asked about that neither tier knows is NEW: it is stored in the RAM (and, as a new arrival, in the fast block).
Workloads (all with FLIPS noisy wires in each cue): 'zipf' = a few objects asked about often, the popular set changes half way; 'scan' = the same plus bursts of 64 objects each asked once; 'new' = the same plus 10 percent never-seen objects.
Metrics per lookup: fast-block hit rate, mean cycles, RAM reads and writes, right / wrong / unknown for objects that were stored, and for the never-seen objects the share called known (false known).
Usage: python3 tools/hexn_tiers_v1.py [SEEDS]"""
import sys, numpy as np
W, T, K, B, THR, FLIPS = 64, 3, 11, 4, 8, 2
RAM_COST = 9.9 + 2.22 * (T - 1)
def make(rng, n):
    objs = rng.integers(0, 2, (n, W), dtype=np.uint8)
    wires = [rng.choice(W, K, replace=False) for _ in range(T)]; pw = 1 << np.arange(K)
    tab = -np.ones((T, 1 << K, B), dtype=np.int32); ptr = np.zeros((T, 1 << K), dtype=np.int32)
    return objs, wires, pw, tab, ptr
def run(seed, workload, S, promote, update, n=4000, q=5000, zipf=1.0, upd_p=0.2, hot_known=None):
    rng = np.random.default_rng(seed)
    objs, wires, pw, tab, ptr = make(rng, n + q)                        # ids beyond n are 'never seen' objects, used by the 'new' workload
    stored = set()
    def ram_insert(i):
        for t in range(T):
            a = int(objs[i][wires[t]] @ pw); tab[t, a, ptr[t, a] % B] = i; ptr[t, a] += 1
        stored.add(i)
    for i in range(n): ram_insert(i)
    p = 1.0 / np.arange(1, n + 1) ** zipf; p /= p.sum(); order = [rng.permutation(n), rng.permutation(n)]
    hot = []; dirty = set(); touches = {}; cycles = 0.0; hits = ram_r = ram_w = 0
    right = wrong = unk = 0; known_q = new_q = false_known = 0; next_new = n; scan_left = 0; scan_ids = []
    def evict_check():
        nonlocal ram_w, cycles
        while len(hot) > S:
            v = hot.pop(0)
            if v in dirty: dirty.discard(v); ram_w += 1; cycles += RAM_COST      # write-back
            touches.pop(v, None)
    for k in range(q):
        is_new = False
        if scan_left == 0 and workload == "scan" and rng.random() < 0.01: scan_ids = list(rng.choice(n, 64, replace=False)); scan_left = 64
        if scan_left: i = int(scan_ids[64 - scan_left]); scan_left -= 1
        elif workload == "new" and rng.random() < 0.10: i = next_new; next_new += 1; is_new = True
        else: i = int(order[0 if k < q // 2 else 1][rng.choice(n, p=p)])
        cue = objs[i].copy(); cue[rng.choice(W, FLIPS, replace=False)] ^= 1
        cycles += 1
        got = None
        if hot:
            d = (objs[hot] != cue).sum(1); j = int(d.argmin())
            if d[j] <= THR: got = hot[j]; hits += 1; hot.append(hot.pop(j))
        if got is None:
            cycles += RAM_COST; ram_r += 1
            cand = set()
            for t in range(T): cand.update(tab[t, int(cue[wires[t]] @ pw)].tolist())
            cand.discard(-1)
            if cand:
                c = np.array(sorted(cand)); d = (objs[c] != cue).sum(1); j = int(d.argmin())
                if d[j] <= THR: got = int(c[j])
            if got is not None and S > 0:
                touches[got] = touches.get(got, 0) + 1
                if promote == "first" or touches[got] >= 2:
                    if got not in hot: hot.append(got)
                    evict_check()
        if is_new:
            new_q += 1
            if got is not None: false_known += 1
            else:
                ram_insert(i); ram_w += 1; cycles += RAM_COST
                if S > 0: hot.append(i); evict_check()
        else:
            known_q += 1
            if got is None: unk += 1
            elif got == i or (objs[got] == objs[i]).all(): right += 1
            else: wrong += 1
        if got is not None and not is_new and rng.random() < upd_p:                         # the pattern is updated (learning)
            if update == "through": ram_w += 1; cycles += RAM_COST
            elif got in hot: dirty.add(got)
            else: ram_w += 1; cycles += RAM_COST
    kq = max(1, known_q)
    return dict(hit=hits / q, cycles=cycles / q, ram_r=ram_r / q, ram_w=ram_w / q, right=right / kq, wrong=wrong / kq, unknown=unk / kq, false_known=false_known / max(1, new_q))
KEYS = ("hit", "cycles", "ram_r", "ram_w", "right", "wrong", "unknown", "false_known")
if __name__ == "__main__":
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    print("n=4000 stored objects, 5000 lookups, Zipf 1.0, 2 noisy wires per cue, hashed RAM T=3 K=11 B=4; cycles are controller cycles; WRITE cost assumed = read cost")
    print("workload | fast slots | promote | update  | " + " | ".join(KEYS))
    for wl in ("zipf", "scan", "new"):
        for S, promote, update in ((0, "first", "through"), (8, "first", "through"), (8, "second", "through"), (8, "second", "back"), (32, "first", "through"), (32, "second", "through"), (32, "second", "back"), (128, "second", "through"), (128, "second", "back")):
            r = [run(s, wl, S, promote, update) for s in range(seeds)]
            print(f"{wl:<8} | {S:<10} | {promote:<7} | {update:<7} | " + " | ".join("%.2f" % np.mean([x[k] for x in r]) for k in KEYS))
