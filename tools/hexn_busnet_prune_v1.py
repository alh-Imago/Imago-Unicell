"""hexn_busnet_prune_v1 (8 Nov 2026): train the feedback weights, then PRUNE, like a growing child (Alan 19:47: start with many connections and high plasticity; once paths are established prune to the most efficient shapes). Companion of hexn_busnet_v1 / _train_v1 / _fb_v1 / _gen_v1 (all untouched).
Training here covers layers 1, 2 and 3 including the feedback links into layer 1. The correct map of a pattern = the 10 teacher target cells in layers 2 and 3 (as before) plus the layer 1 cells that fire for the CLEAN pattern on the starting net (a clean teacher presentation). Same rule as before: target cell that did not fire gets weights from active sources raised, a cell that fired outside the target gets them lowered; bounded by the drift ceiling.
Pruning: a consolidation pass counts, for every connection, how often its source was active when its cell fired inside the correct map ('useful use'). Each cell then keeps only its KEEP most-used connections (ties: larger |weight|); the rest are removed and the bus delivery table is rebuilt.
Experiment: RICH net (k=24 plus 8 feedback links per layer 1 cell) trained, pruned to 14 per cell, short retrain; against LEAN net (k=10 plus 4 feedback, 14 per cell) trained for the same total epochs. Also the rich net trained but not pruned (more connections and traffic).
Simulation only. Usage: python3 tools/hexn_busnet_prune_v1.py"""
import random, copy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_fb_v1 as F, hexn_busnet_gen_v1 as G


def layer1_targets(net, pats):
    out = []
    for p in pats:
        ev = {}
        for i, t in p: ev.setdefault(t, []).append(i)
        n = T.fresh_run(net, ev); out.append({g for g in n.fires if n.layer_of(g) == 1})
    return out


def full_map(net): return {g for g in net.fires}


def step_all(net, w0, ev, target, step=1, ceil=6, freeze_fb=False):
    m = full_map(net); act = {i for ids in ev.values() for i in ids} | set(net.fires)
    for g in net.table:
        d = step if g in target and g not in m else -step if g in m and g not in target else 0
        if not d: continue
        for s in net.table[g]:
            if freeze_fb and net.layer_of(g) == 1 and s >= net.nin: continue
            if s in act:
                lo = max(w0[g][s] - ceil, -T.WMAX); hi = min(w0[g][s] + ceil, T.WMAX)
                net.table[g][s] = max(lo, min(hi, net.table[g][s] + d))


def train(net, pats, tg2, tg1, epochs, ceil=6, seed=77, w0=None, freeze_fb=False):
    w0 = w0 or copy.deepcopy(net.table); r = random.Random(seed)
    for e in range(epochs):
        for k in range(T.NPAT):
            ev = B.noisy(pats[k], random.Random(r.random())); n = T.fresh_run(net, ev)
            step_all(n, w0, ev, tg2[k] | tg1[k], ceil=ceil, freeze_fb=freeze_fb)
            for g in net.table: net.table[g] = n.table[g]
    return w0


def useful_counts(net, pats, tg2, tg1, nrun=10):
    use = {g: {s: 0 for s in net.table[g]} for g in net.table}
    for k in range(T.NPAT):
        for j in range(nrun):
            ev = B.noisy(pats[k], random.Random(30000 + 31 * k + j)); n = T.fresh_run(net, ev); act = {i for ids in ev.values() for i in ids} | set(n.fires)
            for g in n.fires:
                if g in (tg2[k] | tg1[k]):
                    for s in net.table[g]:
                        if s in act: use[g][s] += 1
    return use


def rebuild_targets(net):
    net.targets = {}
    for g, tab in net.table.items():
        l = net.layer_of(g); b = (l, (g - net.nin - (l - 1) * net.groups * net.per) // net.per)
        for s in tab: net.targets.setdefault(s, set()).add(b)
    net.bus_cells = {}
    for g in net.table:
        l = net.layer_of(g); net.bus_cells.setdefault((l, (g - net.nin - (l - 1) * net.groups * net.per) // net.per), []).append(g)


def prune(net, use, keep):
    """keep: an int (same for every cell) or {layer: n}"""
    for g in net.table:
        kp = keep[net.layer_of(g)] if isinstance(keep, dict) else keep
        order = sorted(net.table[g], key=lambda s: (-use[g][s], -abs(net.table[g][s]), s))
        net.table[g] = {s: net.table[g][s] for s in order[:kp]}
    rebuild_targets(net)


def n_conn(net): return sum(len(t) for t in net.table.values())


def traffic(net, pats, nrun=3):
    pk = dr = 0; tot = 0
    for k in range(T.NPAT):
        for j in range(nrun):
            n = T.fresh_run(net, B.noisy(pats[k], random.Random(8000 + 10 * k + j))); pk += n.pushed; dr += n.dropped; tot += 1
    return pk / tot, dr / tot


def report(label, net, pats, tg2):
    rec = [G.recall(net, pats, tg2, d, 3, ntest=10) for d in (0.1, 0.3, 0.5, 0.7)]; pk, dr = traffic(net, pats)
    return label, n_conn(net), [r[0] for r in rec], [r[1] for r in rec], pk, dr, F.afterglow(net, pats, 2)[0]


LEAN_KEEP = {1: 14, 2: 10, 3: 10}      # what the lean net has per cell (k=10, plus 4 feedback links on layer 1)


def main(seeds=(1, 2, 3, 4, 5), epochs=40, ft=10, stages=(LEAN_KEEP,), qd=8):
    """stages: the keep tables applied one after another, each followed by ft epochs of retraining (one stage = one-shot pruning). The last stage should equal LEAN_KEEP so the connection counts match."""
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; agg = {}; total = epochs + ft * len(stages)
    for s in seeds:
        rich = F.make(s, 0.5, fb_k=8, fb_w=2, k=24, refr=6, qdepth=qd); lean = F.make(s, 0.5, fb_k=4, fb_w=2, k=10, refr=6, qdepth=qd); tg2 = T.targets(rich, s)
        t1r = layer1_targets(rich, pats); t1l = layer1_targets(lean, pats)
        train(rich, pats, tg2, t1r, epochs); r_unp = copy.deepcopy(rich)
        for kp in stages:
            use = useful_counts(rich, pats, tg2, t1r); prune(rich, use, kp); w0p = copy.deepcopy(rich.table); train(rich, pats, tg2, t1r, ft, w0=w0p, seed=78)
        train(lean, pats, tg2, t1l, total)
        for name, net in (("rich, trained %d epochs, not pruned" % epochs, r_unp), ("rich, pruned in %d stage(s), %d epochs in all" % (len(stages), total), rich), ("lean from the start, %d epochs" % total, lean)):
            lab, c, ok, tot, pk, dr, gl = report(name, net, pats, tg2); a = agg.setdefault(lab, [0, [0] * 4, [0] * 4, 0, 0, 0, 0])
            a[0] += c; a[3] += pk; a[4] += dr; a[5] += gl; a[6] += 1
            for i in range(4): a[1][i] += ok[i]; a[2][i] += tot[i]
    print("%-46s %8s %s %9s %8s %7s" % ("network (all trained, %d wiring seeds)" % len(seeds), "conns", "  ".join("drop%2d%%" % d for d in (10, 30, 50, 70)), "pk/run", "dropped", "glow"))
    for lab, a in agg.items(): print("%-46s %8d %s %9.0f %8.1f %7.1f" % (lab, a[0] / a[6], "  ".join("%6d%%" % (100 * a[1][i] / a[2][i]) for i in range(4)), a[3] / a[6], a[4] / a[6], a[5] / a[6]))


def fb_control(seeds=(1, 2, 3, 4, 5), epochs=60):
    """lean net, layers 1 to 3 trained: feedback weights trained vs feedback weights frozen at the random +-2 start; and the same with no feedback links at all"""
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; agg = {}
    for s in seeds:
        for lab, kw, inh, fz in (("feedback weights trained", dict(fb_k=4, fb_w=2, refr=6), 0.5, False), ("feedback weights frozen", dict(fb_k=4, fb_w=2, refr=6), 0.5, True), ("no feedback links", dict(refr=6), 0.0, False)):
            net = F.make(s, inh, **kw); tg2 = T.targets(net, s); t1 = layer1_targets(net, pats); train(net, pats, tg2, t1, epochs, freeze_fb=fz)
            r = [G.recall(net, pats, tg2, d, 3, ntest=10) for d in (0.1, 0.3, 0.5, 0.7)]; a = agg.setdefault(lab, [[0] * 4, [0] * 4])
            for i in range(4): a[0][i] += r[i][0]; a[1][i] += r[i][1]
    print("%-28s %s" % ("lean net, layers 1-3 trained", "  ".join("drop%2d%%" % d for d in (10, 30, 50, 70))))
    for lab, a in agg.items(): print("%-28s %s" % (lab, "  ".join("%6d%%" % (100 * a[0][i] / a[1][i]) for i in range(4))))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "oneshot"
    if mode == "oneshot": main()
    elif mode == "long": main(epochs=100)
    elif mode == "gradual": main(stages=({1: 22, 2: 16, 3: 16}, LEAN_KEEP))
    elif mode == "fbcontrol": fb_control()
    elif mode == "deepq": main(qd=64)
    elif mode == "long-gradual": main(epochs=100, stages=({1: 22, 2: 16, 3: 16}, LEAN_KEEP))
