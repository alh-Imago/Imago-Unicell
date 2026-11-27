"""Pool-level gate for sc_sys_v21 (ledger #1514, clone of test_sys18 with the alone sweep up to lw 5): tasks submitted with widths 0..ULW on a block with one fusion unit.
Every task's a0 must equal the instruction-set simulator's x10, no trap; reports the clocks per task (end - start).
Usage: python3 test_sys21.py [S] [ULW] [FZ] [NU]"""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import runtests as R
S = int(sys.argv[1]) if len(sys.argv) > 1 else 8
ULW = int(sys.argv[2]) if len(sys.argv) > 2 else 2
FZ = int(sys.argv[3]) if len(sys.argv) > 3 else 1
NU = int(sys.argv[4]) if len(sys.argv) > 4 else 2
W = 1 << ULW
wd = '/tmp/sys21p_S%d_U%d_F%d_N%d' % (S, ULW, FZ, NU); os.makedirs(wd, exist_ok=True)
srcs = ['tb_sys21.v', 'sc_sys_v21.v', 'fit_search_tree.v', 'uc_core_v2v.v', 'uc_unitw%d.v' % W, 'uc_unith%d.v' % W]
r = subprocess.run(['iverilog', '-g2012', '-P', 'tb_sys21.S=%d' % S, '-P', 'tb_sys21.ULW=%d' % ULW, '-P', 'tb_sys21.FZ=%d' % FZ, '-P', 'tb_sys21.NU=%d' % NU, '-o', wd + '/sim'] + [os.path.join(HERE, f) for f in srcs], capture_output=True, text=True)
if r.returncode: print(r.stderr[-2000:]); sys.exit(1)
EPI = {'fib': 'mv a0, t1', 'crc32': 'mv a0, s2'}      # make the result visible in a0 (the pool returns a0)
def prog_text(n):
    t = R.PROGRAMS[n]
    if n in EPI:
        k = t.rindex('ebreak'); t = t[:k] + EPI[n] + '\n    ' + t[k:]
    return t
SHSUM = '''
    lui t0, 0x10
    li t1, 0
    li t2, 0
    li t3, 64
L: add t4, t0, t2
    lw t5, 0(t4)
    add t1, t1, t5
    addi t2, t2, 4
    bne t2, t3, L
    sw t1, 80(t0)
    lw a0, 80(t0)
    ebreak
'''
R.PROGRAMS['shsum'] = SHSUM      # reads shared words 0..15 (3i+1), stores the sum in shared word 20, reads it back into a0
PSTORE = '''
    li t0, 0
    li t1, 0x12345678
    li t2, 0x0f0f0f0f
    li t3, 0x7edcba98
    sw t1, 0(t0)
    sw t2, 4(t0)
    sw t3, 8(t0)
    lw t4, 0(t0)
    lw t5, 4(t0)
    lw t6, 8(t0)
    xor a0, t4, t5
    add a0, a0, t6
    ebreak
'''
R.PROGRAMS['pstore'] = PSTORE
names = ['pstore']
img = []; base = {}
for n in names:
    base[n] = len(img); img += R.assemble(prog_text(n))
exp = {n: (376 if n == 'shsum' else R.iss(R.assemble(prog_text(n)))['x'][10] & 0xFFFFFFFF) for n in names}
open(wd + '/prog.hex', 'w').write('\n'.join('%08x' % w for w in img) + '\n')
def run(tasks, tag):
    open(wd + '/tasks.hex', 'w').write('\n'.join('%08x\n%08x\n%08x' % (0, base[n], lw) for n, lw in tasks) + '\n')
    o = subprocess.run(['vvp', wd + '/sim', '+prog=' + wd + '/prog.hex', '+tasks=' + wd + '/tasks.hex', '+ntasks=%d' % len(tasks), '+out=' + wd + '/out.txt'], capture_output=True, text=True)
    L = open(wd + '/out.txt').read().splitlines(); done = L[0].split()
    shm = {int(l.split()[1]): int(l.split()[2]) for l in L if l.startswith('m ')}
    if any(n == 'shsum' for n, _ in tasks) and shm.get(20) != 376: print('  FAIL', tag, 'shared word 20 =', shm.get(20)); return 1, []
    t = [l.split() for l in L if l.startswith('t ')]
    bad = 0; rows = []
    for (n, lw), tt in zip(tasks, t):
        a0, trap, cause, st, en, sl = [int(x) for x in tt[2:8]]
        ok = a0 == exp[n] and trap == 0
        bad += not ok
        rows.append((n, lw, en - st, sl))
        if not ok: print('  FAIL', tag, n, 'lw', lw, 'a0', hex(a0), 'expect', hex(exp[n]), 'trap', trap, 'cause', cause)
    if int(done[1]) != len(tasks) or int(done[3]) != 0: bad += 1; print('  FAIL', tag, 'done', done)
    return bad, rows
total = 0
# 1. each program alone at each width
print('alone (clocks per task):')
tab = {}
for n in names:
    line = []
    for lw in range(0, min(5, S.bit_length() - 1) + 1):
        b, rows = run([(n, lw)], 'alone'); total += b; line.append(rows[0][2])
    tab[n] = line
    print('  %-12s lw0..5: %s' % (n, line))

print('RESULT PASS' if total == 0 else 'RESULT FAIL %d' % total)
