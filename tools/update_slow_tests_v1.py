#!/usr/bin/env python3
"""tools/update_slow_tests_v1.py -- build tests/slow_tests.txt from a measured pytest run (ledger #1036 addendum 45).

    python3 -m pytest tests/vm -q -n 2 --log-durations=durations.log     (stopping it early is fine: every test is logged as it ends)
    python3 tools/update_slow_tests_v1.py durations.log [--threshold 5.0]

Adds up every setup/call/teardown time per test FUNCTION (parameters folded together), and lists the functions at or over
the threshold (seconds, default 5). tests/conftest.py gives those the `slow` marker. A function that was never timed (a run
stopped early) is simply not listed. The output is sorted, so it diffs cleanly."""
import argparse
import collections
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINE = re.compile(r"^\s*([0-9.]+)s\s+(setup|call|teardown)\s+(\S+)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("durations", help="log written by pytest --log-durations=FILE (or saved --durations output)")
    ap.add_argument("--threshold", type=float, default=5.0)
    ap.add_argument("--out", default=os.path.join(ROOT, "tests", "slow_tests.txt"))
    a = ap.parse_args()
    seen = {}                      # (phase, node id) -> seconds; a repeated line (older logs doubled them under xdist) counts once
    for ln in open(a.durations, errors="replace"):
        m = LINE.match(ln)
        if m:
            seen[(m.group(2), m.group(3))] = float(m.group(1))
    total = collections.defaultdict(float)
    for (_, node), sec in seen.items():
        total[node.split("[")[0]] += sec
    if not total:
        sys.exit("no duration lines found: run pytest with --log-durations=FILE")
    slow = sorted(k for k, v in total.items() if v >= a.threshold)
    with open(a.out, "w") as f:
        f.write(f"# Test functions that take {a.threshold:g} s or more in total (measured). Marked `slow` by tests/conftest.py.\n")
        f.write(f"# Built from a log covering {len(total)} timed test functions: a run stopped early lists only what it timed, so refresh after a longer run.\n")
        f.write("# Regenerate: tools/update_slow_tests_v1.py (see its docstring). Run the quick set with: pytest tests/vm -m 'not slow'\n")
        f.write("\n".join(slow) + "\n")
    print(f"{len(slow)} slow functions of {len(total)} timed -> {os.path.relpath(a.out, ROOT)}  "
          f"(slow total {sum(total[k] for k in slow):.0f} s of {sum(total.values()):.0f} s listed)")


if __name__ == "__main__":
    main()
