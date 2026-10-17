#!/usr/bin/env python3
"""tools/board_sub_carrier_div_v1.py -- ledger #1186: clone of board_sub_carrier_v1.py (#1184) with the trimmed carrier's DIVISION core in the middle: flex -> SUB -> flex -> carrier DIVIDER -> flex. Was: tools/board_sub_carrier_v1.py -- ledger #1184: clone of board_mixed_std_v1.py with ONE case, flex -> SUB -> flex -> trimmed CARRIER -> flex (the sub bridge and the std adapter in one design; sub and carrier are never adjacent, the assembler refuses that). Was: tools/board_mixed_std_v1.py -- ledger #1168: board bitstreams for the flex <-> STANDARD / CARRIER mixed designs (#1162), the one family crossing never run on the card.
Same wrapper, UART line, tooling and rules as tools/board_loops_v1.py (whose `assemble` and `build` it reuses; mixed_pipe there = flex-bridge-SUB-bridge-flex, passed on the card #1120/#1122).
  mixed_std_pipe     flex(+1000) -> adapter -> STANDARD v4 cells(+234) -> adapter -> flex(+5): 8 words, each x + 1239, random exit stalls
  mixed_carrier_pipe flex(+1000) -> adapter -> trimmed CARRIER cells(+234) -> adapter -> flex(+5): same words
  python3 tools/board_sub_carrier_div_v1.py [--out fpga/board_tests_sub_carrier_div] [--only NAME] [--seed N] [--no-pnr]"""
import argparse, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import board_loops_v1 as BL                                   # noqa: E402
ROOT = BL.ROOT
CASES = [("mixed_sub_carrier_div_pipe", "flex(+1000) -> SUB(+234) -> flex(+5) -> trimmed CARRIER DIVIDER (1000000 // d) -> flex(+3): 1000000 // (x + 1239) + 3, one word divides by zero, random exit stalls", "mixed_flex_sub_flex_carrier_div_flex_v1.icm-hier.json")]
XS = [5, 100, -7, 12345, -1239, 77, 1000, 31]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "fpga", "board_tests_sub_carrier_div")); ap.add_argument("--only", default=""); ap.add_argument("--seed", type=int, default=1); ap.add_argument("--no-pnr", action="store_true")
    a = ap.parse_args(); out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
    work = tempfile.mkdtemp(prefix="bsubcar_"); res = []
    for name, what, icm in CASES:
        if a.only and name not in a.only.split(","):
            continue
        print("== " + name, flush=True)
        g = os.path.join(work, "gen_" + name)
        top, files = BL.assemble(["-s", "flex", "--icm", os.path.join(ROOT, "nano", "examples", icm), "--top", "mix"], g)
        exp = [(0xFFFFFFFF if ((x + 1239) & 0xFFFFFFFF) == 0 else 1000000 // ((x + 1239) & 0xFFFFFFFF)) + 3 & 0xFFFFFFFF for x in XS]
        r = BL.build(name, what, "stream", top, files, None, exp, XS, out, not a.no_pnr, a.seed, work)
        print("   ok: %s   %s LUT4  Fmax %s" % (r["sim_line"], r.get("lut4", "-"), r.get("fmax_mhz", "-")), flush=True); res.append(r)
    for fn in ("run_all.bat", "board_run.py", "board_collect.py", "run_one.sh", "run_all.sh", "run_all_v2.sh", "run_one_v2.sh", "watch_serial.py"):     # same helper scripts as the loops package
        src = os.path.join(ROOT, "fpga", "board_tests_loops", fn)
        if os.path.exists(src):
            import shutil; shutil.copy(src, os.path.join(out, fn))
    print("wrote %d tests to %s" % (len(res), out))


if __name__ == "__main__":
    main()
