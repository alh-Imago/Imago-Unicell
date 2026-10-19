#!/usr/bin/env python3
"""decode_user1.py -- turn the three words printed by read_user1.sh into plain statements."""
import re
import sys

text = open(sys.argv[1]).read()
m = re.search(r"USER1\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)", text)
if not m:
    sys.exit("no USER1 line found: step B (load the bitstream) or the OpenOCD run failed; see the log")
w0, w1, w2 = (int(x, 16) for x in m.groups())
print("word0 = 0x%08X   %s" % (w0, "OK, the fixed pattern 'UNIC' came back" if w0 == 0x554E4943 else "NOT the expected 0x554E4943"))
print("word1 = %d clocks of 50 MHz since power-up (a snapshot; changes on every read) -> %.3f s" % (w1, w1 / 50e6))
seen, bad, tmo, lamp = w2 & 1, (w2 >> 1) & 1, (w2 >> 2) & 1, (w2 >> 3) & 1
print("word2 = 0x%08X   seen=%d bad=%d timeout=%d lamp_on=%d idx=%d" % (w2, seen, bad, tmo, lamp, (w2 >> 8) & 0xFF))
print("compare: %s" % ("PASS (a complete line was received and every byte matched)" if seen and not bad and not tmo else "NOT a pass"))
