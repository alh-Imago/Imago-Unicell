"""hexn_host_promote_v1: the HOST ROUTINE that picks the promotion level (N sightings inside W blocks) from a training stream (Alan, 27 Oct 2026: the level is set by the host and must follow the data analysed). Python only; no RTL; new file; builds on hexn_promote_v1's rate rule.
What it does, given a training stream of blocks and the set of known blocks:
 1. MEASURE: n blocks, anomaly rate a (blocks not known), and how often each anomaly variant occurs.
 2. If fewer than MIN_ANOM anomalies were seen it says so and returns the DEFAULT (N=3, W=20): there is not enough data to set it from.
 3. Otherwise it simulates every (N, W) on the measured anomaly mix and keeps those whose false promotions are at or under TARGET per 1000 blocks; of those it takes the one most likely to catch a REAL new routine that turns up at 1 block in M (default M=12, i.e. the slowest new routine we still want caught), ties to the smaller N then smaller W.
Real data: blocks are the real routine blocks from the three recorded routine runs (keys end at goal codes 18/19; key code = key+11). Noise is injected: one random key code 12..17 inserted into a share r of blocks. Validation draws a FRESH stream with the same noise plus a new routine from block 200 and reports the false promotions per 1000 and the blocks to promote the new routine at the chosen level, against the default level.
Limits: noise is injected, not measured (only one real anomaly exists, run 3's extra 4); the variant frequencies are taken from the training stream as seen (unseen variants are not allowed for, so a short training stream under-counts repeats); blocks compared whole; counts forgotten after W blocks.
Usage: python3 tools/hexn_host_promote_v1.py"""
import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer2_v2 as V
GOALS = (18, 19); MIN_ANOM = 10; DEFAULT = (3, 20); NS = (2, 3, 4); WS = (10, 20, 40, 80, 160)
def blocks_of(keys):
    out, cur = [], []
    for k in keys:
        cur.append(k)
        if k in GOALS: out.append(tuple(cur)); cur = []
    return out
def real_blocks():
    V.R = V.runs(); return [blocks_of([k for k, _ in r]) for r in V.R]
def measure(blocks, known):
    cnt = {}
    for b in blocks:
        if b not in known: cnt[b] = cnt.get(b, 0) + 1
    na = sum(cnt.values()); return len(blocks), na / max(1, len(blocks)), cnt
def _promoted(arrivals, N, W):
    """arrivals: block numbers of one variant; True if N of them fall inside W blocks."""
    return any(arrivals[i + N - 1] - arrivals[i] < W for i in range(len(arrivals) - N + 1))
def false_rate(a, cnt, N, W, rnd, nblk=3000, reps=30):
    items = list(cnt.items()); tot = sum(c for _, c in items); fp = 0
    for _ in range(reps):
        arr = {}
        for i in range(nblk):
            if rnd.random() < a:
                x = rnd.random() * tot; acc = 0
                for b, c in items:
                    acc += c
                    if x < acc: arr.setdefault(b, []).append(i); break
        fp += sum(1 for L in arr.values() if _promoted(L, N, W))
    return fp / reps / nblk * 1000
def detect_prob(M, N, W, rnd, horizon=600, reps=300):
    ok = 0
    for _ in range(reps):
        arr = [i for i in range(horizon) if rnd.random() < 1 / M]; ok += _promoted(arr, N, W) if len(arr) >= N else 0
    return ok / reps
def choose(blocks, known, M=12, target=1.0, seed=5):
    n, a, cnt = measure(blocks, known); na = sum(cnt.values())
    if na < MIN_ANOM: return dict(N=DEFAULT[0], W=DEFAULT[1], source="default (only %d anomalies seen, need %d)" % (na, MIN_ANOM), a=a, variants=len(cnt))
    rnd = random.Random(seed); best = None
    for N in NS:
        for W in WS:
            fr = false_rate(a, cnt, N, W, rnd); 
            if fr > target: continue
            dp = detect_prob(M, N, W, rnd); key = (-round(dp, 2), N, W)
            if best is None or key < best[0]: best = (key, N, W, fr, dp)
    if best is None: return dict(N=max(NS), W=min(WS), source="strictest level (no setting met the target)", a=a, variants=len(cnt))
    return dict(N=best[1], W=best[2], source="from data", a=a, variants=len(cnt), false_model=best[3], detect=best[4])
def make_stream(pool, rnd, r, nblk, new=None, new_from=200):
    out = []
    for i in range(nblk):
        if new and i >= new_from and rnd.random() < 1 / 6: out.append((new, "E")); continue
        b = rnd.choice(pool); kind = "R"
        if rnd.random() < r:
            p = rnd.randrange(len(b)); b = b[:p] + (rnd.randrange(12, 18),) + b[p:]; kind = "N"
        out.append((b, kind))
    return out
def evaluate(stream, known, N, W):
    known = set(known); seen = {}; fp = 0; prom = None
    for i, (b, kind) in enumerate(stream):
        if b in known: continue
        L = [t for t in seen.get(b, []) if i - t < W] + [i]; seen[b] = L
        if len(L) >= N:
            known.add(b)
            if kind == "N": fp += 1
            if kind == "E" and prom is None: prom = i
    return fp / len(stream) * 1000, prom
def main():
    rb = real_blocks(); pool = list(set(b for run in rb[:2] for b in run)); known = set(pool)
    print("known routine blocks:", len(pool), "| real blocks per run:", [len(x) for x in rb])
    new = (12, 16, 14, 18)   # new routine: key 1, key 5, key 3, goal 7
    print("\nr = injected noise share; level chosen by the host from a 1500-block training stream; checked on a fresh 3000-block stream (30 streams) with a new routine from block 200")
    print(" r    | host choice               | false/1000 (host) | new routine at block (host) | false/1000 (default N=3,W=20) | (default) block")
    for r in (0.02, 0.1, 0.3, 0.6):
        tr = [b for b, _ in make_stream(pool, random.Random(11), r, 1500)]
        ch = choose(tr, known)
        fh = ph = fd = pd = 0.0; nh = nd = 0
        for s in range(30):
            st = make_stream(pool, random.Random(1000 + s), r, 3000, new)
            a, b = evaluate(st, known, ch["N"], ch["W"]); fh += a; nh += b is not None; ph += (b if b is not None else 3000)
            a, b = evaluate(st, known, *DEFAULT); fd += a; nd += b is not None; pd += (b if b is not None else 3000)
        print(" %.2f | N=%d W=%-3d %-14s | %17.3f | %27.0f | %29.3f | %.0f" % (r, ch["N"], ch["W"], "(%s)" % ch["source"].split(" ")[0], fh / 30, ph / 30, fd / 30, pd / 30))
    print("\nreal run 3 as it was recorded (one real anomaly, the extra 4): the host has too few anomalies, so:")
    print(" ", choose(rb[2], set(b for run in rb[:2] for b in run)))
if __name__ == "__main__": main()
