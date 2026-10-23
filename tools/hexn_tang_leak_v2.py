"""(v2: clone of hexn_tang_leak_v1.py, left untouched. Works for any class count up to 20 (needs a bitstream with NCELL >= classes, e.g. the Kintex hex19 design with 19 cells), so it exercises EVERY cell n = 0..K-1, not only cell 0. Run on the card with tools/hexn_card_run_v1.py.)"""
"""Hex-N on the Tang Nano 20K, LEAKY CELLS test (bitstream built with tools/hexn_tang_build_v15.sh, hex7 with NCELL = 7: detectors -> glue buffer -> 7 leaky cells, board top v10). New file; uses Board of tools/hexn_tang_host_v3.py, the rules of tools/hexn_tang_script_v1.py and the episodes of tools/hexn_leak_rtl_v1.py (same random seed, so the board's table can be compared with the simulation's).
Usage:  python3 tools/hexn_tang_leak_v1.py SCRIPT.txt --port /dev/ttyUSB1 [--noise 0.15] [--per 12]   |  --selftest (Python stand-in, no board)
SCRIPT.txt = the 7-class training script (docs/hex-n/frontend/example_sensors_script_v1.txt). Trains the board, reads the settings back, loads cell g as 'positive on detector g' with threshold 0 (so its forward total is class g's accumulator), then plays episodes: scene A for 8 windows, then scene B for 8 windows, each window a fresh noisy copy. The first window of an episode is sent with leak setting 0 (cleared), the others with the tested setting. Every cell total is compared with the Python chain; the answer (unique highest total) is scored."""
import sys, os, argparse, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_host_v3 as H, hexn_tang_script_v1 as S1, hexn_cellbank_check_v4 as C4
class LeakBoard(H.Board):
    def setleak(self, s): self.s.write(bytes([0x10, s])); self._ack()
    def loadcelln(self, n, thr, cfg):
        lc = sum(c << (2 * i) for i, c in enumerate(cfg)); self.s.write(bytes([0x11, n, thr] + [(lc >> (8 * j)) & 255 for j in range(5)])); self._ack()
    def runcelln(self, m, nc):
        self.s.write(bytes([0x12, m & 255, (m >> 8) & 255, (m >> 16) & 255])); d = self._rd(2 * nc + self.K)
        return [d[2 * c + 1] for c in range(nc)], [d[2 * c] for c in range(nc)]
class FakeLeakBoard(S1.FakeBoard):
    """Stand-in for --selftest (tests this script's framing and bookkeeping only, not the hardware)."""
    leak = 0; thr = {}; cfg = {}; state = {}
    def write(self, d):
        if d[0] == 0x10: self.leak = d[1]; self.out.append(H.ACK)
        elif d[0] == 0x11:
            n = d[1]; self.thr[n] = d[2]; lc = sum(d[3 + j] << (8 * j) for j in range(5)); self.cfg[n] = [(lc >> (2 * i)) & 3 for i in range(self.m["K"])]; self.out.append(H.ACK)
        elif d[0] == 0x12:
            K = self.m["K"]; bits = [(d[1] | (d[2] << 8) | (d[3] << 16)) >> j & 1 for j in range(self.m["NB"])]; _, lens = S1.classify(self.m, bits); body = []
            for n in range(len(self.cfg)):
                acc, cnt = C4.cell_run(K, lens, self.cfg[n], self.thr[n], C4.leaked(self.state.get(n, 0), self.leak)); self.state[n] = acc; body += [cnt, acc]
            self.out += bytes(body + lens)
        else: super().write(d)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200); ap.add_argument("--noise", type=float, default=0.15); ap.add_argument("--per", type=int, default=12)
    ap.add_argument("--hw-s", type=int, default=16); ap.add_argument("--selftest", action="store_true"); a = ap.parse_args()
    d = S1.parse_script(open(a.script).read()); K, NB, AW = d["classes"], d["wires"], d["aw"]; assert K <= 20 and NB == 18 and AW == 7, "this test needs 18 wires, AW 7 and at most 20 classes (the cell lane settings are 5 bytes); the bitstream needs NCELL >= classes"
    m = S1.make_model(d, a.hw_s)
    if a.selftest: H.M.t5.mc.AW = AW; ser = FakeLeakBoard(m)
    else:
        import serial; ser = serial.Serial(a.port, a.baud, timeout=5)
    b = LeakBoard(ser, K, NB)
    if not a.selftest and not b.sync(): sys.exit(2)
    b.train(m); got = b.dump(); bad_set = sum(1 for k in range(K) if got[k] != (sum(1 << j for j in range(NB) if m["wts"][k][j] > 0), sum(1 << j for j in range(NB) if m["wts"][k][j] < 0), m["thr"][k]))
    print("trained settings: %d of %d detectors differ from the rules" % (bad_set, K))
    onehot = [[1 if j == g else 0 for j in range(K)] for g in range(K)]
    for g in range(K): b.loadcelln(g, 0, onehot[g])
    tpl = {}
    for bits, y in d["train"] + d["test"]: tpl.setdefault(y, []).append(bits)
    L = 8; SETTINGS = [("clear", 0), ("half", 1), ("a-a>>2", 2), ("a-a>>3", 3), ("none", 7)]; r = random.Random(11); episodes = []
    for ya in range(K):
        for _ in range(a.per):
            yb = r.choice([c for c in range(K) if c != ya]); ba = r.choice(tpl[ya]); bb = r.choice(tpl[yb])
            episodes.append((ya, yb, [[x ^ (1 if r.random() < a.noise else 0) for x in (ba if w < L else bb)] for w in range(2 * L)]))
    KS = (0, 1, 2, 3, 4, 6, 8); print("board, noise %.2f, %d episodes per setting (scene A %d windows then B %d): share of episodes where the unique highest class total is the scene's true class, k windows after the switch (k=0: last window of A)" % (a.noise, len(episodes), L, L))
    print("%-8s" % "leak" + "".join("  k=%d  " % k for k in KS)); mism = frames = 0
    for name, s in SETTINGS:
        hit = [0] * len(KS)
        for ya, yb, fr in episodes:
            state = [0] * K
            for w in range(2 * L):
                lk = 0 if w == 0 else s; b.setleak(lk); lens = S1.classify(m, fr[w])[1]; state = [C4.cell_run(K, lens, onehot[g], 0, C4.leaked(state[g], lk))[0] for g in range(K)]
                tot, _ = b.runcelln(H.mask(fr[w]), K); frames += 1; mism += tot != state; k = w + 1 - L
                if k in KS: truth = ya if k == 0 else yb; mx = max(tot); hit[KS.index(k)] += (tot.count(mx) == 1 and tot[truth] == mx and mx > 0)
        print("%-8s" % name + "".join(" %.3f " % (h / len(episodes)) for h in hit))
    print("frames where the board's class totals differ from the Python chain: %d of %d" % (mism, frames)); ok = not (bad_set or mism); print("LEAK TEST PASS" if ok else "LEAK TEST FAIL"); sys.exit(0 if ok else 1)
if __name__ == "__main__": main()
