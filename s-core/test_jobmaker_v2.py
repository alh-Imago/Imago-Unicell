"""jobmaker_v2 (more operands: min max gt lt eq ne rol ror sra mul diff prefix pair) through the shell's `make`: answers worked out by hand, a regression against v1 (byte-identical code for
every recipe v1 accepts), and a fuzz of random recipes checked on the interpreter.  No card.  python3 test_jobmaker_v2.py"""
import os, sys, io, glob, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import jobmaker_v1 as A, jobmaker_v2 as J, score_shell_v1 as S
bad = 0
def check(name, cond):
    global bad
    print('%-112s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)
def fresh():
    buf = io.StringIO(); return S.Shell(out=buf), buf
def do(sh, buf, text): buf.truncate(0); buf.seek(0); sh.run_lines(text); return buf.getvalue()
made = []
def answer(sh, buf, name, recipe, data, want, arg=None):
    made.append(name); o = do(sh, buf, 'make %s %s' % (name, recipe)); ok = 'made %s' % name in o and 'error' not in o
    o2 = do(sh, buf, 'add %s %s%s' % (name, data, (' arg=%d' % arg) if arg is not None else ''))
    check('%-44s %-28s -> %s' % (recipe, data[:28], want), ok and ('-> ' + ' ' + str(want)) in o2.replace('->  ', '-> ').replace('->', '-> ', 1).replace('->  ', '-> ') or ok and str(want) in o2)
try:
    # regression: v2 gives byte-identical code for what v1 accepts
    rng = random.Random(7); n = 0; diff = 0
    for i in range(600):
        words = []
        for _ in range(rng.randint(0, 6)):
            op = rng.choice(list(A.STEP1) + ['not'])
            if op == 'not': words += ['not']
            elif op in ('shl', 'shr'): words += [op, rng.choice(['arg', str(rng.randint(0, 31))])]
            else: words += [op, rng.choice(['arg', str(rng.randint(-3000, 3000)), hex(rng.getrandbits(32)), str(rng.randint(0, 40))])]
        if not words or rng.random() < 0.5: words += ['then', rng.choice(A.REDUCE)]
        try: sa = A.assemble('x', *A.parse(words), words)
        except A.RecipeError: continue
        body = lambda t: [l for l in t.split('\n') if not l.startswith('# job kind') and not l.startswith('# in plain')]
        n += 1; diff += body(sa) != body(J.assemble('x', *J.parse(words), words))
    check('regression: %d recipes that v1 accepts give byte-identical code in v2 (%d differ)' % (n, diff), n > 300 and diff == 0)
    # by hand
    sh, buf = fresh()
    answer(sh, buf, 'zz_clamp', 'max 10 min 100', '5 50 500', '[10, 50, 100]')
    answer(sh, buf, 'zz_gt', 'gt 9', '5 9 10 4294967295', '[0, 0, 1, 1]')
    answer(sh, buf, 'zz_lt', 'lt 9', '5 9 10', '[1, 0, 0]')
    answer(sh, buf, 'zz_eq', 'eq 9', '5 9 10', '[0, 1, 0]')
    answer(sh, buf, 'zz_ne', 'ne arg', '5 9 10', '[1, 0, 1]', arg=9)
    answer(sh, buf, 'zz_rol', 'rol 8', '0x12345678', '[878082066]')            # 0x34567812
    answer(sh, buf, 'zz_ror', 'ror 8', '0x12345678', '[2014458966]')           # 0x78123456
    answer(sh, buf, 'zz_rola', 'rol arg', '0x12345678', '[878082066]', arg=8)
    answer(sh, buf, 'zz_sra', 'sra 4', '0x80000000 64', '[4160749568, 4]')      # 0xF8000000
    answer(sh, buf, 'zz_mul10', 'mul 10', '1 2 3 0xFFFFFFFF', '[10, 20, 30, 4294967286]')
    answer(sh, buf, 'zz_mulm1', 'mul 0xFFFFFFFF', '1 2 3', '[4294967295, 4294967294, 4294967293]')
    answer(sh, buf, 'zz_mula', 'mul arg', '1 2 3 100', '[7, 14, 21, 700]', arg=7)
    answer(sh, buf, 'zz_dot', 'pair mul then sum', '1 2 3 4 5 6', '[32]')
    answer(sh, buf, 'zz_padd', 'pair add', '1 2 3 10 20 30 99', '[11, 22, 33]')
    answer(sh, buf, 'zz_pmax', 'pair max then sum', '5 1 9 2 8 3', '[22]')
    answer(sh, buf, 'zz_diff', 'diff', '5 7 12 12', '[5, 2, 5, 0]')
    answer(sh, buf, 'zz_prefix', 'prefix', '1 2 3 4', '[1, 3, 6, 10]')
    answer(sh, buf, 'zz_dp', 'diff prefix', '5 7 12 12', '[5, 7, 12, 12]')       # the running total of the differences gives the original back
    for r, frag in [('pair', 'pair needs'), ('pair frob', 'pair needs'), ('mul 0x55555555', 'shifts and adds'), ('diff diff', 'at most one diff'), ('rol 40', '0..31'), ('prefix then', 'needs one of')]:
        o = do(sh, buf, 'make zz_bad %s' % r); check('refused: make zz_bad %s' % r, frag in o and not os.path.exists(os.path.join(S.MADE, 'zz_bad.s')))
    o = do(sh, buf, 'make zz_many add 0x10001 add 0x20002 add 0x30003 add 0x40004 pair mul'); check('pair is only allowed first: refused with a reason', 'error' in o)
    # old kinds made with v1 are found again by the same recipe (header text differs, the recipe is what counts)
    made.append('zz_old'); do(sh, buf, 'make zz_old add 5 xor arg then sum')
    p = os.path.join(S.MADE, 'zz_old.s'); t = open(p).read().replace('jobmaker_v2', 'jobmaker_v1'); open(p, 'w').write(t)
    sh2, buf2 = fresh(); o = do(sh2, buf2, 'make zz_old add 5 xor arg then sum'); check('a kind made by v1 with the same recipe is reused, not refused', 'already made' in o)
    # fuzz: random recipes with all the new steps
    rng = random.Random(1428); okc = 0; N = 120
    for i in range(N):
        words = []
        if rng.random() < 0.25: words += ['pair', rng.choice(J.PAIROPS)]
        for _ in range(rng.randint(0, 4)):
            op = rng.choice(list(J.STEP1) + list(J.STEP0))
            if op in J.STEP0: words += [op]
            elif op in J.SHIFTS: words += [op, rng.choice(['arg', str(rng.randint(0, 31))])]
            elif op == 'mul': words += [op, rng.choice(['arg', str(rng.randint(0, 1000)), '0xFFFFFFFF', hex(rng.getrandbits(4) * 0x1111)])]
            else: words += [op, rng.choice(['arg', str(rng.randint(-3000, 3000)), hex(rng.getrandbits(32)), str(rng.randint(0, 40))])]
        if len(words) == 0 or rng.random() < 0.4: words += ['then', rng.choice(J.REDUCE)]
        try: J.parse(words)
        except J.RecipeError: continue
        name = 'zz_f%d' % i; made.append(name)
        o = do(sh, buf, 'make %s %s' % (name, ' '.join(words)))
        if 'made %s' % name in o and 'error' not in o: okc += 1
        elif 'too many' in o: pass                      # a recipe with more constants than registers: refused with a reason, fine
        else: print('   FUZZ FAIL: make %s %s -> %s' % (name, ' '.join(words), o.strip()[:300])); bad += 1
    check('fuzz: %d random recipes with the new steps built, assembled, fitted and agreed with Python on the interpreter (the rest refused with a reason)' % okc, okc > 70)
finally:
    for n in set(made) | {'zz_bad'}:
        for f in glob.glob(os.path.join(S.MADE, n + '.*')): os.remove(f)
print('FAILED %d' % bad if bad else 'all ok'); sys.exit(1 if bad else 0)
