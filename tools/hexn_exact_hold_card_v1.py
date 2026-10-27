"""hexn_exact_hold_card_v1: LAYER 1 EXACT-MATCH MODE + HOLD TOGETHER on the real bank (core v5, lattice 18, bank v19; simulation, or the card with a core v5 bitstream, none built yet). Run: HEXN_SIM_CORE=v5 HEXN_SIM_LAT=18 python3 tools/hexn_card_run_v4.py --sim tools/hexn_exact_hold_card_v1.py <any sensors script, e.g. docs/hex-n/frontend/example_sensors_script_v1.txt> [--segments 12]
The bank (7 classes, 8 of the 18 wires used) is set by the host with LOADDET to direct/exact wiring for the first 7 remote keys (0x45 0x46 0x47 0x44 0x40 0x43 0x07: several are one bit apart): weight +1 for a 1-bit, -1 for a 0-bit, threshold = number of ones (tools/hexn_layer1_v2.py direct0). The stream is runs of the same key (a held key repeats its frame) with 15 percent of frames damaged by ONE flipped bit. For hold lengths 1 and 3: (a) raw answers equal the Python model, (b) held answers/flags equal the hold rule on the raw answers; (c) reported, not asserted: damaged frames that came back 'unknown' (NONE), damaged frames that landed on ANOTHER valid key (cannot be seen as errors), and held-output changes against the number of real key changes. PASS needs (a) and (b)."""
import sys, os, random, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_host_v3 as H, hexn_tang_script_v1 as S1, hexn_layer1_v1 as L, hexn_hold_card_v1 as HC
KEYS = [0x45, 0x46, 0x47, 0x44, 0x40, 0x43, 0x07]
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200); ap.add_argument("--segments", type=int, default=12)
    a = ap.parse_args(); bits = lambda c: L.pad([(c >> j) & 1 for j in range(8)])
    m = L.bank([(bits(c), i) for i, c in enumerate(KEYS)], 7)
    for k, c in enumerate(KEYS): m["wts"][k] = [1 if (c >> j) & 1 else -1 for j in range(8)] + [0] * 10; m["thr"][k] = max(1, S1.fwd_of(bin(c).count("1"), m["AW"]))
    import serial; ser = serial.Serial(a.port, a.baud, timeout=5); b = HC.HB(ser, 7, 18)
    if not b.sync(): sys.exit(2)
    for k in range(7):
        wp = sum(1 << j for j in range(18) if m["wts"][k][j] > 0); wn = sum(1 << j for j in range(18) if m["wts"][k][j] < 0); b.s.write(bytes([0x13, wp & 255, wp >> 8 & 255, wp >> 16 & 255, wn & 255, wn >> 8 & 255, wn >> 16 & 255, m["thr"][k] & 255])); b._ack()
    NONE = 15; r = random.Random(9); seq = []; truth = []
    for _ in range(a.segments):
        k = r.randrange(7)
        for _ in range(r.randrange(3, 10)):
            c = KEYS[k]; flip = r.random() < 0.15
            if flip: c ^= 1 << r.randrange(8)
            seq.append((c, flip)); truth.append(k)
    bad = 0
    for n in (1, 3):
        b.sethold(n); raws = []; got = []; modelbad = 0
        for c, flip in seq:
            hc, fl, raw = b.runhold(H.mask(bits(c))); got.append((hc, fl & 1, (fl >> 1) & 1)); rc = (raw & 31) if raw & 128 else -1; raws.append(rc if rc >= 0 else NONE)
            modelbad += (S1.classify(m, bits(c))[0] != rc)
        ref = HC.hold_ref(raws, n); mism = sum(1 for (hc, v, ch), (rc_, rch) in zip(got, ref) if (hc, v, ch) != (rc_, 1, rch))
        dmg = [(i, c) for i, (c, f) in enumerate(seq) if f]; unk = sum(raws[i] == NONE for i, _ in dmg); other = sum(c in KEYS for _, c in dmg if True)
        held_wrong = sum(1 for i in range(len(seq)) if got[i][0] != truth[i] and not (i > 0 and truth[i] != truth[i - 1]) and got[i][0] != NONE)
        print("n=%d: %d frames (%d damaged: %d answered unknown, %d landed on another valid key), raw different from model %d, held different from hold rule %d, held changes %d against %d real key changes" % (n, len(seq), len(dmg), unk, other, modelbad, mism, sum(c for _, _, c in got), sum(truth[i] != truth[i - 1] for i in range(1, len(truth)))))
        bad += modelbad + mism
    print("EXACT+HOLD CHECK %s" % ("PASS" if bad == 0 else "FAIL (%d differences)" % bad)); sys.exit(0 if bad == 0 else 1)
main()
