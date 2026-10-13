#!/usr/bin/env python3
"""tools/scan_flow_check_v2.py -- ledger #1151: the whole in-flight save / move / restore flow of tools/scan_flow_check_v1.py, for the design compiled from a LaTeX formula (board_scan_v2.py).
Card A runs the loop z -> f(z) (f = the formula) and freezes itself part-way; the host captures its state twice; a FRESH simulated card B is reset, configured, given the image through CRC-checked chunks, applied, read back
and released with A; at the next stop their complete states are identical and the word is the Python model of the formula's iteration.  Same damage scenarios as v1.
  python3 tools/scan_flow_check_v2.py [--scenario NAME|all] [--k1 3] [--k2 4] [--lag 0] [--dly 0] [--formula ...]"""
import argparse, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools")); sys.path.insert(0, os.path.join(ROOT, "nano"))
import board_scan_v1 as v1, board_scan_v2 as b2, scan_host_v2 as h  # noqa: E402
from scan_flow_check_v1 import SCENARIOS, PERSISTENT  # noqa: E402

Z0 = 50000


def step_fn(z):
    return ((z * z + 12345) & 0xFFFFFFFF) % 65521          # the formula in plain Python; the 32-bit word wraps BEFORE the mod, as the hardware (and the front end reference) does


def model(n, z=Z0, f=step_fn):
    out = []
    for _ in range(n):
        z = f(z); out.append(z)
    return out


def run_flow(built, name, k1=3, k2=4, lag=0, dly=0, dly2=3, lag2=0, faults=(), mutant="none", cpb=8, tmo=3000, retries=4, log=print, f=step_fn):
    ca = v1.SimCard(cpb=cpb, tmo=tmo, built=built)
    cb = v1.SimCard(cpb=cpb, tmo=tmo, built=built)
    try:
        la = h.FaultLink(ca, faults) if faults else ca
        lb = h.FaultLink(cb, faults) if faults else cb
        A, B = h.Card(la, retries=retries, log=log, design=name), h.Card(lb, retries=retries, log=log, design=name)
        A.reset(); ca.idle(1500); B.reset(); cb.idle(1500)
        A.configure(2, k1, dly, lag); A.load(Z0)
        qa = A.wait_stopped()
        ses, img = A.capture_verified()
        tr = h.parse_trailer(img)
        B.configure(2, k2, dly2, lag2)
        B.restore(ses, img)
        A.configure(2, k2, dly2, lag2)
        A.go(); B.go()
        fa = A.wait_stopped(steps=tr["steps"] + k2); fb = B.wait_stopped(steps=tr["steps"] + k2)
        ia = (A.capture(), A.dump_image())[1][1]
        ib = (B.capture(), B.dump_image())[1][1]
        m = model(tr["steps"] + k2 + 2, f=f)
        res = dict(k1=k1, k2=k2, lag=lag, dly=dly, steps_at_cut=tr["steps"], busy_at_cut=qa["busy"], held_valid_at_cut=qa["held_valid"],
                   same_state=(ia == ib), same_flags=(fa["busy"], fa["held_valid"], fa["steps"], fa["word"]) == (fb["busy"], fb["held_valid"], fb["steps"], fb["word"]),
                   model_ok=bool(fb["held_valid"]) and (fb["word"] == m[fb["steps"] - 1]), held_valid_at_end=fb["held_valid"], word=fb["word"],
                   retries=dict(A=A.stats, B=B.stats), injected=(getattr(la, "injected", 0), getattr(lb, "injected", 0)))
        res["ok"] = bool(res["same_state"] and res["same_flags"] and res["model_ok"])
        return res
    finally:
        ca.close(); cb.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--scenario", default="clean"); ap.add_argument("--k1", type=int, default=3); ap.add_argument("--k2", type=int, default=4)
    ap.add_argument("--lag", type=int, default=0); ap.add_argument("--dly", type=int, default=0)
    a = ap.parse_args()
    names = list(SCENARIOS) if a.scenario == "all" else [a.scenario]
    bad = 0
    work = tempfile.mkdtemp(prefix="scan_flow2_")
    try:
        top, files, g, meta = b2.build_files(work, 8, 3000)
        for n in names:
            fa = SCENARIOS.get(n, PERSISTENT.get(n, []))
            try:
                r = run_flow((top, files, g), meta["name"], a.k1, a.k2, a.lag, a.dly, faults=fa, log=lambda *x: None)
                print(n, "->", "PASS" if r["ok"] else "FAIL", r); bad += not r["ok"]
            except h.ScanError as e:
                print(n, "-> ScanError:", e); bad += not n.startswith("persistent")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
