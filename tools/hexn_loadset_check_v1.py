#!/usr/bin/env python3
"""hexn_loadset_check_v1: does the LOADDET recall path (core v4, lattice v18, bank v19, loader) restore a stored set of detector settings exactly? (design: docs/hex-n/CARD_SLICE_v1.md)
Run through the JTAG wrapper in simulation:  HEXN_SIM_CORE=v4 HEXN_SIM_LAT=18 python3 tools/hexn_card_run_v3.py --sim tools/hexn_loadset_check_v1.py docs/hex-n/frontend/example_sensors_script_v1.txt [--per 6]
or on the card with a bitstream that has the v4 core. Steps: train set A (the script's own labels) -> dump A, run the test samples -> answers A; train set B (the same data with the class labels shifted by 3, so the settings differ) -> dump B, answers B; then LOADDET the stored dump A for detectors 0..K-1 -> dump again must equal A and the answers must equal answers A;
LOADDET B -> equals B; LOADDET A again -> equals A (A, B, A). Prints the number of differing detectors and answers in each step. --per limits training samples per class (to keep the simulation short)."""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_tang_host_v3 as H, hexn_tang_script_v1 as S1
class LB(H.Board):
    def loaddet(self, wp, wn, thr): self.s.write(bytes([0x13, wp & 255, (wp >> 8) & 255, (wp >> 16) & 255, wn & 255, (wn >> 8) & 255, (wn >> 16) & 255, thr & 255])); self._ack()
    def load_all(self, settings):
        for wp, wn, thr in settings: self.loaddet(wp, wn, thr)
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("script"); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200); ap.add_argument("--per", type=int, default=6); ap.add_argument("--tests", type=int, default=30); ap.add_argument("--hw-s", type=int, default=16); a = ap.parse_args()
    d = S1.parse_script(open(a.script).read()); K, NB = d["classes"], d["wires"]
    def limit(samples, per): cnt = {}; out = []; [out.append((b, y)) for b, y in samples if cnt.__setitem__(y, cnt.get(y, 0) + 1) or cnt[y] <= per]; return out
    dA = dict(d); dA["train"] = limit(d["train"], a.per); dB = dict(dA); dB["train"] = [(b, (y + 3) % K) for b, y in dA["train"]]
    mA = S1.make_model(dA, a.hw_s); mB = S1.make_model(dB, a.hw_s); tests = [H.mask(b) for b, y in (d["test"] or d["train"])][:a.tests]
    import serial; ser = serial.Serial(a.port, a.baud, timeout=5); b = LB(ser, K, NB)
    if not b.sync(): sys.exit(2)
    def answers(): return [b.run(m) for m in tests]
    b.train(mA); dumpA = b.dump(); ansA = answers(); b.train(mB); dumpB = b.dump(); ansB = answers()
    print("set A and set B differ in %d of %d detectors, in %d of %d answers (the test only means something if they do)" % (sum(x != y for x, y in zip(dumpA, dumpB)), K, sum(x != y for x, y in zip(ansA, ansB)), len(tests)))
    bad = 0
    for tag, store, ans in (("load A over B", dumpA, ansA), ("load B over A", dumpB, ansB), ("load A again", dumpA, ansA)):
        b.load_all(store); got = b.dump(); dd = sum(x != y for x, y in zip(got, store)); da = sum(x != y for x, y in zip(answers(), ans)); bad += dd + da
        print("%-14s: %d of %d detectors differ from the stored dump, %d of %d answers differ from the original's" % (tag, dd, K, da, len(tests)))
    print("LOADSET CHECK %s" % ("PASS" if bad == 0 else "FAIL (%d differences)" % bad)); sys.exit(0 if bad == 0 else 1)
main()
