"""hexn_hold_card_v1: the HOLD COUNTER behind the bank (core v5: commands 0x14 SETHOLD, 0x16 RUNHOLD) against the Python rules. Run in simulation (core v5 + lattice 18 + bank v19):
  HEXN_SIM_CORE=v5 HEXN_SIM_LAT=18 python3 tools/hexn_card_run_v4.py --sim tools/hexn_hold_card_v1.py docs/hex-n/frontend/example_sensors_script_v1.txt [--per 6]
or on the card with a bitstream that has core v5 (none built yet): same script, without --sim.
Steps: train the script's set; for each hold length n in 1, 3, 6: SETHOLD n, then stream a run of test samples in segments (a class repeated, 12 percent single-sample glitches from another class) through RUNHOLD. Checked per reply: (a) the raw answer byte equals the Python model's classification of that sample; (b) the held class, valid and chg equal the hold rule (tools/hexn_hold_v1.py hold(), first sample taken at once, answer NONE = all ones in KW+1 bits) applied to the raw answers that came back. Also checks that SETHOLD clears the hold (the first sample after it is taken at once). Prints counts and PASS/FAIL."""
import sys, os, random, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_host_v3 as H, hexn_tang_script_v1 as S1
class HB(H.Board):
    def sethold(self, n): self.s.write(bytes([0x14, n & 255])); self._ack()
    def runhold(self, m): self.s.write(bytes([0x16, m & 255, (m >> 8) & 255, (m >> 16) & 255])); r = self._rd(3); return r[0], r[1], r[2]
def hold_ref(xs, n):
    cur = None; cand = None; cnt = 0; res = []
    for x in xs:
        chg = 0
        if cur is None: cur = x
        elif x == cur: cand = None; cnt = 0
        else:
            cnt = cnt + 1 if (cand is not None and x == cand) else 1; cand = x
            if cnt >= max(n, 1): cur = x; cand = None; cnt = 0; chg = 1
        res.append((cur, chg))
    return res
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200); ap.add_argument("--per", type=int, default=6); ap.add_argument("--segments", type=int, default=25); ap.add_argument("--hw_s", type=int, default=16)
    a = ap.parse_args(); d = S1.parse_script(open(a.script).read()); K, NB = d["classes"], d["wires"]; KW = max(1, (K - 1).bit_length()); NONE = (1 << (KW + 1)) - 1
    cnt = {}; tr = []
    for b, y in d["train"]:
        cnt[y] = cnt.get(y, 0) + 1
        if cnt[y] <= a.per: tr.append((b, y))
    dd = dict(d); dd["train"] = tr; m = S1.make_model(dd, a.hw_s); pool = d["test"] or d["train"]; by = {}
    for b, y in pool: by.setdefault(y, []).append(b)
    import serial; ser = serial.Serial(a.port, a.baud, timeout=5); b = HB(ser, K, NB)
    if not b.sync(): sys.exit(2)
    b.train(m); r = random.Random(5); bad = 0; total = 0
    classes = sorted(by)
    for n in (1, 3, 6):
        b.sethold(n); seq = []
        for _ in range(a.segments):
            c = r.choice(classes)
            for _ in range(r.randrange(1, 13)):
                cc = r.choice([x for x in classes if x != c]) if r.random() < 0.12 and len(classes) > 1 else c
                seq.append(r.choice(by[cc]))
        raws = []; got = []; modelbad = 0
        for bits in seq:
            hc, fl, raw = b.runhold(H.mask(bits)); got.append((hc, fl & 1, (fl >> 1) & 1)); rc = (raw & 31) if raw & 128 else -1; raws.append(rc if rc >= 0 else NONE)
            k, g = S1.classify(m, bits); modelbad += (k != rc)
        ref = hold_ref(raws, n); mism = sum(1 for (hc, v, ch), (rc_, rch) in zip(got, ref) if (hc, v, ch) != (rc_, 1, rch))
        print("n=%d: %d samples, raw answers different from the Python model %d, held answers/flags different from the hold rule %d, hold changes %d" % (n, len(seq), modelbad, mism, sum(c for _, _, c in got)))
        bad += modelbad + mism; total += len(seq)
    b.sethold(20); hc1 = b.runhold(H.mask(by[classes[0]][0])); b.sethold(20); hc2 = b.runhold(H.mask(by[classes[-1]][0]))
    fresh = hc1[1] & 1 == 1 and hc2[1] & 1 == 1 and hc2[0] == (S1.classify(m, by[classes[-1]][0])[0] if S1.classify(m, by[classes[-1]][0])[0] >= 0 else NONE)
    print("SETHOLD clears the hold (first sample after it is taken at once): %s" % ("yes" if fresh else "NO")); bad += 0 if fresh else 1
    print("HOLD CHECK %s (%d samples)" % ("PASS" if bad == 0 else "FAIL (%d differences)" % bad, total)); sys.exit(0 if bad == 0 else 1)
main()
