#!/usr/bin/env python3
"""tools/yosys_stat_v1.py -- ledger #1164: read the cell counts out of a yosys `stat` report in BOTH layouts.
Older yosys printed   'Number of cells:  6'  followed by  '     LUT4      1'   (name, then count).
Yosys 0.69 prints     '6 cells'              followed by  '     1   LUT4'      (count, then name) and also counts wires, ports and so on in the same column.
cell_counts(text) returns {cell_type: count} for the LAST statistics block, whichever layout it is in. wires / ports / memories / processes / cells totals are not cell types and are left out."""
import re

_NOT_CELLS = {"wires", "ports", "memories", "memory", "processes", "cells", "submodules", "bits"}


def cell_counts(text):
    t = text
    k = t.rfind("Printing statistics")
    if k >= 0:
        t = t[k:]
    else:                                                     # a report handed in without the banner: start at the last 'Number of cells' / '=== name ==='
        k = max(t.rfind("Number of cells"), t.rfind("==="))
        t = t[k:] if k >= 0 else t
    c = {}
    for line in t.splitlines():
        m = re.match(r"^\s+(\d+)\s+([\w$.\\]+)\s*$", line)    # new layout: count first
        if m and m.group(2).lower() not in _NOT_CELLS:
            c[m.group(2)] = c.get(m.group(2), 0) + int(m.group(1)); continue
        m = re.match(r"^\s+([\w$.\\]+)\s+(\d+)\s*$", line)    # old layout: name first
        if m and m.group(1).lower() not in _NOT_CELLS:
            c[m.group(1)] = c.get(m.group(1), 0) + int(m.group(2))
    return c


if __name__ == "__main__":
    import sys
    print(cell_counts(open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()))


def run_text(cmd, cwd=None, timeout=None, **_ignored):
    """Run yosys and return its full report as text. This yosys (YoWASP) cuts its standard output short on a long run (measured: 56537 bytes, ending at the ABC9 step, exit code 0), so the report is
    also written with -l to a log file and THAT is returned. Paths in the command must be relative to cwd (this yosys opens only names inside its working folder)."""
    import os, subprocess, tempfile
    log = "_yosys_run.log"
    c = list(cmd) + ["-l", log]
    wd = cwd or os.getcwd()
    r = subprocess.run(c, cwd=wd, capture_output=True, text=True, timeout=timeout)
    p = os.path.join(wd, log)
    try:
        txt = open(p).read()
        os.remove(p)
    except OSError:
        txt = ""
    return txt if len(txt) >= len(r.stdout) else r.stdout
