#!/usr/bin/env python3
"""tools/scan_flow_check_v1.py -- ledger #1146: the whole in-flight save/restore over the serial protocol, on the real design in simulation, with damage injected on the wire.

Card A runs the looped CORDIC and freezes itself mid-flight; the host captures its state (twice, must agree), then a FRESH card B (a separate simulation) is reset, configured, loaded with the image through checked chunks,
applied, and read back. Both are released with the same settings; at the next stop their complete states (image) must be identical, and the word must be the Python model's.
Scenarios damage the traffic (bit flips, dropped bytes, repeated bytes, in both directions) and show the host retrying until the data is right, or refusing (ScanError) when the damage never stops.
Mutants (card without the chunk CRC check) show that the second line of defence, the read-back, still catches a corrupted chunk.

  python3 tools/scan_flow_check_v1.py [--scenario NAME|all] [--k1 3] [--k2 4] [--lag 0] [--dly 0]
"""
import argparse, os, sys, tempfile, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.join(ROOT, "nano"))
import board_scan_v1 as bs, scan_host_v1 as h, looped_cordic_v1 as L  # noqa: E402

SCENARIOS = {
    "clean": [],
    "dump_flip": [("rx", "D", 3, "flip", 60)],                  # a bit flipped in a dumped data line
    "dump_flip_crc": [("rx", "D", 2, "flip", 105)],             # ... in the CRC field
    "dump_drop": [("rx", "D", 5, "drop", 40)],                  # a byte lost in a dumped line
    "dump_dup": [("rx", "D", 4, "dup", 70)],                    # a byte repeated
    "write_flip": [("tx", "W", 4, "flip", 20)],                 # a bit flipped in a written chunk's data (host->card)
    "write_flip_crc": [("tx", "W", 2, "flip", 38)],             # ... in the chunk's CRC
    "write_flip_hdr": [("tx", "W", 3, "flip", 3)],              # ... in its sequence byte
    "write_drop": [("tx", "W", 6, "drop", 10)],                 # a byte lost: the card times out and says 'T'
    "write_dup": [("tx", "W", 1, "dup", 15)],
    "reply_flip": [("rx", "W", 2, "flip", 0)],                  # the card's 'K' arrives damaged: the host writes the chunk again
    "mixed": [("rx", "D", 2, "flip", 60), ("tx", "W", 5, "drop", 12), ("rx", "D", 9, "drop", 5)],   # several different damages in one run
}
PERSISTENT = {"persistent_write": [("tx", "W", 0, "flip", 22)], "persistent_dump": [("rx", "D", 0, "flip", 70)]}


def run_flow(k1=3, k2=4, lag=0, dly=0, dly2=3, lag2=0, faults_a=(), faults_b=(), mutant="none", built=None, cpb=8, tmo=3000, retries=4, log=print):
    ca = bs.SimCard(cpb=cpb, tmo=tmo, mutant=mutant, built=built)
    cb = bs.SimCard(cpb=cpb, tmo=tmo, mutant=mutant, built=ca.files)
    try:
        la = h.FaultLink(ca, faults_a) if faults_a else ca
        lb = h.FaultLink(cb, faults_b) if faults_b else cb
        A, B = h.Card(la, retries=retries, log=log), h.Card(lb, retries=retries, log=log)
        A.reset(); ca.idle(1500); B.reset(); cb.idle(1500)
        A.configure(2, k1, dly, lag); A.load(L.Z0)
        qa = A.wait_stopped(steps=k1)
        ses, img = A.capture_verified()
        tr = h.parse_trailer(img)
        # fresh card B: same configuration for the rest of the run, the image, release
        B.configure(2, k2, dly2, lag2)
        B.restore(ses, img)
        A.configure(2, k2, dly2, lag2)
        A.go(); B.go()
        fa = A.wait_stopped(steps=tr["steps"] + k2); fb = B.wait_stopped(steps=tr["steps"] + k2)
        _, ia = (A.capture(), A.dump_image())[1]
        _, ib = (B.capture(), B.dump_image())[1]
        model = L.model(tr["steps"] + k2 + 2)
        res = dict(k1=k1, k2=k2, lag=lag, dly=dly, dly2=dly2, steps_at_cut=tr["steps"], busy_at_cut=qa["busy"], held_valid_at_cut=qa["held_valid"],
                   same_state=(ia == ib), same_flags=(fa["busy"], fa["held_valid"], fa["steps"], fa["word"]) == (fb["busy"], fb["held_valid"], fb["steps"], fb["word"]),
                   model_ok=bool(fb["held_valid"]) and (fb["signed"] == model[fb["steps"] - 1]), held_valid_at_end=fb["held_valid"],
                   retries=dict(A=A.stats, B=B.stats), injected=(getattr(la, "injected", 0), getattr(lb, "injected", 0)))
        res["ok"] = bool(res["same_state"] and res["same_flags"] and res["model_ok"])
        return res
    finally:
        ca.close(); cb.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--scenario", default="clean"); ap.add_argument("--k1", type=int, default=3); ap.add_argument("--k2", type=int, default=4)
    ap.add_argument("--lag", type=int, default=0); ap.add_argument("--dly", type=int, default=0); ap.add_argument("--mutant", default="none")
    a = ap.parse_args()
    names = list(SCENARIOS) if a.scenario == "all" else [a.scenario]
    bad = 0
    work = tempfile.mkdtemp(prefix="scan_flow_")
    try:
        top, files, g = bs.build_files(work, 8, 3000, a.mutant)
        for n in names:
            fa = SCENARIOS.get(n, PERSISTENT.get(n, []))
            try:
                r = run_flow(a.k1, a.k2, a.lag, a.dly, 3, 0, fa, fa, a.mutant, built=(top, files, g), log=lambda *x: None)
                print(n, "->", "PASS" if r["ok"] else "FAIL", r)
                bad += not r["ok"]
            except h.ScanError as e:
                print(n, "-> ScanError:", e)
                bad += not n.startswith("persistent")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
