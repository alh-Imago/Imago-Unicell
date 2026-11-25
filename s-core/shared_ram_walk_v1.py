#!/usr/bin/env python3
"""shared_ram_walk_v1.py - find out HOW one block's shared RAM goes wrong (ledger #1477), through the host commands M (write) and L (read).  Writes ONLY that block's shared RAM.
shared_ram_check_v1.py says that words come back wrong; this says where each wrong word came from.  Three tests, all on block BLK, words 0..N-1:
  1  unique values: word i gets a value that is different for every i and has no simple bit pattern (a scrambled index).  Then every word is read back, and each wrong
     one is looked up among the written values: "came from word j" (address aliasing / swap), or "no match" (data bits altered), or "zero / old".
  2  read twice: every word is read two times in a row; reports words where the two reads differ (a read that depends on the previous read = pipeline / stale data).
  3  single write: the RAM is cleared, then ONE word k is written (for k in a few addresses incl. powers of two) and the whole RAM is read: reports which addresses show the value.
Usage (card loaded, openOCD on the path, run from s-core):   nix shell nixpkgs#openocd --command python3 shared_ram_walk_v1.py jtag [BLK] [N]       default BLK 0, N 256"""
import sys
import host_sc as hs
port = sys.argv[1] if len(sys.argv) > 1 else 'jtag'
blk = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
N = int(sys.argv[3], 0) if len(sys.argv) > 3 else 256
b = hs.Board(port)
print('# board version', b.version(), ' block', blk, ' words', N)
b.s.write(hs.cmd_O(blk)); b.s.flush()
M32 = 0xFFFFFFFF
def val(i): return ((i * 0x9E3779B1) ^ 0x5A5A1234 ^ (i << 20)) & M32 or 1     # scrambled, nonzero, unique for i < 4096 (checked below)
vals = [val(i) for i in range(N)]
assert len(set(vals)) == N, 'values not unique'
where = {v: i for i, v in enumerate(vals)}

print('\n== 1  unique values')
b.shared_write(0, vals)
got = b.shared_read(0, N)
bad = [(i, got[i]) for i in range(N) if got[i] != vals[i]]
print('%d of %d words wrong' % (len(bad), N))
kinds = {'came from another word': 0, 'zero': 0, 'no match': 0}
shown = 0
for i, g in bad:
    if g in where: kinds['came from another word'] += 1; note = 'is the value written to word %d  (xor of the two addresses 0x%x)' % (where[g], i ^ where[g])
    elif g == 0: kinds['zero'] += 1; note = 'zero'
    else: kinds['no match'] += 1; note = 'matches no written word  (xor with the right value 0x%08x)' % (g ^ vals[i])
    if shown < 16: print('   word %3d  read 0x%08x  %s' % (i, g, note)); shown += 1
print('wrong words by kind:', kinds)

print('\n== 2  read twice')
diff2 = 0
for i in range(0, N):
    r = b.shared_read(i, 1)[0]; r2 = b.shared_read(i, 1)[0]
    if r != r2:
        diff2 += 1
        if diff2 <= 8: print('   word %3d  first read 0x%08x  second read 0x%08x' % (i, r, r2))
print('%d of %d words changed between two reads in a row' % (diff2, N))

print('\n== 3  single write into a cleared RAM')
b.shared_write(0, [0] * N)
cl = b.shared_read(0, N)
print('after clearing: %d words not zero' % sum(1 for x in cl if x))
ks = sorted(set([0, 1, 2, 3, 4, 8, 16, 32, 64, 128, N - 1]) & set(range(N)))
for k in ks:
    b.shared_write(0, [0] * N)
    b.shared_write(k, [0xC0DE0001])
    r = b.shared_read(0, N)
    hits = [i for i in range(N) if r[i] == 0xC0DE0001]
    other = [(i, r[i]) for i in range(N) if r[i] not in (0, 0xC0DE0001)]
    print('   wrote word %3d -> value seen at words %s%s' % (k, hits if len(hits) <= 8 else '%s ... (%d words)' % (hits[:8], len(hits)), ('   other non-zero: ' + str(other[:4])) if other else ''))
