"""Hex-N on the Tang Nano 20K, CELL MODE test (bitstream built with tools/hexn_tang_build_v13.sh: detectors -> glue buffer -> one full cell). New file; uses the Board class of tools/hexn_tang_host_v3.py and the rules of tools/hexn_tang_script_v1.py.
Usage:  python3 tools/hexn_tang_cell_v1.py SCRIPT.txt --port /dev/ttyUSB1 --cells 7 [--trials 60] [--seed 1]      |  --selftest (Python stand-in, no board)
SCRIPT.txt = a training script exported by the Hex-N Explorer page (docs/hex-n/frontend/example_sensors_script_v1.txt for 7 detectors). It trains the board, reads the trained settings back and compares them, then runs random trials, alternately
mode 0 (RUN: answer and burst counts) and mode 1 (LOADCELL with random lane settings and threshold, then RUNCELL: the cell's output burst count, its forward total and the burst lengths the glue buffer captured). Everything is compared with the rules and a
clock-by-clock model of the cell. Prints the mismatch counts and CELL TEST PASS or FAIL."""
import sys, os, argparse, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_host_v3 as H, hexn_tang_script_v1 as S1, hexn_cellbank_check_v1 as CB
class CellBoard(H.Board):
    def loadcell(self, thr, cfg):
        lc = sum(c << (2 * i) for i, c in enumerate(cfg)); self.s.write(bytes([14, thr] + [(lc >> (8 * j)) & 255 for j in range(5)])); self._ack()
    def runcell(self, m):
        self.s.write(bytes([15, m & 255, (m >> 8) & 255, (m >> 16) & 255])); d = self._rd(2 + self.K)
        return d[0], d[1], list(d[2:])
class FakeCellBoard(S1.FakeBoard):
    """Stand-in for --selftest: also answers LOADCELL and RUNCELL from the rules (tests this script's framing only, not the hardware)."""
    cfg = None; cthr = 0
    def write(self, d):
        if d[0] == 14:
            lc = sum(d[2 + j] << (8 * j) for j in range(5)); self.cthr = d[1]; self.cfg = [(lc >> (2 * i)) & 3 for i in range(self.m["K"])]; self.out.append(H.ACK)
        elif d[0] == 15:
            bits = [(d[1] | (d[2] << 8) | (d[3] << 16)) >> j & 1 for j in range(self.m["NB"])]; _, lens = S1.classify(self.m, bits); acc, cnt = CB.cell_model(self.m["K"], lens, self.cfg, self.cthr)
            self.out += bytes([cnt, acc] + lens)
        else: super().write(d)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200); ap.add_argument("--cells", type=int); ap.add_argument("--trials", type=int, default=60); ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--hw-s", type=int, default=16); ap.add_argument("--selftest", action="store_true"); a = ap.parse_args()
    d = S1.parse_script(open(a.script).read()); K, NB, AW = d["classes"], d["wires"], d["aw"]
    if a.cells and a.cells != K: sys.exit("script has %d classes, bitstream %d detectors" % (K, a.cells))
    m = S1.make_model(d, a.hw_s)
    if a.selftest: H.M.t5.mc.AW = AW; ser = FakeCellBoard(m)
    else:
        import serial; ser = serial.Serial(a.port, a.baud, timeout=5)
    b = CellBoard(ser, K, NB)
    if not a.selftest and not b.sync(): sys.exit(2)
    b.train(m); got = b.dump(); bad_set = sum(1 for k in range(K) if got[k] != (sum(1 << j for j in range(NB) if m["wts"][k][j] > 0), sum(1 << j for j in range(NB) if m["wts"][k][j] < 0), m["thr"][k]))
    print("trained settings: %d of %d detectors differ from the rules" % (bad_set, K))
    rnd = random.Random(a.seed); samples = [bits for bits, y in d["train"] + d["test"]]; b0 = b1 = bc = bf = bo = n0 = n1 = fired = 0; shown = 0
    for n in range(a.trials):
        bits = [x ^ (1 if rnd.random() < rnd.choice([0.05, 0.2, 0.4]) else 0) for x in samples[rnd.randrange(len(samples))]]; pred, lens = S1.classify(m, bits)
        if n % 2 == 0:
            gp, gg = b.run(H.mask(bits)); n0 += 1; ok = (gp == pred and gg == lens); b0 += not ok
            if not ok and shown < 5: shown += 1; print("RUN trial %d: board answer %d counts %s | rules %d %s" % (n, gp, gg, pred, lens))
        else:
            cfg = [rnd.choices([0, 1, 2], [0.3, 0.45, 0.25])[0] for _ in range(K)]; acc0, _ = CB.cell_model(K, lens, cfg, 0); cthr = rnd.randint(0, 127) if rnd.random() < 0.1 else max(0, acc0 - rnd.randint(-4, 9))
            acc, cnt = CB.cell_model(K, lens, cfg, cthr); b.loadcell(cthr, cfg); gc, gf, gcap = b.runcell(H.mask(bits)); n1 += 1; fired += cnt > 0
            e1, e2, e3 = gcap != lens, gf != acc, gc != cnt; bc += e1; bf += e2; bo += e3
            if (e1 or e2 or e3) and shown < 5: shown += 1; print("CELL trial %d: captured %s (rules %s) | cell total %d (model %d) | cell burst %d (model %d)" % (n, gcap, lens, gf, acc, gc, cnt))
    print("mode 0 (RUN) trials %d: wrong %d | mode 1 (RUNCELL) trials %d: captured burst lengths wrong %d, cell forward total wrong %d, cell output burst wrong %d (cell fired in %d)" % (n0, b0, n1, bc, bf, bo, fired))
    ok = not (bad_set or b0 or bc or bf or bo); print("CELL TEST PASS" if ok else "CELL TEST FAIL"); sys.exit(0 if ok else 1)
if __name__ == "__main__": main()
