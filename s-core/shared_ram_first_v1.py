#!/usr/bin/env python3
"""shared_ram_first_v1.py - tells apart "the shared RAM's READ ADDRESS is stuck at word 0" from "the read data only updates ONCE after loading" (ledger #1477).  Writes ONLY the shared RAM of block BLK.
Run it straight after a fresh bitstream load (no reads before it): earlier tests always read word 0 first, so they could not tell the two apart.
Writes (one request at a time, with a pause): word 5 = B first, then word 0 = A, then word 7 = C.  Then reads: 5, 7, 0, 5, 0.  Expected pattern for each explanation:
   a healthy RAM:                              B C A B A
   read address stuck at 0:                    A A A A A
   read data updates only on the first read:   B B B B B
   only the first write ever lands (word 5):   B 0 0 B 0
Usage (card just loaded, openOCD on the path, run from s-core):   nix shell nixpkgs#openocd --command python3 shared_ram_first_v1.py jtag [BLK] [PAUSE_SECONDS]"""
import sys, time
import host_sc as hs
port = sys.argv[1] if len(sys.argv) > 1 else 'jtag'
blk = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
P = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05
A, B, C = 0xAAAA0001, 0xBBBB0002, 0xCCCC0003
b = hs.Board(port)
print('# board version', b.version(), ' block', blk, ' pause', P, 's  (this run must be the first thing after the load)')
b.s.write(hs.cmd_O(blk)); b.s.flush(); time.sleep(P)
for k, v in ((5, B), (0, A), (7, C)):
    b.shared_write(k, [v]); time.sleep(P)
names = {A: 'A', B: 'B', C: 'C', 0: '0'}
seq = [5, 7, 0, 5, 0]; out = []
for k in seq:
    g = b.shared_read(k, 1)[0]; time.sleep(P); out.append(names.get(g, '?0x%08x' % g))
    print('   read word %d -> 0x%08x  (%s)' % (k, g, out[-1]))
print('read order 5 7 0 5 0 gave:', ' '.join(out))
print('healthy B C A B A | address stuck at 0: A A A A A | data updates once: B B B B B | only first write lands: B 0 0 B 0')
