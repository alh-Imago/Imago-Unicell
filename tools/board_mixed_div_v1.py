#!/usr/bin/env python3
"""tools/board_mixed_div_v1.py -- ledger #1171: board bitstreams for flex -> STANDARD / CARRIER DIVIDER -> flex pipelines (the division core on the v4 / v4c line, never before on the card).
Clone of board_mixed_std_v1.py (#1168) with the divider examples. Each word x: flex A adds 1000 (divisor d = x + 1000, 32 bit), the middle block divides the fixed dividend 1000000 by d
(unsigned; d = 0 gives all ones, the rule of the LaTeX front end), flex C adds 5; the exit gives q + 5 (32 bit). One of the 9 words has d = 0.
  mixed_std_div_pipe      middle block = the standard line's join-mode divider (div_cell_v4e)
  mixed_carrier_div_pipe  middle block = the trimmed VIXeN carrier with its division core
  python3 tools/board_mixed_div_v1.py [--out fpga/board_tests_mixed_div] [--only NAME] [--seed N] [--no-pnr] [--steps K]"""
import argparse, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import board_loops_v1 as BL                                   # noqa: E402
ROOT = BL.ROOT
XS = [5, 100, -7, 12345, 0, 77, 1000, 31, -1000]
K = 1000000
CASES = [("mixed_std_div_pipe", "flex -> adapter -> STANDARD join-mode DIVIDER -> adapter -> flex pipeline, 1000000 // (x + 1000) + 5, one word divides by zero (random exit stalls)", "mixed_flex_std_div_flex_v1.icm-hier.json"),
         ("mixed_carrier_div_pipe", "flex -> adapter -> trimmed CARRIER with its DIVISION core -> adapter -> flex pipeline, 1000000 // (x + 1000) + 5, one word divides by zero (random exit stalls)", "mixed_flex_carrier_div_flex_v1.icm-hier.json")]


def expected(xs):
    out = []
    for x in xs:
        d = (x + 1000) & 0xFFFFFFFF
        q = 0xFFFFFFFF if d == 0 else K // d
        out.append((q + 5) & 0xFFFFFFFF)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "fpga", "board_tests_mixed_div")); ap.add_argument("--only", default=""); ap.add_argument("--seed", type=int, default=1); ap.add_argument("--no-pnr", action="store_true")
    a = ap.parse_args(); out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
    work = tempfile.mkdtemp(prefix="bmixdiv_"); res = []
    for name, what, icm in CASES:
        if a.only and name not in a.only.split(","):
            continue
        print("== " + name, flush=True)
        g = os.path.join(work, "gen_" + name)
        top, files = BL.assemble(["-s", "flex", "--icm", os.path.join(ROOT, "nano", "examples", icm), "--top", "mix"], g)
        r = BL.build(name, what, "stream", top, files, None, expected(XS), XS, out, not a.no_pnr, a.seed, work)
        print("   ok: %s   %s LUT4  Fmax %s" % (r["sim_line"], r.get("lut4", "-"), r.get("fmax_mhz", "-")), flush=True); res.append(r)
    for fn in ("run_all.bat", "board_run.py", "board_collect.py", "run_one.sh", "run_all.sh", "run_all_v2.sh", "run_one_v2.sh", "watch_serial.py"):
        src = os.path.join(ROOT, "fpga", "board_tests_loops", fn)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(out, fn))
    print("wrote %d tests to %s" % (len(res), out))


if __name__ == "__main__":
    main()
