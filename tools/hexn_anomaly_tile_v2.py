"""hexn_anomaly_tile_v2 (11 Nov 2026): the anomaly store with a COMPARE step and PROMOTION. Alan 16:38: promote to the storage, and add a compare system: if the pattern is found by the main system, add a score for the weaker
signal in a separate table; if it is new, note it as new. Direction doc section 90. hexn_anomaly_tile_v1 is untouched; its store and line masks are used. Simulation only, toy patterns.
As v1: one block of the main tile sees a stream of its 8 known patterns, noisy; the RESIDUE of each run = the input lines active that the recalled pattern does not normally use; residues go to 16 counting slots.
NEW: when a slot reaches N hits its template (the lines present in at least half of its hits) is COMPARED with the main system's stored patterns (their line masks):
  KNOWN, WEAK : at least 70% of the template's lines belong to one stored pattern j -> the slot is tagged 'weak j'; the WEAK TABLE entry of j gets the slot's hits and 1 more for every later hit. Nothing is stored anew.
  NEW         : otherwise -> the template is PROMOTED: stored as new pattern number 8, 9, ... (a line mask with a note 'new'); every later hit of the slot counts as a sighting of it.
After promotion the new pattern is looked for in every run: SEEN when at least half of its lines are among the run's residue lines.
PROBATION: a promoted pattern is only 'noted as new'; it is CONFIRMED when it has been seen in at least 5 of the 100 runs after its promotion, otherwise it stays unconfirmed (and could be dropped).
What is laid over the input, per stream of 400 runs (each thing in 20% of the runs, independently):
  new        : a pattern never trained or stored: 6 lines x 2 events
  weak known : a faint copy of known pattern number 3: 5 of its lines, 2 of the 3 events of each, at the pattern's own times (while another known pattern is the main input)
  both, none
No guard is used (every residue is passed on): the leftovers of a wrong recall are the true pattern's own lines, so the compare step should file them under 'known, weak' instead of reporting them as patterns.
Usage: python3 tools/hexn_anomaly_tile_v2.py [SEEDS]"""
import random, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_recall_blocks_v1 as R, hexn_recall_pool_v3 as P3, hexn_anomaly_tile_v1 as A1

RUNS = 400; WEAKJ = 3; NS = (5, 8)


def compare(tp, lmask):
    """-> ('weak', j) or ('new', None)"""
    j = max(range(len(lmask)), key=lambda x: len(tp & lmask[x]))
    return ("weak", j) if tp and 10 * len(tp & lmask[j]) >= 7 * len(tp) else ("new", None)


def main(seeds):
    out = {}
    for s in seeds:
        pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; net = R.build(s, pats); keys = [b[0] for b in R.make_blocks(net, pats)]; lmask, _ = A1.learn_masks(net, pats)
        hr = random.Random(9100 + 31 * s); hidden = [(i, hr.randrange(40)) for i in hr.sample(range(B.NIN), 6) for _ in range(2)]; hlines = {i for i, _ in hidden}
        wl = hr.sample(sorted({i for i, _ in pats[WEAKJ]}), 5); weak = []
        for i in wl: weak += [(i, t) for (ii, t) in pats[WEAKJ] if ii == i][:2]
        for drop in (0.1, 0.3):
            for case, pn, pw in (("new", 0.2, 0.0), ("weak known", 0.0, 0.2), ("both", 0.2, 0.2), ("none", 0.0, 0.0)):
                for n in NS:
                    r = random.Random(60000 + 1000 * s + int(10 * drop) + 7 * len(case)); store = A1.Store(); tags = {}; promoted = []; ptime = []; pseen = []; weak_tab = [0] * T.NPAT
                    o = out.setdefault((case, drop, n), dict(streams=0, new_right=0, new_wrong=0, when=[], weak_right=0, weak_other=0, seen=[0, 0], false_seen=[0, 0], when_w=[], rec=[0, 0], npromo=0)); o["streams"] += 1
                    first_new = None; first_weak = None
                    for t in range(RUNS):
                        k = r.randrange(T.NPAT)
                        while pw and k == WEAKJ: k = r.randrange(T.NPAT)                  # the faint copy rides on ANOTHER pattern
                        ev = B.noisy(pats[k], random.Random(r.random()), drop=drop, jit=3); hasn = r.random() < pn; hasw = r.random() < pw
                        for flag, src in ((hasn, hidden), (hasw, weak)):
                            if flag:
                                for i, tt in src:
                                    if r.random() >= 0.1: ev.setdefault(max(0, tt + r.randint(-3, 3)), []).append(i)
                        run = T.fresh_run(net, ev); rec = P3.best([R.acc_int(B.map_of(run, (2,)), x) for x in keys]); o["rec"][0] += (rec == k); o["rec"][1] += 1
                        res = {i for v in ev.values() for i in v} - lmask[rec]
                        for pi, (tp, right) in enumerate(promoted):                        # look for promoted patterns in this run
                            seen = 2 * len(res & tp) >= len(tp)
                            if t <= ptime[pi] + 100: pseen[pi] += seen
                            if right:
                                if hasn: o["seen"][0] += seen; o["seen"][1] += 1
                                else: o["false_seen"][0] += seen; o["false_seen"][1] += 1
                        before = {id(sl): sl["hits"] for sl in store.slots}; store.feed(res, t, int(hasn))
                        for sl in store.slots:
                            if sl["hits"] == before.get(id(sl), 0): continue               # this slot took the residue
                            tag = tags.get(id(sl))
                            if tag is None and sl["hits"] >= n:
                                tp = A1.Store.template(sl); kind, j = compare(tp, lmask)
                                if kind == "weak":
                                    tags[id(sl)] = ("weak", j); weak_tab[j] += sl["hits"]
                                    if j == WEAKJ and first_weak is None: first_weak = t + 1
                                else:
                                    right = pn > 0 and len(tp & hlines) >= 0.6 * len(tp) and len(tp & hlines) >= 0.5 * len(hlines)
                                    tags[id(sl)] = ("new", len(promoted)); promoted.append((tp, right)); ptime.append(t); pseen.append(0); o["npromo"] += 1
                                    if right and first_new is None: first_new = t + 1
                            elif tag is not None and tag[0] == "weak": weak_tab[tag[1]] += 1
                        live = {id(sl) for sl in store.slots}; tags = {i: v for i, v in tags.items() if i in live}
                    nr = sum(1 for _, right in promoted if right); o["new_right"] += (nr > 0); o["new_wrong"] += len(promoted) - nr
                    o["conf_right"] = o.get("conf_right", 0) + (any(right and pseen[i] >= 5 for i, (_, right) in enumerate(promoted)))
                    o["conf_wrong"] = o.get("conf_wrong", 0) + sum(1 for i, (_, right) in enumerate(promoted) if not right and pseen[i] >= 5)
                    if first_new: o["when"].append(first_new)
                    if first_weak: o["when_w"].append(first_weak)
                    o["weak_right"] += weak_tab[WEAKJ]; o["weak_other"] += sum(weak_tab) - weak_tab[WEAKJ]
    med = lambda w: (sorted(w)[len(w) // 2] if w else "-")
    print("%d streams of %d runs per line; each laid-over thing is in 20%% of the runs. recall = the block's own recall, percent right." % (len(seeds), RUNS))
    print("%-11s %-5s %-3s | %-34s | %-41s | %-33s | %s" % ("laid over", "drop", "N", "NEW: streams found / run / wrong new", "WEAK TABLE: score on pattern 3 / on others", "after promotion: seen / false seen", "recall | CONFIRMED new: right streams / wrong per stream"))
    for (case, drop, n), o in sorted(out.items(), key=lambda x: (("new", "weak known", "both", "none").index(x[0][0]), x[0][1], x[0][2])):
        pc = lambda a: ("%.0f%%" % (100.0 * a[0] / a[1])) if a[1] else "-"
        print("%-11s %-5s %-3d | %-34s | %-41s | %-33s | %.1f" % (case, "%d%%" % (100 * drop), n, "%d/%d    run %s    wrong %.1f per stream" % (o["new_right"], o["streams"], med(o["when"]), o["new_wrong"] / o["streams"]),
              "%.0f / %.0f per stream (first at run %s)" % (o["weak_right"] / o["streams"], o["weak_other"] / o["streams"], med(o["when_w"])), "%s / %s" % (pc(o["seen"]), pc(o["false_seen"])), 100.0 * o["rec"][0] / o["rec"][1]) + " | %d/%d / %.1f" % (o["conf_right"], o["streams"], o["conf_wrong"] / o["streams"]))


if __name__ == "__main__":
    main(tuple(range(1, 1 + (int(sys.argv[1]) if len(sys.argv) > 1 else 5))))
