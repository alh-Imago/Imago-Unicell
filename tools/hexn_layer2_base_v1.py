"""Hex-N LAYER 2 against SIMPLE SEQUENCE PREDICTORS, and where it may lose information. PYTHON MODEL ONLY (new file, 30 Oct 2026; no RTL, nothing on a card).
Alan, 30 Oct 22:59 (going out): 'see if there is anything similar that can be done with layer 2' = the checks made on layer 1 (baseline, information lost, cheap fixes).
Layer 2 here is the BIT-TRUE MODEL of the store (tools/hexn_store_v3.py, StoreV3: contexts of the last 1, 2 and 3 events, entries (context, next event, seen, contra), the longest known context
gives the prediction, the best follower = highest 'seen' (ties: lower event); a new pair must be seen N times within W events before it is stored; the table holds KCAP entries and drops the
lowest-'seen' entry when full; verdict 0 ok / 1 contradiction / 2 novel). The store rules are used UNCHANGED for the 'store' arms; variants only subclass it.
Simple predictors (textbook, written here): last = repeat the last event; freq = the most frequent event so far; ngram-k = count table over the last k events with back-off to shorter ones, learns every pair at once, best follower = highest count (ties: lower event).
Streams (alphabet A = 6): ORDER2 = next event is a fixed function of the last TWO events with probability 0.9, else a random event (order-1 cannot predict it); NOISE = the same plus a random event inserted after each event with probability 0.1 (observation noise: it also spoils the contexts);
SWITCH = the function changes at event 400. Scores are PREQUENTIAL (each event is predicted before it is seen), no prediction counts as wrong, mean of 25 seeds; windows of events given.
Real data: the three IR routine recordings (as tools/hexn_layer2_v2.py), leave one run out."""
import argparse, collections, os, random, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_store_v3 as S3

A = 6
class Ngram:
    def __init__(s, k, decay=0): s.k = k; s.t = collections.defaultdict(collections.Counter); s.h = []; s.decay = decay
    def predict(s):
        for j in range(min(s.k, len(s.h)), 0, -1):
            c = s.t.get(tuple(s.h[-j:]))
            if c: return min(c, key=lambda e: (-c[e], e))
        return None
    def observe(s, ev):
        for j in range(1, min(s.k, len(s.h)) + 1):
            c = s.t[tuple(s.h[-j:])]
            if s.decay and c and ev not in c:                       # forgetting: a surprise at this context weakens the old followers
                for e in list(c): c[e] -= (c[e] * s.decay) // 4
            c[ev] += 1
        s.h.append(ev); s.h = s.h[-3:]
    def flag(s, ev):   # True = surprise: the event was never seen after the longest known context
        for j in range(min(s.k, len(s.h)), 0, -1):
            c = s.t.get(tuple(s.h[-j:]))
            if c: return ev not in c
        return True
class Last:
    def __init__(s): s.h = None
    def predict(s): return s.h
    def observe(s, ev): s.h = ev
class Freq:
    def __init__(s): s.c = collections.Counter()
    def predict(s): return min(s.c, key=lambda e: (-s.c[e], e)) if s.c else None
    def observe(s, ev): s.c[ev] += 1
class Store(S3.StoreV3):
    """The layer 2 store. score='seen' is the rule as built; 'net' picks the follower with the highest seen minus contra; decay forgets old followers on a contradiction."""
    def __init__(s, N=3, W=80, KCAP=128, score="seen", decay=0): super().__init__(N=N, W=W, KCAP=KCAP); s.score = score; s.dec = decay; s.t = 0
    def _scan(s, ev):
        r = super()._scan(ev)
        if s.score == "net":
            for j in r:
                ctx = s._ctx(j); es = [e for e in s.k if e and e[0][0] == j and e[0][1] == ctx]
                b = min(es, key=lambda e: (-(e[1] - e[2]), e[0][2])); r[j]["bev"] = b[0][2]; r[j]["bseen"] = b[1]
        return r
    def predict(s):
        o = S3.StoreV3.step(s, S3.RD, 0, s.t); return o["pbest"] if o["plevel"] else None
    def verdict(s, ev): return S3.StoreV3.step(s, S3.RD, ev, s.t)["verdict"]
    def observe(s, ev):
        if s.dec and s.hist:
            sc = s._scan(ev); lv = max(sc) if sc else 0
            if lv and not sc[lv]["ex"]:
                ctx = s._ctx(lv)
                for e in s.k:
                    if e and e[0][0] == lv and e[0][1] == ctx: e[1] = max(1, e[1] - ((e[1] * s.dec) // 4))
        S3.StoreV3.step(s, S3.OBS, ev, s.t); s.t += 1
    def flag(s, ev): return s.verdict(ev) != 0

class StoreLRU(Store):
    """As Store, but when the table is full the entry dropped is the LEAST RECENTLY USED one (a hit or an add refreshes it), not the one with the lowest 'seen'."""
    def __init__(s, **kw): super().__init__(**kw); s.last = [0] * s.KCAP
    def _klook(s, key):
        hit, free, vic = super()._klook(key); live = [i for i, e in enumerate(s.k) if e]
        vic = min(live, key=lambda i: (s.last[i], i)) if live else None
        if hit is not None: s.last[hit] = s.t
        return hit, free, vic
    def _addk(s, key, seen, free, vic): i = super()._addk(key, seen, free, vic); s.last[i] = s.t; return i

def table(rnd): return [[rnd.randrange(A) for _ in range(A)] for _ in range(A)]
def stream(seed, kind, n=700):
    rnd = random.Random(seed); T1, T2 = table(rnd), table(rnd); ev = [rnd.randrange(A), rnd.randrange(A)]; injected = [False, False]
    while len(ev) < n:
        T = T2 if (kind == "SWITCH" and len(ev) >= 400) else T1
        e = T[ev[-2]][ev[-1]] if rnd.random() < 0.9 else rnd.randrange(A); ev.append(e); injected.append(False)
        if kind == "NOISE" and rnd.random() < 0.1: ev.append(rnd.randrange(A)); injected.append(True)
    return ev[:n]

def preq(model, ev, spans):
    ok = [0] * len(spans); cnt = [0] * len(spans)
    for i, e in enumerate(ev):
        p = model.predict()
        for k, (a, b) in enumerate(spans):
            if a <= i < b: ok[k] += (p == e); cnt[k] += 1
        model.observe(e)
    return [o / c for o, c in zip(ok, cnt)]

def anomaly(model_f, seed, n=700, p=0.05):
    """After 400 events of ORDER2 learning, replace 5 percent of events by a random OTHER event; flag = the model's surprise signal. Returns (share of injected events flagged, share of normal events flagged)."""
    rnd = random.Random(seed); T = table(rnd); m = model_f(); ev = [rnd.randrange(A), rnd.randrange(A)]; hit = fa = ni = nn = 0
    for i in range(n):
        if i >= 2:
            true = T[ev[-2]][ev[-1]] if rnd.random() < 0.9 else rnd.randrange(A); e = true
            inj = i >= 400 and rnd.random() < p
            if inj: e = rnd.choice([x for x in range(A) if x != true])
            ev.append(e)
        else: e = ev[i]; inj = False
        if i >= 400:
            f = m.flag(e)
            if inj: ni += 1; hit += f
            else: nn += 1; fa += f
        m.observe(e)
    return hit / max(1, ni), fa / max(1, nn)

ARMS = {"last": Last, "freq": Freq, "ngram1": lambda: Ngram(1), "ngram2": lambda: Ngram(2), "ngram3": lambda: Ngram(3),
        "store N=3": lambda: Store(N=3), "store N=2": lambda: Store(N=2), "store N=1": lambda: Store(N=1), "store N=3 KCAP 1024": lambda: Store(N=3, KCAP=1024),
        "store N=1 KCAP 1024": lambda: Store(N=1, KCAP=1024), "store net score": lambda: Store(N=1, KCAP=1024, score="net"), "store decay": lambda: Store(N=1, KCAP=1024, decay=2), "store N=1 KCAP 128 LRU": lambda: StoreLRU(N=1, KCAP=128), "store N=3 KCAP 128 LRU": lambda: StoreLRU(N=3, KCAP=128), "ngram3 decay": lambda: Ngram(3, decay=2)}

def reset(m):
    if isinstance(m, Ngram): m.h = []
    else: S3.StoreV3.step(m, S3.CLR)

def real(seeds=0):
    import hexn_layer2_v2 as V
    V.R = V.runs(); runs = [[k - 12 for k, _ in r] for r in V.R]; GOALS = (18 - 12, 19 - 12); out = {}
    for name, f in (("ngram1", lambda: Ngram(1)), ("ngram2", lambda: Ngram(2)), ("ngram3", lambda: Ngram(3)), ("store N=3 (learns by seeing)", lambda: Store(N=3, KCAP=1024)), ("store N=2", lambda: Store(N=2, KCAP=1024)), ("store N=1", lambda: Store(N=1, KCAP=1024))):
        a = g = ta = tg = 0
        for hold in range(3):
            m = f()
            for i, r in enumerate(runs):
                if i == hold: continue
                reset(m)
                for e in r: m.observe(e)
            reset(m)
            for e in runs[hold]:
                p = m.predict(); ta += 1; a += (p == e)
                if e in GOALS: tg += 1; g += (p == e)
                m.observe(e)
        out[name] = (a / ta, g / max(1, tg))
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--seeds", type=int, default=25); ap.add_argument("--only", default="", help="comma list of arm names to run (skips the flag and real parts)"); a = ap.parse_args()
    if a.only:
        for kind, spans in (("ORDER2", [(100, 200), (300, 700)]), ("SWITCH", [(300, 400), (400, 500), (500, 700)])):
            for name in a.only.split(","):
                rs = [preq(ARMS[name](), stream(x, kind), spans) for x in range(a.seeds)]; print(f"{kind:7s} {name:24s} " + "  ".join(f"{st.mean(r[i] for r in rs):.3f}" for i in range(len(spans))), flush=True)
        raise SystemExit
    for kind, spans, lab in (("ORDER2", [(100, 200), (300, 700)], "events 100-200 | 300-700"), ("NOISE", [(100, 200), (300, 700)], "events 100-200 | 300-700"), ("SWITCH", [(300, 400), (400, 500), (500, 700)], "300-400 (before) | 400-500 | 500-700 (after the switch at 400)")):
        print(f"\n{kind}: prequential next-event accuracy ({lab}); {a.seeds} seeds; chance = {1/A:.2f}")
        for name, f in ARMS.items():
            rs = [preq(f(), stream(s, kind), spans) for s in range(a.seeds)]
            print(f"  {name:22s} " + "  ".join(f"{st.mean(r[i] for r in rs):.3f}" for i in range(len(spans))), flush=True)
    print(f"\nSURPRISE FLAGS after learning (5 percent of events replaced by a random other event; {a.seeds} seeds): share of injected events flagged | share of normal events flagged")
    for name, f in (("ngram3 'never seen after this context'", lambda: Ngram(3)), ("store verdict 1 or 2", lambda: Store(N=1, KCAP=1024)), ("store N=3 verdict", lambda: Store(N=3, KCAP=1024))):
        rs = [anomaly(f, s) for s in range(a.seeds)]; print(f"  {name:40s} {st.mean(r[0] for r in rs):.3f} | {st.mean(r[1] for r in rs):.3f}")
    print("\nREAL IR routine recordings, leave one run out (all events | goal events):")
    for k, (x, y) in real().items(): print(f"  {k:30s} {x:.3f} | {y:.3f}")
