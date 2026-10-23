#!/usr/bin/env python3
"""Run a ypcb uberddr3 script (or memlat.py) with jtagdr replaced by the OpenOCD version, so no xsdb is needed.
Usage (from ~/ypcb-00338-1p1, inside the nix shell with openocd):
  nix shell nixpkgs#openocd --command env OPENOCD=openocd python3 ~/hexn-wt/fpga/ypcb/hexn_ram/run_with_openocd.py <script.py> [args]
  e.g. designs/uberddr3/check.py        ~/hexn-wt/fpga/ypcb/hexn_ram/memlat.py --len 10"""
import os, runpy, sys
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import jtagdr_openocd
sys.modules["jtagdr"] = jtagdr_openocd
if len(sys.argv) < 2: sys.exit(__doc__)
target = os.path.abspath(sys.argv[1]); sys.argv = sys.argv[1:]
try: runpy.run_path(target, run_name="__main__")
finally:
    if jtagdr_openocd._ex is not None: jtagdr_openocd._ex.close()
