"""hexn_busnet_hw_v1 (8 Nov 2026): the bus network with the MERGER, i.e. the hardware-faithful traffic model. Alan 22:08 (design the merger with the other parts in mind). Direction doc section 44. Earlier tools untouched.
Why: the ideal model lets any number of packets enter one bus queue in one clock. A real bus takes one. Design modelled here (every part is a queue or an arbiter, all of it plain logic):
  * SOURCE SERIALISER: every source group (one bus of cells, or the external input lines) has one PENDING bit per source and a rotating pointer. Everything that fires in a clock sets its bit at once; ONE pending source per clock is sent to every target bus that listens to it. (A first version of this model used a first-in-first-out fire queue; that cannot take several writes in one clock, so it was replaced. Its results were similar: see section 44.)
  * SUB-QUEUES: each target bus has one small queue (depth SQ) per source group that feeds it, so a target bus never gets two writes in a clock (one from each source group at most).
  * ARBITER: each target bus takes PORTS packets per clock from its sub-queues, round robin; PORTS=2 needs a table with two read ports.
Everything else is as hexn_busnet_homeo_v1 (per-cell thresholds, refractory, leak, weights). Drops are counted at the fire queues and the sub-queues.
Usage: python3 tools/hexn_busnet_hw_v1.py PORTS FQ SQ GROUPS PER [transfer]"""
import random, copy, sys, os, bisect
from collections import deque
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_busnet_v1 as B, hexn_busnet_train_v1 as T, hexn_busnet_gen_v1 as G, hexn_busnet_prune_v1 as P, hexn_busnet_prune2_v1 as Q, hexn_busnet_homeo_v1 as H, hexn_busnet_shape_v1 as S


class HWNet(H.AdaptNet):
    """hardware-faithful traffic model. Serialiser = a PENDING bit per source (cell or input line) plus a rotating pointer: all cells that fire in a clock set their bit at once, one pending bit per clock is sent (first set bit at or after the pointer), a second fire of a cell whose bit is still set is MERGED (lost, counted). Sub-queues: one FIFO (depth SQ) per (target bus, source group), all created up front; the arbiter of a bus takes PORTS packets per clock round robin. This is exactly what sub/verilog/hexn_bnet_net_v1.v builds (cross-checked clock for clock in tests/vm/test_hexn_bnet_net_v1.py, PORTS=1)."""
    def __init__(self, *a, fq=16, sq=8, ports=1, **kw):
        self.sq, self.ports = sq, ports
        super().__init__(*a, **kw)

    def reset_stats(self):
        super().reset_stats(); self.drop_fq = 0; self.drop_sq = 0; self.pend = {}; self.ptr = {}; self.rr = {}; self.sqs = {}; self.bsg = {}
        ncell = self.groups * self.per; l3first = self.nin + (self.layers - 1) * ncell
        self.fb = any(s >= l3first for g in self.table if self.layer_of(g) == 1 for s in self.table[g])
        for l in range(1, self.layers + 1):
            for i in range(self.groups):
                srcs = ([(0, 0)] + ([(self.layers, j) for j in range(self.groups)] if self.fb else [])) if l == 1 else [(l - 1, j) for j in range(self.groups)]
                self.bsg[(l, i)] = srcs
                for sg in srcs: self.sqs[((l, i), sg)] = deque()

    def bus_of(self, g):
        l = self.layer_of(g); return (l, (g - self.nin - (l - 1) * self.groups * self.per) // self.per)

    def sgroup(self, s): return (0, 0) if s < self.nin else self.bus_of(s)

    def _local(self, sg, s): return s if sg == (0, 0) else (s - self.nin - (sg[0] - 1) * self.groups * self.per) % self.per

    def _global(self, sg, i): return i if sg == (0, 0) else self.nin + (sg[0] - 1) * self.groups * self.per + sg[1] * self.per + i

    def _mark(self, sg, s):
        p = self.pend.setdefault(sg, set()); i = self._local(sg, s)
        if i in p: self.dropped += 1; self.drop_fq += 1
        else: p.add(i)

    def step(self, t, inputs=()):
        for s in inputs: self._mark((0, 0), s)
        for sg in sorted(self.pend):                                      # serialiser: one pending source per source group per clock
            p = self.pend[sg]
            if not p: continue
            n = self.nin if sg == (0, 0) else self.per; start = self.ptr.get(sg, 0)
            i = next((start + k) % n for k in range(n) if (start + k) % n in p); p.discard(i); self.ptr[sg] = (i + 1) % n; s = self._global(sg, i)
            for tb in self.targets.get(s, ()):
                sq = self.sqs[(tb, sg)]
                if len(sq) >= self.sq: self.dropped += 1; self.drop_sq += 1
                else: sq.append(s); self.pushed += 1; self.maxq = max(self.maxq, len(sq))
        for b, sgs in self.bsg.items():                                   # arbiter: PORTS packets per clock, round robin over this bus's sub-queues
            for _ in range(self.ports):
                n = len(sgs); start = self.rr.get(b, 0) % n; got = None
                for k in range(n):
                    j = (start + k) % n
                    if self.sqs[(b, sgs[j])]: got = j; break
                if got is None: break
                s = self.sqs[(b, sgs[got])].popleft(); self.rr[b] = got + 1; self.served += 1
                for g in self.bus_cells[b]:
                    w = self.table[g].get(s)
                    if w is not None and self.rleft[g] == 0: self.acc[g] += w
        fired = []
        for g in self.acc:
            if self.rleft[g] > 0: self.rleft[g] -= 1; continue
            if self.leak_every and t % self.leak_every == 0 and self.acc[g] > 0: self.acc[g] -= 1
            if self.acc[g] >= self.th_cell[g]: self.acc[g] = 0; self.rleft[g] = self.refr; fired.append(g)
        for g in fired:
            self.fires[g] = self.fires.get(g, 0) + 1; self.fire_t.setdefault(g, t); self._mark(self.bus_of(g), g)
        return fired


def run_cfg(ports, fq, sq, groups, per, th=5, seeds=(1, 2, 3, 4, 5), epochs=40, ft=10, transfer=False):
    pats = [B.pattern(random.Random(100 + k)) for k in range(T.NPAT)]; rows = {}
    for s in seeds:
        kw = dict(refr=6, th=th, groups=groups, per=per)
        ideal = H.make(s, 0.5, fb_k=8, fb_w=2, k=24, **kw); tg2 = T.targets(ideal, s); t1 = P.layer1_targets(ideal, pats)
        H.train(ideal, pats, tg2, t1, epochs, homeo=True); Q.prune_by(ideal, P.LEAN_KEEP, "weight"); H.train(ideal, pats, tg2, t1, ft, homeo=True)
        if transfer:
            hw = HWNet(s, fq=fq, sq=sq, ports=ports, k=24, fb_k=8, fb_w=2, **kw)
            hw.th_cell = dict(ideal.th_cell); hw.table = copy.deepcopy(ideal.table); P.rebuild_targets(hw); nets = (("ideal model, pruned dense", ideal), ("same weights run on the merger model", hw))
        else:
            orig = H.AdaptNet; H.AdaptNet = lambda seed, **k2: HWNet(seed, fq=fq, sq=sq, ports=ports, **k2)
            try:
                hw = H.make(s, 0.5, fb_k=8, fb_w=2, k=24, **kw); t1h = P.layer1_targets(hw, pats); H.train(hw, pats, tg2, t1h, epochs, homeo=True); Q.prune_by(hw, P.LEAN_KEEP, "weight"); H.train(hw, pats, tg2, t1h, ft, homeo=True)
            finally: H.AdaptNet = orig
            nets = (("ideal model, pruned dense", ideal), ("merger model, trained in it", hw))
        for name, net in nets:
            rec = [G.recall(net, pats, tg2, d, 3, ntest=10) for d in (0.1, 0.3, 0.5, 0.7)]; dfq = dsq = 0.0; runs = 0
            for k in range(T.NPAT):
                for j in range(3):
                    n = T.fresh_run(net, B.noisy(pats[k], random.Random(8000 + 10 * k + j))); runs += 1
                    dfq += getattr(n, "drop_fq", 0); dsq += getattr(n, "drop_sq", n.dropped if not hasattr(n, "drop_sq") else 0)
            a, b = S.delays(net, pats); r = rows.setdefault(name, [[0] * 4, [0] * 4, 0, 0, 0, 0, 0])
            for i in range(4): r[0][i] += rec[i][0]; r[1][i] += rec[i][1]
            r[2] += dfq / runs; r[3] += dsq / runs; r[4] += a; r[5] += b; r[6] += 1
    print("PORTS %d  fire queue %d  sub-queue %d  buses/layer %d x %d cells" % (ports, fq, sq, groups, per))
    for name, r in rows.items(): print("  %-38s %s  dropped fire-queue %5.1f sub-queue %5.1f  delay first L3 %.1f, 90%% of map %.1f" % (name, "  ".join("%3d%%" % (100 * r[0][i] / r[1][i]) for i in range(4)), r[2] / r[6], r[3] / r[6], r[4] / r[6], r[5] / r[6]))


if __name__ == "__main__":
    a = sys.argv; run_cfg(int(a[1]), int(a[2]), int(a[3]), int(a[4]), int(a[5]), transfer=(len(a) > 6 and a[6] == "transfer"))
