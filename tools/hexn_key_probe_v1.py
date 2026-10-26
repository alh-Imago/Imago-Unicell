"""hexn_key_probe_v1: does CHOOSING the probe patterns beat drawing them at random? (Python model of the bank only; no RTL; new file; uses hexn_key_unrel_v1 and hexn_key_v1 unchanged.)
Same engram sets and the same damage/noise sweep as hexn_key_unrel_v1 (kinds shift / perm / unrel, 7 engrams, 3 seeds). Three ways to pick the P probes, all from the same candidate pool (the pooled training samples of the engrams plus 200 random 18-bit patterns):
  random   = P drawn at random from the pooled training samples (what unrel_v1 did)
  balanced = P/E probes taken at random from each engram's own training samples
  robust   = as greedy, but only over the 40 percent of candidates whose key block changes least under noise 0.2 and damage 12 (stability measured on the stored settings; a hand-made choice)
  greedy   = one at a time, add the candidate that most raises the smallest pairwise Hamming distance between the engrams' clean keys (ties: the largest sum of distances). This looks only at CLEAN keys; whether the choice survives damage and noise is what the sweep measures.
Reported: right engram recalled (ties counted as misses) at damage 12 / 48 and noise 0.1 / 0.2 / 0.3, and the stored keys' smallest and mean pairwise distance.
Usage: python3 tools/hexn_key_probe_v1.py script [E] [reps] [P] [seeds]"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_script_v1 as S1, hexn_key_v1 as KV, hexn_key_unrel_v1 as U
def pick(sets, models, d, how, P, seed):
    E = len(models); K = d["classes"]; NB = d["wires"]; r = random.Random(100 + P + seed)
    if how == "random": pool = [b for ds, m in sets for b, y in ds["train"]]; return [r.choice(pool) for _ in range(P)]
    if how == "balanced": return [r.choice(sets[i % E][0]["train"])[0] for i in range(P)]
    cand = [b for ds, m in sets for b, y in ds["train"]] + [[r.randint(0, 1) for _ in range(NB)] for _ in range(200)]
    if how == "robust":  # keep the 40 percent of candidates whose block (per engram) changes least under input noise 0.2 and damage 12 (10 draws per engram)
        rr = random.Random(900 + seed); dmg = [[KV.damage(m, rr, 12) for _ in range(10)] for m in models]
        def stab(c): return sum(sum(KV.ham(KV.key_of(dm, [U.noisy(c, 0.2, rr)]), KV.key_of(m, [c])) == 0 for dm in dmg[i]) for i, m in enumerate(models))
        sc = sorted(((stab(c), i) for i, c in enumerate(cand)), reverse=True); cand = [cand[i] for _, i in sc[:int(0.4 * len(cand))]]
    blk = [[KV.key_of(m, [c]) for m in models] for c in cand]  # blk[c][e] = K-bit block
    dist = {(i, j): 0 for i in range(E) for j in range(i)}; chosen = []
    for _ in range(P):
        best = None
        for ci, bl in enumerate(blk):
            nd = {(i, j): dist[(i, j)] + KV.ham(bl[i], bl[j]) for (i, j) in dist}; sc = (min(nd.values()), sum(nd.values()))
            if best is None or sc > best[0]: best = (sc, ci, nd)
        chosen.append(cand[best[1]]); dist = best[2]
    return chosen
def run(d, kind, how, E, reps, P, seed):
    sets = U.make_sets(d, kind, E, seed); models = [m for ds, m in sets]; probes = pick(sets, models, d, how, P, seed)
    keys = [KV.key_of(m, probes) for m in models]; dd = [KV.ham(keys[i], keys[j]) for i in range(E) for j in range(i)]; res = {}
    for nd in (12, 48):
        for q in (0.1, 0.2, 0.3):
            rnd = random.Random(7 + seed); hit = tot = 0
            for e in range(E):
                for _ in range(reps):
                    dm = KV.damage(models[e], rnd, nd); obs = KV.key_of(dm, [U.noisy(p, q, rnd) for p in probes]); dist = [KV.ham(obs, k) for k in keys]; best = min(dist); cand = [i for i, x in enumerate(dist) if x == best]
                    hit += len(cand) == 1 and cand[0] == e; tot += 1
            res[(nd, q)] = (hit, tot)
    return min(dd), sum(dd) / len(dd), res
def main():
    d = S1.parse_script(open(sys.argv[1]).read()); E = int(sys.argv[2]) if len(sys.argv) > 2 else 7; reps = int(sys.argv[3]) if len(sys.argv) > 3 else 20; P = int(sys.argv[4]) if len(sys.argv) > 4 else 24; seeds = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    print("E=%d, P=%d probes (%d-bit keys), reps=%d, %d seeds; right engram recalled (share; ties are misses)" % (E, P, P * d["classes"], reps, seeds))
    print("%-6s %-9s | min / mean key distance | d12 n0.1  n0.2  n0.3 | d48 n0.1  n0.2  n0.3" % ("sets", "probes"))
    for kind in ("shift", "unrel"):
        for how in ("random", "balanced", "greedy", "robust"):
            agg = {}; mins = []; means = []
            for sd in range(seeds):
                mn, me, res = run(d, kind, how, E, reps, P, sd); mins.append(mn); means.append(me)
                for k, (h, t) in res.items(): a = agg.setdefault(k, [0, 0]); a[0] += h; a[1] += t
            f = lambda nd: "  ".join("%.2f" % (agg[(nd, q)][0] / agg[(nd, q)][1]) for q in (0.1, 0.2, 0.3))
            print("%-6s %-9s |   %5.1f / %5.1f         |     %s    |     %s" % (kind, how, sum(mins) / seeds, sum(means) / seeds, f(12), f(48)))
main()
