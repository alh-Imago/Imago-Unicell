"""Hex-N on the Tang Nano 20K: run a training script exported by the Hex-N Explorer page (docs/hex-n/frontend/hexn_explorer_v1.html).
New file; it imports the proven Board class from tools/hexn_tang_host_v3.py (left untouched). Runs on YOUR machine, talks to the board over the USB serial port. Needs pyserial.
Usage:  python3 tools/hexn_tang_script_v1.py SCRIPT.txt --port /dev/ttyUSB1 [--cells K] [--wires NB] [--aw AW] [--hw-s 16]
        python3 tools/hexn_tang_script_v1.py SCRIPT.txt --selftest        (no board: checks this script's reading and bookkeeping against a Python stand-in)
What it does: reads the script (train and test samples), trains the board (CLEAR, COUNT x all, SETW, ACCUM x all, FINISH), reads the trained weights and thresholds back and compares them with
what the counting rules give, then runs every test sample on the board and compares the board's answer and its K burst counts with the same rules computed here.
The rules are the ones in tools/hexn_bank_model_v2.py (checked equal to the page on 17160 samples). NOTE: the bitstreams fix the training samples per class (parameter S, 16 in the current builds):
the threshold divider uses that number, so a script with another count gives thresholds on the board that differ from the page's. This tool computes the board's expectation with the bitstream's S (--hw-s) and says so."""
import sys, os, argparse
from fractions import Fraction
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_host_v3 as H
CAP = 31; PL = 10; MAXOUT = 7
def parse_script(text):
    d = dict(wires=None, classes=None, spc=None, T=None, aw=None, labels=[], train=[], test=[])
    for n, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line[0] == "#": continue
        p = line.split()
        key = p[0]
        if key in ("wires", "classes", "samples_per_class", "weight_cutoff", "accumulator_bits"):
            d[{"wires": "wires", "classes": "classes", "samples_per_class": "spc", "weight_cutoff": "T", "accumulator_bits": "aw"}[key]] = int(p[1])
        elif key == "labels": d["labels"] = [x.split("=", 1)[1] for x in p[1:]]
        elif key in ("train", "test"):
            if len(p) != 3 or not set(p[2]) <= {"0", "1"}: raise SystemExit("line %d: expected '%s CLASS BITS'" % (n, key))
            d[key].append(([int(c) for c in p[2]], int(p[1])))
        else: raise SystemExit("line %d: unknown word '%s'" % (n, key))
    for k in ("wires", "classes", "T", "aw"):
        if d[k] is None: raise SystemExit("script has no '%s' line" % k)
    for bits, y in d["train"] + d["test"]:
        if len(bits) != d["wires"] or not 0 <= y < d["classes"]: raise SystemExit("a sample does not fit wires=%d classes=%d" % (d["wires"], d["classes"]))
    if not d["train"]: raise SystemExit("script has no training samples")
    return d
def fwd_of(net, AW): return min(PL * net, (1 << AW) - 1) if net > 0 else 0
def net_of(w, bits): return sum(wj for wj, b in zip(w, bits) if b)
def rhe(num, den):
    q, r = divmod(num, den)
    return q + 1 if (2 * r > den or (2 * r == den and q % 2)) else q
def make_model(d, hw_s):
    """Counting rules as the chip does them. The threshold divider uses the bitstream's S (hw_s): nP = S, nN = S*(K-1)."""
    K, NB, AW, T = d["classes"], d["wires"], d["aw"], d["T"]
    cnt = [[0] * NB for _ in range(K)]
    for bits, y in d["train"]:
        for k in range(K):
            dl = K - 1 if y == k else -1
            for j in range(NB):
                if bits[j]: cnt[k][j] = max(-CAP, min(CAP, cnt[k][j] + dl))
    wts = [[1 if c >= T else -1 if c <= -T else 0 for c in r] for r in cnt]
    nP, nN = hw_s, hw_s * (K - 1); thr = []; sump = []; sumn = []
    for k in range(K):
        sp = sum(fwd_of(net_of(wts[k], b), AW) for b, y in d["train"] if y == k); sn = sum(fwd_of(net_of(wts[k], b), AW) for b, y in d["train"] if y != k)
        sump.append(sp); sumn.append(sn); thr.append(max(0, min((1 << AW) - 1, rhe(sp * nN + sn * nP, 2 * nP * nN))))
    return dict(K=K, NB=NB, AW=AW, T=T, S=hw_s, cnt=cnt, wts=wts, thr=thr, sump=sump, sumn=sumn, train=d["train"], test=d["test"])
def classify(m, bits):
    g = []
    for k in range(m["K"]):
        f = fwd_of(net_of(m["wts"][k], bits), m["AW"]); g.append(min(f - m["thr"][k] + 1, MAXOUT) if f >= m["thr"][k] else 0)
    mx = max(g); return (g.index(mx) if (mx > 0 and g.count(mx) == 1) else -1), g
class FakeBoard(H.FakeSerial):
    """Stand-in for --selftest: the host's FakeSerial (answers RUN from the independent hexn_tally model) plus DUMP from this file's own weights."""
    def write(self, dat):
        if dat == bytes([7]):
            for k in range(self.m["K"]):
                wp = sum(1 << j for j in range(self.m["NB"]) if self.m["wts"][k][j] > 0); wn = sum(1 << j for j in range(self.m["NB"]) if self.m["wts"][k][j] < 0)
                self.out += bytes([wp & 255, wp >> 8 & 255, wp >> 16 & 255, wn & 255, wn >> 8 & 255, wn >> 16 & 255, self.m["thr"][k]])
            return
        super().write(dat)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--cells", type=int, help="detectors in the bitstream (default: classes in the script)"); ap.add_argument("--wires", type=int, help="wires in the bitstream (default: from the script)")
    ap.add_argument("--aw", type=int, help="accumulator bits in the bitstream (default: from the script)"); ap.add_argument("--hw-s", type=int, default=16, help="training samples per class fixed in the bitstream (16 in the current builds)")
    ap.add_argument("--selftest", action="store_true"); a = ap.parse_args()
    d = parse_script(open(a.script).read()); K = d["classes"]; NB = d["wires"]
    if a.cells and a.cells != K: sys.exit("the script has %d classes but --cells says the bitstream has %d detectors: they must be equal" % (K, a.cells))
    if a.wires and a.wires != NB: sys.exit("the script has %d wires but --wires says the bitstream has %d" % (NB, a.wires))
    if a.aw and a.aw != d["aw"]: print("note: the script says accumulator_bits %d, the bitstream has %d: using the bitstream's" % (d["aw"], a.aw)); d["aw"] = a.aw
    counts = [sum(1 for b, y in d["train"] if y == k) for k in range(K)]
    if any(c != a.hw_s for c in counts):
        print("WARNING: the bitstream trains exactly %d samples per class; this script has per-class counts %s." % (a.hw_s, counts))
        print("  The board's thresholds will differ from the page's. The expected values below are what the BOARD should give (its divider uses S=%d)." % a.hw_s)
        if len(d["train"]) != a.hw_s * K: print("  The script also does not hold %d training samples in total; the board still counts them all." % (a.hw_s * K))
    m = make_model(d, a.hw_s); AW = m["AW"]
    if a.selftest:
        H.M.t5.mc.AW = AW; ser = FakeBoard(m)
    else:
        import serial; ser = serial.Serial(a.port, a.baud, timeout=5)
    b = H.Board(ser, K, NB)
    if not a.selftest and not b.sync(): sys.exit(2)
    b.train(m)
    got = b.dump(); bad = 0
    for k in range(K):
        wp = sum(1 << j for j in range(NB) if m["wts"][k][j] > 0); wn = sum(1 << j for j in range(NB) if m["wts"][k][j] < 0)
        if got[k] != (wp, wn, m["thr"][k]):
            bad += 1; print("detector %d: board +%05x -%05x thr %d | expected +%05x -%05x thr %d  <-- DIFFERENT" % (k, got[k][0], got[k][1], got[k][2], wp, wn, m["thr"][k]))
    print("trained settings: %d of %d detectors differ from the rules" % (bad, K))
    same = bok = mok = 0; shown = 0; per = {}
    for bits, y in d["test"]:
        ep, eg = classify(m, bits); gp, gg = b.run(H.mask(bits)); ok = (gp == ep and gg == eg); same += ok; bok += (gp == y); mok += (ep == y)
        s = per.setdefault(y, [0, 0, 0]); s[0] += 1; s[1] += (gp == y); s[2] += (ep == y)
        if not ok and shown < 8: shown += 1; print("test sample (class %d, bits %s): board says %d %s | rules say %d %s  <-- DIFFERENT" % (y, "".join(map(str, bits)), gp, gg, ep, eg))
    n = len(d["test"])
    if n:
        lab = d["labels"]
        for y in sorted(per): print("  class %-2d %-14s test %3d  board right %3d  rules right %3d" % (y, lab[y] if y < len(lab) else "", per[y][0], per[y][1], per[y][2]))
        print("test samples identical to the rules (answer and all %d burst counts): %d of %d | board accuracy %.3f | rules accuracy %.3f" % (K, same, n, bok / n, mok / n))
    else: print("the script has no test samples")
    sys.exit(0 if (same == n and bad == 0) else 1)
if __name__ == "__main__": main()
