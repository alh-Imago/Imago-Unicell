#!/usr/bin/env python3
"""shared_ram_spaced_v1.py - the shared-RAM test with every host request sent ON ITS OWN, with a pause after it (ledger #1477).  Writes ONLY that block's shared RAM.
Why: shared_ram_walk_v1.py (Vivado v5 bitstream) showed that reads of ANY address return word 0's value and that writes to other words never show.  Two explanations:
(a) the read side is stuck on word 0 / its data register does not update; (b) requests sent back to back are dropped, only the first of a burst lands.  Sending one request
at a time with a pause tells them apart: if (b), this test passes; if (a), every read still returns word 0's value.
Tests, block BLK:  1  for a few addresses k: write val(k), pause, read k, pause, report;   2  the same for ALL N words (slow: one write + one read per word, PAUSE s each).
Usage (card loaded, openOCD on the path, run from s-core):   nix shell nixpkgs#openocd --command python3 shared_ram_spaced_v1.py jtag [BLK] [N] [PAUSE_SECONDS]
Defaults: BLK 0, N 64, PAUSE 0.02."""
import sys, time
import host_sc as hs
port = sys.argv[1] if len(sys.argv) > 1 else 'jtag'
blk = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
N = int(sys.argv[3], 0) if len(sys.argv) > 3 else 64
P = float(sys.argv[4]) if len(sys.argv) > 4 else 0.02
b = hs.Board(port)
print('# board version', b.version(), ' block', blk, ' words', N, ' pause', P, 's')
b.s.write(hs.cmd_O(blk)); b.s.flush(); time.sleep(P)
M32 = 0xFFFFFFFF
def val(i): return ((i * 0x9E3779B1) ^ 0x5A5A1234 ^ (i << 20)) & M32 or 1
def wr(k, v): b.shared_write(k, [v]); time.sleep(P)
def rd(k): r = b.shared_read(k, 1)[0]; time.sleep(P); return r
print('\n== 1  single words, one request at a time')
for k in [0, 1, 2, 3, 5, 7, 8, 16, 32, N - 1]:
    if k >= N: continue
    wr(k, val(k)); g = rd(k); g2 = rd(k)
    print('   word %3d  wrote 0x%08x  read 0x%08x  read again 0x%08x  %s' % (k, val(k), g, g2, 'ok' if g == val(k) else 'WRONG'))
print('\n== 2  all %d words, one request at a time' % N)
for k in range(N): wr(k, val(k))
bad = []
for k in range(N):
    g = rd(k)
    if g != val(k): bad.append((k, g))
print('%d of %d words wrong' % (len(bad), N))
w0 = val(0)
print('   of the wrong ones, %d returned word 0\'s value' % sum(1 for k, g in bad if g == w0))
for k, g in bad[:8]: print('   word %3d  wrote 0x%08x  read 0x%08x' % (k, val(k), g))
print('RESULT:', 'spaced requests work' if not bad else 'still wrong with spaced requests')
