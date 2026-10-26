#!/usr/bin/env python3
"""hexn_key_check_v3: the larger key test on the (simulated or real) bank (clone of hexn_key_check_v2.py, left untouched). docs/hex-n/CARD_SLICE_v1.md, test-ladder step 4.
Run on the card:  nix shell nixpkgs#openocd --command env OPENOCD=openocd HEXN_CHAIN=2 python3 ~/hexn-wt/tools/hexn_card_run_v3.py tools/hexn_key_check_v3.py docs/hex-n/frontend/example_sensors_script_v1.txt
In simulation:    HEXN_SIM_CORE=v4 HEXN_SIM_LAT=18 python3 tools/hexn_card_run_v3.py --sim tools/hexn_key_check_v3.py docs/hex-n/frontend/example_sensors_script_v1.txt --shifts 0,1,2 --probes 12 --trials 1
Sweep to find where recall fails: 7 engrams, 24 data probes, damage 12..384 changed settings (the bank has 133 settings, draws can hit the same one twice), probe noise 0.1..0.4, 3 trials per engram and combination (21 per cell of the table).
Steps: (1) each engram's settings (from the model) are written with LOADDET and the probes run: every detector's count must equal the model's; (2) for each trial the bank is loaded with DAMAGED settings, the probes are shown with noise, the observed key (which detectors fire) must equal the model's key for the same settings and noise, and is matched (smallest Hamming distance, a tie = no recall) against the stored keys; (3) the recalled engram's settings are written back and DUMP must equal the stored settings when the recall was right.
ASSUMPTION: the bank's burst counts equal the model's g values (verified for 2 engrams on the card and in simulation)."""
import sys, os, random, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_host_v3 as H, hexn_tang_script_v1 as S1, hexn_key_v1 as KV
class LB(H.Board):
    def loaddet(self, wp, wn, thr): self.s.write(bytes([0x13, wp & 255, (wp >> 8) & 255, (wp >> 16) & 255, wn & 255, (wn >> 8) & 255, (wn >> 16) & 255, thr & 255])); self._ack()
    def load_model(self, m):
        for k in range(m["K"]):
            wp = sum(1 << j for j in range(m["NB"]) if m["wts"][k][j] > 0); wn = sum(1 << j for j in range(m["NB"]) if m["wts"][k][j] < 0); self.loaddet(wp, wn, m["thr"][k])
def settings_of(m): return [(sum(1 << j for j in range(m["NB"]) if m["wts"][k][j] > 0), sum(1 << j for j in range(m["NB"]) if m["wts"][k][j] < 0), m["thr"][k]) for k in range(m["K"])]
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--shifts", default="0,1,2,3,4,5,6"); ap.add_argument("--probes", type=int, default=24); ap.add_argument("--trials", type=int, default=3); ap.add_argument("--damage", default="12,24,48,96,192,384"); ap.add_argument("--noise", default="0.1,0.2,0.3,0.4"); a = ap.parse_args()
    d = S1.parse_script(open(a.script).read()); K, NB = d["classes"], d["wires"]; shifts = [int(x) for x in a.shifts.split(",")]; dmg = [int(x) for x in a.damage.split(",")]; noises = [float(x) for x in a.noise.split(",")]
    models = {s: KV.engram_model(d, s) for s in shifts}; pr = random.Random(100 + a.probes); probes = [pr.choice(d["train"])[0] for _ in range(a.probes)]
    keys = {s: KV.key_of(models[s], probes) for s in shifts}; dd = [KV.ham(keys[x], keys[y]) for i, x in enumerate(shifts) for y in shifts[:i]]
    print("%d engrams, %d probes (%d-bit keys); stored keys differ pairwise by min %d, mean %.1f bits" % (len(shifts), a.probes, a.probes * K, min(dd), sum(dd) / len(dd)))
    import serial; ser = serial.Serial(a.port, a.baud, timeout=5); b = LB(ser, K, NB)
    if not b.sync(): sys.exit(2)
    def board_counts(plist): return [b.run(H.mask(p)) for p in plist]
    bad_counts = n_counts = 0
    for s in shifts:
        b.load_model(models[s]); got = board_counts(probes)
        for p, (cl, cnt) in zip(probes, got): ref = S1.classify(models[s], p); n_counts += 1; bad_counts += (cnt != ref[1]) or (cl != ref[0])
    print("step 1, clean engrams: %d of %d probe runs differ from the model (class or any detector's count)" % (bad_counts, n_counts))
    rnd = random.Random(5); bad_keys = bad_restore = 0; table = {}
    for nd in dmg:
        for q in noises:
            hit = tot = ties = 0
            for s in shifts:
                for t in range(a.trials):
                    dm = KV.damage(models[s], rnd, nd); noisy = [[x ^ (1 if rnd.random() < q else 0) for x in p] for p in probes]
                    b.load_model(dm); obs = [int(c > 0) for (cl, cnt) in board_counts(noisy) for c in cnt]; ref = KV.key_of(dm, noisy); bad_keys += obs != ref
                    dist = [KV.ham(obs, keys[x]) for x in shifts]; best = min(dist); cand = [x for x, v in zip(shifts, dist) if v == best]; rec = cand[0] if len(cand) == 1 else None
                    hit += rec == s; tot += 1; ties += rec is None
                    if rec is not None: b.load_model(models[rec]); bad_restore += (rec == s) and (b.dump() != settings_of(models[s]))
            table[(nd, q)] = (hit, tot, ties)
    print("step 2, damaged banks: %d observed keys differ from the model's key" % bad_keys)
    print("        damage | probe noise | right engram recalled")
    for (nd, q), (h, t, ti) in table.items(): print("         %3d   |    %.1f      |   %d / %d   (%d ties, %d wrong)" % (nd, q, h, t, ti, t - h - ti))
    print("step 3, after a right recall the written-back settings differ from the stored ones in %d cases" % bad_restore)
    bad = bad_counts + bad_keys + bad_restore; print("KEY CHECK v3 %s (counts and keys equal the model: %s; recall rates above are the result, not a pass criterion)" % ("PASS" if bad == 0 else "FAIL (%d differences)" % bad, "yes" if bad_counts + bad_keys == 0 else "NO")); sys.exit(0 if bad == 0 else 1)
main()
