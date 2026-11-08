"""hexn_busnet_homeo_v1 (8 Nov 2026): cells that set their own firing level (threshold). Alan 20:17 ('that sounds right') following direction doc section 38. Earlier tools untouched.
AdaptNet = the bus network with a threshold per cell. Homeostasis: after every training epoch the network is run on the patterns and each cell's firing rate (share of runs in which it fired) is compared with the target rate for its layer; a cell firing well above target raises its own threshold by 1, a cell well below lowers it by 1 (limits 2 to 9). Target rates are set per layer (layer 1: 0.40, layer 2: 0.08, layer 3: 0.05; chosen after measuring the tuned fixed-threshold net, which fired at 0.39, 0.08 and 0.03 on average, so these numbers are NOT independent of the answer; the test is that the result no longer depends on the starting threshold).
Experiment: start thresholds 2, 3, 5, 7; fixed against homeostatic; lean net (10 sources per cell) and rich net (24); 50 epochs, 5 seeds, same recall test (spikes dropped 10/30/50/70 percent). Simulation only.
Usage: python3 tools/hexn_busnet_homeo_v1.py MODE NET TH   (MODE fixed|homeo, NET lean|rich)"""
import random, copy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_fb_v1 as F, hexn_busnet_gen_v1 as G, hexn_busnet_prune_v1 as P

TARGET = {1: 0.40, 2: 0.08, 3: 0.05}; TH_MIN, TH_MAX = 2, 9


class AdaptNet(B.Net):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw); self.th_cell = {g: self.th for g in self.table}

    def step(self, t, inputs=()):
        for s in inputs:
            for b in self.targets.get(s, ()): self.push(b, s)
        for b, q in self.queues.items():
            if q:
                s = q.popleft(); self.served += 1
                for g in self.bus_cells[b]:
                    w = self.table[g].get(s)
                    if w is not None and self.rleft[g] == 0: self.acc[g] += w
        fired = []
        for g in self.acc:
            if self.rleft[g] > 0: self.rleft[g] -= 1; continue
            if self.leak_every and t % self.leak_every == 0 and self.acc[g] > 0: self.acc[g] -= 1
            if self.acc[g] >= self.th_cell[g]: self.acc[g] = 0; self.rleft[g] = self.refr; fired.append(g)
        for g in fired:
            self.fires[g] = self.fires.get(g, 0) + 1; self.fire_t.setdefault(g, t)
            for b in self.targets.get(g, ()): self.push(b, g)
        return fired


def make(seed, fb_inhib=0.5, **kw):
    n = AdaptNet(seed, **kw)
    if fb_inhib:
        r = random.Random(4000 + seed); l3 = {n.gid(n.layers, j) for j in range(n.groups * n.per)}
        for g in n.table:
            if n.layer_of(g) == 1:
                for s in list(n.table[g]):
                    if s in l3 and r.random() < fb_inhib: n.table[g][s] = -abs(n.table[g][s])
    return n


def rates(net, pats, nrun=2):
    cnt = {g: 0 for g in net.table}; tot = 0
    for k in range(T.NPAT):
        for j in range(nrun):
            n = T.fresh_run(net, B.noisy(pats[k], random.Random(60000 + 13 * k + j)))
            for g in n.fires: cnt[g] += 1
            tot += 1
    return {g: c / tot for g, c in cnt.items()}


def homeostat(net, pats):
    r = rates(net, pats); up = down = 0
    for g, x in r.items():
        tgt = TARGET[net.layer_of(g)]
        if x > 1.5 * tgt + 0.02 and net.th_cell[g] < TH_MAX: net.th_cell[g] += 1; up += 1
        elif x < 0.5 * tgt and net.th_cell[g] > TH_MIN: net.th_cell[g] -= 1; down += 1
    return up, down


def train(net, pats, tg2, tg1, epochs, homeo=True, ceil=6):
    w0 = copy.deepcopy(net.table)
    for e in range(epochs):
        P.train(net, pats, tg2, tg1, 1, ceil=ceil, seed=77 + e, w0=w0)
        if homeo: homeostat(net, pats)


def mean_th(net):
    out = {}
    for l in (1, 2, 3):
        v = [net.th_cell[g] for g in net.table if net.layer_of(g) == l]; out[l] = sum(v) / len(v)
    return out


def main(mode, netkind, th, seeds=(1, 2, 3, 4, 5), epochs=50):
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; kw = dict(fb_k=4, k=10) if netkind == "lean" else dict(fb_k=8, k=24)
    ok = [0] * 4; tot = [0] * 4; dr = 0; ths = {1: 0, 2: 0, 3: 0}
    for s in seeds:
        net = make(s, 0.5, fb_w=2, refr=6, th=th, **kw); tg2 = T.targets(net, s); t1 = P.layer1_targets(net, pats)
        train(net, pats, tg2, t1, epochs, homeo=(mode == "homeo"))
        rec = [G.recall(net, pats, tg2, d, 3, ntest=10) for d in (0.1, 0.3, 0.5, 0.7)]
        for i in range(4): ok[i] += rec[i][0]; tot[i] += rec[i][1]
        dr += P.traffic(net, pats)[1]; m = mean_th(net)
        for l in ths: ths[l] += m[l]
    print("%-6s %-5s start th %d : %s  dropped %6.1f  final mean th L1 %.1f L2 %.1f L3 %.1f" % (mode, netkind, th, "  ".join("%3d%%" % (100 * ok[i] / tot[i]) for i in range(4)), dr / len(seeds), ths[1] / len(seeds), ths[2] / len(seeds), ths[3] / len(seeds)))


if __name__ == "__main__": main(sys.argv[1], sys.argv[2], int(sys.argv[3]))
