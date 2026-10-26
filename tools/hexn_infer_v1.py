"""hexn_infer_v1: the INFERENCE question with a graded reply, and its price: how often does the system 'see a face in the toast' (answer confidently on pure noise)? (ABSTRACT MODEL, not cells; Python only; new file.)
A store holds R learned routes (token sequences of length Lr over NTOK tokens), each with a goal (assumed already learned). A query is either a TRUE route seen through noise (each token wrong with chance p) or a RANDOM sequence of the same length (the toast: no route at all).
Reply policy with a closeness setting c (tokens allowed to disagree, 0 = exact only): find the stored route with the most agreeing tokens; answer its goal if it has at least Lr - c agreeing tokens AND is the unique best; otherwise 'unknown'.
Reported: on true queries right / wrong / unknown; on random queries the share that got an answer anyway (a false alarm). Averaged over many random route sets.
ASSUMPTIONS: routes are random distinct sequences; the sequence end is marked and its length is known; the store is already learned; tokens wrong independently.
Usage: python3 tools/hexn_infer_v1.py"""
import random
NTOK, R, GOALS = 8, 8, 3
def score(q, r): return sum(a == b for a, b in zip(q, r))
def reply(q, store, Lr, c):
    sc = sorted(((score(q, r), g) for r, g in store), key=lambda x: -x[0])
    best = sc[0][0]
    if best >= Lr - c and (len(sc) < 2 or sc[1][0] < best): return sc[0][1]
    return None
def trial(Lr, c, p, sets=300, per=100):
    right = wrong = unk = fa = tot = 0
    for s in range(sets):
        rnd = random.Random(s); routes = set()
        while len(routes) < R: routes.add(tuple(rnd.randrange(NTOK) for _ in range(Lr)))
        store = [(r, rnd.randrange(GOALS)) for r in routes]
        for _ in range(per):
            r, g = rnd.choice(store); q = tuple(t if rnd.random() >= p else rnd.randrange(NTOK) for t in r); a = reply(q, store, Lr, c)
            right += a == g; wrong += a is not None and a != g; unk += a is None
            toast = tuple(rnd.randrange(NTOK) for _ in range(Lr)); fa += reply(toast, store, Lr, c) is not None; tot += 1
    return right / tot, wrong / tot, unk / tot, fa / tot
if __name__ == "__main__":
    print(f"{R} routes over {NTOK} tokens; token noise p = 0.15; true queries: right/wrong/unknown;  toast (random sequence): share answered anyway")
    print("route length | closeness c | right  wrong  unknown | false alarm on toast")
    for Lr in (2, 3, 4, 5):
        for c in (0, 1, 2):
            if c >= Lr: continue
            r, w, u, fa = trial(Lr, c, 0.15); print(f"     {Lr}       |      {c}      | {r:.2f}   {w:.2f}   {u:.2f}   |  {fa:.2f}")
