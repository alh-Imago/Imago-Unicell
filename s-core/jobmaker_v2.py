#!/usr/bin/env python3
"""jobmaker_v2.py - jobmaker_v1.py (ledger #1422) with more operands (ledger #1428).  v1 is kept as it was; every recipe v1 accepts gives byte-identical code here.

A recipe is what happens to every input word, in order, and optionally one summing-up at the end:

    add 5  xor arg  shl 1  then sum          each word: +5, xor with the job's arg, shift left 1; then add all results up

Steps (x is the word; all arithmetic is 32-bit, wrapping; compares and min / max are UNSIGNED):
    add N | sub N | xor N | and N | or N     N is a number (hex ok, negative ok) or the word  arg  (the job's own arg)
    shl N | shr N | sra N | rol N | ror N    shifts and rotates by N (0..31) or by arg (its low 5 bits); shr is logical, sra copies the top bit
    min N | max N                            clamp:  x becomes the smaller / larger of x and N
    gt N | lt N | eq N | ne N                x becomes 1 if the test is true, else 0 (unsigned)
    mul N                                    x times N (N a number, or arg), wrapping.  A number is built from shifts and adds (RV32I has no multiply): at most 12 set bits, or 12 in its negative (so `mul -1` is cheap);
                                             `mul arg` is a 32-step loop (slow)
    not                                      flip every bit
    diff                                     x minus the previous x at this point of the recipe (the first word minus 0)
    prefix                                   running total of x at this point of the recipe (one word out per word in)
Start (optional, first):  pair OP            the data is two equal halves a and b; the recipe starts from  a[i] OP b[i]  (OP: add sub xor and or min max gt lt eq ne mul);
                                             an odd last word is ignored
Ending (optional):  then sum | xor | or | and | min | max      one word out;   without it: one word out per word in.

The recipe becomes (1) RV32I source built from programs/template.s's shape, (2) a Python reference, so the shell can check the new kind on the interpreter at once.
Registers: t2 input pointer, t3 words left, t4 result / count, t5 the job arg, t0 the word, t1 and t6 scratch, a0 output pointer, a2..a7 constants and the extra
state of diff, prefix, pair and the multiply loop (a7 downward; constants from a2 up).  Pure functions: no files here (the shell writes them).
"""
import re
M32 = 0xFFFFFFFF
STEP1 = ('add', 'sub', 'xor', 'and', 'or', 'shl', 'shr', 'sra', 'rol', 'ror', 'min', 'max', 'gt', 'lt', 'eq', 'ne', 'mul')
STEP0 = ('not', 'diff', 'prefix')
REDUCE = ('sum', 'xor', 'or', 'and', 'min', 'max')
PAIROPS = ('add', 'sub', 'xor', 'and', 'or', 'min', 'max', 'gt', 'lt', 'eq', 'ne', 'mul')
SHIFTS = ('shl', 'shr', 'sra', 'rol', 'ror')
NAME_RE = re.compile(r'^[a-z][a-z0-9_]{0,23}$')
MAX_MUL_BITS = 12

class RecipeError(Exception): pass

def parse_value(w):
    if w == 'arg': return 'arg'
    try: v = int(w, 0)
    except ValueError: raise RecipeError('not a number (or arg): %r' % w)
    if not -(1 << 31) <= v <= M32: raise RecipeError('%s does not fit in 32 bits' % w)
    return v & M32

def parse(words):
    """words -> (steps, reduce).  steps = [(op, operand|None)], operand a 32-bit int or 'arg'; a leading ('pair', OP) marks pair mode"""
    steps, red, i = [], None, 0
    words = [str(w) for w in words]
    if words and words[0].lower() == 'pair':
        if len(words) < 2 or words[1].lower() not in PAIROPS: raise RecipeError('pair needs one of: %s' % ', '.join(PAIROPS))
        steps.append(('pair', words[1].lower())); i = 2
    while i < len(words):
        w = words[i].lower()
        if w == 'then':
            if i + 1 >= len(words): raise RecipeError('`then` needs one of: %s' % ', '.join(REDUCE))
            red = words[i + 1].lower()
            if red not in REDUCE: raise RecipeError('cannot end with %r (use: %s)' % (red, ', '.join(REDUCE)))
            if i + 2 != len(words): raise RecipeError('nothing can follow `then %s`' % red)
            break
        if w in STEP0: steps.append((w, None)); i += 1; continue
        if w in STEP1:
            if i + 1 >= len(words): raise RecipeError('%s needs a number or arg' % w)
            v = parse_value(words[i + 1])
            if w in SHIFTS and v != 'arg' and v > 31: raise RecipeError('%s: shift by 0..31, not %s' % (w, words[i + 1]))
            if w == 'mul' and v != 'arg' and min(bin(v).count('1'), bin((-v) & M32).count('1')) > MAX_MUL_BITS: raise RecipeError('mul %s needs more than %d shifts and adds: use `mul arg` or `pair mul`' % (words[i + 1], MAX_MUL_BITS))
            steps.append((w, v)); i += 2; continue
        raise RecipeError('unknown step %r (steps: %s; start: pair OP; ending: then %s)' % (words[i], ', '.join(STEP1 + STEP0), '|'.join(REDUCE)))
    if sum(1 for op, _ in steps if op == 'diff') > 1: raise RecipeError('at most one diff in a recipe')
    if sum(1 for op, _ in steps if op == 'prefix') > 1: raise RecipeError('at most one prefix in a recipe')
    if not steps and red is None: raise RecipeError('an empty recipe: give at least one step (add 5, xor arg, shl 1, not ...) or `then sum`')
    return steps, red

def _show(v): return 'the job arg' if v == 'arg' else (hex(v) if v >= 1024 else v)

def describe(steps, red):
    """the recipe in plain words"""
    names = {'add': 'add %s', 'sub': 'subtract %s', 'xor': 'xor with %s', 'and': 'and with %s', 'or': 'or with %s', 'shl': 'shift left by %s', 'shr': 'shift right by %s',
             'sra': 'shift right keeping the sign by %s', 'rol': 'rotate left by %s', 'ror': 'rotate right by %s', 'min': 'the smaller of it and %s', 'max': 'the larger of it and %s',
             'gt': '1 if it is greater than %s else 0', 'lt': '1 if it is less than %s else 0', 'eq': '1 if it equals %s else 0', 'ne': '1 if it differs from %s else 0', 'mul': 'multiply by %s'}
    pair = steps[0][1] if steps and steps[0][0] == 'pair' else None
    rest = steps[1:] if pair else steps
    parts = []
    for op, v in rest:
        if op == 'not': parts.append('flip every bit')
        elif op == 'diff': parts.append('subtract the previous one')
        elif op == 'prefix': parts.append('running total')
        else: parts.append(names[op] % _show(v))
    head = ('pairs (first half %s second half)' % pair) if pair else 'each word'
    s = head + (': ' + ', then '.join(parts) if parts else (' as it is' if not pair else ''))
    if red: s += '; then %s of all the results (one word out)' % red
    else: s += ' (one word out per %s)' % ('pair' if pair else 'word in')
    return s

def _sgn(x): return x - (1 << 32) if x >= (1 << 31) else x

def _op(op, x, v):
    if op == 'add': return (x + v) & M32
    if op == 'sub': return (x - v) & M32
    if op == 'xor': return x ^ v
    if op == 'and': return x & v
    if op == 'or': return x | v
    if op == 'shl': return (x << (v & 31)) & M32
    if op == 'shr': return x >> (v & 31)
    if op == 'sra': return (_sgn(x) >> (v & 31)) & M32
    if op == 'rol': n = v & 31; return ((x << n) | (x >> ((32 - n) & 31))) & M32
    if op == 'ror': n = v & 31; return ((x >> n) | (x << ((32 - n) & 31))) & M32
    if op == 'min': return min(x, v)
    if op == 'max': return max(x, v)
    if op == 'gt': return int(x > v)
    if op == 'lt': return int(x < v)
    if op == 'eq': return int(x == v)
    if op == 'ne': return int(x != v)
    if op == 'mul': return (x * v) & M32
    raise RecipeError('no such step %r' % op)

def stream(steps, inputs, arg):
    """the values after all the steps, one per element (pairs: one per pair)"""
    pair = steps[0][1] if steps and steps[0][0] == 'pair' else None
    rest = steps[1:] if pair else steps
    inputs = [x & M32 for x in inputs]
    if pair:
        h = len(inputs) // 2; first = [_op(pair, inputs[i], inputs[h + i]) for i in range(h)]
    else: first = inputs
    out = []; prev = 0; acc = 0
    for x in first:
        for op, v in rest:
            v = (arg & M32) if v == 'arg' else v
            if op == 'not': x = ~x & M32
            elif op == 'diff': x, prev = (x - prev) & M32, x
            elif op == 'prefix': acc = (acc + x) & M32; x = acc
            else: x = _op(op, x, v)
        out.append(x)
    return out

def apply_steps(steps, x, arg): return stream(steps, [x], arg)[0]       # (kept for v1 callers: one word, no pairs)

def reference(steps, red, inputs, arg):
    """the right answer: a list of words"""
    ys = stream(steps, inputs, arg)
    if red is None: return ys
    if not ys: return [0]
    if red == 'sum': r = sum(ys) & M32
    elif red == 'xor':
        r = 0
        for y in ys: r ^= y
    elif red == 'or':
        r = 0
        for y in ys: r |= y
    elif red == 'and':
        r = M32
        for y in ys: r &= y
    elif red == 'min': r = min(ys)
    else: r = max(ys)
    return [r]

def _signed(c): return c - (1 << 32) if c >= (1 << 31) else c

def _mul_const(N):
    """lines that turn t0 into t0 * N (mod 2**32) with shifts and adds; t1 keeps x"""
    if N == 0: return ['  li t0,0']
    neg = (-N) & M32
    if bin(neg).count('1') < bin(N).count('1'): return _mul_const(neg) + ['  sub t0,zero,t0']          # x * N = -(x * (2**32 - N)): cheaper when 2**32 - N has fewer set bits (e.g. N = -1)
    bits = [b for b in range(31, -1, -1) if (N >> b) & 1]
    if len(bits) == 1: return ['  slli t0,t0,%d' % bits[0]] if bits[0] else []
    L = ['  mv t1,t0']
    for k in range(1, len(bits)): L += ['  slli t0,t0,%d' % (bits[k - 1] - bits[k]), '  add t0,t0,t1']
    if bits[-1]: L += ['  slli t0,t0,%d' % bits[-1]]
    return L

def assemble(name, steps, red, words):
    """RV32I source for the recipe"""
    pair = steps[0][1] if steps and steps[0][0] == 'pair' else None
    rest = steps[1:] if pair else steps
    uses_arg = any(v == 'arg' for _, v in rest)
    ops_all = [op for op, _ in rest]
    need_loop = (pair == 'mul') or any(op == 'mul' and v == 'arg' for op, v in rest)
    reserved = []                                   # extra state registers, taken from a7 downward
    def take(): reserved.append('a%d' % (7 - len(reserved))); return reserved[-1]
    r_prev = take() if 'diff' in ops_all else None
    r_acc = take() if 'prefix' in ops_all else None
    r_pb = take() if pair else None
    r_x = take() if need_loop else None
    regs, consts = {}, []
    cap = 6 - len(reserved)
    def reg_for(c):
        if c not in regs:
            if len(consts) >= cap: raise RecipeError('too many different large constants and extra state in one recipe (constants that need a register: at most %d here)' % cap)
            regs[c] = 'a%d' % (2 + len(consts)); consts.append(c)
        return regs[c]
    lab = [0]
    def newlab(): lab[0] += 1; return 'L%d' % lab[0]
    def mulloop(mcand, mplier):
        a, b, c = newlab(), newlab(), newlab()
        return ['  li t0,0', '%s:' % a, '  beqz %s,%s' % (mplier, b), '  andi %s,%s,1' % (r_x, mplier), '  beqz %s,%s' % (r_x, c), '  add t0,t0,%s' % mcand,
                '%s:' % c, '  slli %s,%s,1' % (mcand, mcand), '  srli %s,%s,1' % (mplier, mplier), '  j %s' % a, '%s:' % b]
    body = []
    if pair:
        body += ['  lw t0,0(t2)', '  lw t1,0(%s)' % r_pb]
        if pair in ('add', 'sub', 'xor', 'and', 'or'): body += ['  %s t0,t0,t1' % pair]
        elif pair == 'min': l = newlab(); body += ['  bltu t0,t1,%s' % l, '  mv t0,t1', '%s:' % l]
        elif pair == 'max': l = newlab(); body += ['  bgeu t0,t1,%s' % l, '  mv t0,t1', '%s:' % l]
        elif pair == 'gt': body += ['  sltu t0,t1,t0']
        elif pair == 'lt': body += ['  sltu t0,t0,t1']
        elif pair == 'eq': body += ['  xor t0,t0,t1', '  sltiu t0,t0,1']
        elif pair == 'ne': body += ['  xor t0,t0,t1', '  sltu t0,zero,t0']
        elif pair == 'mul': body += ['  mv t6,t0'] + mulloop('t6', 't1')
    else: body += ['  lw t0,0(t2)']
    for op, v in rest:
        if op == 'not': body.append('  xori t0,t0,-1            # not'); continue
        if op == 'diff': body += ['  mv t1,t0', '  sub t0,t0,%s' % r_prev, '  mv %s,t1' % r_prev]; continue
        if op == 'prefix': body += ['  add %s,%s,t0' % (r_acc, r_acc), '  mv t0,%s' % r_acc]; continue
        if op in SHIFTS:
            if op in ('shl', 'shr', 'sra'):
                if v == 'arg': body.append('  %s t0,t0,t5' % {'shl': 'sll', 'shr': 'srl', 'sra': 'sra'}[op])
                else: body.append('  %s t0,t0,%d' % ({'shl': 'slli', 'shr': 'srli', 'sra': 'srai'}[op], v))
            else:                                   # rotate: (x shifted one way) or (x shifted the other way by 32 - n)
                a, b = ('sll', 'srl') if op == 'rol' else ('srl', 'sll'); ai, bi = ('slli', 'srli') if op == 'rol' else ('srli', 'slli')
                if v == 'arg': body += ['  andi t6,t5,31', '  %s t1,t0,t6' % a, '  sub t6,zero,t6', '  andi t6,t6,31', '  %s t0,t0,t6' % b, '  or t0,t0,t1']
                elif v & 31: body += ['  %s t1,t0,%d' % (ai, v & 31), '  %s t0,t0,%d' % (bi, 32 - (v & 31)), '  or t0,t0,t1']
            continue
        if op == 'mul':
            if v == 'arg': body += ['  mv t1,t0', '  mv t6,t5'] + mulloop('t1', 't6')
            else: body += _mul_const(v)
            continue
        if op in ('min', 'max', 'gt'):
            R = 't5' if v == 'arg' else reg_for(v)
            if op == 'gt': body.append('  sltu t0,%s,t0' % R)
            else: l = newlab(); body += ['  %s t0,%s,%s' % ('bltu' if op == 'min' else 'bgeu', R, l), '  mv t0,%s' % R, '%s:' % l]
            continue
        if op in ('lt', 'eq', 'ne'):
            if v == 'arg': R = 't5'; imm = None
            else:
                s = _signed(v); imm = s if -2048 <= s <= 2047 else None; R = None if imm is not None else reg_for(v)
            if op == 'lt': body.append('  sltiu t0,t0,%d' % imm if imm is not None else '  sltu t0,t0,%s' % R)
            else:
                body.append('  xori t0,t0,%d' % imm if imm is not None else '  xor t0,t0,%s' % R)
                body.append('  sltiu t0,t0,1' if op == 'eq' else '  sltu t0,zero,t0')
            continue
        if v == 'arg':
            body.append('  %s t0,t0,t5' % op); continue
        c = ((-v) & M32) if op == 'sub' else v; s = _signed(c)
        if op in ('add', 'sub'):
            if -2048 <= s <= 2047: body.append('  addi t0,t0,%d' % s)
            else: body.append('  add t0,t0,%s' % reg_for(c))
        else:
            if -2048 <= s <= 2047: body.append('  %si t0,t0,%d' % (op, s))
            else: body.append('  %s t0,t0,%s' % (op, reg_for(v)))
    setup = []
    if uses_arg: setup += ['  li t0,0x10000', '  lw t5,24(t0)             # t5 = the job arg']
    if pair: setup += ['  srli t3,a1,1', '  slli t1,t3,2', '  add %s,t2,t1' % r_pb]          # pairs = words / 2; second half starts after the first
    state = (['  li %s,0' % r_prev] if r_prev else []) + (['  li %s,0' % r_acc] if r_acc else [])
    step_ptr = ['  addi t2,t2,4'] + (['  addi %s,%s,4' % (r_pb, r_pb)] if pair else [])
    L = ['# job kind %r, made by jobmaker_v2 from this recipe:  %s' % (name, ' '.join(words)),
         '# in plain words: %s' % describe(steps, red),
         '# RV32I only, lw/sw only, shape of programs/template.s.  Do not edit: make a new name (make %s2 ...) to change it.' % name,
         'main:', '  push ra', '  call lib_io_in', '  mv t2,a0', '  mv t3,a1']
    if red is None:
        L += ['  mv t4,a1'] if not pair else []
        # pair: the count of outputs is the number of pairs, known after setup
        if uses_arg: L += ['  li t0,0x10000', '  lw t5,24(t0)             # t5 = the job arg']
        if pair: L += ['  srli t3,a1,1', '  slli t1,t3,2', '  add %s,t2,t1' % r_pb, '  mv t4,t3']
        L += ['  call lib_io_out', '  bltu a1,t4,bad           # output area too small: refuse (status 2)']
        L += ['  li %s,%d' % (r, _signed(c)) for c, r in regs.items()] + state
        L += ['loop:', '  beqz t3,done'] + body + ['  sw t0,0(a0)'] + step_ptr + ['  addi a0,a0,4', '  addi t3,t3,-1', '  j loop',
              'done:', '  mv a0,t4', '  call lib_io_done', '  mv a0,t4', '  j end',
              'bad:', '  li a0,2', '  call lib_io_fail', '  li a0,0', 'end:', '  pop ra', '  ret']
    else:
        L += setup
        L += ['  li %s,%d' % (r, _signed(c)) for c, r in regs.items()] + state
        start = {'sum': 0, 'xor': 0, 'or': 0, 'and': -1, 'min': -1, 'max': 0}[red]
        L += ['  li t4,%d                 # the running result' % start, '  beqz t3,none             # no inputs: the answer is 0', 'loop:', '  beqz t3,fin'] + body
        if red in ('sum', 'xor', 'or', 'and'): L += ['  %s t4,t4,t0' % {'sum': 'add', 'xor': 'xor', 'or': 'or', 'and': 'and'}[red]]
        elif red == 'min': L += ['  bgeu t0,t4,skip', '  mv t4,t0', 'skip:']
        else: L += ['  bgeu t4,t0,skip', '  mv t4,t0', 'skip:']
        L += step_ptr + ['  addi t3,t3,-1', '  j loop', 'none:', '  li t4,0', 'fin:', '  call lib_io_out', '  beqz a1,bad', '  sw t4,0(a0)',
              '  li a0,1', '  call lib_io_done', '  li a0,1', '  j end', 'bad:', '  li a0,2', '  call lib_io_fail', '  li a0,0', 'end:', '  pop ra', '  ret']
    return '\n'.join(L) + '\n'

def ref_module(name, words):
    """source of programs/made/NAME.py: the reference function the registry imports as programs.made.NAME:ref"""
    return ('"""reference answer for the job kind %r made by jobmaker_v2 (recipe: %s).  Generated; do not edit."""\n'
            'import jobmaker_v2\n'
            'WORDS = %r\n'
            '_steps, _red = jobmaker_v2.parse(WORDS)\n'
            'def ref(inputs, arg, out_len): return jobmaker_v2.reference(_steps, _red, inputs, arg)\n') % (name, ' '.join(words), list(words))

def build(name, words):
    """(source, ref module text, out) for a recipe given as words; raises RecipeError"""
    if not NAME_RE.match(name): raise RecipeError('a name is lower-case letters, digits and _, starting with a letter (max 24): %r' % name)
    steps, red = parse(words)
    return assemble(name, steps, red, words), ref_module(name, words), (1 if red else 'same')

def verify(name, steps, red, trials=14, seed=1428):
    """run the made kind on the reference interpreter with varied sizes (0, 1, 2, 5, 6, 17 words), random words and random arg values, and compare with reference()."""
    import random, jobio as J, jobiss, progs
    rng = random.Random(seed); sizes = [0, 1, 2, 5, 6, 17, 8]; n = 0
    for t in range(trials):
        size = sizes[t % len(sizes)]
        inputs = [rng.choice([0, 1, 2, M32, 0x80000000, 0x7FFFFFFF, rng.getrandbits(32), rng.getrandbits(32)]) for _ in range(size)]
        arg = rng.choice([0, 1, 5, 31, 32, 33, M32, rng.getrandbits(32), rng.getrandbits(8)])
        job = J.Job(0, name, inputs, progs.default_out_len(name, size) if red is None else 1, arg=arg)
        lk = J.build_link([job])
        status, nout, out, steps_run = jobiss.reference(lk, job)
        want = reference(steps, red, inputs, arg)
        if status != 1 or out != want:
            raise RecipeError('checked on the interpreter with %d inputs and arg=%#x: the program gave %s (status %d), the recipe says %s' % (size, arg, out, status, want))
        n += 1
    return n
