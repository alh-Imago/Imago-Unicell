"""hexn_conf_v1: LEARNED CONFIDENCE per stored route sets how loose a match may be (ABSTRACT MODEL, not cells; Python only; new file; imports hexn_infer_v1.py, untouched).
Same world as hexn_infer_v1 (R=8 routes over 8 tokens, route length Lr, token noise p=0.15) but as an ONLINE STREAM: 70 percent of queries are a true route through noise, 30 percent are random sequences (toast). After every answered query the OUTCOME arrives (assumed always): right +1 to the matched route's confidence, wrong -2 (kept 0..7).
Policy 'learned': a route may be matched with c=1 token disagreeing only when its confidence >= T (default 3); otherwise exact match only. Compared with fixed c=0 and fixed c=1. Score per query: right +1, wrong -0.5 (also an answer on toast), unknown 0.
ASSUMPTIONS: the store (routes and goals) is given, only the confidence is learned; the outcome of every answer arrives; the toast share is fixed at 30 percent; hand-built numbers.
Usage: python3 tools/hexn_conf_v1.py"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_infer_v1 as I
def stream(Lr, policy, seed, n=4000, p=0.15, T=3):
    rnd = random.Random(seed); routes = set()
    while len(routes) < I.R: routes.add(tuple(rnd.randrange(I.NTOK) for _ in range(Lr)))
    store = [(r, rnd.randrange(I.GOALS)) for r in routes]; conf = [0] * I.R; stat = {"t": 0, "right": 0, "wrong": 0, "toast": 0, "fa": 0, "score": 0.0, "n": 0}
    for i in range(n):
        toast = rnd.random() < 0.3
        if toast: q = tuple(rnd.randrange(I.NTOK) for _ in range(Lr)); g = None
        else: j = rnd.randrange(I.R); q = tuple(t if rnd.random() >= p else rnd.randrange(I.NTOK) for t in store[j][0]); g = store[j][1]
        sc = sorted(((I.score(q, store[k][0]), k) for k in range(I.R)), reverse=True); best, k = sc[0]; unique = sc[1][0] < best
        c = {"fixed0": 0, "fixed1": 1, "learned": (1 if conf[k] >= T else 0)}[policy]
        ans = store[k][1] if (best >= Lr - c and unique) else None
        if ans is not None: conf[k] = min(7, conf[k] + 1) if (not toast and ans == g) else max(0, conf[k] - 2)
        if i >= n - 1500:
            stat["n"] += 1; stat["toast"] += toast
            if ans is None: continue
            if toast: stat["fa"] += 1; stat["score"] -= 0.5
            elif ans == g: stat["right"] += 1; stat["score"] += 1.0
            else: stat["wrong"] += 1; stat["score"] -= 0.5
    return stat
if __name__ == "__main__":
    seeds = 100
    print(f"online stream, 70 percent true routes (noise p = 0.15) / 30 percent toast, last 1500 of 4000 queries, {seeds} route sets; per query: right / wrong on true routes, false alarm on toast (share of ALL queries), score (right +1, wrong -0.5, false alarm -0.5)")
    print("Lr | policy  | right  wrong  false-alarm | score")
    for Lr in (2, 3, 4, 5):
        for pol in ("fixed0", "fixed1", "learned"):
            tot = {"right": 0, "wrong": 0, "fa": 0, "score": 0.0, "n": 0}
            for s in range(seeds):
                r = stream(Lr, pol, s)
                for k in tot: tot[k] += r[k]
            n = tot["n"]; print(f" {Lr} | {pol:7s} | {tot['right']/n:.2f}   {tot['wrong']/n:.2f}   {tot['fa']/n:.2f}        | {tot['score']/n:+.2f}")
