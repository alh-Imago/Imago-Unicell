#!/usr/bin/env python3
"""far_dump_v1.py - READ-ONLY dump of the card's far RAM (no writes of any kind), to compare what two different bitstreams left there after the same job.
Run it right AFTER scblocks.py ran a job (the board keeps the far RAM until it is loaded again).  Reads the same way far_ram_check_v1.py does (cmd_O + c_r).
Usage (card loaded, a job just run, openOCD on the path):
    nix shell nixpkgs#openocd --command python3 far_dump_v1.py jtag 0x2000 128 > dump_NAME.txt
Prints one line per word: address, hex, decimal.  Then compare two files with:   diff dump_open.txt dump_vivado.txt
(the code image and job data are identical in both runs; the words that differ are what the two netlists produced).
Written for ledger #1476 (the Vivado-built 8x4 gives status 8 / result 8 where the open-tool build gives status 1 / result 10)."""
import sys
import host_sc as hs, sdt_host as H
port = sys.argv[1] if len(sys.argv) > 1 else 'jtag'
start = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x2000
count = int(sys.argv[3], 0) if len(sys.argv) > 3 else 128
b = hs.Board(port)
print('# board version', b.version(), ' far RAM 0x%x .. 0x%x' % (start, start + count - 1))
def put(c): b.s.write(c)
def rd(a):
    put(hs.cmd_O(0)); put(H.c_r(a)); b.s.flush()
    return H.dec_r(b._rd(4))
for i in range(count):
    a = start + i
    v = rd(a)
    print('0x%05x  0x%08x  %d' % (a, v, v))
