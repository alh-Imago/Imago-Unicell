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
    def clear(self): self.s.write(bytes([1])); self._ack()
    def count(self, label, m): self.s.write(bytes([2, label, m & 255, m >> 8])); self._ack()
    def setw(self, t): self.s.write(bytes([3, t])); self._ack()
    def accum(self, label, m): self.s.write(bytes([4, label, m & 255, m >> 8])); self._ack()
    def finish(self): self.s.write(bytes([5])); self._ack()
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
    ap.add_argument("--seeds", default="0-4"); ap.add_argument("--train-noise", type=float, default=0.15); ap.add_argument("--test-noise", default="0.05,0.15,0.25"); ap.add_argument("--per-class", type=int, default=16); ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(); K = a.cells; tests = [float(x) for x in a.test_noise.split(",")]; allok = tot = 0
    print("seed  test-noise  samples  identical-to-model  board-accuracy  model-accuracy")
    for seed in parse_range(a.seeds):
        m = M.make(seed, K, 12, 6, a.per_class, a.train_noise)
        if a.selftest: ser = FakeSerial(m)
        else:
            import serial
            ser = serial.Serial(a.port, a.baud, timeout=5)
        b = Board(ser, K); b.train(m)
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
