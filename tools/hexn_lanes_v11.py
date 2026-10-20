"""Hex-N lanes-per-face experiment v11 (new file). VM only. How much learning detail does a smaller or larger cell keep?
Re-runs the v10 task (delay D, plain cell with M=0, v6 learner, 4-bit reward, 1500 tries) with PAIRS (lanes per face) set to --lanes.
The earlier files hold the cell size as module-level constants, so this script sets them in every loaded module before the run
(checked: --lanes 4 gives the same numbers as the unpatched v10 for the same seeds).  Usage: python3 tools/hexn_lanes_v11.py --lanes P [--delay D]"""
import argparse, importlib.util, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("hexn_state_v10", os.path.join(ROOT, "tools", "hexn_state_v10.py"))
v10 = importlib.util.module_from_spec(sp); sp.loader.exec_module(v10)


def set_lanes(P):
    N = v10.F * P
    for mod in (v10, v10.v1, v10.v1.m, v10.v3, v10.v9):
        if hasattr(mod, "P"): mod.P = P
        if hasattr(mod, "N"): mod.N = N


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--lanes", type=int, default=4); ap.add_argument("--delay", type=int, default=0)
    ap.add_argument("--first", type=int, default=0); ap.add_argument("--runs", type=int, default=20); ap.add_argument("--tries", type=int, default=1500)
    ap.add_argument("--check", action="store_true", help="run one seed and print it (to compare lanes 4 against v10)"); a = ap.parse_args()
    set_lanes(a.lanes)
    print(f"lanes per face {a.lanes}, delay {a.delay}, plain cell, {a.tries} tries")
    print(f"{'seed':>4} {'learned':>8} {'random-best':>11}")
    for s in range(a.first, a.first + (1 if a.check else a.runs)):
        l, rb = v10.one(s, a.delay, 0, False, a.tries, 0.5, 100, 4); print(f"{s:>4} {l:>8} {rb:>11}", flush=True)
