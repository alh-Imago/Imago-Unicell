"""hexn_recall_blocks_v1 (11 Nov 2026): MAP BLOCKS beside the cells. Alan 11:06, 11:13 and 11:25 (direction doc section 74): maps are outputs of the cells and are kept in separate blocks; recall = cue in, best block out;
the recalled map is replayed into the next layer, or applied as a hint in proportion to the confidence of the match; blocks are never erased, only their RANK moves (recency, accuracy, frequency). Direction doc section 77.
Simulation only, toy patterns; every number is a property of this toy. Earlier tools untouched. Network = the 'ideal model, pruned dense' of section 49 (4 x 16 cells, 3 layers, homeostat, pruned, retrained).

A BLOCK is made from what the cells themselves produced (no teacher map): for each pattern, 5 noisy training runs (10% dropped); key = layer 2 cells that fired in at least 3 of the 5, payload = the same for layer 3.
Part 1 (the next layer's answer = which stored layer 3 map the layer 3 activity is closest to):
  cells      : the network alone (layer 2 feeds layer 3 as built)
  replay     : live layer 2 map -> best block by overlap -> the block's stored layer 2 cells are sent to an empty layer 3 as if they had fired (REP times each) -> layer 3 map
  payload    : live layer 2 map -> best block -> the block's layer 3 payload is the answer directly (no cells used after the recall)
Part 2 (the hint): pass 1 = normal run and recall; pass 2 = the same input again with the cells of the recalled block (layers 2 and 3) PRIMED = their firing threshold lowered by p for that run.
  fixed p = 1 or 2 whatever the match; scaled p = 0 below overlap 1/4, 1 below 1/2, 2 from 1/2 (confidence-scaled). Measured: how complete the right map becomes (overlap of the pass 2 map with the right block),
  what happens when the recall was WRONG, and on NOVEL inputs (patterns never stored) how many block cells are made to fire that did not fire by themselves (false memory).
Part 3 (rank): a stream of recalls in which some patterns come much more often than others and repeat in bursts; the block is picked by accuracy alone, or by accuracy plus a small integer bonus from frequency and recency.
  Score = accuracy (overlap as an integer 0..32) + frequency bonus (0..3 = number of bits of the hit count) + recency bonus (2 if used in the last 4 recalls, 1 in the last 16); "ties only" = the bonus decides only between equal accuracies.
  A block's hit count rises when its recall is confirmed and halves every 64 recalls (the count fades, the block does not). Confirmed = by a teacher (the truth is known) or by itself (best beats second best by a margin).
Usage: python3 tools/hexn_recall_blocks_v1.py [SEEDS]"""
import random, sys, os, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H

DROPS = (0.1, 0.3, 0.5, 0.7); NT = 10; REP = 2


def build(seed, pats, epochs=40, ft=10, th=5):
    net = H.make(seed, 0.5, fb_k=8, fb_w=2, k=24, refr=6, th=th, groups=4, per=16); tg = T.targets(net, seed); t1 = P.layer1_targets(net, pats)
    H.train(net, pats, tg, t1, epochs, homeo=True); Q.prune_by(net, P.LEAN_KEEP, "weight"); H.train(net, pats, tg, t1, ft, homeo=True)
    return net


def make_blocks(net, pats):
    """-> list of (key = layer 2 map, payload = layer 3 map) from the network's own runs"""
    out = []
    for k, p in enumerate(pats):
        c2 = {}; c3 = {}
        for j in range(5):
            run = T.fresh_run(net, B.noisy(p, random.Random(31000 + 13 * k + j), drop=0.1, jit=3))
            for g in B.map_of(run, (2,)): c2[g] = c2.get(g, 0) + 1
            for g in B.map_of(run, (3,)): c3[g] = c3.get(g, 0) + 1
        out.append(({g for g, c in c2.items() if c >= 3}, {g for g, c in c3.items() if c >= 3}))
    return out


def best2(m, maps):
    sc = [B.jaccard(m, x) if (m or x) else 0.0 for x in maps]; o = sorted(range(len(maps)), key=lambda i: (-sc[i], i))
    return o[0], sc[o[0]], (sc[o[1]] if len(o) > 1 else 0.0)


def replay_l3(net, cells, rep=REP):
    """the stored layer 2 cells are sent to an empty network as source ids (rep times each, 8 clocks apart); only layer 3 listens to them"""
    ev = {}
    for i, g in enumerate(sorted(cells)):
        for r in range(rep): ev.setdefault(i % 4 + 8 * r, []).append(g)
    run = T.fresh_run(net, ev, total=60); return B.map_of(run, (3,))


def primed_run(net, ev, cells, p):
    n = copy.deepcopy(net)
    for g in cells: n.th_cell[g] = max(1, n.th_cell[g] - p)
    return T.fresh_run(n, ev)


def scaled(conf): return 0 if conf < 0.25 else 1 if conf < 0.5 else 2


def part12(seeds):
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; novel = [B.pattern(random.Random(700 + k)) for k in range(T.NPAT)]
    a = {d: dict(tot=0, cells=0, replay=0, payload=0, rec=0) for d in DROPS}
    modes = ("none", "fixed 1", "fixed 2", "scaled")
    h = {d: {m: dict(right_ov=0.0, nright=0, wrong_ov_true=0.0, wrong_ov_rec=0.0, nwrong=0, ident=0, tot=0) for m in modes} for d in DROPS}
    nv = {m: dict(extra=0.0, n=0, conf=0.0) for m in modes}; sizes = []; empty3 = 0
    for s in seeds:
        net = build(s, pats); blk = make_blocks(net, pats); keys = [b[0] for b in blk]; pay = [b[1] for b in blk]; full = [b[0] | b[1] for b in blk]
        sizes += [(len(b[0]), len(b[1])) for b in blk]; empty3 += sum(1 for b in blk if not b[1])
        rp = [replay_l3(net, k) for k in keys]                                 # what layer 3 does with each stored key (the same every time: computed once)
        for d in DROPS:
            for k in range(T.NPAT):
                for j in range(NT):
                    ev = B.noisy(pats[k], random.Random(20000 + 97 * k + j), drop=d, jit=3); run = T.fresh_run(net, ev)
                    m2 = B.map_of(run, (2,)); m3 = B.map_of(run, (3,)); A = a[d]; A["tot"] += 1
                    A["cells"] += (best2(m3, pay)[0] == k)
                    r, conf, _ = best2(m2, keys); A["rec"] += (r == k)
                    A["replay"] += (best2(rp[r], pay)[0] == k); A["payload"] += (r == k)
                    for m in modes:
                        p = 0 if m == "none" else 1 if m == "fixed 1" else 2 if m == "fixed 2" else scaled(conf)
                        mm = B.map_of(run) if p == 0 else B.map_of(primed_run(net, ev, full[r], p)); H_ = h[d][m]; H_["tot"] += 1
                        H_["ident"] += (best2(mm, full)[0] == k)
                        if r == k: H_["right_ov"] += B.jaccard(mm, full[k]); H_["nright"] += 1
                        else: H_["wrong_ov_true"] += B.jaccard(mm, full[k]); H_["wrong_ov_rec"] += B.jaccard(mm, full[r]); H_["nwrong"] += 1
        for k in range(T.NPAT):                                                # novel inputs: never stored
            for j in range(NT):
                ev = B.noisy(novel[k], random.Random(52000 + 97 * k + j), drop=0.1, jit=3); run = T.fresh_run(net, ev); base = B.map_of(run)
                r, conf, _ = best2(B.map_of(run, (2,)), keys)
                for m in modes:
                    p = 0 if m == "none" else 1 if m == "fixed 1" else 2 if m == "fixed 2" else scaled(conf)
                    mm = base if p == 0 else B.map_of(primed_run(net, ev, full[r], p))
                    nv[m]["extra"] += len((mm - base) & full[r]); nv[m]["n"] += 1; nv[m]["conf"] += conf
    print("blocks made from the cells' own runs: key (layer 2) size %.1f cells on average, payload (layer 3) %.1f; blocks with an EMPTY payload: %d of %d" % (
        sum(x for x, _ in sizes) / len(sizes), sum(y for _, y in sizes) / len(sizes), empty3, len(sizes)))
    print("\nPart 1. Which pattern does the NEXT layer (layer 3) report? percent right at 10 / 30 / 50 / 70%% of events dropped (%d seeds, %d tests per pattern)" % (len(seeds), NT))
    for nm, key in (("cells alone (layer 3 map as built)", "cells"), ("recall, replay the stored layer 2 map into layer 3", "replay"), ("recall, read the block's layer 3 payload", "payload")):
        print("   %-55s %s" % (nm, " / ".join("%.0f" % (100.0 * a[d][key] / a[d]["tot"]) for d in DROPS)))
    print("   (the recall itself, layer 2 map against the keys: %s)" % " / ".join("%.0f" % (100.0 * a[d]["rec"] / a[d]["tot"]) for d in DROPS))
    print("\nPart 2. The hint: second pass with the recalled block's cells primed (threshold lowered by p)")
    print("   %-9s | %-27s | %-27s | %-39s | %s" % ("priming", "pattern right, whole map %", "right recall: overlap with", "WRONG recall: overlap with true / with", "wrong recalls"))
    print("   %-9s | %-27s | %-27s | %-39s |" % ("", "", "the right block", "the wrongly recalled block (50%, 70%)"))
    for m in modes:
        print("   %-9s | %-27s | %-27s | %-39s | %s" % (m, " / ".join("%.0f" % (100.0 * h[d][m]["ident"] / h[d][m]["tot"]) for d in DROPS),
              " / ".join("%.2f" % (h[d][m]["right_ov"] / max(1, h[d][m]["nright"])) for d in DROPS),
              "  ".join("%.2f / %.2f" % (h[d][m]["wrong_ov_true"] / max(1, h[d][m]["nwrong"]), h[d][m]["wrong_ov_rec"] / max(1, h[d][m]["nwrong"])) for d in (0.5, 0.7)),
              " / ".join("%d" % h[d][m]["nwrong"] for d in DROPS)))
    print("   NOVEL inputs (never stored, %d runs): mean overlap of the best block %.2f; block cells made to fire that did not fire by themselves, per run:" % (nv["none"]["n"], nv["none"]["conf"] / nv["none"]["n"]))
    print("   " + "; ".join("%s %.2f" % (m, nv[m]["extra"] / nv[m]["n"]) for m in modes))


# ---------------- Part 3: rank
def acc_int(m, x): return (32 * len(m & x)) // len(m | x) if (m or x) else 0


def stream(r, n, skew, burst):
    """-> (sequence of pattern numbers, the 4 least used patterns). Which pattern is used most is drawn at random, so it has nothing to do with the pattern's number (ties in the matcher go to the lowest number)."""
    order = list(range(T.NPAT)); r.shuffle(order); w = [0.0] * T.NPAT
    for rank, k in enumerate(order): w[k] = 1.0 / (rank + 1) ** skew
    out = []; last = None
    for _ in range(n):
        if last is not None and r.random() < burst: out.append(last)
        else: last = r.choices(range(T.NPAT), w)[0]; out.append(last)
    return out, set(order[T.NPAT // 2:])


def part3(seeds, n=400, margin=3):
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]
    cases = (("skewed use (1/k), bursts 50%", 1.0, 0.5), ("skewed use (1/k), no bursts", 1.0, 0.0), ("even use, bursts 50%", 0.0, 0.5), ("even use, no bursts", 0.0, 0.0))
    rules = ("accuracy only", "+ frequency", "+ recency", "+ both (teacher confirms)", "+ both (self confirms)", "both, ties only (teacher)")
    res = {(c[0], d): {u: [0, 0] for u in rules} for c in cases for d in (0.5, 0.7)}; rare = {(c[0], d): {u: [0, 0] for u in rules} for c in cases for d in (0.5, 0.7)}
    for s in seeds:
        net = build(s, pats); keys = [b[0] for b in make_blocks(net, pats)]
        for d in (0.5, 0.7):
            pool = {k: [B.map_of(T.fresh_run(net, B.noisy(pats[k], random.Random(61000 + 97 * k + j), drop=d, jit=3)), (2,)) for j in range(20)] for k in range(T.NPAT)}
            for name, skew, burst in cases:
                seq, rareset = stream(random.Random(900 + s), n, skew, burst); pick = random.Random(77 + s); live = [pool[k][pick.randrange(20)] for k in seq]
                for u in rules:
                    freq = [0] * T.NPAT; last = [-10 ** 6] * T.NPAT
                    for t, (k, m) in enumerate(zip(seq, live)):
                        a = [acc_int(m, x) for x in keys]
                        def bonus(i):
                            fb = min(3, freq[i].bit_length()) if u not in ("accuracy only", "+ recency") else 0
                            age = t - last[i]; rb = (2 if age < 4 else 1 if age < 16 else 0) if u not in ("accuracy only", "+ frequency") else 0
                            return fb + rb
                        sc = [(8 * a[i] if u == "both, ties only (teacher)" else a[i]) + bonus(i) for i in range(T.NPAT)]; o = sorted(range(T.NPAT), key=lambda i: (-sc[i], i)); r = o[0]
                        res[(name, d)][u][0] += (r == k); res[(name, d)][u][1] += 1
                        if k in rareset: rare[(name, d)][u][0] += (r == k); rare[(name, d)][u][1] += 1
                        conf = (r == k) if u != "+ both (self confirms)" else (a[o[0]] - a[o[1]] >= margin)
                        if conf: freq[r] += 1; last[r] = t
                        if t % 64 == 63: freq = [f >> 1 for f in freq]
    print("\nPart 3. Rank: percent of recalls right (layer 2 map against the keys), %d recalls per stream, %d seeds; in brackets: the 4 least used patterns only" % (n, len(seeds)))
    print("   %-30s %-5s " % ("stream", "drop") + " ".join("%-27s" % u for u in rules))
    for name, _, _ in cases:
        for d in (0.5, 0.7):
            print("   %-30s %-5s " % (name, "%d%%" % (100 * d)) + " ".join("%-27s" % ("%.1f (%.1f)" % (100.0 * res[(name, d)][u][0] / res[(name, d)][u][1], 100.0 * rare[(name, d)][u][0] / max(1, rare[(name, d)][u][1]))) for u in rules))


if __name__ == "__main__":
    seeds = tuple(range(1, 1 + (int(sys.argv[1]) if len(sys.argv) > 1 else 5)))
    part12(seeds); part3(seeds)
