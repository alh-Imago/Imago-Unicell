"""Own programs, plain Python (no iverilog): the reference interpreter jobiss.py, the registry progs.py and the job compiler with user programs.
 1. the interpreter gives the same answers as the independent Python answers for the three built-in jobs (random sizes and values, 32-bit wrap-around);
 2. the example programs (vmax, vprefix) and the template agree with their Python answers over many random inputs, including empty / one-word / maximum cases;
 3. programs that are WRONG are caught before any board is involved, with a message that says what: does not assemble, no main, reads outside its window,
    writes outside its window, runaway loop, byte load, multiply, refuses on a trial run, disagrees with its Python answer; a taken or bad name;
 4. a mixed list of built-in and user jobs compiles into batches that fit the board and their expected answers are right."""
import os, sys, random
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import jobio as J, jobiss, progs, jobcomp as C
M32 = 0xFFFFFFFF

LIB_HEAD = ''
def prog(body): return 'main:\n  push ra\n' + body + '\n  pop ra\n  ret\n'
OK_TAIL = '  li a0,1\n  call lib_io_done\n  li a0,1\n'

def main():
    bad = 0
    def check(name, cond, extra=''):
        nonlocal bad
        print('%-96s %s %s' % (name, 'ok' if cond else 'FAIL', extra)); bad += (not cond)
    r = random.Random(7)
    ok = True
    for _ in range(40):
        n = r.randint(1, 20); ins = [r.choice([0, M32, r.randrange(1 << 32)]) for _ in range(n)]
        for kind, out, arg in (('vsum', 1, 0), ('vscale', n, 0), ('vstress', 1, r.randint(1, 4))):
            j = J.Job(0, kind, ins, out, arg=arg); lk = J.build_link([j]); st, nn, o, steps = jobiss.reference(lk, j)
            ok &= (st == 1 and o == j.expected())
    check('interpreter == Python answers for vsum / vscale / vstress, 120 random jobs', ok)
    progs.register('vmax', 'programs/vmax.s', expect='programs.examples:vmax_ref', out=1, base_dir=HERE, replace=True)
    progs.register('vprefix', 'programs/vprefix.s', expect='programs.examples:vprefix_ref', out='same', base_dir=HERE, replace=True)
    progs.register('copy', 'programs/template.s', expect='iss', out='same', base_dir=HERE, replace=True)
    ok = True
    for _ in range(40):
        n = r.randint(1, 25); ins = [r.choice([0, 1, M32, r.randrange(1 << 32)]) for _ in range(n)]
        from programs import examples as E
        t1, t2, t3 = C.Task('vmax', ins), C.Task('vprefix', ins), C.Task('copy', ins)
        ok &= t1.expected() == E.vmax_ref(ins, 0, 1) and t2.expected() == E.vprefix_ref(ins, 0, n) and t3.expected() == ins
    check('vmax, vprefix and the template: interpreter == Python answer, 40 random inputs each', ok)
    t = C.Task('vmax', [], out_len=1)
    check('vmax with no inputs gives 0', t.expected() == [0])
    j = J.Job(0, 'vprefix', [1, 2, 3], 2); lk = J.build_link([j]); st, n, o, _ = jobiss.reference(lk, j)
    check('vprefix told it has too little output space refuses (status 2, nothing written)', st == 2 and n == 0 and o == [])
    def rejects(label, src, expect='iss', out=1, want=None):
        try: progs.register('bad_' + label.split()[0], src, expect=expect, out=out, base_dir=HERE); got = None
        except Exception as e: got = str(e)
        finally: progs.unregister('bad_' + label.split()[0])
        check('rejected: %s' % label, got is not None and (want is None or want in got), (got or 'ACCEPTED')[:100])
    rejects('typo (does not assemble)', prog('  frobnicate a0,a1'), want='assemble')
    rejects('no main label', 'start:\n  ret\n', want='main')
    rejects('read outside its window', prog('  li t0,0x20000\n  lw t1,0(t0)\n' + OK_TAIL), want='outside the shared window')
    rejects('write outside its window', prog('  li t0,0x10400\n  sw t0,0(t0)\n' + OK_TAIL), want='outside the shared window')
    rejects('runaway loop', prog('spin:\n  j spin'), want='runaway')
    rejects('byte load (lbu): the assembler has no such instruction', prog('  li t0,0x10000\n  lbu t1,0(t0)\n' + OK_TAIL), want='unknown op')
    rejects('multiply (mul): the pool core has no RV32M', prog('  li t0,3\n  mul t1,t0,t0\n' + OK_TAIL), want='unknown op')
    rejects('refuses on the trial run', prog('  li a0,3\n  call lib_io_fail\n  li a0,0'), want='status 3')
    rejects('never says done (status stays 0)', prog('  li a0,0'), want='status 0')
    rejects('disagrees with its Python answer', open(os.path.join(HERE, 'programs', 'vmax.s')).read(), expect=lambda i, a, o: [0], want='disagrees')
    rejects('bad Python reference name', open(os.path.join(HERE, 'programs', 'vmax.s')).read(), expect='nomodule.nothing:f', want='cannot load')
    try: progs.register('vsum', 'programs/vmax.s', base_dir=HERE); got = None
    except progs.ProgramRegistryError as e: got = str(e)
    check('a built-in name cannot be taken', got is not None and 'already taken' in got)
    try: progs.register('1bad name', 'programs/vmax.s', base_dir=HERE); got = None
    except progs.ProgramRegistryError as e: got = str(e)
    check('a bad program name is refused', got is not None and 'letters' in got)
    try: progs.register('missing', 'programs/nothere.s', base_dir=HERE); got = None
    except progs.ProgramRegistryError as e: got = str(e)
    check('a missing source file is refused with its path', got is not None and 'nothere.s' in got)
    # 4. compile a mixed list
    tasks = []
    for _ in range(30):
        k = r.choice(['vsum', 'vscale', 'vstress', 'vmax', 'vprefix', 'copy']); n = r.randint(1, 20)
        tasks.append(C.Task(k, [r.randrange(1 << 32) if k != 'vstress' else r.randrange(100) for _ in range(n)], arg=r.randint(1, 3)))
    p = C.compile(tasks)
    cs = [C.need([tasks[i] for i in b], 128, 256) for b in p.batches]
    check('30 mixed tasks (3 built-in + 3 user programs) -> %d batches, all within 128 code words and 256 shared words' % len(p.batches), all(c <= 128 and d <= 256 for c, d in cs) and sorted(i for b in p.batches for i in b) == list(range(30)))
    check('every task has an expected answer of the right size', all(len(p.expected[i]) == p.results[i][2] for i in range(30)))
    print('RESULT:', 'PASS' if not bad else 'FAIL (%d)' % bad)
    return 1 if bad else 0

if __name__ == '__main__': sys.exit(main())
