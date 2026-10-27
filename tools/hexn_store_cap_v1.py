"""hexn_store_cap_v1: CAPACITY and DROP test of the layer 2 store v5 on the card (core v9). Host-LOADs a long random event stream straight into the store (command 0x1A, LOAD, N=3, W=80; a load adds entries directly, while observe mode on random events promotes almost nothing because of the 32-slot candidate table) until the dense heap and the address index fill, and checks every answer and the counters (known, candidates, promoted, dropk, dropc) against the bit-true model tools/hexn_store_v5.py as it goes; then reads back and compares every index slot, row header, entry and candidate word. Prints the counter trajectory so you can see where the first drop happens and how the store behaves afterwards (entries already held must still answer; new contexts are dropped and counted).
The model predicts the first drop after about 140 events (index probe full) and the heap full (512 rows) by about 450.
Start from a FRESHLY LOADED bitstream: the store's clock t counts from 0 at load and the model assumes that.
  python3 tools/hexn_store_cap_v1.py --port /dev/ttyUSB1 [--events 2000] [--sample 1 (compare every n-th table row; 1 = all)] [--classes 15] [--seed 7]
Result line: STORE CAPACITY CHECK PASS / FAIL."""
import sys, os, random, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_host_v3 as H, hexn_hold_card_v1 as HC, hexn_store_v5 as M
class HB5(HC.HB):
    def sethm(self, m): self.s.write(bytes([0x17, m & 1])); self._ack()
    def scfg(self, n, w, mode): self.s.write(bytes([0x18, n & 15, w & 255, (w >> 8) & 255, mode & 3])); self._ack()
    def sclr(self): self.s.write(bytes([0x19])); self._ack()
    def sval(self, s, g): self.s.write(bytes([0x1E, s & 7, g & 3])); self._ack()
    def reward(self, r): self.s.write(bytes([0x1F, r & 255])); self._ack()
    def srd(self, tab, addr): self.s.write(bytes([0x27, tab, addr & 255, (addr >> 8) & 255])); r = self._rd(5); return sum(r[i] << (8 * i) for i in range(5))
    def sstat(self): self.s.write(bytes([0x1C])); r = self._rd(10); return [r[2 * i] | r[2 * i + 1] << 8 for i in range(5)]
    def slast(self):
        self.s.write(bytes([0x1D])); r = self._rd(5)
        return dict(verdict=r[0] & 3, vlevel=(r[0] >> 2) & 3, plevel=(r[0] >> 4) & 3, pbest=r[1] & 15, pbest_seen=r[2], ptotal=r[3] | (r[4] & 15) << 8)
    def sgoal(self):
        self.s.write(bytes([0x26])); r = self._rd(2); return dict(gbest=r[0] & 15, gval=r[1] if r[1] < 128 else r[1] - 256)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200); ap.add_argument("--events", type=int, default=2000); ap.add_argument("--classes", type=int, default=15); ap.add_argument("--seed", type=int, default=7); ap.add_argument("--every", type=int, default=250); ap.add_argument("--sample", type=int, default=1)
    a = ap.parse_args()
    import serial; ser = serial.Serial(a.port, a.baud, timeout=5); b = HB5(ser, 7, 18)
    if not b.sync(): sys.exit(2)
    bad = 0; model = M.StoreV5(N=3, W=80, vshift=2, glvl=1, EVB=4, IB=10, R=4, HROWS=512, P=4, CCAP=32)
    b.sethm(1); b.sclr(); model.step(M.CLR); b.scfg(3, 80, 1); model.N = 3; model.W = 80
    r = random.Random(a.seed); t = 0; first_drop = None
    def stcmd(c, e):
        b.s.write(bytes([0x1A, c, e])); q = b._rd(5)
        return dict(verdict=q[0] & 3, vlevel=(q[0] >> 2) & 3, plevel=(q[0] >> 4) & 3, pbest=q[1] & 15, pbest_seen=q[2], ptotal=q[3] | (q[4] & 15) << 8)
    print("events  known  cand  promoted  dropk  dropc")
    for n in range(1, a.events + 1):
        e = r.randrange(a.classes); out = model.step(M.LOAD, e, t); t += 1
        got = stcmd(2, e); want = {k: out[k] for k in got}
        if got != want: bad += 1; print("event %d: store answer differs: card %s model %s" % (n, got, want))
        if bad > 20: break
        if n % a.every == 0 or n == a.events:
            st = b.sstat(); wn = [model.n_known, model.n_cand, model.promoted, model.dropk, model.dropc]
            print("%6d %6d %5d %9d %6d %6d" % ((n,) + tuple(st)))
            if st != wn: bad += 1; print("counters differ: card %s model %s" % (st, wn))
            if first_drop is None and st[3]: first_drop = n
    print("model: heap rows used %d of 512, index slots used %d of 1024, first drop seen by event %s" % (len(model.heap), sum(1 for e in model.index if e), first_drop))
    rr = random.Random(a.seed)
    for n in range(200):
        e = rr.randrange(a.classes); out = model.step(M.RD, e, t); got = stcmd(3, e); want = {k: out[k] for k in got}
        if got != want: bad += 1; print("read-back %d differs: card %s model %s" % (n, got, want))
    EVB = 4; pack = lambda ctx: sum(x << (EVB * (len(ctx) - 1 - i)) for i, x in enumerate(ctx)); tg = lambda tag: (tag[0] << (3 * EVB)) | pack(tag[1])
    used = [i for i, e in enumerate(model.index) if e]; empties = [i for i in range(0, 1024, 61) if not model.index[i]]
    for i in used[::a.sample] + empties:
        e = model.index[i]; w = b.srd(0, i); exp = ((1 << (2 + 3 * EVB + 9)) | (tg(e["tag"]) << 9) | e["row"]) if e else 0
        if w != exp: bad += 1; print("index slot %d differs: card %x model %x" % (i, w, exp))
    for r_ in list(range(0, len(model.heap) + 2, a.sample)) + [len(model.heap) - 1, len(model.heap), len(model.heap) + 1]:
        h = model.heap[r_] if r_ < len(model.heap) else None; w = b.srd(1, r_); exp = ((1 << 9) | h["next"]) if h and h["next"] is not None else 0
        if w != exp: bad += 1; print("row header %d differs: card %x model %x" % (r_, w, exp))
        for sl in range(4):
            q = h["slots"][sl] if h and sl < len(h["slots"]) else None; w = b.srd(2, r_ * 4 + sl); exp = ((1 << (EVB + 24)) | (q[0] << 24) | (q[1][0] << 16) | (q[1][1] << 8) | (q[1][2] & 255)) if q else 0
            if w != exp: bad += 1; print("entry %d/%d differs: card %x model %x" % (r_, sl, w, exp))
    for i in range(32):
        w = b.srd(3, i); e = model.c[i]; exp = ((1 << (1 + 2 + 4 * EVB + 20 - 1)) | (((e[0][0] << (4 * EVB)) | (pack(e[0][1]) << EVB) | e[0][2]) << 20) | (e[1] << 16) | e[2]) if e else 0
        if w != exp: bad += 1; print("candidate slot %d differs: card %x model %x" % (i, w, exp))
    print("dropped entries: %d known, %d candidates" % (model.dropk, model.dropc))
    print("STORE CAPACITY CHECK %s" % ("PASS" if bad == 0 else "FAIL (%d differences)" % bad)); sys.exit(0 if bad == 0 else 1)
main()
