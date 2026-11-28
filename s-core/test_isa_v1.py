"""test_isa_v1.py - what the S-Core core runs, checked on the RTL (ledger #1587).  Every legal instruction of the core (read from uc_core_v2v.v) is run on the pool simulation (sc_sys_v22, S=4, one fusion unit)
at lw 0 (the plain core) and lw 2 (the fusion unit's lanes), with edge operands; the answer is computed here in Python from the RISC-V definition, NOT from the project's ISS.
Instructions the core refuses must stop the task with the trap flag set.  Usage: python3 test_isa_v1.py"""
import os, sys, subprocess, itertools
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import runtests as R
M = 0xFFFFFFFF
sx = lambda v: v - (1 << 32) if v >> 31 else v
S, ULW = 4, 2
wd = '/tmp/isa_v1'; os.makedirs(wd, exist_ok=True)
srcs = ['tb_sys22.v', 'sc_sys_v22.v', 'fit_search_tree.v', 'uc_core_v2v.v', 'uc_unitw4.v', 'uc_unith4.v']
r = subprocess.run(['iverilog', '-g2012', '-P', 'tb_sys22.S=%d' % S, '-P', 'tb_sys22.ULW=%d' % ULW, '-P', 'tb_sys22.FZ=1', '-P', 'tb_sys22.NU=1', '-o', wd + '/sim'] + [os.path.join(HERE, f) for f in srcs], capture_output=True, text=True)
if r.returncode: print(r.stderr[-1500:]); sys.exit(1)
cases = []      # (name, words, expected a0 or None for 'must trap')
def prog(text): return R.assemble(text)
def add(name, text, exp): cases.append((name, prog(text), exp & M))
def trap(name, words): cases.append((name, list(words), None))
V = [0, 1, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 0x12345678, 0x9ABCDEF0, 5]
R3 = {'add': lambda a, b: a + b, 'sub': lambda a, b: a - b, 'sll': lambda a, b: a << (b & 31), 'srl': lambda a, b: a >> (b & 31), 'sra': lambda a, b: sx(a) >> (b & 31),
      'slt': lambda a, b: int(sx(a) < sx(b)), 'sltu': lambda a, b: int(a < b), 'xor': lambda a, b: a ^ b, 'or': lambda a, b: a | b, 'and': lambda a, b: a & b}
PAIRS = [(0, 0), (1, 0xFFFFFFFF), (0x80000000, 31), (0x7FFFFFFF, 1), (0xFFFFFFFF, 0xFFFFFFFF), (0x12345678, 0x9ABCDEF0), (5, 33), (0x80000000, 0), (0xF0F0F0F0, 4)]
for op, f in R3.items():
    for a, b in PAIRS: add('%s %#x,%#x' % (op, a, b), 'li t0,%d\nli t1,%d\n%s a0,t0,t1\nebreak' % (sx(a), sx(b), op), f(a, b))
I3 = {'addi': lambda a, i: a + i, 'slti': lambda a, i: int(sx(a) < i), 'sltiu': lambda a, i: int(a < (i & M)), 'xori': lambda a, i: a ^ (i & M), 'ori': lambda a, i: a | (i & M), 'andi': lambda a, i: a & (i & M)}
for op, f in I3.items():
    for a in (0, 1, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 0x12345678):
        for i in (-2048, -1, 0, 1, 5, 2047): add('%s %#x,%d' % (op, a, i), 'li t0,%d\n%s a0,t0,%d\nebreak' % (sx(a), op, i), f(a, i))
for op, f in (('slli', lambda a, s: a << s), ('srli', lambda a, s: a >> s), ('srai', lambda a, s: sx(a) >> s)):
    for a in (1, 0x80000000, 0xFFFFFFFF, 0x12345678):
        for s in (0, 1, 4, 31): add('%s %#x,%d' % (op, a, s), 'li t0,%d\n%s a0,t0,%d\nebreak' % (sx(a), op, s), f(a, s))
add('lui', 'lui a0,0xABCDE\nebreak', 0xABCDE000); add('lui 0x80000', 'lui a0,0x80000\nebreak', 0x80000000)
add('auipc (difference of two)', 'auipc t1,0\nauipc t2,1\nsub a0,t2,t1\nebreak', 0x1004)
add('jal links pc+4 and jumps', 'auipc t1,0\njal ra,L\nli a0,99\nebreak\nL: sub a0,ra,t1\nebreak', 8)
add('jalr links pc+4, target from register', 'auipc t1,0\naddi t0,t1,12\njalr a0,t0,0\nsub a0,a0,t1\nebreak', 12)
add('jalr with offset, lowest bit cleared', 'auipc t1,0\naddi t0,t1,12\njalr a0,t0,1\nsub a0,a0,t1\nebreak', 12)
add('x0 stays zero', 'li t0,5\nadd zero,t0,t0\nmv a0,zero\nebreak', 0)
BR = {'beq': lambda a, b: a == b, 'bne': lambda a, b: a != b, 'blt': lambda a, b: sx(a) < sx(b), 'bge': lambda a, b: sx(a) >= sx(b), 'bltu': lambda a, b: a < b, 'bgeu': lambda a, b: a >= b}
for op, f in BR.items():
    for a, b in [(1, 1), (1, 2), (2, 1), (0xFFFFFFFF, 1), (1, 0xFFFFFFFF), (0x80000000, 0x7FFFFFFF), (0x7FFFFFFF, 0x80000000), (0, 0)]:
        add('%s %#x,%#x' % (op, a, b), 'li a0,1\nli t0,%d\nli t1,%d\n%s t0,t1,T\nj E\nT: li a0,2\nE: ebreak' % (sx(a), sx(b), op), 2 if f(a, b) else 1)
add('backward branch loop', 'li a0,0\nli t0,5\nL: addi a0,a0,3\naddi t0,t0,-1\nbnez t0,L\nebreak', 15)
add('lw / sw private word', 'li t0,0x12345678\nli t1,8\nsw t0,0(t1)\nlw a0,0(t1)\nebreak', 0x12345678)
add('sw offset and lw offset', 'li t0,-5\nli t1,16\nsw t0,4(t1)\nlw a0,4(t1)\nebreak', 0xFFFFFFFB)
add('two words do not overlap', 'li t0,11\nli t1,22\nli t2,8\nsw t0,0(t2)\nsw t1,4(t2)\nlw a0,0(t2)\nlw a1,4(t2)\nslli a1,a1,8\nadd a0,a0,a1\nebreak', 11 + (22 << 8))
add('ecall stops the task (no trap)', 'li a0,7\necall_here: ebreak', 7)
cases.append(('ecall word (0x73) stops without trap', prog('li a0,7') + [0x00000073], 7))
cases.append(('csrrs word stops without trap', prog('li a0,8') + [0x300022F3], 8))
def w_i(opc, f3, imm=0, rs1=5, rd=10): return (imm & 0xFFF) << 20 | rs1 << 15 | f3 << 12 | rd << 7 | opc
def w_s(f3): return 0 << 25 | 6 << 20 | 5 << 15 | f3 << 12 | 8 << 7 | 0x23
def w_r(f7, f3, opc=0x33): return f7 << 25 | 6 << 20 | 5 << 15 | f3 << 12 | 10 << 7 | opc
for nm, f3 in (('lb', 0), ('lh', 1), ('lbu', 4), ('lhu', 5)): trap(nm, [w_i(0x03, f3)])
for nm, f3 in (('sb', 0), ('sh', 1)): trap(nm, [w_s(f3)])
trap('mul', [w_r(1, 0)]); trap('mulh', [w_r(1, 1)]); trap('div', [w_r(1, 4)]); trap('rem', [w_r(1, 6)])
trap('fence (0x0F)', [0x0000000F]); trap('custom-0 opcode 0x0B', [0x0000000B]); trap('amo opcode 0x2F', [0x0000002F]); trap('load-fp opcode 0x07', [0x00000007])
trap('jalr with funct3 1', [w_i(0x67, 1)]); trap('branch funct3 2', [0x00000063 | 2 << 12]); trap('branch funct3 3', [0x00000063 | 3 << 12])
trap('slli with bit 30 set', [w_i(0x13, 1, 0x400 | 3)]); trap('srli/srai with funct7 0x10', [w_i(0x13, 5, 0x200 | 3)])
trap('R-type with funct7 0x10', [w_r(0x10, 0)]); trap('sltu with funct7 0x20', [w_r(0x20, 3)]); trap('xor with funct7 0x20', [w_r(0x20, 4)])
trap('add with funct7 0x01 (RV32M)', [w_r(1, 0)])
def run(lw):
    base = {}; img = []
    for i, (n, w, e) in enumerate(cases): base[i] = len(img); img += w + [0x00100073]
    open(wd + '/prog.hex', 'w').write('\n'.join('%08x' % x for x in img) + '\n')
    bad = 0
    for k in range(0, len(cases), 24):
        chunk = list(range(k, min(k + 24, len(cases))))
        open(wd + '/tasks.hex', 'w').write('\n'.join('%08x\n%08x\n%08x' % (0, base[i], lw) for i in chunk) + '\n')
        subprocess.run(['vvp', wd + '/sim', '+prog=' + wd + '/prog.hex', '+tasks=' + wd + '/tasks.hex', '+ntasks=%d' % len(chunk), '+out=' + wd + '/out.txt'], capture_output=True, text=True)
        L = open(wd + '/out.txt').read().splitlines(); t = [l.split() for l in L if l.startswith('t ')]
        if len(t) != len(chunk): print('  FAIL: %d results for %d tasks' % (len(t), len(chunk))); return len(chunk)
        for i, tt in zip(chunk, t):
            a0, tr = int(tt[2]), int(tt[3]); n, w, e = cases[i]
            ok = (tr == 1) if e is None else (tr == 0 and a0 == e)
            if not ok: bad += 1; print('  FAIL lw %d: %s: a0 %#x trap %d (expected %s)' % (lw, n, a0, tr, 'trap' if e is None else hex(e)))
    return bad
total = 0
for lw in (0, 2):
    b = run(lw); total += b; print('lw %d: %d cases, %d wrong' % (lw, len(cases), b))
print('RESULT', 'PASS' if total == 0 else 'FAIL (%d)' % total); sys.exit(1 if total else 0)
