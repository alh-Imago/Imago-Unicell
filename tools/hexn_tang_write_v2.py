"""WRITE RULE v2 (merge on store) test on the Tang Nano 20K (memory bitstream hexn_mem16, no new hardware): runs the online stream of tools/hexn_mem_write_v2.py for the four write policies on the real board and (a) checks every board answer against the Python copy of the block, (b) checks the board's result table equals the Python-only table for the same seeds.
Usage: python3 tools/hexn_tang_write_v2.py --port /dev/ttyUSB1 [--seeds 3]  |  --selftest"""
import sys, os, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hexn_mem_write_v2 as W
from hexn_tang_mem_v1 import SerialLink
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--port"); ap.add_argument("--baud", type=int, default=115200); ap.add_argument("--seeds", type=int, default=3); ap.add_argument("--selftest", action="store_true"); a = ap.parse_args()
    seeds = range(1, a.seeds + 1)
    if a.selftest: fac = W.RefLink
    else:
        import serial; ser = serial.Serial(a.port, a.baud, timeout=5); ser.reset_input_buffer(); fac = lambda: SerialLink(ser)
    bad = checks = 0; rows = []; fb = []
    for name, pol in W.POLICIES.items():
        acc = None
        for sd in seeds:
            r = W.run(fac(), pol, sd); bad += r["bad"]; checks += r["checks"]; fb += r["fb"]
            acc = {k: (acc[k] if acc else 0) + r[k] for k in W.KEYS}
        rows.append((name, {k: v / len(seeds) for k, v in acc.items()}))
    W.show(rows); ref = W.study(W.RefLink, seeds)
    same = all(abs(x[1][k] - y[1][k]) < 1e-9 for x, y in zip(rows, ref) for k in W.KEYS)
    print("board answers that differ from the Python rules: %d of %d; result table equals the Python-only table: %s" % (bad, checks, same))
    for f in fb[:5]: print("  ", f)
    ok = bad == 0 and same; print("WRITE RULE TEST PASS" if ok else "WRITE RULE TEST FAIL"); sys.exit(0 if ok else 1)
if __name__ == "__main__": main()
