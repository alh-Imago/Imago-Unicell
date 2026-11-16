"""Job compiler (jobcomp.py) + batch sequencer in the whole-board simulation.  Needs iverilog.
 1. plain Python: 60 random tasks are split into batches that respect the code store, the shared RAM and the job limit; every task appears exactly once;
    tasks too big for the board are refused with a clear message; far-RAM blocks do not overlap; the results of the tasks are laid out in task order;
 2. simulation: 6 tasks with big windows (3 batches) are compiled, the images written into far RAM, the sequencer started with J; the status words and the
    results of ALL tasks, read back from far RAM, are checked by plan.verify (status 1, n_out right, outputs equal to the Python answer)."""
import os, sys, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import host_sc as hs, sdt_host as H, jobcomp as C
import test_farram_sim as F
from test_seq_sim import jcmd, dec_A

def pure(check):
    random.seed(11); tasks = []
    for i in range(60):
        k = random.choice(['vsum', 'vscale', 'vstress']); n = random.randint(1, 30)
        tasks.append(C.Task(k, [random.randrange(1 << 32) for _ in range(n)], arg=random.randint(1, 9)))
    p = C.compile(tasks)
    flat = sorted(i for b in p.batches for i in b)
    check('every task is in exactly one batch (%d tasks, %d batches)' % (len(tasks), len(p.batches)), flat == list(range(60)))
    ok = True
    for b in p.batches:
        c, d = C.need([tasks[i] for i in b], 128, 256)
        ok &= c <= 128 and d <= 256 and len(b) <= 16
    check('each batch fits the code store (128), the shared RAM (256) and 16 jobs', ok)
    for lk in p.links: ok &= len(lk.words) <= 128
    check('the real links agree (code words within the store)', ok)
    spans = sorted((a, a + n) for a, n in [(ra, n) for (_, ra, n) in p.results.values()] + [(p.status_at[i], 2) for i in p.status_at])
    check('status and result blocks do not overlap', all(x[1] <= y[0] for x, y in zip(spans, spans[1:])))
    lo, ln = p.window
    check('every result and status lies inside the copy window', all(lo <= a and e <= lo + ln for a, e in spans))
    ra = [p.results[i][1] for i in range(60)]
    check('results are in task order', all(ra[i] + p.results[i][2] == ra[i + 1] for i in range(59)))
    try: C.compile([C.Task('vsum', list(range(300)))]); ok = False
    except C.JobCompError as e: ok = 'cannot fit' in str(e)
    check('a task that cannot fit the board is refused with a message', ok)
    try: C.Task('nonsense', [1]); ok = False
    except C.JobCompError: ok = True
    check('an unknown program name is refused', ok)

def main():
    bad = 0
    def check(name, cond, extra=''):
        nonlocal bad
        print('%-92s %s %s' % (name, 'ok' if cond else 'FAIL', extra)); bad += (not cond)
    pure(check)
    rnd = random.Random(5)
    tasks = [C.Task('vsum', [rnd.randrange(1 << 32) for _ in range(90)]), C.Task('vscale', [rnd.randrange(1 << 32) for _ in range(45)]),
             C.Task('vstress', [rnd.randrange(1000) for _ in range(60)], arg=1), C.Task('vsum', [rnd.randrange(1 << 32) for _ in range(95)]),
             C.Task('vscale', [rnd.randrange(1 << 32) for _ in range(40)]), C.Task('vstress', [rnd.randrange(1000) for _ in range(80)], arg=1)]
    p = C.compile(tasks, wait_k=1000)
    print(p.report())
    check('the sim case really needs several batches', len(p.batches) >= 3, str(len(p.batches)))
    exe = F.build('jc', seq=True)
    s = F.Script(); s.wait(0x3000)
    s.send(H.c_D(*p.window))
    for a in sorted(p.image): s.send(H.c_w(a, p.image[a]), extra=0x40)
    s.send(jcmd(p.entry))
    for _ in range(3): s.wait(1_500_000); s.send(b'A', 8, 'A')
    lo, ln = p.window
    first = min(a for (sa, ra, n) in p.results.values() for a in (sa,)); last = max(ra + n for (sa, ra, n) in p.results.values())
    for a in range(first, last): s.send(H.c_r(a), 4, 'r')
    rx, errs = F.run(exe, s, tag='jc', maxcyc=250_000_000)
    pos = 0; got = []
    for kind, m in s.reps: got.append((kind, rx[pos:pos + m])); pos += m
    As = [dec_A(b) for k, b in got if k == 'A']; rs = [H.dec_r(b) for k, b in got if k == 'r']
    a = As[-1]
    check('the sequencer ran the whole compiled chain: done, error 0, end tag', a['done'] and not a['busy'] and a['err'] == 0 and a['tag'] == p.tag, str(a))
    check('step count equals the compiled script steps (%d)' % p.steps, a['steps'] == p.steps, str(a['steps']))
    mem = {first + k: v for k, v in enumerate(rs)}
    problems = p.verify(lambda x: mem.get(x, 0xEEEEEEEE))
    check('status 1, n_out and outputs of all %d tasks equal the Python answer (checked by plan.verify)' % len(tasks), not problems, str(problems[:3]))
    check('SDRAM model reports no timing violations', not errs, repr(errs[:2]))
    print('RESULT:', 'PASS' if not bad else 'FAIL (%d)' % bad)
    return 1 if bad else 0

if __name__ == '__main__': sys.exit(main())
