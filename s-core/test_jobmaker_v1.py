"""jobmaker_v1 + the shell's `make` / `code`: recipes become programs that agree with their Python answer on the interpreter.  No card.  python3 test_jobmaker_v1.py"""
import os, sys, io, json, random, glob
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import jobmaker_v1 as J, score_shell_v1 as S
bad = 0
def check(name, cond):
    global bad
    print('%-108s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)
def fresh():
    buf = io.StringIO(); return S.Shell(out=buf), buf
def do(sh, buf, text): buf.truncate(0); buf.seek(0); sh.run_lines(text); return buf.getvalue()
made = []
def mk(sh, buf, name, text):
    made.append(name); return do(sh, buf, 'make %s %s' % (name, text))
try:
    # pure parts
    check('parse: add 5 xor arg then sum', J.parse('add 5 xor arg then sum'.split()) == ([('add', 5), ('xor', 'arg')], 'sum'))
    check('parse: negative numbers wrap to 32 bits', J.parse(['add', '-1'])[0] == [('add', 0xFFFFFFFF)])
    for bad_words, frag in [([], 'empty recipe'), (['frob', '1'], 'unknown step'), (['shl', '32'], '0..31'), (['add'], 'needs a number'), (['add', 'x'], 'not a number'),
                            (['add', '1', 'then', 'sum', 'add', '2'], 'nothing can follow'), (['add', '1', 'then', 'mean'], 'cannot end'), (['add', '1', 'then'], 'needs one of')]:
        try: J.parse(bad_words); ok = False
        except J.RecipeError as e: ok = frag in str(e)
        check('parse refuses %r (%s)' % (' '.join(bad_words), frag), ok)
    check('reference: add 5, xor arg, shl 1, sum on [1,2,3] arg 255 = 1488', J.reference(*J.parse('add 5 xor arg shl 1 then sum'.split()), [1, 2, 3], 255) == [1488])
    check('reference: not wraps', J.reference(*J.parse(['not']), [0, 1], 0) == [0xFFFFFFFF, 0xFFFFFFFE])
    check('reference: and over nothing is 0, min over nothing is 0', J.reference([], 'and', [], 0) == [0] and J.reference([], 'min', [], 0) == [0])
    # shell
    sh, buf = fresh()
    o = mk(sh, buf, 'zz_bump', 'add 5 xor arg shl 1 then sum'); check('make: reports made, checked on the interpreter', 'made zz_bump' in o and 'runs' in o and 'error' not in o)
    o = do(sh, buf, 'add zz_bump 1 2 3 arg=255'); check('the new kind is usable at once: answer [1488]', '[1488]' in o)
    check('files kept: .s .py .json', all(os.path.exists(os.path.join(S.MADE, 'zz_bump' + e)) for e in ('.s', '.py', '.json')))
    sh2, buf2 = fresh(); o = do(sh2, buf2, 'add zz_bump 1 2 3 arg=255'); check('a fresh shell (a later session) finds the made kind by itself', '[1488]' in o)
    o = do(sh2, buf2, 'programs'); check('programs lists it under made', 'zz_bump' in o)
    o = do(sh2, buf2, 'code zz_bump'); check('code shows the assembly', 'main:' in o and 'slli t0,t0,1' in o)
    check('completion offers it after add and code; steps after make NAME', 'zz_bump' in S.completions(sh2, 'add ') and 'zz_bump' in S.completions(sh2, 'code ') and 'xor' in S.completions(sh2, 'make q '))
    check('the live colouring knows it as a kind', ('kind', 'zz_bump') in S.tokenize(sh2, 'add zz_bump 1'))
    o = mk(sh2, buf2, 'zz_bump', 'add 5 xor arg shl 1 then sum'); check('same name, same recipe: fine (ready to use)', 'already made' in o)
    o = mk(sh2, buf2, 'zz_bump', 'add 6'); check('same name, different recipe: refused, names the old recipe, nothing changed', 'different recipe' in o and 'add 5 xor arg' in o and 'zz_bump2' in o)
    o = do(sh2, buf2, 'make vmax not'); check('a library name is refused', 'already a kind' in o)
    o = do(sh2, buf2, 'make Bad! not'); check('a bad name is refused', 'lower-case' in o)
    o = do(sh2, buf2, 'make zz_none'); check('a recipe with no steps is refused and leaves no files', 'empty recipe' in o and not os.path.exists(os.path.join(S.MADE, 'zz_none.s')))
    o = do(sh2, buf2, 'make'); check('make alone prints the menu', 'steps' in o and 'endings' in o)
    # saved job file works with the other tools (the program source is kept next to it)
    import tempfile, scbatch
    d = tempfile.mkdtemp(); f = os.path.join(d, 'm.json'); do(sh, buf, 'save %s' % f)
    check('a job file using a made kind saves and loads with scbatch', [t.expected() for t in scbatch.load_jobs(f)] == [[1488]])
    # fuzz: random recipes, built through the shell, checked on the interpreter by make itself
    rng = random.Random(1422); okc = 0; N = 80
    for i in range(N):
        words = []
        for _ in range(rng.randint(0, 5)):
            op = rng.choice(list(J.STEP1) + ['not'])
            if op == 'not': words += ['not']
            elif op in ('shl', 'shr'): words += [op, rng.choice(['arg', str(rng.randint(0, 31))])]
            else: words += [op, rng.choice(['arg', str(rng.randint(-3000, 3000)), hex(rng.getrandbits(32)), str(rng.randint(0, 40))])]
        if not words or rng.random() < 0.5: words += ['then', rng.choice(J.REDUCE)]
        name = 'zz_f%d' % i; made.append(name)
        o = do(sh, buf, 'make %s %s' % (name, ' '.join(words)))
        if 'made %s' % name in o and 'error' not in o: okc += 1
        else: print('   FUZZ FAIL: make %s %s -> %s' % (name, ' '.join(words), o.strip()[:300]))
    check('fuzz: %d random recipes all built, assembled, fitted and agreed with Python on the interpreter (%d ok)' % (N, okc), okc == N)
finally:
    for n in set(made) | {'zz_none'}:
        for f in glob.glob(os.path.join(S.MADE, n + '.*')): os.remove(f)
print('FAILED %d' % bad if bad else 'all ok'); sys.exit(1 if bad else 0)
