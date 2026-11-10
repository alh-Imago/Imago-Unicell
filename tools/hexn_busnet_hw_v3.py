"""hexn_busnet_hw_v3 (10 Nov 2026): HWNetP (hexn_busnet_hw_v2, untouched) with a REGISTER between each merger's arbiter and its bus, matching sub/verilog/hexn_bnet_net_v5.v. The packet popped from the sub-queues in clock t is added to the cell accumulators, and can fire, in clock t+1 (one clock more per hop). Queue behaviour and drops are unchanged. Direction doc section 69. Step text cloned from hexn_busnet_hw_v2.HWNetP.step; the only changes are marked."""
import hexn_busnet_hw_v2 as P


class HWNetP2(P.HWNetP):
    def reset_stats(self):
        super().reset_stats(); self.popped = []

    def step(self, t, inputs=()):
        for b, s in self.popped:                                           # CHANGED: packets popped in the previous clock reach the cells now (refractory state as it was at the end of the previous clock)
            for g in self.bus_cells[b]:
                w = self.table[g].get(s)
                if w is not None and self.rleft[g] == 0: self.acc[g] += w
        self.popped = []
        for s in self.stage: self._push(s)
        self.stage = []
        for s in inputs: self._mark((0, 0), s)
        for sg in sorted(self.pend):
            p = self.pend[sg]
            if not p: continue
            n = self.nin if sg == (0, 0) else self.per; start = self.ptr.get(sg, 0)
            i = next((start + k) % n for k in range(n) if (start + k) % n in p); p.discard(i); self.ptr[sg] = (i + 1) % n; self.stage.append(self._global(sg, i))
        for b, sgs in self.bsg.items():
            for _ in range(self.ports):
                n = len(sgs); start = self.rr.get(b, 0) % n; got = None
                for k in range(n):
                    j = (start + k) % n
                    if self.sqs[(b, sgs[j])]: got = j; break
                if got is None: break
                s = self.sqs[(b, sgs[got])].popleft(); self.rr[b] = got + 1; self.served += 1
                self.popped.append((b, s))                                 # CHANGED: remembered for the next clock instead of added now
        fired = []
        for g in self.acc:
            if self.rleft[g] > 0: self.rleft[g] -= 1; continue
            if self.leak_every and t % self.leak_every == 0 and self.acc[g] > 0: self.acc[g] -= 1
            if self.acc[g] >= self.th_cell[g]: self.acc[g] = 0; self.rleft[g] = self.refr; fired.append(g)
        for g in fired:
            self.fires[g] = self.fires.get(g, 0) + 1; self.fire_t.setdefault(g, t); self._mark(self.bus_of(g), g)
        return fired
