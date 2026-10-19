#!/usr/bin/env python3
"""decode_clock.py LOG SECONDS -- the counter (word 1) is 32 bits and wraps every 85.9 s at 50 MHz; two reads 10 s apart are fine."""
import re
import sys

text = open(sys.argv[1]).read()
secs = float(sys.argv[2])
a = re.search(r"CLK1\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)", text)
b = re.search(r"CLK2\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)", text)
if not (a and b):
    sys.exit("could not find the CLK1 / CLK2 lines; see the log")
c1, c2 = int(a.group(2), 16), int(b.group(2), 16)
d = (c2 - c1) % (1 << 32)
print("counter %d -> %d, difference %d clocks in about %.3f s" % (c1, c2, d, secs))
print("clock = %.4f MHz (nominal 50; good to about 0.1 %% because of the host-side timing)" % (d / secs / 1e6))
