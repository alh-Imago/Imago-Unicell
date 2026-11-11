"""hexn_recall_pool_v3 (11 Nov 2026): the pool's monitor with CONFIDENCE WEIGHTING and an INPUT CHECK. Alan 14:00: apply the confidence weighting; is there a way to test the inputs, to see if they are in bounds or how damaged
they are? Direction doc section 87. Same model as hexn_recall_pool_v1/v2 (untouched): 4 blocks (3-layer network + own map blocks), 16 large maps of 4 local codes, one round of feedback, a block's own answer never used for its own hint.
Each block now gets a WEIGHT 0, 1 or 2, by one of two tests that need no knowledge of the right answer:
  match  : from the block's own recall: 2 if its best overlap score is at least 16 (of 32) and beats the second best by at least 4; 1 if the best is at least 8; else 0
  input  : from the INPUT, before any cell fires: the number of events that arrived in the run, against the block's normal count (the mean over the runs its map blocks were made from): 2 if at least 3/4 of normal,
           1 if at least 1/2, else 0 (a counter and two comparisons; 3/4 and 1/2 are shifts and adds)
  both   : the smaller of the two
Monitor rules compared on the SAME runs:
  plain    : section 80: every block's vote counts 1; hint bonus 4 if 2 of the other 3 agree, 8 if all 3
  weighted : votes count their weight; for block i the other blocks' weights are added per large map; best sum below 2: no hint; below 4: bonus 4; else 8. The RECEIVER's own weight scales the bonus: weight 0 doubles it
             (a block that knows it is blind listens), weight 2 halves it (a block that is sure resists).
Cases: all blocks alike (10/30/50/70% dropped); 1, 2, 3 of 4 blocks at 90% (others 10%); novel combinations (30%).
Usage: python3 tools/hexn_recall_pool_v3.py [SEEDS]"""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_recall_blocks_v1 as R, hexn_recall_pool_v1 as P1
NB, NL, NS, NTEST, DROPS = P1.NB, P1.NL, P1.NS, P1.NTEST, P1.DROPS
best = P1.best
RULES = ("plain", "weighted: match", "weighted: input", "weighted: both")


def w_match(sc):
    o = sorted(sc, reverse=True); return 2 if o[0] >= 16 and o[0] - o[1] >= 4 else 1 if o[0] >= 8 else 0


def w_input(nev, normal): return 2 if 4 * nev >= 3 * normal else 1 if 2 * nev >= normal else 0


def monitor_w(scs, maps, w):
    top = [best(s) for s in scs]; new = []
    for i in range(NB):
        v = [sum(w[b] for b in range(NB) if b != i and m[b] == top[b]) for m in maps]; mx = max(v)
        if mx < 2: new.append(top[i]); continue
        bonus = (4 if mx < 4 else 8); bonus = bonus * 2 if w[i] == 0 else bonus // 2 if w[i] == 2 else bonus
        want = {maps[j][i] for j in range(NL) if v[j] == mx}
        new.append(best([scs[i][c] + (bonus if c in want else 0) for c in range(T.NPAT)]))
    return new


def main(seeds):
    res = {}; wstat = {}
    def acc(case, rule, key, ok, n=1):
        a = res.setdefault(case, {}).setdefault(rule, {}).setdefault(key, [0, 0]); a[0] += ok; a[1] += n
    for s in seeds:
        pool = []; normal = []
        for b in range(NB):
            pats = [B.pattern(random.Random(100 + 50 * b + k)) for k in range(T.NPAT)]; net = R.build(10 * s + b, pats); kb = [x[0] for x in R.make_blocks(net, pats)]
            normal.append(sum(sum(len(v) for v in B.noisy(pats[k], random.Random(31000 + 13 * k + j), drop=0.1, jit=3).values()) for k in range(T.NPAT) for j in range(5)) / (5.0 * T.NPAT))     # the runs the map blocks were made from
            d_ = {}
            for k in range(T.NPAT):
                for d in DROPS:
                    runs = []
                    for j in range(NS):
                        ev = B.noisy(pats[k], random.Random(71000 + 1000 * b + 97 * k + j + int(1000 * d)), drop=d, jit=3); m2 = B.map_of(T.fresh_run(net, ev), (2,))
                        runs.append(([R.acc_int(m2, x) for x in kb], sum(len(v) for v in ev.values())))
                    d_[(k, d)] = runs
            pool.append(d_)
        r = random.Random(500 + s); maps = P1.large_maps(r); stored = set(maps); novel = []
        while len(novel) < NL:
            t = tuple(r.randrange(T.NPAT) for _ in range(NB))
            if t not in stored and t not in novel: novel.append(t)
        def one(case, truth, drops, j_large, nbad=0):
            pick = [pool[b][(truth[b], drops[b])][r.randrange(NS)] for b in range(NB)]; scs = [p[0] for p in pick]; top = [best(x) for x in scs]
            wm = [w_match(x) for x in scs]; wi = [w_input(pick[b][1], normal[b]) for b in range(NB)]
            for b in range(NB):
                st = wstat.setdefault(drops[b], [0, 0, 0, 0, 0]); st[0] += 1; st[1] += wm[b]; st[2] += wi[b]; st[3] += (wm[b] == 2 and top[b] != truth[b]); st[4] += (wi[b] == 2)
            for rule in RULES:
                w = [1] * NB if rule == "plain" else wm if rule.endswith("match") else wi if rule.endswith("input") else [min(a, c) for a, c in zip(wm, wi)]
                new = P1.monitor(scs, maps)[0] if rule == "plain" else monitor_w(scs, maps, w)
                acc(case, rule, "local", sum(new[b] == truth[b] for b in range(NB)), NB); acc(case, rule, "bad", sum(new[b] == truth[b] for b in range(nbad)), nbad)
                acc(case, rule, "spoiled", sum(top[b] == truth[b] and new[b] != truth[b] for b in range(NB)), NB)
                if j_large is not None: acc(case, rule, "large", P1.by_votes(new, maps)[0] == j_large)
            acc(case, "none", "local", sum(top[b] == truth[b] for b in range(NB)), NB); acc(case, "none", "bad", sum(top[b] == truth[b] for b in range(nbad)), nbad)
            if j_large is not None: acc(case, "none", "large", P1.by_votes(top, maps)[0] == j_large); acc(case, "none", "scores", P1.by_scores(scs, maps) == j_large)
        for d in DROPS[:4]:
            for j in range(NL):
                for _ in range(NTEST): one("all blocks %d%% dropped" % (100 * d), maps[j], [d] * NB, j)
        for nbad in (1, 2, 3):
            for j in range(NL):
                for _ in range(NTEST): one("%d of 4 blocks at 90%%, others 10%%" % nbad, maps[j], [0.9] * nbad + [0.1] * (NB - nbad), j, nbad)
        for t in novel:
            for _ in range(NTEST): one("NOVEL combination, 30% dropped", t, [0.3] * NB, None)
    pc = lambda a: "%5.1f" % (100.0 * a[0] / a[1]) if a[1] else "    -"
    print("The two tests, by how damaged the block's input really was (mean weight 0..2; %d seeds):" % len(seeds))
    for d in sorted(wstat):
        st = wstat[d]; print("   %2d%% dropped: match weight %.2f (weight 2 but WRONG answer: %.1f%% of blocks), input weight %.2f (weight 2: %.0f%%)" % (100 * d, st[1] / st[0], 100.0 * st[3] / st[0], st[2] / st[0], 100.0 * st[4] / st[0]))
    print("\npercent right; columns: no feedback | " + " | ".join(RULES))
    for key, title in (("large", "LARGE map named right (by votes after the feedback; in brackets: pool reading full scores, no feedback)"), ("bad", "DAMAGED blocks' local answer right"), ("local", "all local answers right"), ("spoiled", "right answers SPOILED by the feedback")):
        print(title)
        for case, d in res.items():
            if key not in d["plain"] and key not in d["none"]: continue
            row = [pc(d["none"][key]) if key in d["none"] else "    -"] + [pc(d[rule][key]) if key in d[rule] else "    -" for rule in RULES]
            if all(x.strip() == "-" for x in row): continue
            print("   %-34s %s%s" % (case, " | ".join(row), ("   (%s)" % pc(d["none"]["scores"]).strip()) if key == "large" and "scores" in d["none"] else ""))


if __name__ == "__main__":
    main(tuple(range(1, 1 + (int(sys.argv[1]) if len(sys.argv) > 1 else 5))))
