"""Pool-level gate for sc_sys_v23 (ledger #1584): the memory-mapped multiply unit.  Programs store operands A and B to the device window (byte 0x20000, +0, +4) and load the product (+8).
Checks: with MULU=1 every product equals (A*B) mod 2^32 (Python), at every width, alone and with other tasks (several slices multiplying at once, different operands);
with MULU=0 the same programs trap (cause 2) and ordinary programs still pass; ordinary programs pass with MULU=1 too.
Usage: python3 test_sys23.py [S] [ULW] [FZ] [NU]"""
import os, sys, subprocess, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import runtests as R
S = int(sys.argv[1]) if len(sys.argv) > 1 else 8
ULW = int(sys.argv[2]) if len(sys.argv) > 2 else 2
FZ = int(sys.argv[3]) if len(sys.argv) > 3 else 1
NU = int(sys.argv[4]) if len(sys.argv) > 4 else 2
W = 1 << ULW
M32 = 0xFFFFFFFF
def build(mulu):
    wd = '/tmp/sys23_S%d_U%d_F%d_N%d_M%d' % (S, ULW, FZ, NU, mulu); os.makedirs(wd, exist_ok=True)
    srcs = ['tb_sys23.v', 'sc_sys_v23.v', 'fit_search_tree.v', 'uc_core_v2v.v', 'uc_unitw%d.v' % W, 'uc_unith%d.v' % W]
    r = subprocess.run(['iverilog', '-g2012', '-P', 'tb_sys23.S=%d' % S, '-P', 'tb_sys23.ULW=%d' % ULW, '-P', 'tb_sys23.FZ=%d' % FZ, '-P', 'tb_sys23.NU=%d' % NU, '-P', 'tb_sys23.MULU=%d' % mulu, '-o', wd + '/sim'] + [os.path.join(HERE, f) for f in srcs], capture_output=True, text=True)
    if r.returncode: print(r.stderr[-2000:]); sys.exit(1)
    return wd
def mul_prog(a, b, n=1):
    # n multiplies in a row: acc = a*b, then acc = acc*b, ...; the result is returned in a0
    t = '    lui t0, 0x20\n    li t2, %d\n    li t3, %d\n    li a0, 0\n' % (a - (1 << 32) if a >> 31 else a, b - (1 << 32) if b >> 31 else b)
    t += '    sw t2, 0(t0)\n    sw t3, 4(t0)\n    lw a0, 8(t0)\n'
    for _ in range(n - 1): t += '    sw a0, 0(t0)\n    sw t3, 4(t0)\n    lw a0, 8(t0)\n'
    return t + '    ebreak\n'
def exp_mul(a, b, n=1):
    x = (a * b) & M32
    for _ in range(n - 1): x = (x * b) & M32
    return x
LIB = open(os.path.join(HERE, 'jobio', 'lib_mul_unit.s')).read().replace('  ret', '  jalr zero, ra, 0')     # the test assembler has no ret pseudo-op (sclink expands it the same way)
def lib_prog(a, b):
    # the real library routine (jobio/lib_mul_unit.s, as linked into jobs) called with jal; the result is returned in a0
    sx = lambda v: v - (1 << 32) if v >> 31 else v
    return '    li a0, %d\n    li a1, %d\n    jal ra, lib_mul32\n    ebreak\n' % (sx(a), sx(b)) + LIB
BAD_LOAD = '    lui t0, 0x20\n    lw a0, 0(t0)\n    ebreak\n'       # load from the operand-A word: traps
BAD_STORE = '    lui t0, 0x20\n    li t1, 5\n    sw t1, 8(t0)\n    ebreak\n'   # store to the product word: traps
BAD_WORD3 = '    lui t0, 0x20\n    lw a0, 12(t0)\n    ebreak\n'
CASES = [(3, 5, 1), (0xFFFFFFFF, 0xFFFFFFFF, 1), (123456789, 987654321, 1), (0x80000000, 2, 1), (7, 0, 1), (0xDEADBEEF, 0x12345, 3), (1, 1, 1), (65535, 65537, 1)]
random.seed(23)
CASES += [(random.getrandbits(32), random.getrandbits(32), random.choice([1, 1, 2])) for _ in range(8)]
progs = {}; exp = {}; base = {}; img = []
for i, (a, b, n) in enumerate(CASES):
    nm = 'mul%d' % i; progs[nm] = mul_prog(a, b, n); exp[nm] = exp_mul(a, b, n)
for i, (a, b) in enumerate([(3, 5), (0xFFFFFFFF, 0xFFFFFFFF), (0x12345678, 0x9ABCDEF0), (1 << 31, 3)]):
    progs['lib%d' % i] = lib_prog(a, b); exp['lib%d' % i] = (a * b) & M32
for nm, tx in (('badload', BAD_LOAD), ('badstore', BAD_STORE), ('badword3', BAD_WORD3)): progs[nm] = tx
for nm in ('sum100', 'fib', 'crc32', 'softmul_gcd'):
    progs[nm] = R.PROGRAMS[nm]
    if nm in ('fib', 'crc32'):
        t = progs[nm]; k = t.rindex('ebreak'); progs[nm] = t[:k] + ('mv a0, t1' if nm == 'fib' else 'mv a0, s2') + '\n    ' + t[k:]
    exp[nm] = R.iss(R.assemble(progs[nm]))['x'][10] & M32
for nm, tx in progs.items(): base[nm] = len(img); img += R.assemble(tx)
def run(wd, tasks, tag, mulu):
    open(wd + '/prog.hex', 'w').write('\n'.join('%08x' % w for w in img) + '\n')
    open(wd + '/tasks.hex', 'w').write('\n'.join('%08x\n%08x\n%08x' % (0, base[n], lw) for n, lw in tasks) + '\n')
    subprocess.run(['vvp', wd + '/sim', '+prog=' + wd + '/prog.hex', '+tasks=' + wd + '/tasks.hex', '+ntasks=%d' % len(tasks), '+out=' + wd + '/out.txt'], capture_output=True, text=True)
    L = open(wd + '/out.txt').read().splitlines(); done = L[0].split()
    t = [l.split() for l in L if l.startswith('t ')]
    bad = 0; rows = []
    for (n, lw), tt in zip(tasks, t):
        a0, trap, cause, st, en, sl = [int(x) for x in tt[2:8]]
        isbad = n.startswith('bad') or ((n.startswith('mul') or n.startswith('lib')) and not mulu)
        ok = (trap == 1 and cause == 2) if isbad else (a0 == exp[n] and trap == 0)
        bad += not ok; rows.append((n, lw, en - st))
        if not ok: print('  FAIL', tag, n, 'lw', lw, 'a0', hex(a0), 'expect', hex(exp.get(n, 0)), 'trap', trap, 'cause', cause)
    if int(done[1]) != len(tasks) or int(done[3]) != 0: bad += 1; print('  FAIL', tag, 'done', done)
    return bad, rows
total = 0
for mulu in (1, 0):
    wd = build(mulu); print('MULU=%d (S=%d ULW=%d FZ=%d NU=%d)' % (mulu, S, ULW, FZ, NU))
    for lw in range(0, min(ULW, S.bit_length() - 1) + 1):
        tasks = [('mul%d' % i, lw) for i in range(len(CASES))]
        b, rows = run(wd, tasks, 'one-by-one lw%d' % lw, mulu); total += b
        print('  lw %d, %d multiply tasks together: %s  clocks %s' % (lw, len(tasks), 'ok' if b == 0 else 'FAIL', [c for _, _, c in rows][:6]))
    allt = [('mul%d' % i, 0) for i in range(len(CASES))] + [('lib%d' % i, 0) for i in range(4)] + [(n, 0) for n in ('sum100', 'fib', 'crc32', 'softmul_gcd', 'badload', 'badstore', 'badword3')] * 2
    random.shuffle(allt)
    b, rows = run(wd, allt, 'mixed', mulu); total += b; print('  mixed with ordinary and trapping tasks:', 'ok' if b == 0 else 'FAIL')
    for n in ('badload', 'badstore', 'badword3'):
        b, rows = run(wd, [(n, 0)], n, mulu); total += b
    for lw in range(0, min(ULW, S.bit_length() - 1) + 1):
        b, rows = run(wd, [('mul5', lw)], 'alone', mulu); total += b
        print('  alone lw %d: mul5 clocks %d' % (lw, rows[0][2]))
print('RESULT', 'PASS' if total == 0 else 'FAIL (%d)' % total); sys.exit(0 if total == 0 else 1)
