"""hexn_recall_pool_v1 (11 Nov 2026): FOUR NEURAL BLOCKS AROUND A CENTRE POOL, WITH A MONITOR. Alan 12:13 and 12:15 (direction doc sections 79 and 80): the 3-layer block with its own recall becomes one block of a larger matrix;
a RAM pool at the centre holds large maps (a map of maps); an overarching monitor works with the map of maps to give the feedback. Simulation only, toy patterns; every number is a property of this toy. Earlier tools untouched.

Blocks: 4 networks as in section 49 (3 layers, 4 x 16 cells, trained, pruned), each with its OWN 48 inputs and its own 8 local patterns, and its own map blocks (keys = layer 2 maps from its own runs, as hexn_recall_blocks_v1).
Large patterns: 16, each = one local pattern per block (a tuple of 4 codes of 3 bits). Every local pattern of a block belongs to exactly 2 large patterns, so one block alone cannot name the large pattern.
Pool: the 16 tuples. Three ways to name the large pattern from the blocks' recalls:
  votes     : each block reports its best local block (top 1); the large map with the most agreeing blocks wins (ties: lowest number)
  scores    : each block reports its overlap score for every local block; the large map with the largest sum wins (the pool reads full scores, no monitor needed)
  monitor   : votes, then ONE round of feedback, then votes again. For block i the monitor looks at the OTHER three blocks only (so a block's own answer is never evidence for its own hint): if 3 of 3 point to the same
              large map(s) the hint bonus is 8, if 2 of 3 it is 4 (overlap scores run 0..32); the bonus is added to the local score of the code(s) those large maps expect from block i, and block i re-ranks.
              No hint when the others do not agree on anything. Nothing loops: hints are computed from the first answers only.
Tests: all four blocks damaged alike (10/30/50/70% of events dropped); ONE block badly damaged (90%) with the others at 10%; and NOVEL combinations (known local patterns in a tuple the pool never stored, 30% dropped),
where a hint can only do harm: how many right local answers does the monitor spoil?
Usage: python3 tools/hexn_recall_pool_v1.py [SEEDS]"""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_recall_blocks_v1 as R

NB = 4; NL = 16; NS = 10; NTEST = 20; DROPS = (0.1, 0.3, 0.5, 0.7, 0.9)


def large_maps(r):
    """16 tuples; in each block every local code 0..7 is used by exactly two large maps; all tuples different"""
    while True:
        cols = []
        for b in range(NB):
            p = list(range(NL)); r.shuffle(p); cols.append([x // 2 for x in p])
        maps = [tuple(cols[b][j] for b in range(NB)) for j in range(NL)]
        if len(set(maps)) == NL: return maps


def best(sc): return max(range(len(sc)), key=lambda i: (sc[i], -i))


def by_votes(top, maps):
    v = [sum(1 for b in range(NB) if m[b] == top[b]) for m in maps]; return best(v), v


def by_scores(scs, maps): return best([sum(scs[b][m[b]] for b in range(NB)) for m in maps])


def monitor(scs, maps):
    """-> (new top-1 per block, number of blocks that received a hint)"""
    top = [best(s) for s in scs]; new = []; hinted = 0
    for i in range(NB):
        v = [sum(1 for b in range(NB) if b != i and m[b] == top[b]) for m in maps]; mx = max(v)
        if mx < 2: new.append(top[i]); continue
        bonus = 8 if mx == 3 else 4; want = {maps[j][i] for j in range(NL) if v[j] == mx}; hinted += 1
        new.append(best([scs[i][c] + (bonus if c in want else 0) for c in range(T.NPAT)]))
    return new, hinted


def main(seeds):
    res = {}
    def acc(case, key, ok, n=1):
        d = res.setdefault(case, {}); a = d.setdefault(key, [0, 0]); a[0] += ok; a[1] += n
    for s in seeds:
        keys = []; pool = []
        for b in range(NB):
            pats = [B.pattern(random.Random(100 + 50 * b + k)) for k in range(T.NPAT)]; net = R.build(10 * s + b, pats); kb = [x[0] for x in R.make_blocks(net, pats)]; keys.append(kb)
            pool.append({(k, d): [[R.acc_int(B.map_of(T.fresh_run(net, B.noisy(pats[k], random.Random(71000 + 1000 * b + 97 * k + j + int(1000 * d)), drop=d, jit=3)), (2,)), x) for x in kb] for j in range(NS)]
                         for k in range(T.NPAT) for d in DROPS})
        r = random.Random(500 + s); maps = large_maps(r); stored = set(maps)
        novel = []
        while len(novel) < NL:
            t = tuple(r.randrange(T.NPAT) for _ in range(NB))
            if t not in stored and t not in novel: novel.append(t)
        def one(case, truth, drops, j_large):
            scs = [pool[b][(truth[b], drops[b])][r.randrange(NS)] for b in range(NB)]; top = [best(x) for x in scs]
            new, hinted = monitor(scs, maps)
            acc(case, "local before", sum(top[b] == truth[b] for b in range(NB)), NB); acc(case, "local after", sum(new[b] == truth[b] for b in range(NB)), NB)
            acc(case, "block 0 before", top[0] == truth[0]); acc(case, "block 0 after", new[0] == truth[0])
            acc(case, "spoiled", sum(top[b] == truth[b] and new[b] != truth[b] for b in range(NB)), NB); acc(case, "repaired", sum(top[b] != truth[b] and new[b] == truth[b] for b in range(NB)), NB)
            acc(case, "hinted", hinted, NB)
            if j_large is not None:
                acc(case, "large votes", by_votes(top, maps)[0] == j_large); acc(case, "large scores", by_scores(scs, maps) == j_large); acc(case, "large monitor", by_votes(new, maps)[0] == j_large)
        for d in DROPS[:4]:
            for j in range(NL):
                for _ in range(NTEST): one("all blocks %d%% dropped" % (100 * d), maps[j], [d] * NB, j)
        for j in range(NL):
            for _ in range(NTEST): one("block 0 at 90%, others 10%", maps[j], [0.9, 0.1, 0.1, 0.1], j)
            for _ in range(NTEST): one("block 0 at 90%, others 30%", maps[j], [0.9, 0.3, 0.3, 0.3], j)
        for t in novel:
            for _ in range(NTEST): one("NOVEL combination, 30% dropped", t, [0.3] * NB, None)
    pc = lambda a: "%5.1f" % (100.0 * a[0] / max(1, a[1]))
    print("4 blocks around a centre pool of 16 large maps, %d seeds, %d tests per large map; percent" % (len(seeds), NTEST))
    print("%-32s | %-23s | %-26s | %-17s | %s" % ("case", "LARGE map named right", "local answers right", "block 0 right", "hints: given / repaired / spoiled"))
    print("%-32s | %-23s | %-26s | %-17s | %s" % ("", "votes  scores monitor", "before  after monitor", "before  after", "(share of block answers)"))
    for case, d in res.items():
        lg = "  ".join(pc(d[k]) for k in ("large votes", "large scores", "large monitor")) if "large votes" in d else "   (not a stored map)  "
        print("%-32s | %-23s | %-26s | %-17s | %s" % (case, lg, pc(d["local before"]) + "   " + pc(d["local after"]), pc(d["block 0 before"]) + "   " + pc(d["block 0 after"]),
                                                    pc(d["hinted"]) + " / " + pc(d["repaired"]) + " / " + pc(d["spoiled"])))


if __name__ == "__main__":
    main(tuple(range(1, 1 + (int(sys.argv[1]) if len(sys.argv) > 1 else 5))))
