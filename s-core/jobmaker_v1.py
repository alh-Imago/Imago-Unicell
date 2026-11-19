#!/usr/bin/env python3
"""jobmaker_v1.py - build a NEW job kind from a short recipe, with no assembly to write (ledger #1422).

A recipe is what happens to every input word, in order, and optionally one summing-up at the end:

    add 5  xor arg  shl 1  then sum          each word: +5, xor with the job's arg, shift left 1; then add all results up

Steps (the word is called x; all arithmetic is 32-bit, wrapping):
    add N | sub N | xor N | and N | or N     N is a number (hex ok, negative ok) or the word  arg  (the job's own arg value)
    shl N | shr N                            shift left / logical shift right by N (0..31) or by arg (its low 5 bits)
    not                                      flip every bit
Ending (optional):  then sum | xor | or | and | min | max      one word out;   without it: one word out per word in.

The recipe becomes (1) RV32I source built from programs/template.s's shape, (2) a Python reference that gives the right answer,
so the shell can check the new kind on the interpreter at once.  Pure functions: no files here (the shell writes them).
"""
import re
M32 = 0xFFFFFFFF
STEP1 = ('add', 'sub', 'xor', 'and', 'or', 'shl', 'shr')       # take an operand
STEP0 = ('not',)
REDUCE = ('sum', 'xor', 'or', 'and', 'min', 'max')
NAME_RE = re.compile(r'^[a-z][a-z0-9_]{0,23}$')

class RecipeError(Exception): pass

def parse_value(w):
    if w == 'arg': return 'arg'
    try: v = int(w, 0)
    except ValueError: raise RecipeError('not a number (or arg): %r' % w)
    if not -(1 << 31) <= v <= M32: raise RecipeError('%s does not fit in 32 bits' % w)
    return v & M32

def parse(words):
    """words -> (steps, reduce).  steps = [(op, operand|None)], operand a 32-bit int or 'arg'"""
    steps, red, i = [], None, 0
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
            if w in ('shl', 'shr') and v != 'arg' and v > 31: raise RecipeError('%s: shift by 0..31, not %s' % (w, words[i + 1]))
            steps.append((w, v)); i += 2; continue
        raise RecipeError('unknown step %r (steps: %s; ending: then %s)' % (words[i], ', '.join(STEP1 + STEP0), '|'.join(REDUCE)))
    if not steps and red is None: raise RecipeError('an empty recipe: give at least one step (add 5, xor arg, shl 1, not ...) or `then sum`')
    return steps, red

def describe(steps, red):
    """the recipe in plain words"""
    names = {'add': 'add %s', 'sub': 'subtract %s', 'xor': 'xor with %s', 'and': 'and with %s', 'or': 'or with %s', 'shl': 'shift left by %s', 'shr': 'shift right by %s'}
    show = lambda v: 'the job arg' if v == 'arg' else (hex(v) if v >= 1024 else v)
    parts = ['flip every bit' if op == 'not' else names[op] % show(v) for op, v in steps]
    s = 'each word: ' + ', then '.join(parts) if parts else 'each word as it is'
    if red: s += '; then %s of all the results (one word out)' % red
    else: s += ' (one word out per word in)'
    return s

def apply_steps(steps, x, arg):
    x &= M32
    for op, v in steps:
        v = (arg & M32) if v == 'arg' else v
        if op == 'add': x = (x + v) & M32
        elif op == 'sub': x = (x - v) & M32
        elif op == 'xor': x ^= v
        elif op == 'and': x &= v
        elif op == 'or': x |= v
        elif op == 'shl': x = (x << (v & 31)) & M32
        elif op == 'shr': x = x >> (v & 31)
        elif op == 'not': x = ~x & M32
    return x

def reference(steps, red, inputs, arg):
    """the right answer: a list of words"""
    ys = [apply_steps(steps, x, arg) for x in inputs]
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

def assemble(name, steps, red, words):
    """RV32I source for the recipe.  Constants that do not fit a 12-bit immediate live in a2..a7 (the library never touches them)."""
    uses_arg = any(v == 'arg' for _, v in steps)
    regs, consts = {}, []                       # constant -> register
    def reg_for(c):
        if c not in regs:
            if len(consts) >= 6: raise RecipeError('too many different large constants (at most 6 that do not fit in 12 bits)')
            regs[c] = 'a%d' % (2 + len(consts)); consts.append(c)
        return regs[c]
    body = []
    for op, v in steps:
        if op == 'not': body.append('  xori t0,t0,-1            # not'); continue
        if op in ('shl', 'shr'):
            if v == 'arg': body.append('  %s t0,t0,t5' % ('sll' if op == 'shl' else 'srl'))
            else: body.append('  %s t0,t0,%d' % ('slli' if op == 'shl' else 'srli', v))
            continue
        if v == 'arg':
            body.append('  %s t0,t0,t5' % {'add': 'add', 'sub': 'sub', 'xor': 'xor', 'and': 'and', 'or': 'or'}[op]); continue
        c = ((-v) & M32) if op == 'sub' else v; s = _signed(c)
        if op in ('add', 'sub'):
            if -2048 <= s <= 2047: body.append('  addi t0,t0,%d' % s)
            else: body.append('  add t0,t0,%s' % reg_for(c))
        else:
            if -2048 <= s <= 2047: body.append('  %si t0,t0,%d' % (op, s))
            else: body.append('  %s t0,t0,%s' % (op, reg_for(v)))
    L = ['# job kind %r, made by jobmaker_v1 from this recipe:  %s' % (name, ' '.join(words)),
         '# in plain words: %s' % describe(steps, red),
         '# RV32I only, lw/sw only, shape of programs/template.s.  Do not edit: make a new name (make %s2 ...) to change it.' % name,
         'main:', '  push ra', '  call lib_io_in', '  mv t2,a0', '  mv t3,a1']
    if red is None:
        L += ['  mv t4,a1']
        if uses_arg: L += ['  li t0,0x10000', '  lw t5,24(t0)             # t5 = the job arg']
        L += ['  call lib_io_out', '  bltu a1,t4,bad           # output area too small: refuse (status 2)']
    else:
        if uses_arg: L += ['  li t0,0x10000', '  lw t5,24(t0)             # t5 = the job arg']
    # constants live in a2..a7: the library only changes t0,t1,a0,a1, so they survive its calls
    if red is None:
        L += ['  li %s,%d' % (r, _signed(c)) for c, r in regs.items()]
        L += ['loop:', '  beqz t3,done', '  lw t0,0(t2)'] + body + ['  sw t0,0(a0)', '  addi t2,t2,4', '  addi a0,a0,4', '  addi t3,t3,-1', '  j loop',
              'done:', '  mv a0,t4', '  call lib_io_done', '  mv a0,t4', '  j end',
              'bad:', '  li a0,2', '  call lib_io_fail', '  li a0,0', 'end:', '  pop ra', '  ret']
    else:
        L += ['  li %s,%d' % (r, _signed(c)) for c, r in regs.items()]
        start = {'sum': 0, 'xor': 0, 'or': 0, 'and': -1, 'min': -1, 'max': 0}[red]
        L += ['  li t4,%d                 # the running result' % start, '  beqz t3,none             # no inputs: the answer is 0', 'loop:', '  beqz t3,fin', '  lw t0,0(t2)'] + body
        if red in ('sum', 'xor', 'or', 'and'): L += ['  %s t4,t4,t0' % {'sum': 'add', 'xor': 'xor', 'or': 'or', 'and': 'and'}[red]]
        elif red == 'min': L += ['  bgeu t0,t4,skip', '  mv t4,t0', 'skip:']
        else: L += ['  bgeu t4,t0,skip', '  mv t4,t0', 'skip:']
        L += ['  addi t2,t2,4', '  addi t3,t3,-1', '  j loop', 'none:', '  li t4,0', 'fin:', '  call lib_io_out', '  beqz a1,bad', '  sw t4,0(a0)',
              '  li a0,1', '  call lib_io_done', '  li a0,1', '  j end', 'bad:', '  li a0,2', '  call lib_io_fail', '  li a0,0', 'end:', '  pop ra', '  ret']
    return '\n'.join(L) + '\n'

def ref_module(name, words):
    """source of programs/made/NAME.py: the reference function the registry imports as programs.made.NAME:ref"""
    return ('"""reference answer for the job kind %r made by jobmaker_v1 (recipe: %s).  Generated; do not edit."""\n'
            'import jobmaker_v1\n'
            'WORDS = %r\n'
            '_steps, _red = jobmaker_v1.parse(WORDS)\n'
            'def ref(inputs, arg, out_len): return jobmaker_v1.reference(_steps, _red, inputs, arg)\n') % (name, ' '.join(words), list(words))

def build(name, words):
    """(source, ref module text, out) for a recipe given as words; raises RecipeError"""
    if not NAME_RE.match(name): raise RecipeError('a name is lower-case letters, digits and _, starting with a letter (max 24): %r' % name)
    steps, red = parse(words)
    return assemble(name, steps, red, words), ref_module(name, words), (1 if red else 'same')

def verify(name, steps, red, trials=12, seed=1422):
    """run the made kind on the reference interpreter with varied sizes (0, 1, 2, 5, 17 words), random words and random arg values, and
    compare with reference().  (progs.register only does one trial run with 4 inputs and arg 0.)  Returns the number of runs; raises RecipeError."""
    import random, jobio as J, jobiss, progs
    rng = random.Random(seed); sizes = [0, 1, 2, 5, 17]; n = 0
    for t in range(trials):
        size = sizes[t % len(sizes)]
        inputs = [rng.choice([0, 1, M32, 0x80000000, rng.getrandbits(32), rng.getrandbits(32)]) for _ in range(size)]
        arg = rng.choice([0, 1, 31, 32, M32, rng.getrandbits(32)])
        out_len = max(size, 1) if red is None else 1
        job = J.Job(0, name, inputs, progs.default_out_len(name, size) if red is None else 1, arg=arg)
        lk = J.build_link([job])
        status, nout, out, steps_run = jobiss.reference(lk, job)
        want = reference(steps, red, inputs, arg)
        if status != 1 or out != want:
            raise RecipeError('checked on the interpreter with %d inputs and arg=%#x: the program gave %s (status %d), the recipe says %s' % (size, arg, out, status, want))
        n += 1
    return n
