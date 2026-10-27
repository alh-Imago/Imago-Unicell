"""hexn_store_card_v1: the WHOLE CHAIN on the simulated card: IR codes -> layer 1 bank (exact-match mode) -> hold counter -> layer 2 store (core v7: commands 0x18 STORECFG, 0x19 STORECLR, 0x1B STORERD, 0x1C STORESTAT, 0x1D STORELAST; the store is fed from RUNHOLD). Run in simulation:
  HEXN_SIM_CORE=v7 HEXN_SIM_LAT=18 python3 tools/hexn_card_run_v6.py --sim tools/hexn_store_card_v1.py docs/hex-n/frontend/example_sensors_script_v1.txt
(the script argument is only there because the runner passes one; it is not used.) On the card: same script without --sim, with a bitstream that has core v7 (none built yet).
Steps: (1) the bank is set to exact wiring for 7 remote keys (as hexn_exact_hold_card_v2); (2) routines on 7 key classes, A = 0 1 2 5, B = 3 1 2 6, C = 0 4 2 6, D = 3 4 2 5 (goal 5 or 6 depends on the first two keys), each press = 2 or 3 frames of the same key with 10 percent of frames damaged by one flipped bit; (3) TRAINING in store mode 2 (host load) on 25 routines; STORECLR; (4) TEST in store mode 1 (observe, N=2 sightings in 80 events) on 20 routines in which 2 routines have an extra key (class 3) before the goal. Every frame goes through RUNHOLD (hold length 1, ignore-unknown mode). The Python chain (the bank's exact-match model, the hold rule, tools/hexn_store_v2.py) predicts every held class, which frames feed the store, and the store's answer after each fed event (STORELAST); afterwards the store counters and every used slot of both tables are read back and compared.
Result line: STORE CHAIN CHECK PASS / FAIL."""
import sys, os, random, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_host_v3 as H, hexn_tang_script_v1 as S1, hexn_layer1_v1 as L, hexn_hold_card_v1 as HC, hexn_store_v2 as M
class HB3(HC.HB):
    def sethm(self, m): self.s.write(bytes([0x17, m & 1])); self._ack()
    def scfg(self, n, w, mode): self.s.write(bytes([0x18, n & 15, w & 255, (w >> 8) & 255, mode & 3])); self._ack()
    def sclr(self): self.s.write(bytes([0x19])); self._ack()
    def srd(self, tab, addr): self.s.write(bytes([0x1B, tab, addr])); r = self._rd(5); return sum(r[i] << (8 * i) for i in range(5))
    def sstat(self): self.s.write(bytes([0x1C])); r = self._rd(10); return [r[2 * i] | r[2 * i + 1] << 8 for i in range(5)]
    def slast(self):
        self.s.write(bytes([0x1D])); r = self._rd(5)
        return dict(verdict=r[0] & 3, vlevel=(r[0] >> 2) & 3, plevel=(r[0] >> 4) & 3, pbest=r[1] & 7, pbest_seen=r[2], ptotal=r[3] | (r[4] & 7) << 8)
KEYS = [0x45, 0x46, 0x47, 0x44, 0x40, 0x43, 0x07]
ROUT = {"A": [0, 1, 2, 5], "B": [3, 1, 2, 6], "C": [0, 4, 2, 6], "D": [3, 4, 2, 5]}
def stream(r, n, extra):
    """frames for n random routines; extra = routine numbers that get an extra key 3 before the goal; returns frames [(code, damaged)], event truth list"""
    frames = []; truth = []
    for i in range(n):
        seq = list(ROUT[r.choice("ABCD")])
        if i in extra: seq.insert(len(seq) - 1, 3)
        for k in seq:
            truth.append(k)
            for _ in range(r.choice((2, 3))):
                c = KEYS[k]; flip = r.random() < 0.10
                if flip: c ^= 1 << r.randrange(8)
                frames.append((c, flip))
    return frames, truth
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200); ap.add_argument("--train", type=int, default=25); ap.add_argument("--test", type=int, default=20)
    a = ap.parse_args(); bits = lambda c: L.pad([(c >> j) & 1 for j in range(8)])
    m = L.bank([(bits(c), i) for i, c in enumerate(KEYS)], 7)
    for k, c in enumerate(KEYS): m["wts"][k] = [1 if (c >> j) & 1 else -1 for j in range(8)] + [0] * 10; m["thr"][k] = max(1, S1.fwd_of(bin(c).count("1"), m["AW"]))
    import serial; ser = serial.Serial(a.port, a.baud, timeout=5); b = HB3(ser, 7, 18)
    if not b.sync(): sys.exit(2)
    for k in range(7):
        wp = sum(1 << j for j in range(18) if m["wts"][k][j] > 0); wn = sum(1 << j for j in range(18) if m["wts"][k][j] < 0); b.s.write(bytes([0x13, wp & 255, wp >> 8 & 255, wp >> 16 & 255, wn & 255, wn >> 8 & 255, wn >> 16 & 255, m["thr"][k] & 255])); b._ack()
    r = random.Random(21); tr_frames, _ = stream(r, a.train, set()); te_frames, te_truth = stream(r, a.test, {5, 11})
    NONE = 15; bad = 0; model = M.StoreV2(N=2, W=80); hold = dict(cur=None, cand=None, cnt=0); t = 0; fed_total = 0; fed_check = 0
    def hold_step(x):          # hold length 1, ignore-unknown (skip) mode, as the core's hold v2
        chg = 0; fresh = hold["cur"] is None
        if fresh: hold["cur"] = x
        elif x == NONE: pass
        elif x == hold["cur"]: hold["cand"] = None; hold["cnt"] = 0
        else: hold["cur"] = x; chg = 1
        return hold["cur"], chg, fresh
    b.sethm(1); b.sethold(1); b.sclr(); model.step(M.CLR); b.scfg(3, 80, 2); 
    def phase(frames, op, check):
        nonlocal bad, t, fed_total, fed_check
        for c, flip in frames:
            hc, fl, raw = b.runhold(H.mask(bits(c))); rc = (raw & 31) if raw & 128 else -1; x = rc if rc >= 0 else NONE
            if S1.classify(m, bits(c))[0] != rc: bad += 1; print("raw answer differs from the bank model")
            cur, chg, fresh = hold_step(x)
            if (hc, (fl & 1), (fl >> 1) & 1) != (cur, 1, chg): bad += 1; print("held answer differs from the hold rule", (hc, fl), (cur, chg))
            if (chg or fresh) and cur != NONE:
                fed_total += 1; out = model.step(op, cur, t); t += 1
                if check:
                    got = b.slast(); fed_check += 1
                    if got != out: bad += 1; print("store answer differs: card %s model %s" % (got, out))
    phase(tr_frames, M.LOAD, False)
    b.sclr(); model.step(M.CLR); b.scfg(2, 80, 1)
    # the model's own configuration for the test phase
    model.N = 2; model.W = 80; hold["cur"] = hold["cur"]       # the hold keeps running across the phases, as on the card
    phase(te_frames, M.OBS, True)
    st = b.sstat(); want = [model.n_known, model.n_cand, model.promoted, model.dropk, model.dropc]
    if st != want: bad += 1; print("store counters differ: card %s model %s" % (st, want))
    nk = 0
    for i in range(model.n_known + 1):
        w = b.srd(0, i); e = model.k[i] if i < len(model.k) else None
        exp = ((1 << 30) | (M.key_bits(e[0]) << 16) | (e[1] << 8) | e[2]) if e else 0
        if w != exp: bad += 1; print("known slot %d differs" % i)
    for i in range(32):
        w = b.srd(1, i); e = model.c[i]; exp = ((1 << 34) | (M.key_bits(e[0]) << 20) | (e[1] << 16) | e[2]) if e else 0
        if w != exp: bad += 1; print("candidate slot %d differs" % i)
    print("frames %d (train %d, test %d); events fed to the store %d, answers checked %d; store: known %d, candidates %d, promoted %d, dropped %d/%d" % (len(tr_frames) + len(te_frames), len(tr_frames), len(te_frames), fed_total, fed_check, *want))
    print("STORE CHAIN CHECK %s" % ("PASS" if bad == 0 else "FAIL (%d differences)" % bad)); sys.exit(0 if bad == 0 else 1)
main()
