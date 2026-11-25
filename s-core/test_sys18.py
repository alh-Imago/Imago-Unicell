"""Pool-level gate for sc_sys_v18 (ledger #1378): tasks submitted with widths 0..ULW on a block with one fusion unit.
Every task's a0 must equal the instruction-set simulator's x10, no trap; reports the clocks per task (end - start).
Usage: python3 test_sys18.py [S] [ULW] [FZ] [NU]"""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import runtests as R
S = int(sys.argv[1]) if len(sys.argv) > 1 else 8
ULW = int(sys.argv[2]) if len(sys.argv) > 2 else 2
FZ = int(sys.argv[3]) if len(sys.argv) > 3 else 1
NU = int(sys.argv[4]) if len(sys.argv) > 4 else 2
W = 1 << ULW
wd = '/tmp/sys18_S%d_U%d_F%d_N%d' % (S, ULW, FZ, NU); os.makedirs(wd, exist_ok=True)
srcs = ['tb_sys18.v', 'sc_sys_v18.v', 'fit_search_tree.v', 'uc_core_v2v.v', 'uc_unitw%d.v' % W, 'uc_unith%d.v' % W]
r = subprocess.run(['iverilog', '-g2012', '-P', 'tb_sys18.S=%d' % S, '-P', 'tb_sys18.ULW=%d' % ULW, '-P', 'tb_sys18.FZ=%d' % FZ, '-P', 'tb_sys18.NU=%d' % NU, '-o', wd + '/sim'] + [os.path.join(HERE, f) for f in srcs], capture_output=True, text=True)
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
names = ['shsum', 'sum100', 'fib', 'crc32', 'softmul_gcd', 'shifts_signs']
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
    for lw in range(0, min(4, S.bit_length() - 1) + 1):
        b, rows = run([(n, lw)], 'alone'); total += b; line.append(rows[0][2])
    tab[n] = line
    print('  %-12s lw0..4: %s' % (n, line))
# 2. a wide task together with narrow ones, and two wide at once (NU units: the next ones run unfused)
for tag, tasks in [('mix1', [('shsum', 1), ('crc32', 2), ('sum100', 0), ('fib', 0), ('softmul_gcd', 0), ('shifts_signs', 0)]),
                   ('two wide', [('shsum', 2), ('crc32', 2), ('fib', 2), ('sum100', 1), ('crc32', 0)]),
                   ('many', [(names[i % 6], i % (min(3, S.bit_length() - 1) + 1)) for i in range(24)])]:
    b, rows = run(tasks, tag); total += b
    print('%-9s %s' % (tag, ' '.join('%s/%d:%d' % (n[:4], lw, c) for n, lw, c, _ in rows)))
print('RESULT', 'PASS' if total == 0 else 'FAIL (%d)' % total); sys.exit(0 if total == 0 else 1)
