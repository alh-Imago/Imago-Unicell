"""hexn_anomaly_diag_v1 (11 Nov 2026): what are the FALSE 'new' notes of the anomaly store (section 90) made of? Alan 16:55. Direction doc section 91. Uses hexn_anomaly_tile_v1/v2 unchanged; streams with NOTHING laid over
(any slot promoted as new is false), 400 runs, N = 8 and N = 5, 10% and 30% dropped. For every false 'new' slot at the moment it is promoted: the size of its template; how many of the template's lines belong to the best-fitting
stored pattern; and, over the runs that hit the slot, the share that were WRONG recalls, the size of their residues and how many of the residue lines were the true pattern's own lines (the rest is random noise lines).
Usage: python3 tools/hexn_anomaly_diag_v1.py [SEEDS]"""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_recall_blocks_v1 as R, hexn_recall_pool_v3 as P3, hexn_anomaly_tile_v1 as A1, hexn_anomaly_tile_v2 as A2


def main(seeds, runs=400):
    for n in (8, 5):
        rows = []; nstreams = 0; allres = []
        for s in seeds:
            pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; net = R.build(s, pats); keys = [b[0] for b in R.make_blocks(net, pats)]; lmask, _ = A1.learn_masks(net, pats)
            plines = [{i for i, _ in p} for p in pats]
            for drop in (0.1, 0.3):
                r = random.Random(60000 + 1000 * s + int(10 * drop) + 7 * 4); store = A1.Store(); log = {}; done = set(); nstreams += 1
                for t in range(runs):
                    k = r.randrange(T.NPAT); ev = B.noisy(pats[k], random.Random(r.random()), drop=drop, jit=3)
                    run = T.fresh_run(net, ev); rec = P3.best([R.acc_int(B.map_of(run, (2,)), x) for x in keys]); res = {i for v in ev.values() for i in v} - lmask[rec]
                    allres.append((len(res), rec == k))
                    before = {id(sl): sl["hits"] for sl in store.slots}; store.feed(res, t, 0)
                    for sl in store.slots:
                        if sl["hits"] == before.get(id(sl), 0): continue
                        if sl["hits"] == 1: log[id(sl)] = []
                        log[id(sl)].append((rec != k, len(res), len(res & plines[k]) if rec != k else 0))
                        if sl["hits"] >= n and id(sl) not in done:
                            done.add(id(sl)); tp = A1.Store.template(sl); kind, j = A2.compare(tp, lmask)
                            if kind == "new":
                                h = log[id(sl)]; bestfit = max(len(tp & m) for m in lmask)
                                rows.append(dict(size=len(tp), fit=bestfit, wrong=sum(x[0] for x in h) / len(h), rsize=sum(x[1] for x in h) / len(h), own=sum(x[2] for x in h) / max(1, sum(x[0] for x in h)), drop=drop))
        m = lambda key: sum(x[key] for x in rows) / max(1, len(rows))
        print("N = %d: %d false 'new' notes in %d streams (%.1f per stream)" % (n, len(rows), nstreams, len(rows) / nstreams))
        print("   template size (lines): mean %.1f; sizes: %s" % (m("size"), ", ".join("%d lines: %d" % (z, sum(1 for x in rows if x["size"] == z)) for z in sorted({x["size"] for x in rows}))))
        print("   of the template's lines, in the best-fitting stored pattern: mean %.1f" % m("fit"))
        print("   runs that hit these slots: %.0f%% were WRONG recalls; mean residue %.1f lines; in the wrong-recall hits, %.1f of the residue lines were the true pattern's own" % (100 * m("wrong"), m("rsize"), m("own")))
        ok = [x[0] for x in allres if x[1]]; bad = [x[0] for x in allres if not x[1]]
        print("   for scale, all runs: residue after a RIGHT recall %.1f lines on average (%d runs), after a WRONG recall %.1f lines (%d runs)" % (sum(ok) / len(ok), len(ok), sum(bad) / max(1, len(bad)), len(bad)))


if __name__ == "__main__":
    main(tuple(range(1, 1 + (int(sys.argv[1]) if len(sys.argv) > 1 else 5))))
