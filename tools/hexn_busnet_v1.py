"""hexn_busnet_v1 (8 Nov 2026; Alan 18:39 and 18:43: layers of small shared buses, the activity MAP the judge can recall, fuzzy match of two maps, and a feedback matrix). Simulation, host side, pure Python, one step per clock. NOT hardware; every number is a property of this toy, not of the Kintex card.
Network: NIN input ids; LAYERS layers of GROUPS buses with PER cells on each bus. A cell listens to K random sources of the layer below (input ids for layer 1), each with a small signed weight (a power of two or one). A bus carries ONE packet (a source id) per clock from a queue of depth QDEPTH (a full queue drops the packet). A cell with an entry for the packet's id adds its weight to its accumulator (only if not refractory); the accumulator leaks by 1 every LEAK_EVERY clocks; at TH the cell fires, resets, becomes refractory for REFR clocks, and sends one packet to every bus of the next layer that has a listener for it. Optional feedback: each layer 1 cell also listens to FB_K random layer 3 cells with weight FB_W (negative = inhibitory).
Tests (tests/vm/test_hexn_busnet_v1.py): delivery to matching cells only, one packet per bus per clock, queue drop, leak, refractory, determinism. Experiments: see main() and direction doc section 32.
Usage: python3 tools/hexn_busnet_v1.py"""
import random
from collections import deque

NIN = 48; LAYERS = 3; GROUPS = 4; PER = 16; K = 10


class Net:
    def __init__(self, seed=1, th=3, leak_every=4, refr=3, qdepth=8, fb_k=0, fb_w=0, inhib_share=0.2, k=K, nin=NIN, layers=LAYERS, groups=GROUPS, per=PER):
        r = random.Random(seed); self.nin, self.layers, self.groups, self.per = nin, layers, groups, per
        self.th, self.leak_every, self.refr, self.qdepth = th, leak_every, refr, qdepth; ncell = groups * per
        self.gid = lambda l, i: nin + (l - 1) * ncell + i            # global id of cell i of layer l (layers count from 1)
        self.table = {}; self.acc = {}; self.rleft = {}; self.targets = {}; self.bus_cells = {}
        for l in range(1, layers + 1):
            src = list(range(nin)) if l == 1 else [self.gid(l - 1, i) for i in range(ncell)]
            for i in range(ncell):
                g = self.gid(l, i); tab = {}
                for s in r.sample(src, k): w = r.choice((1, 2)); tab[s] = -w if r.random() < inhib_share else w
                if l == 1 and fb_k:
                    for s in r.sample([self.gid(layers, j) for j in range(ncell)], fb_k): tab[s] = fb_w
                self.table[g] = tab; self.acc[g] = 0; self.rleft[g] = 0; self.bus_cells.setdefault((l, i // per), []).append(g)
                for s in tab: self.targets.setdefault(s, set()).add((l, i // per))
        self.queues = {b: deque() for b in self.bus_cells}; self.reset_stats()

    def reset_stats(self):
        self.pushed = 0; self.dropped = 0; self.maxq = 0; self.fires = {}; self.fire_t = {}; self.served = 0

    def push(self, bus, src):
        q = self.queues[bus]
        if len(q) >= self.qdepth: self.dropped += 1; return
        q.append(src); self.pushed += 1; self.maxq = max(self.maxq, len(q))

    def step(self, t, inputs=()):
        for s in inputs:
            for b in self.targets.get(s, ()): self.push(b, s)
        for b, q in self.queues.items():                              # one packet per bus per clock, seen by every cell on that bus
            if q:
                s = q.popleft(); self.served += 1
                for g in self.bus_cells[b]:
                    w = self.table[g].get(s)
                    if w is not None and self.rleft[g] == 0: self.acc[g] += w
        fired = []
        for g in self.acc:
            if self.rleft[g] > 0: self.rleft[g] -= 1; continue
            if self.leak_every and t % self.leak_every == 0 and self.acc[g] > 0: self.acc[g] -= 1
            if self.acc[g] >= self.th: self.acc[g] = 0; self.rleft[g] = self.refr; fired.append(g)
        for g in fired:
            self.fires[g] = self.fires.get(g, 0) + 1; self.fire_t.setdefault(g, t)
            for b in self.targets.get(g, ()): self.push(b, g)
        return fired

    def run(self, events, total):
        """events: {clock: [input ids]}; -> per-clock fire counts"""
        per_clock = []
        for t in range(total): per_clock.append(len(self.step(t, events.get(t, ()))))
        return per_clock

    def layer_of(self, g): return (g - self.nin) // (self.groups * self.per) + 1


def pattern(r, nin=NIN, size=12, spikes=3, window=40): return [(i, r.randrange(window)) for i in r.sample(range(nin), size) for _ in range(spikes)]


def noisy(pat, r, drop=0.1, jit=3, extra=6, nin=NIN, window=40):
    ev = [(i, max(0, t + r.randint(-jit, jit))) for i, t in pat if r.random() >= drop] + [(r.randrange(nin), r.randrange(window)) for _ in range(extra)]
    d = {}
    for i, t in ev: d.setdefault(t, []).append(i)
    return d


def jaccard(a, b): return len(a & b) / len(a | b) if (a or b) else 1.0


def map_of(net, layers=(2, 3)): return {g for g in net.fires if net.layer_of(g) in layers}


def trial(seed, ev, total=100, **kw):
    n = Net(seed, **kw); pc = n.run(ev, total); return n, pc


def main():
    S = 1; r = random.Random(7)
    print("1. Flow, delay and traffic (one clean pattern, 12 inputs x 3 spikes in 40 clocks)")
    pat = pattern(r); ev = {}
    for i, t in pat: ev.setdefault(t, []).append(i)
    n, pc = trial(S, ev)
    first_in = min(t for _, t in pat); l3 = [t for g, t in n.fire_t.items() if n.layer_of(g) == 3]
    print("   cells that fired per layer:", [sum(1 for g in n.fires if n.layer_of(g) == l) for l in (1, 2, 3)], "of", GROUPS * PER, "each")
    print("   first layer 3 fire %s clocks after the first input; packets pushed %d, served %d, dropped %d, longest queue %d (depth %d)" % (min(l3) - first_in if l3 else None, n.pushed, n.served, n.dropped, n.maxq, n.qdepth))
    print("\n2. Recall of the map: 8 patterns, stored map = cells (layers 2 and 3) that fired in at least 3 of 5 noisy training runs; 20 noisy test runs each")
    pats = [pattern(random.Random(100 + k)) for k in range(8)]; stored = []
    for p in pats:
        cnt = {}
        for j in range(5):
            n, _ = trial(S, noisy(p, random.Random(j))); [cnt.__setitem__(g, cnt.get(g, 0) + 1) for g in map_of(n)]
        stored.append({g for g, c in cnt.items() if c >= 3})
    ok = tot = 0; same = []; diff = []
    for k, p in enumerate(pats):
        for j in range(20):
            n, _ = trial(S, noisy(p, random.Random(1000 + 50 * k + j))); m = map_of(n); sc = [jaccard(m, s) for s in stored]
            ok += (max(range(8), key=lambda x: sc[x]) == k); tot += 1; same.append(sc[k]); diff += [sc[x] for x in range(8) if x != k]
    print("   stored map sizes:", [len(s) for s in stored], "| right pattern picked %d of %d | mean overlap (Jaccard) with the right map %.2f, with the wrong ones %.2f" % (ok, tot, sum(same) / len(same), sum(diff) / len(diff)))
    print("\n3. Mixtures: half of pattern A's spikes and half of B's (10 pairs x 10 runs)")
    hit = tot = 0; inside = []; pr = random.Random(5)
    for _ in range(10):
        a, b = pr.sample(range(8), 2); mix = pats[a][:len(pats[a]) // 2] + pats[b][len(pats[b]) // 2:]
        for j in range(10):
            n, _ = trial(S, noisy(mix, random.Random(5000 + 100 * a + 10 * b + j))); m = map_of(n); sc = [jaccard(m, s) for s in stored]
            top2 = sorted(range(8), key=lambda x: -sc[x])[:2]; hit += (set(top2) == {a, b}); tot += 1; inside.append(len(m & (stored[a] | stored[b])) / max(1, len(m)))
    print("   the two best-matching stored maps are exactly A and B in %d of %d runs; share of the mixture's cells that lie in map A or map B: %.2f" % (hit, tot, sum(inside) / len(inside)))
    print("\n4. Feedback (layer 3 -> layer 1, 4 links per layer 1 cell), activity AFTER the input has stopped (clocks 60 to 100 of 100), clean pattern")
    print("   %-34s %12s %12s %9s" % ("setting", "packets/clk", "cells firing", "dropped"))
    for label, kw in (("no feedback", {}), ("feedback w=+1", dict(fb_k=4, fb_w=1)), ("feedback w=+2", dict(fb_k=4, fb_w=2)), ("feedback w=+3", dict(fb_k=4, fb_w=3)), ("w=+3, refractory 8", dict(fb_k=4, fb_w=3, refr=8)), ("w=+3, refractory 8, leak every clock", dict(fb_k=4, fb_w=3, refr=8, leak_every=1)), ("w=+3, 50% inhibitory feedback", dict(fb_k=4, fb_w=3, inhib_share=0.5))):
        n = Net(S, **kw); late = {}; tp = 0
        for t in range(100):
            before = n.pushed; f = n.step(t, ev.get(t, ()))
            if t >= 60: tp += n.pushed - before; [late.__setitem__(g, 1) for g in f]
        print("   %-34s %12.2f %12d %9d" % (label, tp / 40.0, len(late), n.dropped))


if __name__ == "__main__": main()
