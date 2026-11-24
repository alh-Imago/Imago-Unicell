#!/usr/bin/env python3
"""far_ram_check_v1.py - write a known pattern into the card's far RAM through the host commands (the same ones scblocks.py uses), read every word back and compare.
Separates "the far RAM stores or returns data wrongly" from "the jobs compute wrongly".  Writes ONLY the far RAM (addresses 0x2000 upward by default), nothing else.
Usage (card loaded, openOCD on the path):  nix shell nixpkgs#openocd --command python3 far_ram_check_v1.py jtag [START] [COUNT]
Patterns per word: A = address, B = bit-walk (one set bit), C = complement of the address, D = 0xFFFFFFFF/0x00000000 alternating.  Prints per-pattern mismatch counts,
the first mismatches, and which of the 32 data bits ever differed (a stuck or swapped bit lane shows up there)."""
import sys, collections
import host_sc as hs, sdt_host as H
port = sys.argv[1] if len(sys.argv) > 1 else 'jtag'
start = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x2000
count = int(sys.argv[3], 0) if len(sys.argv) > 3 else 512
b = hs.Board(port)
print('board version', b.version())
def put(c): b.s.write(c)
def rd(a):
    put(hs.cmd_O(0)); put(H.c_r(a)); b.s.flush()
    return H.dec_r(b._rd(4))
pats = {
 'A (word = address)':     lambda a, i: a & 0xFFFFFFFF,
 'B (one bit walks)':      lambda a, i: (1 << (i % 32)) & 0xFFFFFFFF,
 'C (complement of addr)': lambda a, i: (~a) & 0xFFFFFFFF,
 'D (all ones / zeros)':   lambda a, i: 0xFFFFFFFF if i % 2 == 0 else 0,
}
bitdiff = collections.Counter(); total_bad = 0
put(hs.cmd_O(0))
for name, f in pats.items():
    exp = {}
    for i in range(count):
        a = start + i; exp[a] = f(a, i); put(H.c_w(a, exp[a]))
    b.s.flush()
    bad = []
    for a in sorted(exp):
        got = rd(a)
        if got != exp[a]: bad.append((a, exp[a], got))
        for k in range(32):
            if ((got ^ exp[a]) >> k) & 1: bitdiff[k] += 1
    total_bad += len(bad)
    print('%-26s %d of %d words wrong' % (name, len(bad), count))
    for a, e, g in bad[:4]: print('    addr 0x%x wrote 0x%08x read 0x%08x  xor 0x%08x' % (a, e, g, e ^ g))
print('data bits that ever differed (bit: count):', dict(sorted(bitdiff.items())) if bitdiff else 'none')
print('RESULT:', 'far RAM stores and returns every pattern correctly' if total_bad == 0 else 'far RAM MISMATCHES: %d words' % total_bad)
