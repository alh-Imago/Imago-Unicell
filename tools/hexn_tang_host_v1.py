"""Hex-N on the Tang Nano 20K: host test script (runs on YOUR machine, talks to the board over the USB serial port).
Needs: pip install pyserial   and the repository (this file imports tools/hexn_bank_model_v1.py).  The bitstream: tools/hexn_tang_build_v1.sh (or the file you were sent), loaded with  openFPGALoader -b tangnano20k hexn_tang_hex7.fs
Usage:  python3 tools/hexn_tang_host_v1.py --port /dev/ttyUSB1 [--cells 7] [--seeds 0-4] [--train-noise 0.15] [--test-noise 0.05,0.15,0.25] [--per-class 16]
        python3 tools/hexn_tang_host_v1.py --selftest         (no board: checks this script against a Python stand-in for the board)
For every seed and noise setting it makes the training and test samples with the Python model, trains the board (CLEAR, COUNT x all samples, SETW, ACCUM x all samples, FINISH), runs every test sample on the board
and compares the board's answer and its K burst counts with the Python model's. It prints one line per setting: samples identical to the model, board accuracy, model accuracy."""
import sys, os, time, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_bank_model_v1 as M
ACK = 0xA5
def parse_range(s):
    out = []
    for part in s.split(","):
        if "-" in part: a, b = part.split("-"); out += list(range(int(a), int(b) + 1))
        else: out.append(int(part))
    return out
def mask(bits): return sum(1 << j for j, b in enumerate(bits) if b)
class Board:
    def __init__(self, ser, K): self.s = ser; self.K = K
    def _rd(self, n):
        d = self.s.read(n)
        if len(d) != n: raise SystemExit("board did not answer (got %d of %d bytes): is the bitstream loaded, and is this the right serial port?" % (len(d), n))
        return d
    def _ack(self):
        a = self._rd(1)[0]
        if a != ACK: raise SystemExit("unexpected reply byte 0x%02x (wanted 0xA5)" % a)
    def sync(self, tries=6):
        """Throw away anything already waiting on the port (text left by an earlier design, noise) and make sure the board answers CLEAR with 0xA5."""
        seen = bytearray()
        time.sleep(0.3)
        for t in range(tries):
            if hasattr(self.s, "reset_input_buffer"):
                n = getattr(self.s, "in_waiting", 0)
                if n: seen += self.s.read(n)
                self.s.reset_input_buffer()
            self.s.write(bytes([1])); d = self.s.read(1)
            if d and d[0] == ACK: return True
            seen += d; time.sleep(0.3)
        print("board did not answer CLEAR with 0xA5 after %d tries. Bytes seen: %s" % (tries, bytes(seen[:40]).hex(" ") or "none"), file=sys.stderr)
        if not seen: print("  (nothing at all came back: check the port, and that the bitstream is loaded; if the board lights nothing, the receive pin may be wrong)", file=sys.stderr)
        else: print("  (something is transmitting but not the expected answer: another design may still be running, or the baud rate / receive pin is wrong)", file=sys.stderr)
        return False
    def clear(self): self.s.write(bytes([1])); self._ack()
    def count(self, label, m): self.s.write(bytes([2, label, m & 255, m >> 8])); self._ack()
    def setw(self, t): self.s.write(bytes([3, t])); self._ack()
    def accum(self, label, m): self.s.write(bytes([4, label, m & 255, m >> 8])); self._ack()
    def finish(self): self.s.write(bytes([5])); self._ack()
    def dump(self):
        r = self._rd(0) if False else None
        self.s.write(bytes([7])); d = self._rd(5 * self.K); out = []
        for k in range(self.K):
            c = d[5 * k:5 * k + 5]; out.append((c[0] | (c[1] << 8), c[2] | (c[3] << 8), c[4]))
        return out
    def dumpsums(self):
        self.s.write(bytes([8])); d = self._rd(4 * self.K)
        return [(d[4 * k] | (d[4 * k + 1] << 8), d[4 * k + 2] | (d[4 * k + 3] << 8)) for k in range(self.K)]
    def divtest(self, num):
        self.s.write(bytes([9, num & 255, (num >> 8) & 255, (num >> 16) & 255])); d = self._rd(5)
        return d[0] | (d[1] << 8) | (d[2] << 16), d[3] | (d[4] << 8)
    def probe(self):
        self.s.write(bytes([10])); d = self._rd(2 * self.K)
        return [((d[2 * k] - 256 if d[2 * k] > 127 else d[2 * k]), d[2 * k + 1]) for k in range(self.K)]
    def peek(self):
        self.s.write(bytes([11])); d = self._rd(12 * self.K)
        return [(x - 256 if x > 127 else x) for x in d]
    def echo(self):
        self.s.write(bytes([12])); d = self._rd(4)
        return d[0] | (d[1] << 8), d[2], d[3]
    def cap(self):
        self.s.write(bytes([13])); d = self._rd(12 * self.K + 1)
        return list(d[:12 * self.K]), d[12 * self.K]
    def run(self, m):
        self.s.write(bytes([6, m & 255, m >> 8])); r = self._rd(1 + self.K)
        return (r[0] & 31 if r[0] & 128 else -1), list(r[1:])
    def train(self, model):
        self.clear()
        for bits, y in model["train"]: self.count(y, mask(bits))
        self.setw(model["T"])
        for bits, y in model["train"]: self.accum(y, mask(bits))
        self.finish()
class FakeSerial:
    """Stand-in for the board for --selftest: answers the same byte protocol from the Python model (so only this script's framing and bookkeeping are tested, not the hardware)."""
    def __init__(self, model_for_run): self.buf = bytearray(); self.out = bytearray(); self.m = model_for_run; self.pending = None
    def write(self, d):
        self.buf += d
        while self.buf:
            c = self.buf[0]; need = {1: 1, 2: 4, 3: 2, 4: 4, 5: 1, 6: 3}[c]
            if len(self.buf) < need: return
            args = bytes(self.buf[1:need]); del self.buf[:need]
            if c == 6:
                bits = [(args[0] | (args[1] << 8)) >> j & 1 for j in range(12)]
                pred, g = M.classify(self.m, [(bits, 0)])[0]
                self.out += bytes([(128 | pred) if pred >= 0 else 0] + g)
            else: self.out.append(ACK)
    def read(self, n): d = bytes(self.out[:n]); del self.out[:n]; return d
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200); ap.add_argument("--cells", type=int, default=7)
    ap.add_argument("--seeds", default="0-4"); ap.add_argument("--train-noise", type=float, default=0.15); ap.add_argument("--test-noise", default="0.05,0.15,0.25"); ap.add_argument("--per-class", type=int, default=16); ap.add_argument("--selftest", action="store_true"); ap.add_argument("--dumpsums", action="store_true", help="after training, read back the two running sums of the threshold pass per detector and test the divider (needs the _v3 bitstream)"); ap.add_argument("--probe", type=int, default=0, metavar="N", help="after training, push N training samples through ACCUM one at a time and compare, per detector, the hardware's net lane count and forward total with the model (needs the _v4 bitstream)"); ap.add_argument("--echo", type=int, default=0, metavar="N", help="after training, for N training samples: ACCUM it, then read back what the board holds for the trainer (sample bits, label, T), the trained weights and the hardware net counts, recompute the net counts on this computer from the board's own bits and weights, and say which of the three disagrees (needs the _v6 top bitstream)"); ap.add_argument("--wstage", action="store_true", help="read the trained weights back from the board after SETW, after every ACCUM and after FINISH and list which lanes differ from the model (works with the _v2 and later bitstreams)"); ap.add_argument("--cap", action="store_true", help="after COUNT and SETW, read back for every weight write the counter value the trainer saw and the weight it formed, and check the counter read, the comparison and the stored chain against the model (needs the _v7 top bitstream)"); ap.add_argument("--peek", action="store_true", help="read all trainer counters back from the board after COUNT, after SETW and after ACCUM and compare with the model (needs the _v5 bitstream)"); ap.add_argument("--dump", action="store_true", help="after training, read the trained weights and thresholds back from the board (needs the _v2 bitstream) and compare with the model")
    a = ap.parse_args(); K = a.cells; tests = [float(x) for x in a.test_noise.split(",")]; allok = tot = 0
    print("seed  test-noise  samples  identical-to-model  board-accuracy  model-accuracy")
    for seed in parse_range(a.seeds):
        m = M.make(seed, K, 12, 6, a.per_class, a.train_noise)
        if a.selftest: ser = FakeSerial(m)
        else:
            import serial
            ser = serial.Serial(a.port, a.baud, timeout=5)
        b = Board(ser, K)
        if a.peek:
            if not b.sync(): sys.exit(2)
            exp = [m["cnt"][k][j] for k in range(K) for j in range(12)]
            def chk(tag):
                got = b.peek(); bad = [i for i in range(len(exp)) if got[i] != exp[i]]
                print("seed %d counters %-14s: %d of %d differ from the model" % (seed, tag, len(bad), len(exp)))
                for i in bad[:6]: print("     detector %d lane %d: board %d, model %d" % (i // 12, i % 12, got[i], exp[i]))
            b.clear()
            for bits, y in m["train"]: b.count(y, mask(bits))
            chk("after COUNT"); b.setw(m["T"]); chk("after SETW")
            for bits, y in m["train"]: b.accum(y, mask(bits))
            chk("after ACCUM"); b.finish(); chk("after FINISH")
            continue
        if not a.selftest and not b.sync(): sys.exit(2)
        if a.cap:
            b.clear()
            for bits, y in m["train"]: b.count(y, mask(bits))
            b.setw(m["T"]); cp, nw = b.cap(); dm = b.dump(); T = m["T"]
            rd_bad = cmp_bad = chain_bad = 0; shown = 0
            for i in range(K * 12):
                k, j = divmod(i, 12); v = cp[i]; wp_ = v >> 7 & 1; wn_ = v >> 6 & 1; c = v & 63; c = c - 64 if c > 31 else c
                ewp = int(c >= T); ewn = int(c <= -T)
                bw = (dm[k][0] >> j & 1) - (dm[k][1] >> j & 1)
                a1 = (c != m["cnt"][k][j]); a2 = (wp_, wn_) != (ewp, ewn); a3 = (bw != wp_ - wn_)
                rd_bad += a1; cmp_bad += a2; chain_bad += a3
                if (a1 or a2 or a3) and shown < 14:
                    shown += 1; print("  detector %d lane %d: trainer saw counter %d (model %d)%s; formed wp %d wn %d (from the counter it saw: %d %d)%s; stored weight %d%s" % (k, j, c, m["cnt"][k][j], "  <-- COUNTER READ WRONG" if a1 else "", wp_, wn_, ewp, ewn, "  <-- COMPARISON WRONG" if a2 else "", bw, "  <-- STORED CHAIN DIFFERS FROM WHAT WAS FORMED" if a3 else ""))
            print("weight writes counted by the board: %d (expected %d)" % (nw, K * 12))
            print("summary of %d weight writes: counter read wrong %d, comparison wrong %d, stored weight differs from formed weight %d" % (K * 12, rd_bad, cmp_bad, chain_bad))
            continue
        if a.wstage:
            def wchk(tag):
                dm = b.dump(); bad = []
                for k in range(K):
                    for j in range(12):
                        bw = (1 if dm[k][0] >> j & 1 else 0) - (1 if dm[k][1] >> j & 1 else 0)
                        if bw != m["wts"][k][j]: bad.append((k, j, bw, m["wts"][k][j]))
                print("weights %-16s: %d of %d lanes differ from the model" % (tag, len(bad), K * 12))
                for k, j, bw, mw in bad[:10]: print("     detector %d lane %d (model counter %d): board weight %d, model weight %d" % (k, j, m["cnt"][k][j], bw, mw))
            b.clear(); wchk("after CLEAR")
            for bits, y in m["train"]: b.count(y, mask(bits))
            wchk("after COUNT"); b.setw(m["T"]); wchk("after SETW")
            b.accum(m["train"][0][1], mask(m["train"][0][0])); wchk("after 1 ACCUM")
            for bits, y in m["train"][1:]: b.accum(y, mask(bits))
            wchk("after all ACCUM"); b.finish(); wchk("after FINISH")
            continue
        b.train(m)
        if a.echo:
            pc = lambda v: bin(v).count("1"); nb = ne = nw = nc = 0
            dm = b.dump(); wpos = [d[0] for d in dm]; wneg = [d[1] for d in dm]
            mw = [sum(1 << j for j in range(12) if m["wts"][k][j] > 0) for k in range(K)]; mn = [sum(1 << j for j in range(12) if m["wts"][k][j] < 0) for k in range(K)]
            print("weights read back equal the model's: %s" % (wpos == mw and wneg == mn))
            for bits, y in m["train"][:a.echo]:
                sent = mask(bits); b.accum(y, sent); eb, el, et = b.echo(); got = b.probe()
                mine = [pc(eb & wpos[k]) - pc(eb & wneg[k]) for k in range(K)]
                modl = [pc(sent & mw[k]) - pc(sent & mn[k]) for k in range(K)]
                nb += (eb != sent); ne += (el != y); nw += sum(1 for k in range(K) if got[k][0] != mine[k]); nc += sum(1 for k in range(K) if got[k][0] != modl[k])
                print("sample label %d sent bits %03x | board holds bits %03x label %d T %d | board nets %s | recomputed from board bits+weights %s | model %s" % (y, sent, eb, el, et, [g[0] for g in got], mine, modl))
            print("summary: samples whose bits differ from what was sent: %d; labels differing: %d; detector nets differing from the recomputation: %d; from the model: %d" % (nb, ne, nw, nc))
            continue
        if a.probe:
            bad = tot = 0; shown = 0
            for bits, y in m["train"][:a.probe]:
                b.accum(y, mask(bits)); got = b.probe()
                for k in range(K):
                    net = sum(m["wts"][k][j] * bits[j] for j in range(12)); fwd = 0 if net <= 0 else min(10 * net, 63)
                    ok = (got[k] == (net, fwd)); bad += (not ok); tot += 1
                    if not ok and shown < 12: shown += 1; print("sample label %d bits %03x detector %d: board net %d fwd %d | model net %d fwd %d  <-- DIFFERENT" % (y, mask(bits), k, got[k][0], got[k][1], net, fwd))
            print("probe: %d of %d (sample, detector) results differ from the model" % (bad, tot))
            continue
        if a.dumpsums:
            S_ = m["S"]; nP = S_; nN = S_ * (K - 1); den = 2 * nP * nN; got = b.dumpsums(); bad = 0
            for k in range(K):
                P, N = m["sump"][k], m["sumn"][k]; gP, gN = got[k]; ok = (gP == P and gN == N); bad += (not ok)
                print("seed %d detector %d: board sumP %5d sumN %6d | model sumP %5d sumN %6d %s" % (seed, k, gP, gN, P, N, "" if ok else "  <-- DIFFERENT"))
            print("seed %d: %d of %d detectors differ in their sums" % (seed, bad, K))
            from fractions import Fraction
            import random as _r
            rr = _r.Random(5); tb = 0
            for num in [0, 1, den - 1, den, den + 1, 5 * den + den // 2, 40 * den + 7, 63 * den, 123456] + [rr.randrange(0, 190000) for _ in range(15)]:
                q, r = b.divtest(num); ok = (q == num // den and r == num % den); tb += (not ok)
                print("divider test: %6d / %d -> board q %5d r %5d | expected q %5d r %5d %s" % (num, den, q, r, num // den, num % den, "" if ok else "  <-- DIFFERENT"))
            print("divider: %d of 24 tests wrong" % tb)
            continue
        if a.dump:
            got = b.dump(); bad = 0
            for k in range(K):
                wp = sum(1 << j for j in range(12) if m["wts"][k][j] > 0); wn = sum(1 << j for j in range(12) if m["wts"][k][j] < 0)
                gp, gn, gt = got[k]; ok = (gp == wp and gn == wn and gt == m["thr"][k]); bad += (not ok)
                print("seed %d detector %d: board +%03x -%03x thr %2d | model +%03x -%03x thr %2d %s" % (seed, k, gp, gn, gt, wp, wn, m["thr"][k], "" if ok else "  <-- DIFFERENT"))
            print("seed %d: %d of %d detectors differ in their trained settings" % (seed, bad, K))
            continue
        import random
        for qn in tests:
            rnd = random.Random(1000 + seed); sm = [(M.sample(rnd, m["tpl"][y], qn), y) for y in range(K) for _ in range(50)]; random.Random(seed + 9).shuffle(sm)
            exp = M.classify(m, sm); same = bok = mok = 0
            for (bits, y), (ep, eg) in zip(sm, exp):
                gp, gg = b.run(mask(bits)); same += (gp == ep and gg == eg); bok += (gp == y); mok += (ep == y)
            n = len(sm); allok += same; tot += n
            print("%-5d %-11.2f %-8d %-19s %-15.3f %.3f" % (seed, qn, n, "%d of %d" % (same, n), bok / n, mok / n), flush=True)
    print("TOTAL: board identical to the Python model on %d of %d test samples" % (allok, tot))
    sys.exit(0 if allok == tot else 1)
if __name__ == "__main__": main()
