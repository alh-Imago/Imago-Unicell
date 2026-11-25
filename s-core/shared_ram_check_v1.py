#!/usr/bin/env python3
"""shared_ram_check_v1.py - look at one block's SHARED data RAM through the host commands M (write) and L (read), the same ones scblocks.py uses.  Ledger #1476.
Why: the Vivado-built 8x4 returns status 8 / n_out 8 / result 8 where the open-tool build returns 1 / 1 / 10, and the far RAM image is identical except those three words
(far_dump_v1.py).  Those three words are copied out of the block's shared RAM after the job.  Two questions: (1) does the shared RAM still hold the job's real answer
(then the copy-out is what is wrong), and (2) does the shared RAM store and return data correctly through the host path.
Two modes (card loaded, openOCD on the path, run from s-core):
  dump     READ ONLY.  Run it right AFTER scblocks.py ran a job; prints words START..START+COUNT-1 of block BLK's shared RAM.
           nix shell nixpkgs#openocd --command python3 shared_ram_check_v1.py jtag dump 0 0 40 > shared_NAME.txt
  pattern  WRITES the shared RAM of block BLK (words START..), four patterns, reads every word back, compares.  Do this on a card that is not about to run a job
           (a job run writes its own window again, so nothing is lost).
           nix shell nixpkgs#openocd --command python3 shared_ram_check_v1.py jtag pattern 0 0 256
Arguments: PORT MODE BLK START COUNT."""
import sys, collections
import host_sc as hs
port = sys.argv[1] if len(sys.argv) > 1 else 'jtag'
mode = sys.argv[2] if len(sys.argv) > 2 else 'dump'
blk = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0
start = int(sys.argv[4], 0) if len(sys.argv) > 4 else 0
count = int(sys.argv[5], 0) if len(sys.argv) > 5 else 40
b = hs.Board(port)
print('# board version', b.version(), ' block', blk, ' shared RAM words', start, '..', start + count - 1, ' mode', mode)
b.s.write(hs.cmd_O(blk)); b.s.flush()
if mode == 'dump':
    words = b.shared_read(start, count)
    for i, w in enumerate(words): print('%4d  0x%08x  %d' % (start + i, w, w))
elif mode == 'pattern':
    pats = {
     'A (word = index)':     lambda a, i: a & 0xFFFFFFFF,
     'B (one bit walks)':    lambda a, i: (1 << (i % 32)) & 0xFFFFFFFF,
     'C (complement)':       lambda a, i: (~a) & 0xFFFFFFFF,
     'D (ones / zeros)':     lambda a, i: 0xFFFFFFFF if i % 2 == 0 else 0,
    }
    bitdiff = collections.Counter(); total_bad = 0
    for name, f in pats.items():
        exp = [f(start + i, i) for i in range(count)]
        b.shared_write(start, exp)
        got = b.shared_read(start, count)
        bad = [(start + i, exp[i], got[i]) for i in range(count) if got[i] != exp[i]]
        total_bad += len(bad)
        for i in range(count):
            for k in range(32):
                if ((got[i] ^ exp[i]) >> k) & 1: bitdiff[k] += 1
        print('%-22s %d of %d words wrong' % (name, len(bad), count))
        for a, e, g in bad[:4]: print('    word %d wrote 0x%08x read 0x%08x  xor 0x%08x' % (a, e, g, e ^ g))
    print('data bits that ever differed (bit: count):', dict(sorted(bitdiff.items())) if bitdiff else 'none')
    print('RESULT:', 'shared RAM host path OK' if total_bad == 0 else '%d wrong words' % total_bad)
else:
    print('mode must be dump or pattern'); sys.exit(2)
