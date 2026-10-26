"""hexn_key_unrel_v1: does the quick key still recall the right engram when the engrams are UNRELATED? (Python model of the bank; no RTL; new file; uses hexn_key_v1 unchanged.)
hexn_key_v1 / hexn_key_check_v2/v3 make their E engrams from ONE data set by shifting the class labels, so the sets are related. Here three kinds of engram set are compared with the same sweep:
  shift    = the script's data, labels shifted by s (as before; the baseline)
  perm     = the script's data, labels randomly permuted per engram
  unrel    = a different data set per engram: K random 18-bit prototypes (each bit 50/50), 16 noisy samples per class (train noise 6 percent, test 10 percent, as the script states), samples shuffled (the bank's counters saturate, so class-ordered samples would bias them; found in the first run, whose results were discarded). ASSUMPTION: random prototypes stand in for 'unrelated machines'; real sensor sets will overlap more or less.
The probes are drawn once from the pooled training samples of all the engrams in the set (one probe set is shared by all engrams, as on the card).
Usage: python3 tools/hexn_key_unrel_v1.py script [E] [reps] [P] [seeds]"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_script_v1 as S1, hexn_key_v1 as KV
def noisy(p, q, r): return [b ^ (1 if r.random() < q else 0) for b in p]
def make_sets(d, kind, E, seed):
    K, NB = d["classes"], d["wires"]; r = random.Random(seed); out = []; nt = sum(1 for b, y in d["train"] if y == 0); ne = max(1, sum(1 for b, y in d["test"] if y == 0))
    for s in range(E):
        ds = dict(d)
        if kind == "shift": ds["train"] = [(b, (y + s) % K) for b, y in d["train"]]; ds["test"] = [(b, (y + s) % K) for b, y in d["test"]]
        elif kind == "perm":
            pm = list(range(K)); r.shuffle(pm) if s else None; ds["train"] = [(b, pm[y]) for b, y in d["train"]]; ds["test"] = [(b, pm[y]) for b, y in d["test"]]
        else:
            protos = [[r.randint(0, 1) for _ in range(NB)] for _ in range(K)]
            ds["train"] = [(noisy(protos[c], 0.06, r), c) for c in range(K) for _ in range(nt)]; ds["test"] = [(noisy(protos[c], 0.10, r), c) for c in range(K) for _ in range(ne)]; r.shuffle(ds["train"])
        out.append((ds, S1.make_model(ds, 16)))
    return out
def run(d, kind, E, reps, P, seed):
    sets = make_sets(d, kind, E, seed); models = [m for ds, m in sets]; pool = [b for ds, m in sets for b, y in ds["train"]]; pr = random.Random(100 + P + seed); probes = [pr.choice(pool) for _ in range(P)]
    keys = [KV.key_of(m, probes) for m in models]; dd = [KV.ham(keys[i], keys[j]) for i in range(E) for j in range(i)]
    acc = sum(KV.accuracy(m, ds["test"]) for ds, m in sets) / E; res = {}
    for nd in (12, 24, 48, 96):
        for q in (0.1, 0.2, 0.3):
            rnd = random.Random(7 + seed); hit = ties = tot = 0
            for e in range(E):
                for _ in range(reps):
                    dm = KV.damage(models[e], rnd, nd); obs = KV.key_of(dm, [noisy(p, q, rnd) for p in probes]); dist = [KV.ham(obs, k) for k in keys]; best = min(dist); cand = [i for i, x in enumerate(dist) if x == best]
                    hit += len(cand) == 1 and cand[0] == e; ties += len(cand) > 1; tot += 1
            res[(nd, q)] = (hit, ties, tot)
    return min(dd), sum(dd) / len(dd), acc, res
def main():
    d = S1.parse_script(open(sys.argv[1]).read()); E = int(sys.argv[2]) if len(sys.argv) > 2 else 7; reps = int(sys.argv[3]) if len(sys.argv) > 3 else 20; P = int(sys.argv[4]) if len(sys.argv) > 4 else 24; seeds = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    print("E=%d engrams, P=%d probes (%d-bit keys), reps=%d per engram and cell, %d seeds. Right engram recalled, share of all trials (ties counted as misses):" % (E, P, P * d["classes"], reps, seeds))
    for kind in ("shift", "perm", "unrel"):
        agg = {}; mins = []; means = []; accs = []
        for sd in range(seeds):
            mn, me, ac, res = run(d, kind, E, reps, P, sd); mins.append(mn); means.append(me); accs.append(ac)
            for k, (h, t, n) in res.items(): a = agg.setdefault(k, [0, 0, 0]); a[0] += h; a[1] += t; a[2] += n
        print("\n%s: stored keys differ pairwise by min %.0f (worst seed %d), mean %.1f bits; undamaged accuracy on own test samples %.2f" % (kind, sum(mins) / seeds, min(mins), sum(means) / seeds, sum(accs) / seeds))
        print("  damage |  noise 0.1 |  noise 0.2 |  noise 0.3")
        for nd in (12, 24, 48, 96): print("   %3d   | " % nd + " | ".join("   %5.2f   " % (agg[(nd, q)][0] / agg[(nd, q)][2]) for q in (0.1, 0.2, 0.3)))
if __name__ == "__main__": main()
