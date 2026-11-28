"""Pool-level gate for sc_sys_v26 (ledger #1595, clone of test_sys25.py): the multiply unit with the high half (MULU 2) as before, plus byte and halfword LOADS (lb lh lbu lhu) on unfused tasks, in the shared window and in private memory; narrow loads in the device window and by fused tasks must trap.  Programs store operands A and B to the device window (byte 0x20000, +0, +4) and load the product (+8).
Checks: with MULU=1 every product equals (A*B) mod 2^32 (Python), at every width, alone and with other tasks (several slices multiplying at once, different operands);
with MULU=0 the same programs trap (cause 2) and ordinary programs still pass; ordinary programs pass with MULU=1 too.
Usage: python3 test_sys26.py [S] [ULW] [FZ] [NU]"""
import os, sys, subprocess, random, re
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
    srcs = ['tb_sys26.v', 'sc_sys_v26.v', 'fit_search_tree_v2.v', 'uc_core_v2w.v', 'uc_unitw%d.v' % W, 'uc_unith%d.v' % W]
    r = subprocess.run(['iverilog', '-g2012', '-P', 'tb_sys26.S=%d' % S, '-P', 'tb_sys26.ULW=%d' % ULW, '-P', 'tb_sys26.FZ=%d' % FZ, '-P', 'tb_sys26.NU=%d' % NU, '-P', 'tb_sys26.MULU=%d' % mulu, '-o', wd + '/sim'] + [os.path.join(HERE, f) for f in srcs], capture_output=True, text=True)
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
def hi_prog(a, b, both=False):
    sx = lambda v: v - (1 << 32) if v >> 31 else v
    t = '    lui t0, 0x20\n    li t2, %d\n    li t3, %d\n    sw t2, 0(t0)\n    sw t3, 4(t0)\n' % (sx(a), sx(b))
    t += ('    lw t4, 8(t0)\n    lw a0, 12(t0)\n    xor a0, a0, t4\n' if both else '    lw a0, 12(t0)\n') + '    ebreak\n'
    return t
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
HCASES = [(3, 5), (0xFFFFFFFF, 0xFFFFFFFF), (0x12345678, 0x9ABCDEF0), (0x80000000, 2), (0x80000000, 0x80000000), (1, 1), (65535, 65537), (0xFFFFFFFF, 2), (0xDEADBEEF, 0xCAFEBABE)] + [(random.getrandbits(32), random.getrandbits(32)) for _ in range(8)]
for i, (a, b) in enumerate(HCASES):
    progs['hi%d' % i] = hi_prog(a, b); exp['hi%d' % i] = ((a * b) >> 32) & M32
    progs['hb%d' % i] = hi_prog(a, b, True); exp['hb%d' % i] = (((a * b) & M32) ^ ((a * b) >> 32)) & M32
for nm, tx in (('badload', BAD_LOAD), ('badstore', BAD_STORE), ('badword3', BAD_WORD3)): progs[nm] = tx
for nm in ('sum100', 'fib', 'crc32', 'softmul_gcd'):
    progs[nm] = R.PROGRAMS[nm]
    if nm in ('fib', 'crc32'):
        t = progs[nm]; k = t.rindex('ebreak'); progs[nm] = t[:k] + ('mv a0, t1' if nm == 'fib' else 'mv a0, s2') + '\n    ' + t[k:]
    exp[nm] = R.iss(R.assemble(progs[nm]))['x'][10] & M32
NARROW = {'lb': 0, 'lh': 1, 'lbu': 4, 'lhu': 5}
def asmx(text):
    # the test assembler has no lb/lh/lbu/lhu: assemble them as lw, then set the f3 field of the n-th load word
    kinds = []; out = []
    for line in text.splitlines():
        m = re.match(r'\s*(lb|lh|lbu|lhu)\s', line)
        if m: kinds.append(NARROW[m.group(1)]); line = re.sub(r'\b(lb|lh|lbu|lhu)\b', 'lw', line, count=1)
        elif re.match(r'\s*lw\s', line): kinds.append(2)
        out.append(line)
    words = R.assemble('\n'.join(out)); k = 0
    for i, w in enumerate(words):
        if (w & 0x7F) == 0x03: words[i] = (w & ~(7 << 12)) | (kinds[k] << 12); k += 1
    return words
def narrow_exp(op, word, off):
    if op in ('lb', 'lbu'):
        v = (word >> (8 * (off & 3))) & 0xFF
        return (v if op == 'lbu' or v < 0x80 else v | 0xFFFFFF00) & M32
    v = (word >> (16 * ((off >> 1) & 1))) & 0xFFFF
    return (v if op == 'lhu' or v < 0x8000 else v | 0xFFFF0000) & M32
def narrow_prog(op, word, off, base):
    sx = lambda v: v - (1 << 32) if v >> 31 else v
    return '    li t0, %d\n    li t1, %d\n    sw t1, 0(t0)\n    %s a0, %d(t0)\n    ebreak\n' % (base, sx(word), op, off)
NCASES = []
random.seed(31)
for dbase, tag in ((0x10000, 's'), (0x40, 'p')):
    for op, offs in (('lb', (0, 1, 2, 3)), ('lbu', (0, 1, 2, 3)), ('lh', (0, 2)), ('lhu', (0, 2))):
        for off in offs:
            for word in (0x80FF7F01, random.getrandbits(32)):   # 48 tasks: the testbench takes at most 64
                nm = 'nl%s%d' % (tag, len(NCASES)); NCASES.append(nm)
                progs[nm] = narrow_prog(op, word, off, dbase + (4 * len(NCASES) if tag == 's' else 0)); exp[nm] = narrow_exp(op, word, off)
progs['badnarrowdev'] = '    lui t0, 0x20\n    lb a0, 8(t0)\n    ebreak\n'
for nm, tx in progs.items(): base[nm] = len(img); img += asmx(tx)
def run(wd, tasks, tag, mulu):
    open(wd + '/prog.hex', 'w').write('\n'.join('%08x' % w for w in img) + '\n')
    open(wd + '/tasks.hex', 'w').write('\n'.join('%08x\n%08x\n%08x' % (0, base[n], lw) for n, lw in tasks) + '\n')
    subprocess.run(['vvp', wd + '/sim', '+prog=' + wd + '/prog.hex', '+tasks=' + wd + '/tasks.hex', '+ntasks=%d' % len(tasks), '+out=' + wd + '/out.txt'], capture_output=True, text=True)
    L = open(wd + '/out.txt').read().splitlines(); done = L[0].split()
    t = [l.split() for l in L if l.startswith('t ')]
    bad = 0; rows = []
    for (n, lw), tt in zip(tasks, t):
        a0, trap, cause, st, en, sl = [int(x) for x in tt[2:8]]
        isbad = (n.startswith('bad') and not (n == 'badword3' and mulu >= 2)) or ((n.startswith('mul') or n.startswith('lib')) and not mulu) or ((n.startswith('hi') or n.startswith('hb') or n == 'badword3') and mulu < 2)
        ok = (trap == 1 and cause == 2) if isbad else (trap == 0 if (n == 'badword3') else (a0 == exp[n] and trap == 0))   # MULU 2: +12 is a valid load (its value is whatever was last multiplied), so only 'no trap' is checked
        bad += not ok; rows.append((n, lw, en - st))
        if not ok: print('  FAIL', tag, n, 'lw', lw, 'a0', hex(a0), 'expect', hex(exp.get(n, 0)), 'trap', trap, 'cause', cause)
    if int(done[1]) != len(tasks) or int(done[3]) != 0: bad += 1; print('  FAIL', tag, 'done', done)
    return bad, rows
total = 0
for mulu in (2, 1, 0):
    wd = build(mulu); print('MULU=%d (S=%d ULW=%d FZ=%d NU=%d)' % (mulu, S, ULW, FZ, NU))
    for lw in range(0, min(ULW, S.bit_length() - 1) + 1):
        tasks = [('mul%d' % i, lw) for i in range(len(CASES))]
        b, rows = run(wd, tasks, 'one-by-one lw%d' % lw, mulu); total += b
        print('  lw %d, %d multiply tasks together: %s  clocks %s' % (lw, len(tasks), 'ok' if b == 0 else 'FAIL', [c for _, _, c in rows][:6]))
    for lw in range(0, min(ULW, S.bit_length() - 1) + 1):
        tasks = [('hi%d' % i, lw) for i in range(len(HCASES))] + [('hb%d' % i, lw) for i in range(len(HCASES))]
        b, rows = run(wd, tasks, 'high half lw%d' % lw, mulu); total += b
        print('  lw %d, %d high-half tasks together (%s): %s' % (lw, len(tasks), 'must trap' if mulu < 2 else 'low and high halves', 'ok' if b == 0 else 'FAIL'))
    for lw in range(0, min(ULW, S.bit_length() - 1) + 1):
        tasks = [(n, lw) for n in NCASES]
        if lw == 0:
            b, rows = run(wd, tasks, 'narrow loads lw0', mulu); total += b
            print('  lw 0, %d narrow-load tasks together: %s' % (len(tasks), 'ok' if b == 0 else 'FAIL'))
    b, rows = run(wd, [('badnarrowdev', 0)], 'narrow load in the device window', mulu); total += b
    print('  lb from the device window must trap: %s' % ('ok' if b == 0 else 'FAIL'))
    allt = [('hi%d' % i, 0) for i in range(len(HCASES))] + [('hb%d' % i, 0) for i in range(4)] + [('mul%d' % i, 0) for i in range(len(CASES))] + [('lib%d' % i, 0) for i in range(4)] + [(n, 0) for n in ('sum100', 'fib', 'crc32', 'softmul_gcd', 'badload', 'badstore', 'badword3')] * 2
    random.shuffle(allt)
    b, rows = run(wd, allt, 'mixed', mulu); total += b; print('  mixed with ordinary and trapping tasks:', 'ok' if b == 0 else 'FAIL')
    for n in ('badload', 'badstore', 'badword3'):
        b, rows = run(wd, [(n, 0)], n, mulu); total += b
    for lw in range(0, min(ULW, S.bit_length() - 1) + 1):
        b, rows = run(wd, [('mul5', lw)], 'alone', mulu); total += b
        print('  alone lw %d: mul5 clocks %d' % (lw, rows[0][2]))
print('RESULT', 'PASS' if total == 0 else 'FAIL (%d)' % total); sys.exit(0 if total == 0 else 1)
