#!/usr/bin/env python3
"""hexn_key_check_v1: is the quick key measured on the (simulated or real) bank the same as the model's? (docs/hex-n/CARD_SLICE_v1.md, test-ladder step 4)
Run: HEXN_SIM_CORE=v4 HEXN_SIM_LAT=18 python3 tools/hexn_card_run_v3.py --sim tools/hexn_key_check_v1.py docs/hex-n/frontend/example_sensors_script_v1.txt [--shifts 0,3] [--probes 12] [--trials 3]
For each engram (the script's labels shifted by s) the model's settings are written into the bank with LOADDET; the P data probes (drawn from the training samples) are run on the bank and the output counts of every detector are compared with the model's (S1.classify); then, for each trial, the bank is loaded with DAMAGED settings (12 changes), the probes are shown with 10 percent bit noise, the observed key (which detectors fire) is compared with the model's key for the same damaged settings and noisy probes, and matched against the stored keys of the engrams in the run.
Prints the number of differing counts and keys and how many recalls were right. ASSUMPTION: the bank's burst counts equal the model's g values (board-verified earlier for trained settings; here for LOADDET-written settings)."""
import sys, os, random, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_host_v3 as H, hexn_tang_script_v1 as S1, hexn_key_v1 as KV
class LB(H.Board):
    def loaddet(self, wp, wn, thr): self.s.write(bytes([0x13, wp & 255, (wp >> 8) & 255, (wp >> 16) & 255, wn & 255, (wn >> 8) & 255, (wn >> 16) & 255, thr & 255])); self._ack()
    def load_model(self, m):
        for k in range(m["K"]):
            wp = sum(1 << j for j in range(m["NB"]) if m["wts"][k][j] > 0); wn = sum(1 << j for j in range(m["NB"]) if m["wts"][k][j] < 0); self.loaddet(wp, wn, m["thr"][k])
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200); ap.add_argument("--shifts", default="0,3"); ap.add_argument("--probes", type=int, default=12); ap.add_argument("--trials", type=int, default=3); a = ap.parse_args()
    d = S1.parse_script(open(a.script).read()); K, NB = d["classes"], d["wires"]; shifts = [int(x) for x in a.shifts.split(",")]
    models = {s: KV.engram_model(d, s) for s in shifts}; pr = random.Random(100 + a.probes); probes = [pr.choice(d["train"])[0] for _ in range(a.probes)]
    keys = {s: KV.key_of(models[s], probes) for s in shifts}
    import serial; ser = serial.Serial(a.port, a.baud, timeout=5); b = LB(ser, K, NB)
    if not b.sync(): sys.exit(2)
    def board_counts(plist): return [b.run(H.mask(p)) for p in plist]
    bad_counts = n_counts = 0
    for s in shifts:
        b.load_model(models[s]); got = board_counts(probes)
        for p, (cl, cnt) in zip(probes, got): ref = S1.classify(models[s], p); n_counts += 1; bad_counts += (cnt != ref[1]) or (cl != ref[0])
    print("clean engrams %s: %d of %d probe runs differ from the model (class or any detector's count)" % (shifts, bad_counts, n_counts))
    rnd = random.Random(5); bad_keys = hits = tot = 0
    for s in shifts:
        for t in range(a.trials):
            dm = KV.damage(models[s], rnd, 12); noisy = [[x ^ (1 if rnd.random() < 0.1 else 0) for x in p] for p in probes]
            b.load_model(dm); obs = [int(c > 0) for (cl, cnt) in board_counts(noisy) for c in cnt]; ref = KV.key_of(dm, noisy); bad_keys += obs != ref
            dist = [KV.ham(obs, keys[x]) for x in shifts]; best = min(dist); cand = [x for x, v in zip(shifts, dist) if v == best]; hits += (len(cand) == 1 and cand[0] == s); tot += 1
    print("damaged banks (12 changes) with 10 percent probe noise: %d of %d observed keys differ from the model's key; right engram recalled %d of %d" % (bad_keys, tot, hits, tot))
    bad = bad_counts + bad_keys; print("KEY CHECK %s" % ("PASS" if bad == 0 else "FAIL (%d differences)" % bad)); sys.exit(0 if bad == 0 else 1)
main()
