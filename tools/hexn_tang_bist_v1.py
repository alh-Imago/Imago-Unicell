"""Hex-N on the Tang Nano 20K: BUILT-IN SELF-TEST (BIST). Run it after every bitstream load; it takes seconds and says which stage of the trainer is wrong, if any.
New file; uses the proven Board class (tools/hexn_tang_host_v3.py) and the counting rules (tools/hexn_tang_script_v1.py). No new hardware: it uses the read-back commands that every bitstream already has.
Usage:  python3 tools/hexn_tang_bist_v1.py --port /dev/ttyUSB1 --cells 7 [--wires 18] [--aw 7]        |  --selftest (Python stand-in, no board)
For each fixed training set (chosen by tools/hexn_bist_sets_v1.py so the battery reaches counters exactly at the weight cutoff and one either side, counters at the +-31 limit, threshold sums on a rounding tie of both parities):
  1 CLEAR then COUNT all samples, PEEK every counter and compare;  2 SETW, DUMP the weights and compare;  3 ACCUM all samples, FINISH, DUMPSUMS and DUMP (thresholds) and compare;
  4 RUN every test sample and compare the answer and all burst counts.  Then 24 divider tests (DIVTEST) against exact integer division.
Prints one line per stage per set, then BIST PASS or BIST FAIL with the first failing stage. Exit code 0 on pass."""
import sys, os, argparse, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_host_v3 as H, hexn_tang_script_v1 as S1, hexn_bist_sets_v1 as BS
CONFIGS = [(1, 0.5, 0.2, 13), (1, 0.7, 0.05, 8), (2, 0.7, 0.2, 8), (1, 0.5, 0.35, 8), (2, 0.5, 0.35, 13), (3, 0.5, 0.2, 8), (5, 0.7, 0.35, 3), (4, 0.5, 0.05, 13)]   # the last two add a threshold of 0 at 7 detectors and an even rounding tie at 19; not reached: a threshold clamped at the accumulator maximum
class FakeBoard(H.FakeSerial):
    """Stand-in for --selftest: answers CLEAR/COUNT/SETW/ACCUM/FINISH with the ack, RUN (via the independent hexn_tally model), and DUMP / DUMPSUMS / DIVTEST / PEEK from the current model self.m (set by the caller)."""
    def write(self, d):
        c = d[0]; m = self.m; K, NB = m["K"], m["NB"]
        if c == 7:
            for k in range(K):
                wp = sum(1 << j for j in range(NB) if m["wts"][k][j] > 0); wn = sum(1 << j for j in range(NB) if m["wts"][k][j] < 0)
                self.out += bytes([wp & 255, wp >> 8 & 255, wp >> 16 & 255, wn & 255, wn >> 8 & 255, wn >> 16 & 255, m["thr"][k]])
        elif c == 8:
            for k in range(K): self.out += bytes([m["sump"][k] & 255, m["sump"][k] >> 8, m["sumn"][k] & 255, m["sumn"][k] >> 8])
        elif c == 9:
            num = d[1] | (d[2] << 8) | (d[3] << 16); den = 2 * m["S"] * m["S"] * (K - 1); q, r = divmod(num, den); self.out += bytes([q & 255, q >> 8 & 255, q >> 16 & 255, r & 255, r >> 8 & 255])
        elif c == 11:
            self.out += bytes([(m["cnt"][k][j] + 256) & 255 for k in range(K) for j in range(NB)])
        else: super().write(d)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200); ap.add_argument("--cells", type=int, default=7); ap.add_argument("--wires", type=int, default=18)
    ap.add_argument("--aw", type=int, default=7); ap.add_argument("--hw-s", type=int, default=16); ap.add_argument("--selftest", action="store_true"); ap.add_argument("--sets", type=int, default=len(CONFIGS)); a = ap.parse_args()
    K, NB, AW, HS = a.cells, a.wires, a.aw, a.hw_s
    sets = [BS.make_set(K, NB, AW, cfg, HS) for cfg in CONFIGS[:a.sets]]
    cov = BS.coverage(K, NB, AW, sets, HS); print("battery coverage:", " ".join("%s=%d" % kv for kv in cov.items()))
    if a.selftest: ser = FakeBoard(S1.make_model(sets[0], HS)); H.M.t5.mc.AW = AW
    else:
        import serial; ser = serial.Serial(a.port, a.baud, timeout=5)
    b = H.Board(ser, K, NB)
    if not a.selftest and not b.sync(): sys.exit(2)
    failed = []
    def stage(tag, bad, n, detail):
        print("  %-26s %s" % (tag, "ok (%d checked)" % n if not bad else "FAIL: %d of %d differ. %s" % (bad, n, detail)))
        if bad: failed.append(tag)
    for si, d in enumerate(sets):
        m = S1.make_model(d, HS); T = d["T"]; print("set %d (seed %d, density %.2f, noise %.2f, cutoff T %d)" % (si + 1, CONFIGS[si][0], CONFIGS[si][1], CONFIGS[si][2], T))
        if a.selftest: ser.m = m
        b.clear()
        for bits, y in d["train"]: b.count(y, H.mask(bits))
        got = b.peek(); exp = [m["cnt"][k][j] for k in range(K) for j in range(NB)]; bad = [i for i in range(len(exp)) if got[i] != exp[i]]
        stage("COUNT -> counters (PEEK)", len(bad), len(exp), "e.g. detector %d wire %d: board %d, rules %d" % (bad[0] // NB, bad[0] % NB, got[bad[0]], exp[bad[0]]) if bad else "")
        b.setw(T); dm = b.dump(); bad = []
        for k in range(K):
            for j in range(NB):
                bw = (1 if dm[k][0] >> j & 1 else 0) - (1 if dm[k][1] >> j & 1 else 0)
                if bw != m["wts"][k][j]: bad.append((k, j, bw))
        stage("SETW -> weights (DUMP)", len(bad), K * NB, "e.g. detector %d wire %d: counter %d, board weight %d, rules weight %d" % (bad[0][0], bad[0][1], m["cnt"][bad[0][0]][bad[0][1]], bad[0][2], m["wts"][bad[0][0]][bad[0][1]]) if bad else "")
        for bits, y in d["train"]: b.accum(y, H.mask(bits))
        b.finish(); sm = b.dumpsums(); bad = [k for k in range(K) if sm[k] != (m["sump"][k], m["sumn"][k])]
        stage("ACCUM -> sums (DUMPSUMS)", len(bad), K, "e.g. detector %d: board %s, rules %s" % (bad[0], sm[bad[0]], (m["sump"][bad[0]], m["sumn"][bad[0]])) if bad else "")
        dm = b.dump(); bad = [k for k in range(K) if dm[k][2] != m["thr"][k]]
        stage("FINISH -> thresholds", len(bad), K, "e.g. detector %d: board %d, rules %d" % (bad[0], dm[bad[0]][2], m["thr"][bad[0]]) if bad else "")
        bad = 0
        for bits, y in d["test"]:
            ep, eg = S1.classify(m, bits); gp, gg = b.run(H.mask(bits)); bad += not (gp == ep and gg == eg)
        stage("RUN -> answers and bursts", bad, len(d["test"]), "")
    rr = random.Random(5); den = 2 * HS * HS * (K - 1); bad = 0; nums = [0, 1, den - 1, den, den + 1, 5 * den + den // 2, 40 * den + 7, 63 * den, 123456] + [rr.randrange(0, 190000) for _ in range(15)]
    if a.selftest: ser.m = S1.make_model(sets[0], HS)
    for num in nums:
        q, r = b.divtest(num); bad += not (q == num // den and r == num % den)
    print("divider"); stage("DIVTEST", bad, len(nums), "")
    print("BIST PASS" if not failed else "BIST FAIL: first failing stage: %s (%d stage checks failed)" % (failed[0], len(failed)))
    sys.exit(0 if not failed else 1)
if __name__ == "__main__": main()
