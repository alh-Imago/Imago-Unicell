"""hexn_anomaly_tile_v1 (11 Nov 2026): A SECOND STORE FOR THE ANOMALIES: is there a hidden pattern in the noise? Alan 14:05 and 16:30 (direction doc sections 88 and 89). Simulation only, toy patterns; every number is a property of this toy.
One block of the main tile (the 3-layer network of section 49 with its map blocks, hexn_recall_blocks_v1; nothing in it is changed by anything here) sees a stream of its 8 known patterns, noisy. In some runs a WEAK HIDDEN pattern
that was never trained or stored is laid over the input (a few lines, a few events, with its own jitter and 10% loss). The block recalls as always. What the recall does not explain is the RESIDUE, taken two ways:
  lines : input lines active in this run that the recalled pattern does not normally use (the block keeps, per stored pattern, the lines seen in at least 2 of the 5 runs its map block was made from: a 48-bit mask)
  cells : layer 1 cells that fired but do not normally fire for the recalled pattern (same rule, a 64-bit mask)
The residue goes to the ANOMALY STORE (the simplest form of the second tile): 16 slots. A slot holds a count per element (line or cell) and a hit count. A residue of at least 3 elements is compared with every slot's
template (the elements present in at least half of that slot's hits); overlap (Jaccard) of at least 0.3 with the best slot = a hit: its counts go up. No slot fits: a new slot (the slot with the fewest hits is replaced).
Real noise should not repeat, so its slots stay at 1 or 2 hits; a hidden pattern should come back to the same slot. A slot with N hits is REPORTED as a pattern.
Scored at the end of a stream of 200 runs: was the hidden pattern found (a reported slot whose template is mostly hidden-pattern lines and covers at least half of the lines that can be seen), after how many runs, and how many
reported slots are FALSE (not the hidden pattern). For the cell residue 'the hidden pattern's cells' are not known in advance, so found = a reported slot that takes at least half of its hits from runs that held the hidden pattern
and a share of at least 80% of them. Guard: residues are passed on only when the block's recall is clear (match weight 2 of section 87), because a wrong recall leaves the main pattern itself as residue.
Usage: python3 tools/hexn_anomaly_tile_v1.py [SEEDS]"""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_recall_blocks_v1 as R, hexn_recall_pool_v3 as P3

RUNS = 200; SLOTS = 16; NS = (3, 5, 8)
HID = (("6 lines x 2 events", 6, 2), ("4 lines x 2 events", 4, 2), ("3 lines x 1 event", 3, 1))


class Store:
    def __init__(s): s.slots = []            # each: dict(cnt={elem: n}, hits, hid (hits from runs with the hidden pattern), when=[run index of each hit])
    @staticmethod
    def template(sl): return {e for e, c in sl["cnt"].items() if 2 * c >= sl["hits"]}
    def feed(s, res, t, hidden):
        if len(res) < 3: return
        best = None; bj = 0.0
        for sl in s.slots:
            j = B.jaccard(res, s.template(sl))
            if j > bj: best, bj = sl, j
        if best is None or bj < 0.3:
            if len(s.slots) >= SLOTS: s.slots.remove(min(s.slots, key=lambda x: (x["hits"], x["when"][-1])))
            best = dict(cnt={}, hits=0, hid=0, when=[]); s.slots.append(best)
        best["hits"] += 1; best["hid"] += hidden; best["when"].append(t)
        for e in res: best["cnt"][e] = best["cnt"].get(e, 0) + 1


def learn_masks(net, pats):
    """per stored pattern: the lines and the layer 1 cells seen in at least 2 of the 5 runs the map block was made from"""
    lines = []; cells = []
    for k, p in enumerate(pats):
        cl = {}; cc = {}
        for j in range(5):
            ev = B.noisy(p, random.Random(31000 + 13 * k + j), drop=0.1, jit=3); run = T.fresh_run(net, ev)
            for i in {i for v in ev.values() for i in v}: cl[i] = cl.get(i, 0) + 1
            for g in B.map_of(run, (1,)): cc[g] = cc.get(g, 0) + 1
        lines.append({i for i, c in cl.items() if c >= 2}); cells.append({g for g, c in cc.items() if c >= 2})
    return lines, cells


def main(seeds):
    out = {}; recall = {}
    for s in seeds:
        pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; net = R.build(s, pats); keys = [b[0] for b in R.make_blocks(net, pats)]; lmask, cmask = learn_masks(net, pats)
        for hname, hl, hs in HID:
            hr = random.Random(9000 + 31 * s + hl * 7 + hs); hidden = [(i, hr.randrange(40)) for i in hr.sample(range(B.NIN), hl) for _ in range(hs)]; hlines = {i for i, _ in hidden}
            for drop in (0.1, 0.3):
                for p in (0.5, 0.2, 0.1, 0.0):
                    if p == 0.0 and hname != HID[0][0]: continue
                    r = random.Random(40000 + 1000 * s + int(100 * p) + int(10 * drop) + hl); st = {(a, g): Store() for a in ("lines", "cells") for g in (False, True)}; nh = 0
                    for t in range(RUNS):
                        k = r.randrange(T.NPAT); ev = B.noisy(pats[k], random.Random(r.random()), drop=drop, jit=3); has = r.random() < p; nh += has
                        if has:
                            for i, tt in hidden:
                                if r.random() >= 0.1: ev.setdefault(max(0, tt + r.randint(-3, 3)), []).append(i)
                        run = T.fresh_run(net, ev); sc = [R.acc_int(B.map_of(run, (2,)), x) for x in keys]; rec = P3.best(sc); clear = P3.w_match(sc) == 2
                        a = recall.setdefault((drop, has), [0, 0]); a[0] += (rec == k); a[1] += 1
                        res = {"lines": {i for v in ev.values() for i in v} - lmask[rec], "cells": B.map_of(run, (1,)) - cmask[rec]}
                        for (kind, guard), store in st.items():
                            if not guard or clear: store.feed(res[kind], t, int(has))
                    for (kind, guard), store in st.items():
                        for n in NS:
                            o = out.setdefault((hname if p else "no hidden pattern", drop, p, kind, guard, n), dict(found=0, when=[], false=0, streams=0)); o["streams"] += 1
                            rep = [sl for sl in store.slots if sl["hits"] >= n]; good = []
                            for sl in rep:
                                tp = Store.template(sl)
                                if kind == "lines": ok = p > 0 and tp and len(tp & hlines) >= 0.6 * len(tp) and len(tp & hlines) >= 0.5 * len(hlines)
                                else: ok = p > 0 and sl["hid"] >= 0.8 * sl["hits"]
                                if ok: good.append(sl)
                            if good: o["found"] += 1; o["when"].append(min(sl["when"][n - 1] for sl in good) + 1)
                            o["false"] += len(rep) - len(good)
    print("the block's own recall, percent right: " + "; ".join("%d%% dropped, hidden pattern %s: %.1f" % (100 * d, "PRESENT" if h else "absent", 100.0 * a[0] / a[1]) for (d, h), a in sorted(recall.items())))
    print("\n%d streams of %d runs per line (one per seed). found = streams in which the hidden pattern was reported; runs = median run at which it was reported; false = other slots reported, per stream" % (len(seeds), RUNS))
    for kind in ("lines", "cells"):
        for guard in (False, True):
            print("\nRESIDUE = %s%s" % (kind.upper(), ", passed on only when the recall is clear" if guard else ", always passed on"))
            print("   %-20s %-5s %-7s | %s" % ("hidden pattern", "drop", "present", " | ".join("N = %d: found  runs  false" % n for n in NS)))
            for (hname, drop, p, kd, gd, n), o in sorted(out.items(), key=lambda x: (x[0][0] == "no hidden pattern", [h[0] for h in HID].index(x[0][0]) if x[0][0] != "no hidden pattern" else 0, x[0][1], -x[0][2], x[0][5])):
                if kd != kind or gd != guard or n != NS[0]: continue
                cells = []
                for nn in NS:
                    q = out[(hname, drop, p, kind, guard, nn)]; w = sorted(q["when"])
                    cells.append("        %d/%d   %4s  %5.1f" % (q["found"], q["streams"], w[len(w) // 2] if w else "-", q["false"] / q["streams"]))
                print("   %-20s %-5s %-7s | %s" % (hname, "%d%%" % (100 * drop), "%d%%" % (100 * p), " | ".join(cells)))


if __name__ == "__main__":
    main(tuple(range(1, 1 + (int(sys.argv[1]) if len(sys.argv) > 1 else 5))))
