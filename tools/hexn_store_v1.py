"""hexn_store_v1: the layer 2 STORE AND RETRIEVE system (model; Alan, 27 Oct 2026: do the store and retrieve first, it solidifies the basis of the idea, then add the reward goal part). Python only; no RTL yet; new file; uses the real routine recordings through hexn_layer2_v2 and the host levels from hexn_host_promote_v1.
What is stored: SEQUENCE ENTRIES (context of 1, 2 or 3 events, next event), each with a count of times seen (seen) and times its context was followed by something else (contra). Two tables with fixed capacity, as hardware would have:
 KNOWN  (capacity KCAP, 128: the three real runs need 76 pairs, runs 1 and 2 need 70): entries that are trusted. Retrieve reads only these.
 CAND   (capacity CCAP): candidates. Every pair (context, event) at levels 1 to K that is not yet known gets a sighting here; when it has N sightings inside the last W events (host-set; the rate rule of hexn_promote_v1) it is promoted to KNOWN and keeps its count. When CAND is full the weakest (lowest count, then oldest) is dropped. A sighting is counted either as an exact sliding window (exact=True) or the hardware-cheap TUMBLING form (a count and a start time, restarted when W has passed; exact=False).
Operations: load(seqs) (host trains the known table directly: every pair counted, as if N=1); retrieve(hist) -> (level, best next event, share of that context's count held by the best, total count at that context) from the longest known context; observe(hist, x, t) -> verdict 'ok' / 'contradiction' / 'novel' (the self-check, as hexn_anomaly_v1) and the store update: known entries seen+1, contradicted successors contra+1, unknown pairs get a sighting.
Time t is in events (a block of the routines is about 4 events, so the host's W in blocks times 4).
Limits: real data is three short runs; noise and repeated anomalies are injected; confidence here is the plain count share, nothing learned; no RTL; no reward.
Usage: python3 tools/hexn_store_v1.py"""
import os, sys, random, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_layer2_v2 as V, hexn_host_promote_v1 as HP
class Store:
    def __init__(s, K=3, N=3, W=80, KCAP=128, CCAP=32, exact=False):
        s.K, s.N, s.W, s.KCAP, s.CCAP, s.exact = K, N, W, KCAP, CCAP, exact
        s.known = {}      # (ctx, ev) -> [seen, contra]
        s.cand = {}       # (ctx, ev) -> [count, start] (tumbling) or list of times (exact)
        s.ctxs = collections.defaultdict(set)   # ctx -> successors known
        s.promoted = 0; s.dropped_c = 0; s.dropped_k = 0
    def _ctx(s, hist, j): return tuple(hist[-j:]) if len(hist) >= j else None
    def retrieve(s, hist):
        for j in range(s.K, 0, -1):
            c = s._ctx(hist, j)
            if c is not None and c in s.ctxs:
                tot = sum(s.known[(c, e)][0] for e in s.ctxs[c]); b = max(s.ctxs[c], key=lambda e: s.known[(c, e)][0])
                return j, b, s.known[(c, b)][0] / tot, tot
        return 0, None, 0.0, 0
    def verdict(s, hist, x):
        for j in range(s.K, 0, -1):
            c = s._ctx(hist, j)
            if c is not None and c in s.ctxs: return ("ok" if x in s.ctxs[c] else "contradiction"), j
        return "novel", 0
    def _add_known(s, key, seen, contra=0):
        if len(s.known) >= s.KCAP:
            v = min(s.known, key=lambda k: s.known[k][0]); s.ctxs[v[0]].discard(v[1])
            if not s.ctxs[v[0]]: del s.ctxs[v[0]]
            del s.known[v]; s.dropped_k += 1
        s.known[key] = [seen, contra]; s.ctxs[key[0]].add(key[1])
    def load(s, seqs):
        for q in seqs:
            for i in range(1, len(q)):
                for j in range(1, s.K + 1):
                    if i >= j:
                        key = (tuple(q[i - j:i]), q[i])
                        if key in s.known: s.known[key][0] += 1
                        else: s._add_known(key, 1)
    def _sight(s, key, t):
        if s.exact:
            L = [u for u in s.cand.get(key, []) if t - u < s.W] + [t]; n = len(L); val = L
        else:
            v = s.cand.get(key)
            val = [1, t] if v is None or t - v[1] >= s.W else [v[0] + 1, v[1]]; n = val[0]
        if n >= s.N:
            s.cand.pop(key, None); s._add_known(key, n); s.promoted += 1; return True
        if key not in s.cand and len(s.cand) >= s.CCAP:
            w = min(s.cand, key=lambda k: ((len(s.cand[k]) if s.exact else s.cand[k][0]), (s.cand[k][-1] if s.exact else s.cand[k][1])))
            del s.cand[w]; s.dropped_c += 1
        s.cand[key] = val; return False
    def observe(s, hist, x, t):
        v, lvl = s.verdict(hist, x)
        if v == "contradiction":
            c = s._ctx(hist, lvl)
            for e in s.ctxs[c]: s.known[(c, e)][1] += 1
        for j in range(1, s.K + 1):
            c = s._ctx(hist, j)
            if c is None: continue
            key = (c, x)
            if key in s.known: s.known[key][0] += 1
            else: s._sight(key, t)
        return v, lvl
def truth_pairs(pool, K=3, nblk=2000, seed=77):
    """every (context, event) pair that a clean random-order stream of the real blocks can produce"""
    rnd = random.Random(seed); q = []
    for _ in range(nblk): q += list(rnd.choice(pool))
    t = Store(K=K, KCAP=10000); t.load([q]); return set(t.known)
def run_stream(st, seq, t0=0, stats=None):
    """feed one pressed sequence; returns list of (event index, verdict) that were not ok, and next-event hits by level"""
    flags = []; hits = collections.Counter(); tries = collections.Counter()
    for i in range(1, len(seq)):
        lvl, b, p, tot = st.retrieve(seq[:i])
        if lvl: tries[lvl] += 1; hits[lvl] += (b == seq[i])
        v, _ = st.observe(seq[:i], seq[i], t0 + i)
        if v != "ok": flags.append((i + 1, v))
    return flags, hits, tries
def main():
    V.R = V.runs(); runs = [[k for k, _ in r] for r in V.R]; nm = lambda c: str(c - 11)
    print("A. REAL RUNS, host-loaded known table (as hexn_anomaly_v1, but unknown pairs go to the candidate store, never straight into the known table)")
    for test in range(3):
        st = Store(N=3, W=80); st.load([runs[j] for j in range(3) if j != test]); f, h, tr = run_stream(st, runs[test], 1000)
        print("  test run %d: flagged %s | known entries %d | candidates %d%s" % (test + 1, [(i, nm(runs[test][i - 1]), v) for i, v in f] or "none", len(st.known), len(st.cand), "" if not f else " (counts %s)" % sorted(v[0] if not st.exact else len(v) for v in st.cand.values())[-3:]))
    print("\nB. COLD START: empty store, learns only by the promotion rule (N sightings inside W events), runs 1 and 2 in turn, then run 3 as the test; next-event accuracy by context length used")
    for N, W in ((2, 80), (3, 80), (3, 160), (4, 160)):
        st = Store(N=N, W=W); t = 0
        for r in (0, 1): run_stream(st, runs[r], t); t += 100
        f, h, tr = run_stream(st, runs[2], t)
        print("  N=%d W=%3d: known %2d, promoted %2d | run 3 flags %s | hits by level %s" % (N, W, len(st.known), st.promoted, [(i, v) for i, v in f] or "none", {l: "%d/%d" % (h[l], tr[l]) for l in sorted(tr)}))
    print("\nC. REPEATED ANOMALY: an extra key 4 put before the last key of a block, repeated every G blocks inside a long stream of real routine blocks; host-loaded store, N=3, W=80 events (20 blocks)")
    rb = HP.real_blocks(); pool = list(set(b for run in rb[:2] for b in run)); base = [k for run in runs[:2] for k in run]; TRUE = truth_pairs(pool)
    print("  clean random-order stream of the 4 real blocks produces %d distinct pairs (runs 1 and 2 alone showed 70)" % len(TRUE))
    for G in (2, 4, 8, 16, 40):
        st = Store(N=3, W=80); st.load([base]); rnd = random.Random(3); seq = []; prom_at = None; t = 0; flags = 0
        for blk in range(300):
            b = rnd.choice(pool); seq += list(b)
            if blk and blk % G == 0: seq.insert(len(seq) - 1, 15)
        hist = []
        for i, x in enumerate(seq):
            if hist:
                kn = set(st.known); v, _ = st.observe(hist, x, i); flags += (v != "ok")
                if prom_at is None and st.promoted and any(k not in TRUE for k in set(st.known) - kn): prom_at = i // 4
            hist.append(x)
        print("  every %2d blocks (%d anomalies): flagged %3d events, anomaly first promoted at block %s" % (G, 299 // G, flags, prom_at if prom_at is not None else "never"))
    print("\nD. NOISE: random key inserted in a share r of blocks (real blocks, random order, 3000 blocks); false entries = known entries that clean data never produces; tumbling vs exact window; host-loaded true table, N=3")
    truekeys = TRUE
    print("  true pairs %d" % len(truekeys))
    print("  r    | W events | mode     | false entries | promoted | dropped cand | alarm events")
    for r in (0.1, 0.3, 0.6):
        for W in (40, 80, 320):
            for ex in (False, True):
                rnd = random.Random(9); st = Store(N=3, W=W, exact=ex, KCAP=256, CCAP=32); st.load([[k for b in rb[0] + rb[1] for k in b]]); seq = []
                for _ in range(3000):
                    b = list(rnd.choice(pool))
                    if rnd.random() < r: b.insert(rnd.randrange(len(b)), rnd.randrange(12, 18))
                    seq += b
                hist = []; al = 0
                for i, x in enumerate(seq):
                    if hist: al += st.observe(hist, x, i)[0] != "ok"
                    hist.append(x)
                print("  %.2f | %8d | %-8s | %13d | %8d | %12d | %d" % (r, W, "exact" if ex else "tumbling", len([k for k in st.known if k not in truekeys]), st.promoted, st.dropped_c, al))
def learn_new(ccap, r=0.3, seeds=20, N=3, W=80):
    """a new routine 1 5 3 7 arrives from block 200 (1 block in 6) in noise r; returns (mean block at which its pair is known, share of streams that learned it, mean false entries)"""
    rb = HP.real_blocks(); pool = list(set(b for run in rb[:2] for b in run)); E = (12, 16, 14, 18); TRUE = truth_pairs(pool + [E]); key = ((12, 16, 14), 18); base = [k for b in rb[0] + rb[1] for k in b]
    when = []; fal = 0
    for sd in range(seeds):
        rnd = random.Random(sd); st = Store(N=N, W=W, KCAP=256, CCAP=ccap); st.load([base]); hist = []; got = None; i = 0
        for blk in range(1500):
            b = list(E) if blk >= 200 and rnd.random() < 1 / 6 else list(rnd.choice(pool))
            if b != list(E) and rnd.random() < r: b.insert(rnd.randrange(len(b)), rnd.randrange(12, 18))
            for x in b:
                if hist: st.observe(hist, x, i)
                hist.append(x); i += 1
                if got is None and key in st.known: got = blk
        when.append(got); fal += len([k for k in st.known if k not in TRUE])
    ok = [w for w in when if w is not None]
    return (sum(ok) / len(ok) if ok else None), len(ok) / seeds, fal / seeds
def main_e():
    print("\nE. CANDIDATE CAPACITY: a new routine 1 5 3 7 from block 200 (1 block in 6) in 30% noise; N=3, W=80 events; known capacity 256; how soon its level-3 pair '1 5 3 -> 7' becomes known (20 streams)")
    print("  CCAP | learned in | at block (mean) | noise entries promoted (mean; entries no clean routine stream, including the new routine, produces)")
    for cc in (4, 8, 16, 32, 64, 128):
        b, sh, fa = learn_new(cc); print("  %4d | %9.0f%% | %15s | %.1f" % (cc, sh * 100, "%.0f" % b if b is not None else "-", fa))
if __name__ == "__main__": main(); main_e()
