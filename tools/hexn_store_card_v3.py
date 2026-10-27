"""hexn_store_card_v3: the whole chain on the layer 2 STORE v5 (address index + dense heap, 4-bit events; core v9): IR codes -> exact-match bank -> hold -> store with values. Clone of hexn_store_card_v2.py (untouched), checked against the bit-true model tools/hexn_store_v5.py. On the board (USB serial) or in simulation:
  python3 tools/hexn_store_card_v3.py docs/hex-n/frontend/example_sensors_script_v1.txt --port /dev/ttyUSB1 --train 14 --test 14
  HEXN_SIM_CORE=v9 HEXN_SIM_LAT=18 python3 tools/hexn_card_run_v8.py --sim tools/hexn_store_card_v2.py docs/hex-n/frontend/example_sensors_script_v1.txt [--train 8 --test 8]
Steps: as v1 (exact bank on 7 keys, routines A = 0 1 2 5, B = 3 1 2 6, C = 0 4 2 6, D = 3 4 2 5, 2 or 3 frames per press, 10 percent damaged frames, hold length 1 with ignore-unknown), then: TRAINING by host load; TEST in observe mode (N=2, W=80) with the step 2^-2 and goal context 1 (0x1E STOREVAL); after every fed event the card's STORELAST and STOREGOAL (gbest, gval) are compared with the Python store v3 model; at every goal key (class 5 = desired, 6 = not) the host sends REWARD (+64 or -32); at the end the counters and every used slot of both tables (known words now include the VALUE) are read back and compared.
Result line: STORE REWARD CHAIN CHECK PASS / FAIL."""
import sys, os, random, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_host_v3 as H, hexn_tang_script_v1 as S1, hexn_layer1_v1 as L, hexn_hold_card_v1 as HC, hexn_store_v5 as M
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
KEYS = [0x45, 0x46, 0x47, 0x44, 0x40, 0x43, 0x07]
ROUT = {"A": [0, 1, 2, 5], "B": [3, 1, 2, 6], "C": [0, 4, 2, 6], "D": [3, 4, 2, 5]}
def stream(r, n):
    frames = []
    for i in range(n):
        for k in ROUT[r.choice("ABCD")]:
            for _ in range(r.choice((2, 3))):
                c = KEYS[k]; flip = r.random() < 0.10
                if flip: c ^= 1 << r.randrange(8)
                frames.append((c, flip))
    return frames
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200); ap.add_argument("--train", type=int, default=8); ap.add_argument("--test", type=int, default=8)
    a = ap.parse_args(); bits = lambda c: L.pad([(c >> j) & 1 for j in range(8)])
    m = L.bank([(bits(c), i) for i, c in enumerate(KEYS)], 7)
    for k, c in enumerate(KEYS): m["wts"][k] = [1 if (c >> j) & 1 else -1 for j in range(8)] + [0] * 10; m["thr"][k] = max(1, S1.fwd_of(bin(c).count("1"), m["AW"]))
    import serial; ser = serial.Serial(a.port, a.baud, timeout=5); b = HB5(ser, 7, 18)
    if not b.sync(): sys.exit(2)
    for k in range(7):
        wp = sum(1 << j for j in range(18) if m["wts"][k][j] > 0); wn = sum(1 << j for j in range(18) if m["wts"][k][j] < 0); b.s.write(bytes([0x13, wp & 255, wp >> 8 & 255, wp >> 16 & 255, wn & 255, wn >> 8 & 255, wn >> 16 & 255, m["thr"][k] & 255])); b._ack()
    r = random.Random(33); tr_frames = stream(r, a.train); te_frames = stream(r, a.test)
    NONE = 15; bad = 0; model = M.StoreV5(N=2, W=80, vshift=2, glvl=1, EVB=4, IB=10, R=4, HROWS=512, P=4, CCAP=32); hold = dict(cur=None); t = 0; fed = 0; checked = 0; rewards = 0
    def hold_step(x):
        chg = 0; fresh = hold["cur"] is None
        if fresh: hold["cur"] = x
        elif x == NONE: pass
        elif x != hold["cur"]: hold["cur"] = x; chg = 1
        return hold["cur"], chg, fresh
    b.sethm(1); b.sethold(1); b.sclr(); model.step(M.CLR); b.scfg(3, 80, 2); b.sval(2, 1)
    def phase(frames, op, check):
        nonlocal bad, t, fed, checked, rewards
        for c, flip in frames:
            hc, fl, raw = b.runhold(H.mask(bits(c))); rc = (raw & 31) if raw & 128 else -1; x = rc if rc >= 0 else NONE
            if S1.classify(m, bits(c))[0] != rc: bad += 1; print("raw answer differs from the bank model")
            cur, chg, fresh = hold_step(x)
            if (hc, fl & 1, (fl >> 1) & 1) != (cur, 1, chg): bad += 1; print("held answer differs from the hold rule")
            if (chg or fresh) and cur != NONE:
                fed += 1; out = model.step(op, cur, t); t += 1
                if check:
                    got = dict(b.slast(), **b.sgoal()); checked += 1; want = {k: out[k] for k in got}
                    if got != want: bad += 1; print("store answer differs: card %s model %s" % (got, want))
                    if cur in (5, 6):
                        rv = 64 if cur == 5 else -32; b.reward(rv); model.step(M.REW, r=rv); rewards += 1
    phase(tr_frames, M.LOAD, False)
    b.sclr(); model.step(M.CLR); b.scfg(2, 80, 1)
    model.N = 2; model.W = 80
    phase(te_frames, M.OBS, True)
    st = b.sstat(); want = [model.n_known, model.n_cand, model.promoted, model.dropk, model.dropc]
    if st != want: bad += 1; print("store counters differ: card %s model %s" % (st, want))
    EVB = 4; pack = lambda ctx: sum(x << (EVB * (len(ctx) - 1 - i)) for i, x in enumerate(ctx)); tg = lambda tag: (tag[0] << (3 * EVB)) | pack(tag[1])
    used = [i for i, e in enumerate(model.index) if e]; empties = [i for i in range(0, 1024, 61) if not model.index[i]]
    for i in used + empties:
        e = model.index[i]; w = b.srd(0, i); exp = ((1 << (2 + 3 * EVB + 9)) | (tg(e["tag"]) << 9) | e["row"]) if e else 0
        if w != exp: bad += 1; print("index slot %d differs: card %x model %x" % (i, w, exp))
    for r_ in range(len(model.heap) + 2):
        h = model.heap[r_] if r_ < len(model.heap) else None; w = b.srd(1, r_); exp = ((1 << 9) | h["next"]) if h and h["next"] is not None else 0
        if w != exp: bad += 1; print("row header %d differs: card %x model %x" % (r_, w, exp))
        for sl in range(4):
            q = h["slots"][sl] if h and sl < len(h["slots"]) else None; w = b.srd(2, r_ * 4 + sl); exp = ((1 << (EVB + 24)) | (q[0] << 24) | (q[1][0] << 16) | (q[1][1] << 8) | (q[1][2] & 255)) if q else 0
            if w != exp: bad += 1; print("entry %d/%d differs: card %x model %x" % (r_, sl, w, exp))
    for i in range(32):
        w = b.srd(3, i); e = model.c[i]; exp = ((1 << (1 + 2 + 4 * EVB + 20 - 1)) | (((e[0][0] << (4 * EVB)) | (pack(e[0][1]) << EVB) | e[0][2]) << 20) | (e[1] << 16) | e[2]) if e else 0
        if w != exp: bad += 1; print("candidate slot %d differs: card %x model %x" % (i, w, exp))
    vals = sorted(set(q[1][2] for h in model.heap for q in h['slots'] if q[1][2]))
    print("frames %d (train %d, test %d); events fed %d, answers checked %d, rewards sent %d; store: known %d, candidates %d, promoted %d; non-zero values %s" % (len(tr_frames) + len(te_frames), len(tr_frames), len(te_frames), fed, checked, rewards, want[0], want[1], want[2], vals))
    print("STORE REWARD CHAIN CHECK %s" % ("PASS" if bad == 0 else "FAIL (%d differences)" % bad)); sys.exit(0 if bad == 0 else 1)
main()
