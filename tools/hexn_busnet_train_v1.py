"""hexn_busnet_train_v1 (8 Nov 2026): map feedback that trains the cells, in the bus network toy (hexn_busnet_v1 untouched). Alan 18:59: build the map feedback.
Teacher mode: each of the 8 patterns is given a TARGET MAP (5 chosen cells in layer 2 and 5 in layer 3, different for every pattern). A training step runs one noisy example of a known pattern and compares the map it made (layer 2 and 3 cells that fired) with the target:
  - target cell that did NOT fire: every weight on it from a source that was active in this run goes up by STEP;
  - cell that fired but is NOT in the target: those weights go down by STEP.
Weights stay within +-CEIL of the starting wiring (the drift ceiling of the training scheme, sections 10 to 12) and within +-WMAX. Only existing connections change (the wiring is fixed).
Test: single recall (nearest target map by overlap) and mixture test (half of A + half of B; hit = the two best maps are A and B), before and after training, over several wiring seeds. Test noise seeds differ from training noise seeds.
Simulation only. Usage: python3 tools/hexn_busnet_train_v1.py"""
import random, copy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B

STEP = 1; CEIL = 3; WMAX = 4; NPAT = 8; PER_LAYER = 5


def targets(net, seed=0):
    r = random.Random(900 + seed); out = [set() for _ in range(NPAT)]
    for l in (2, 3):
        ids = [net.gid(l, i) for i in range(net.groups * net.per)]; r.shuffle(ids)
        for k in range(NPAT): out[k] |= set(ids[k * PER_LAYER:(k + 1) * PER_LAYER])
    return out


def active_sources(net, ev):
    a = {i for ids in ev.values() for i in ids}
    return a | set(net.fires)


def train_step(net, w0, ev, target, step=STEP, ceil=CEIL):
    m = B.map_of(net); act = active_sources(net, ev); changed = 0
    for g in net.table:
        if net.layer_of(g) not in (2, 3): continue
        d = step if g in target and g not in m else -step if g in m and g not in target else 0
        if not d: continue
        for s in net.table[g]:
            if s in act:
                nw = net.table[g][s] + d; lo = max(w0[g][s] - ceil, -WMAX); hi = min(w0[g][s] + ceil, WMAX)
                nw = max(lo, min(hi, nw))
                if nw != net.table[g][s]: net.table[g][s] = nw; changed += 1
    return changed


def fresh_run(net_template, ev, total=100):
    """run a pattern on a copy of the net state (weights kept, accumulators reset)"""
    n = copy.deepcopy(net_template); n.acc = {g: 0 for g in n.acc}; n.rleft = {g: 0 for g in n.rleft}
    for q in n.queues.values(): q.clear()
    n.reset_stats(); n.run(ev, total); return n


def train(net, pats, tg, epochs=40, **kw):
    w0 = copy.deepcopy(net.table); r = random.Random(77); log = []
    for e in range(epochs):
        ch = 0
        for k in range(NPAT):
            ev = B.noisy(pats[k], random.Random(r.random()))             # the same noisy input is run and used to see which sources were active
            n = fresh_run(net, ev)
            ch += train_step(n, w0, ev, tg[k], **kw)
            for g in net.table: net.table[g] = n.table[g]
        log.append(ch)
    return log


def evaluate(net, pats, tg, ntest=20, nmix=10, nrun=10):
    ok = tot = 0; ov = []
    for k in range(NPAT):
        for j in range(ntest):
            n = fresh_run(net, B.noisy(pats[k], random.Random(1000 + 50 * k + j))); m = B.map_of(n); sc = [B.jaccard(m, t) for t in tg]
            ok += (max(range(NPAT), key=lambda x: sc[x]) == k); tot += 1; ov.append(sc[k])
    hit = mt = 0; pr = random.Random(5)
    for _ in range(nmix):
        a, b = pr.sample(range(NPAT), 2); mix = pats[a][:len(pats[a]) // 2] + pats[b][len(pats[b]) // 2:]
        for j in range(nrun):
            n = fresh_run(net, B.noisy(mix, random.Random(5000 + 100 * a + 10 * b + j))); m = B.map_of(n); sc = [B.jaccard(m, t) for t in tg]
            hit += (set(sorted(range(NPAT), key=lambda x: -sc[x])[:2]) == {a, b}); mt += 1
    return ok, tot, hit, mt, sum(ov) / len(ov)


def main(seeds=(1, 2, 3, 4, 5), epochs=40, ceil=CEIL):
    pats = [B.pattern(random.Random(100 + k)) for k in range(NPAT)]
    print("%-5s %-10s %12s %14s %16s" % ("seed", "state", "single", "mixture A+B", "overlap w/ right"))
    tot = {"before": [0, 0, 0, 0], "after": [0, 0, 0, 0]}
    for s in seeds:
        net = B.Net(s); tg = targets(net, s)
        for state in ("before", "after"):
            if state == "after": log = train(net, pats, tg, epochs, ceil=ceil)
            ok, t, hit, mt, ov = evaluate(net, pats, tg)
            print("%-5d %-10s %5d/%-6d %7d/%-6d %16.2f" % (s, state, ok, t, hit, mt, ov))
            for i, v in enumerate((ok, t, hit, mt)): tot[state][i] += v
        print("      weight changes per epoch: first %d, last %d" % (log[0], log[-1]))
    for st in ("before", "after"): print("ALL   %-10s %5d/%-6d %7d/%-6d" % (st, tot[st][0], tot[st][1], tot[st][2], tot[st][3]))


if __name__ == "__main__":
    if len(sys.argv) > 2: main(epochs=int(sys.argv[1]), ceil=int(sys.argv[2]))
    else: main()
