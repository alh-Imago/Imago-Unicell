"""hexn_busnet_hw_v2 (9 Nov 2026): HWNet (hexn_busnet_hw_v1, untouched) with a PIPELINE REGISTER after every serialiser, matching sub/verilog/hexn_bnet_net_v2.v. The packet chosen by a serialiser in clock t enters the sub-queues in clock t+1 (one clock more per hop). Direction doc section 46."""
import hexn_busnet_hw_v1 as W


class HWNetP(W.HWNet):
    def reset_stats(self):
        super().reset_stats(); self.stage = []

    def _push(self, s):
        for tb in self.targets.get(s, ()):
            sq = self.sqs[(tb, self.sgroup(s))]
            if len(sq) >= self.sq: self.dropped += 1; self.drop_sq += 1
            else: sq.append(s); self.pushed += 1; self.maxq = max(self.maxq, len(sq))

    def step(self, t, inputs=()):
        for s in self.stage: self._push(s)                                 # registered serialiser outputs of the previous clock enter the sub-queues
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


if __name__ == "__main__":
    import sys
    W.HWNet = HWNetP                       # run_cfg of v1 builds its merger network from this name: use the pipelined one
    a = sys.argv; W.run_cfg(int(a[1]), int(a[2]), int(a[3]), int(a[4]), int(a[5]), transfer=(len(a) > 6 and a[6] == "transfer"))
