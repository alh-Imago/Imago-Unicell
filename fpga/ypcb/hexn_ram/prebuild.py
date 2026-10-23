#!/usr/bin/env python3
"""hexn_ram: the ypcb designs/uberddr3 DDR3 build with the RAM latency probe in place of the memory test.
This does NOT copy or change anything of Alan's ypcb repo or of UberDDR3 (GPL): it runs ypcb's own designs/uberddr3/prebuild.py
unchanged (same arguments and environment: UBERDDR3_SRC, UBER_CK_PHASE, UBER_CHANNEL, UBER_DUAL ...), which writes the generated
top level into the build dir. The probe arrives as this folder's memtest.v (same module name and ports as ypcb's memtest.v) and memlat.v,
which the build picks up from the design folder in place of designs/uberddr3/memtest.v.
Settings: YPCB = the ypcb checkout (default ~/ypcb-00338-1p1)."""
import os, subprocess, sys
ypcb = os.environ.get("YPCB", os.path.expanduser("~/ypcb-00338-1p1"))
theirs = os.path.join(ypcb, "designs", "uberddr3", "prebuild.py")
if not os.path.exists(theirs): sys.exit("not found: " + theirs)
sys.exit(subprocess.run([sys.executable, theirs] + sys.argv[1:]).returncode)
