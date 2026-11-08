"""hexn_busnet_sparse_v1 (8 Nov 2026): sparser activity maps for the bus network toy (clone-style companion of hexn_busnet_v1, which is untouched). Alan 18:55: make the maps sparser and retest the two maps crossing.
Sparse map options: 'all' (every layer 2/3 cell that fired), 'early' (the first N layer 2/3 cells to fire), 'strong' (fired at least twice). Score options: 'jaccard', 'idf' (each cell counts 1/(number of stored maps holding it), so cells shared by many maps count little).
Settings sweep: threshold th and inhibitory share. Mixture test = half of A's spikes + half of B's; hit = the two best stored maps are exactly A and B.
Simulation only; one wiring seed per setting unless noted. Usage: python3 tools/hexn_busnet_sparse_v1.py"""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B


def sparse_map(net, how, n_early=12):
    cells = [g for g in net.fires if net.layer_of(g) in (2, 3)]
    if how == "all": return set(cells)
    if how == "strong": return {g for g in cells if net.fires[g] >= 2}
    return set(sorted(cells, key=lambda g: (net.fire_t[g], g))[:n_early])


def scores(m, stored, how):
    if how == "jaccard": return [B.jaccard(m, s) for s in stored]
    cnt = {}
    for s in stored:
        for g in s: cnt[g] = cnt.get(g, 0) + 1
    return [sum(1.0 / cnt[g] for g in m & s) / (len(s) ** 0.5 + 1e-9) for s in stored]


def evaluate(mapkind, scorekind, seed=1, npat=8, ntest=20, nmix=10, nrun=10, **kw):
    pats = [B.pattern(random.Random(100 + k)) for k in range(npat)]; stored = []
    for p in pats:
        cnt = {}
        for j in range(5):
            n, _ = B.trial(seed, B.noisy(p, random.Random(j)), **kw)
            for g in sparse_map(n, mapkind): cnt[g] = cnt.get(g, 0) + 1
        stored.append({g for g, c in cnt.items() if c >= 3})
    ok = tot = 0
    for k, p in enumerate(pats):
        for j in range(ntest):
            n, _ = B.trial(seed, B.noisy(p, random.Random(1000 + 50 * k + j)), **kw); sc = scores(sparse_map(n, mapkind), stored, scorekind)
            ok += (max(range(npat), key=lambda x: sc[x]) == k); tot += 1
    hit = mt = 0; pr = random.Random(5)
    for _ in range(nmix):
        a, b = pr.sample(range(npat), 2); mix = pats[a][:len(pats[a]) // 2] + pats[b][len(pats[b]) // 2:]
        for j in range(nrun):
            n, _ = B.trial(seed, B.noisy(mix, random.Random(5000 + 100 * a + 10 * b + j)), **kw); sc = scores(sparse_map(n, mapkind), stored, scorekind)
            hit += (set(sorted(range(npat), key=lambda x: -sc[x])[:2]) == {a, b}); mt += 1
    return ok, tot, hit, mt, sum(len(s) for s in stored) / npat


def main():
    print("%-22s %-8s %-8s %12s %14s %10s" % ("setting", "map", "score", "single", "mixture A+B", "map size"))
    for label, kw in (("default th3", {}), ("th4 leak4", dict(th=4)), ("th4 inhib 40%", dict(th=4, inhib_share=0.4)), ("th3 inhib 40%", dict(th=3, inhib_share=0.4))):
        for mk in ("all", "strong", "early"):
            for sk in ("jaccard", "idf"):
                ok, tot, hit, mt, sz = evaluate(mk, sk, **kw)
                print("%-22s %-8s %-8s %5d/%-6d %7d/%-6d %10.1f" % (label, mk, sk, ok, tot, hit, mt, sz))


if __name__ == "__main__": main()
