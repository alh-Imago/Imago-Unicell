#!/usr/bin/env python3
"""Assembler + reference RV32I simulator + test runner for uc_core.

Usage:  python3 runtests.py            # all programs, all widths
        python3 runtests.py --widths 1 4 32 --random 20
"""
import argparse, os, random, re, subprocess, sys

M32 = 0xFFFFFFFF
DM_WORDS = 1024

# ----------------------------------------------------------------- encoder
def sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v

def enc_r(f7, rs2, rs1, f3, rd, opc): return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | opc
def enc_i(imm, rs1, f3, rd, opc):     return ((imm & 0xFFF) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | opc
def enc_s(imm, rs2, rs1, f3, opc):    return (((imm >> 5) & 0x7F) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | ((imm & 0x1F) << 7) | opc
def enc_b(imm, rs2, rs1, f3, opc):
    return (((imm >> 12) & 1) << 31) | (((imm >> 5) & 0x3F) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (((imm >> 1) & 0xF) << 8) | (((imm >> 11) & 1) << 7) | opc
def enc_u(imm20, rd, opc):            return ((imm20 & 0xFFFFF) << 12) | (rd << 7) | opc
def enc_j(imm, rd, opc):
    return (((imm >> 20) & 1) << 31) | (((imm >> 1) & 0x3FF) << 21) | (((imm >> 11) & 1) << 20) | (((imm >> 12) & 0xFF) << 12) | (rd << 7) | opc

R_OPS = {'add': (0, 0), 'sub': (0x20, 0), 'sll': (0, 1), 'slt': (0, 2), 'sltu': (0, 3),
         'xor': (0, 4), 'srl': (0, 5), 'sra': (0x20, 5), 'or': (0, 6), 'and': (0, 7)}
I_OPS = {'addi': 0, 'slti': 2, 'sltiu': 3, 'xori': 4, 'ori': 6, 'andi': 7}
SH_OPS = {'slli': (0, 1), 'srli': (0, 5), 'srai': (0x20, 5)}
B_OPS = {'beq': 0, 'bne': 1, 'blt': 4, 'bge': 5, 'bltu': 6, 'bgeu': 7}

ABI = {'zero': 0, 'ra': 1, 'sp': 2, 'gp': 3, 'tp': 4, 't0': 5, 't1': 6, 't2': 7, 's0': 8, 'fp': 8, 's1': 9}
for i in range(8): ABI['a%d' % i] = 10 + i
for i in range(2, 12): ABI['s%d' % i] = 16 + i
for i in range(3, 7): ABI['t%d' % i] = 25 + i

def reg(s):
    s = s.strip()
    if s in ABI: return ABI[s]
    m = re.fullmatch(r'x(\d+)', s)
    if m and int(m.group(1)) < 32: return int(m.group(1))
    raise ValueError('bad register ' + s)

def num(s): return int(s.strip(), 0)

def li_words(rd, v):
    v &= M32
    lo = sx(v, 12)
    hi = ((v - lo) & M32) >> 12
    w = []
    if hi: w.append(enc_u(hi, rd, 0x37))
    if lo or not hi: w.append(enc_i(lo, rd if hi else 0, 0, rd, 0x13))
    return w

def assemble(text):
    # pass 1: strip, split labels, expand sizes
    items, labels, pc = [], {}, 0
    for line in text.splitlines():
        line = line.split('#')[0].strip()
        while ':' in line:
            lab, line = line.split(':', 1)
            labels[lab.strip()] = pc
            line = line.strip()
        if not line: continue
        op, _, rest = line.partition(' ')
        args = [a.strip() for a in rest.split(',')] if rest.strip() else []
        size = 4
        if op == 'li':
            size = 4 * len(li_words(reg(args[0]), num(args[1])))
        items.append((pc, op, args))
        pc += size
    out = []
    def target(a, here): return (labels[a] if a in labels else num(a)) - here
    for pc, op, a in items:
        if op in R_OPS:
            f7, f3 = R_OPS[op]; out.append(enc_r(f7, reg(a[2]), reg(a[1]), f3, reg(a[0]), 0x33))
        elif op in I_OPS:
            out.append(enc_i(num(a[2]), reg(a[1]), I_OPS[op], reg(a[0]), 0x13))
        elif op in SH_OPS:
            f7, f3 = SH_OPS[op]; out.append(enc_i((f7 << 5) | num(a[2]), reg(a[1]), f3, reg(a[0]), 0x13))
        elif op in B_OPS:
            out.append(enc_b(target(a[2], pc), reg(a[1]), reg(a[0]), B_OPS[op], 0x63))
        elif op == 'lui':   out.append(enc_u(num(a[1]), reg(a[0]), 0x37))
        elif op == 'auipc': out.append(enc_u(num(a[1]), reg(a[0]), 0x17))
        elif op == 'jal':   out.append(enc_j(target(a[1], pc), reg(a[0]), 0x6F))
        elif op == 'j':     out.append(enc_j(target(a[0], pc), 0, 0x6F))
        elif op == 'jalr':  out.append(enc_i(num(a[2]), reg(a[1]), 0, reg(a[0]), 0x67))
        elif op == 'lw':
            m = re.fullmatch(r'(-?\w+)\((\w+)\)', a[1]); out.append(enc_i(num(m.group(1)), reg(m.group(2)), 2, reg(a[0]), 0x03))
        elif op == 'sw':
            m = re.fullmatch(r'(-?\w+)\((\w+)\)', a[1]); out.append(enc_s(num(m.group(1)), reg(a[0]), reg(m.group(2)), 2, 0x23))
        elif op == 'li':    out += li_words(reg(a[0]), num(a[1]))
        elif op == 'mv':    out.append(enc_i(0, reg(a[1]), 0, reg(a[0]), 0x13))
        elif op == 'nop':   out.append(enc_i(0, 0, 0, 0, 0x13))
        elif op == 'beqz':  out.append(enc_b(target(a[1], pc), 0, reg(a[0]), 0, 0x63))
        elif op == 'bnez':  out.append(enc_b(target(a[1], pc), 0, reg(a[0]), 1, 0x63))
        elif op == 'ebreak': out.append(0x00100073)
        else: raise ValueError('unknown op ' + op)
    return out

# ----------------------------------------------------------------- reference ISS
class Trap(Exception): pass

def iss(words, max_steps=3_000_000):
    x = [0] * 32
    dm = [0] * DM_WORDS
    pc, steps = 0, 0
    while True:
        if (pc >> 2) >= len(words): raise Trap('pc ran off program: %x' % pc)
        ir = words[pc >> 2]; steps += 1
        if steps > max_steps: raise Trap('too many steps')
        opc, rd, f3 = ir & 0x7F, (ir >> 7) & 31, (ir >> 12) & 7
        rs1, rs2, f7 = (ir >> 15) & 31, (ir >> 20) & 31, ir >> 25
        a, b = x[rs1], x[rs2]
        npc = (pc + 4) & M32
        wr = None
        if opc == 0x37: wr = ir & 0xFFFFF000
        elif opc == 0x17: wr = (pc + (ir & 0xFFFFF000)) & M32
        elif opc == 0x6F:
            imm = sx(((ir >> 31) << 20) | (((ir >> 12) & 0xFF) << 12) | (((ir >> 20) & 1) << 11) | (((ir >> 21) & 0x3FF) << 1), 21)
            wr = npc; npc = (pc + imm) & M32
        elif opc == 0x67:
            wr = npc; npc = ((a + sx(ir >> 20, 12)) & M32) & ~1
        elif opc == 0x63:
            imm = sx(((ir >> 31) << 12) | (((ir >> 7) & 1) << 11) | (((ir >> 25) & 0x3F) << 5) | (((ir >> 8) & 0xF) << 1), 13)
            sa, sb = sx(a, 32), sx(b, 32)
            t = {0: a == b, 1: a != b, 4: sa < sb, 5: sa >= sb, 6: a < b, 7: a >= b}[f3]
            if t: npc = (pc + imm) & M32
        elif opc == 0x03:
            wr = dm[(((a + sx(ir >> 20, 12)) & M32) >> 2) & (DM_WORDS - 1)]
        elif opc == 0x23:
            imm = sx(((ir >> 25) << 5) | ((ir >> 7) & 31), 12)
            dm[(((a + imm) & M32) >> 2) & (DM_WORDS - 1)] = b
        elif opc in (0x13, 0x33):
            if opc == 0x13:
                b = sx(ir >> 20, 12) & M32
                sh = (ir >> 20) & 31
            else:
                sh = b & 31
            sa, sb = sx(a, 32), sx(b, 32)
            if f3 == 0: wr = (a - b if (opc == 0x33 and f7 == 0x20) else a + b) & M32
            elif f3 == 1: wr = (a << sh) & M32
            elif f3 == 2: wr = int(sa < sb)
            elif f3 == 3: wr = int(a < b)
            elif f3 == 4: wr = a ^ b
            elif f3 == 5: wr = ((sa >> sh) & M32) if f7 == 0x20 else (a >> sh)
            elif f3 == 6: wr = a | b
            elif f3 == 7: wr = a & b
        elif opc == 0x73:
            return dict(x=x, dm=dm, pc=pc, instret=steps)
        else:
            raise Trap('illegal %08x' % ir)
        if wr is not None and rd: x[rd] = wr & M32
        pc = npc

# ----------------------------------------------------------------- programs
PROGRAMS = {}
PROGRAMS['sum100'] = """
    li a0, 0
    li t0, 1
    li t1, 101
loop: add a0, a0, t0
    addi t0, t0, 1
    bne t0, t1, loop
    ebreak
"""
PROGRAMS['fib'] = """
    li t0, 0
    li t1, 1
    li t2, 0         # byte offset
    li t3, 40
loop: sw t0, 0(t2)
    add t4, t0, t1
    mv t0, t1
    mv t1, t4
    addi t2, t2, 4
    bne t2, t3, loop
    ebreak
"""
PROGRAMS['bubblesort'] = """
    li s0, 16
    li t0, 0
    li t1, 12345
    li t2, 1103515245
fill: mul_free:
    add t1, t1, t2        # cheap LCG-ish: t1 += t2 ; t2 = t2 xor (t1 >> 3)
    srli t3, t1, 3
    xor t2, t2, t3
    slli t4, t0, 2
    andi t5, t1, 1023
    sw t5, 0(t4)
    addi t0, t0, 1
    bne t0, s0, fill
outer: li s1, 0
    li t0, 0
    addi s2, s0, -1
inner: slli t4, t0, 2
    lw t5, 0(t4)
    lw t6, 4(t4)
    bge t6, t5, noswap
    sw t6, 0(t4)
    sw t5, 4(t4)
    li s1, 1
noswap: addi t0, t0, 1
    bne t0, s2, inner
    bnez s1, outer
    ebreak
"""
PROGRAMS['softmul_gcd'] = """
    li a0, 123457
    li a1, 6789
    li a2, 0
mul: andi t0, a1, 1
    beqz t0, skip
    add a2, a2, a0
skip: slli a0, a0, 1
    srli a1, a1, 1
    bnez a1, mul
    li a3, 1071
    li a4, 462
gcd: beq a3, a4, done
    blt a3, a4, less
    sub a3, a3, a4
    j gcd
less: sub a4, a4, a3
    j gcd
done: sw a2, 0(zero)
    sw a3, 4(zero)
    ebreak
"""
PROGRAMS['crc32'] = """
    li s0, 0xFFFFFFFF
    li s1, 0xEDB88320
    li t0, 0
    li t1, 8
    li s2, 0x31323334
word: xor s0, s0, s2
    li t2, 32
bit: andi t3, s0, 1
    srli s0, s0, 1
    beqz t3, nox
    xor s0, s0, s1
nox: addi t2, t2, -1
    bnez t2, bit
    addi s2, s2, 0x111
    addi t0, t0, 1
    bne t0, t1, word
    xori s0, s0, -1
    sw s0, 0(zero)
    ebreak
"""
PROGRAMS['shifts_signs'] = """
    li t0, 0x80000001
    li t1, 0x7FFFFFFF
    li t2, 31
    sra a0, t0, t2
    srl a1, t0, t2
    sll a2, t1, t2
    srai a3, t0, 1
    srai a4, t1, 30
    slli a5, t0, 1
    li t3, 37               # shift amount uses low 5 bits only
    sra a6, t0, t3
    slt s2, t0, t1
    sltu s3, t0, t1
    slti s4, t0, -1
    sltiu s5, t1, -1
    ebreak
"""

# ----------------------------------------------------------------- random programs
def gen_random(seed, n=150):
    rng = random.Random(seed)
    w = []
    for r in range(1, 31): w += li_words(r, rng.getrandbits(32))
    R = lambda: rng.randrange(0, 31)        # x31 reserved as constant 0 base for memory
    RD = lambda: rng.randrange(0, 31)
    RS = lambda: rng.choice([0] + list(range(1, 31)))
    def alu():
        k = rng.randrange(4)
        if k == 0:
            op = rng.choice(list(R_OPS)); f7, f3 = R_OPS[op]; return enc_r(f7, RS(), RS(), f3, RD(), 0x33)
        if k == 1:
            op = rng.choice(list(I_OPS)); return enc_i(rng.randrange(-2048, 2048), RS(), I_OPS[op], RD(), 0x13)
        if k == 2:
            f7, f3 = SH_OPS[rng.choice(list(SH_OPS))]; return enc_i((f7 << 5) | rng.randrange(32), RS(), f3, RD(), 0x13)
        return enc_u(rng.getrandbits(20), RD(), rng.choice([0x37, 0x17]))
    count = 0
    while count < n:
        c = rng.random()
        if c < 0.55: w.append(alu()); count += 1
        elif c < 0.70:
            off = rng.randrange(-512, 512) * 4
            if rng.random() < 0.5: w.append(enc_i(off, 31, 2, RD(), 0x03))
            else: w.append(enc_s(off, RS(), 31, 2, 0x23))
            count += 1
        elif c < 0.85:
            s = rng.randrange(0, 4)
            w.append(enc_b(4 * (s + 1), RS(), RS(), rng.choice(list(B_OPS.values())), 0x63))
            w += [alu() for _ in range(s)]; count += 1 + s
        elif c < 0.93:
            s = rng.randrange(0, 4)
            w.append(enc_j(4 * (s + 1), RD(), 0x6F)); w += [alu() for _ in range(s)]; count += 1 + s
        else:
            s = rng.randrange(0, 4)
            w.append(enc_u(0, 5, 0x17))
            w.append(enc_i(12 + 4 * s + rng.choice([0, 1]), 5, 0, 5, 0x13))
            w.append(enc_i(0, 5, 0, rng.choice([1, 5, 0, 7]), 0x67))
            w += [alu() for _ in range(s)]; count += 3 + s
    w.append(0x00100073)
    return w

# ----------------------------------------------------------------- runner
def run_hw(W, words, tag, workdir, core='uc_core'):
    hexf = os.path.join(workdir, tag + '.hex')
    outf = os.path.join(workdir, '%s_%s_W%d.out' % (core, tag, W))
    with open(hexf, 'w') as f:
        f.write('\n'.join('%08x' % x for x in words) + '\n')
    subprocess.run(['vvp', '-n', os.path.join(workdir, 'sim_%s_%d' % (core, W)), '+prog=' + hexf, '+out=' + outf],
                   check=True, capture_output=True)
    res = dict(x=[0] * 32, dm=[0] * DM_WORDS)
    for line in open(outf):
        p = line.split()
        if p[0] == 'r': res['x'][int(p[1])] = int(p[2])
        elif p[0] == 'm': res['dm'][int(p[1])] = int(p[2])
        else: res[p[0]] = int(p[1])
    return res

def compare(ref, hw):
    errs = []
    if hw['trap']: errs.append('hardware trapped')
    if not hw['halted']: errs.append('hardware did not halt (timeout)')
    if ref['pc'] != hw['pc']: errs.append('pc %x != %x' % (hw['pc'], ref['pc']))
    if ref['instret'] != hw['instret']: errs.append('instret %d != %d' % (hw['instret'], ref['instret']))
    for i in range(32):
        if ref['x'][i] != hw['x'][i]: errs.append('x%d: hw %08x ref %08x' % (i, hw['x'][i], ref['x'][i]))
    for i in range(DM_WORDS):
        if ref['dm'][i] != hw['dm'][i]: errs.append('mem[%d]: hw %08x ref %08x' % (i, hw['dm'][i], ref['dm'][i]))
    return errs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--widths', type=int, nargs='*', default=[1, 2, 4, 8, 16, 32])
    ap.add_argument('--random', type=int, default=30)
    ap.add_argument('--dir', default='.')
    ap.add_argument('--core', default='uc_core', help='module and file name (without .v)')
    args = ap.parse_args()
    wd = args.dir

    for W in args.widths:
        tbf = 'tb_rw.v' if args.core.endswith('_rw') else 'tb.v'
        r = subprocess.run(['iverilog', '-g2012', '-DCORE=' + args.core, '-P', 'tb.W=%d' % W,
                            '-o', os.path.join(wd, 'sim_%s_%d' % (args.core, W)),
                            os.path.join(wd, tbf), os.path.join(wd, args.core + '.v')], capture_output=True, text=True)
        if r.returncode: print(r.stderr); sys.exit(1)

    progs = [(n, assemble(t)) for n, t in PROGRAMS.items()]
    progs += [('rand%03d' % s, gen_random(s)) for s in range(args.random)]

    fails, table = 0, {}
    for name, words in progs:
        ref = iss(words)
        for W in args.widths:
            hw = run_hw(W, words, name, wd, args.core)
            errs = compare(ref, hw)
            if errs:
                fails += 1
                print('FAIL %-14s W=%-2d %s' % (name, W, '; '.join(errs[:4])))
            table.setdefault(name, {})[W] = (hw['cycles'], hw['instret'])
    total = len(progs) * len(args.widths)
    print('\n%d/%d runs matched the reference model' % (total - fails, total))

    print('\ncycles per instruction (CPI), directed programs:')
    print('%-14s %7s ' % ('program', 'instrs') + ' '.join('W=%-5d' % W for W in args.widths))
    for name in PROGRAMS:
        n = table[name][args.widths[0]][1]
        print('%-14s %7d ' % (name, n) + ' '.join('%7.2f' % (table[name][W][0] / n) for W in args.widths))
    rn = [k for k in table if k.startswith('rand')]
    if rn:
        print('%-14s %7s ' % ('random(avg)', '') + ' '.join('%7.2f' % (sum(table[k][W][0] for k in rn) / sum(table[k][W][1] for k in rn)) for W in args.widths))
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    main()
