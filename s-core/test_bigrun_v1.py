"""bigrun_v1: the long test run for the window (ledger #1439).  Host only, no card.  Checks the file format, that five jobs fill a batch, that the plan fits far RAM, that the committed
files are what the generator makes, and that every job's answer is the made kind's Python answer.   python3 test_bigrun_v1.py"""
import os, sys, io, glob, contextlib, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bigrun_v1 as B, score_shell_v1 as S
bad = 0
def check(name, cond):
    global bad
    print('%-112s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)
had = set(S.made_names())
try:
    ls = B.lines(2)
    check('2 batches = the make line + 10 add lines', len(ls) == 11 and ls[0].startswith('make wb_heavy7 ') and ls[0].count('mul arg') == 7 and all(l.startswith('add wb_heavy7 seq ') for l in ls[1:]))
    check('every job has its own arg (3, 5, 7, ...) and the widths repeat 0, 0, 1, 2, 0', [int(re.search(r'arg=(\d+)', l).group(1)) for l in ls[1:6]] == [3, 5, 7, 9, 11] and [int(re.search(r'lw=(\d)', l).group(1)) for l in ls[1:]] == [0, 0, 1, 2, 0] * 2)
    r = B.size(ls)
    check('sized: 10 jobs in 2 batches of five (245 of 256 shared words each), far RAM used > 0, a positive estimate', r['jobs'] == 10 and r['batches'] == 2 and r['plan'].count('5 jobs (wb_heavy7)') == 2 and 'shared 245/256' in r['plan'] and r['words'] > 0 and r['clocks'] > 0)
    check('the planner keeps the widths: batches submit lw2, lw1, then the lw0 jobs', 'wb_heavy7 lw2, wb_heavy7 lw1, wb_heavy7 lw0, wb_heavy7 lw0, wb_heavy7 lw0' in r['plan'])
    # the answers: every job's expected value is the made kind's Python reference, run here on the reference interpreter as well (the made kind's own verify() did 14 runs)
    import progs, jobiss, jobio as J
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sh = S.Shell()
        for l in ls: sh.execute(l)
        tasks = sh.tasks()
    ok = True
    for t in tasks:
        job = J.Job(0, t.kind, list(t.inputs), 1, arg=t.arg)
        st, n, out, steps = jobiss.reference(J.build_link([job], shared_words=256), job)
        ok = ok and st == 1 and out == [w & 0xFFFFFFFF for w in progs.expected(t.kind, list(t.inputs), 1, t.arg)]
    check('all 10 jobs: the interpreter and the Python answer agree', ok and len(tasks) == 10)
    # the committed files are what the generator makes (the heads carry an estimate, the job lines are compared)
    def body(path): return [l.rstrip('\n') for l in open(path) if not l.startswith('#') and l.strip() and l.strip() != 'plan']
    for name, nb in (('window_run_medium_v1.score', 20), ('window_run_big_v1.score', 100)):
        p = os.path.join(HERE, name)
        check('%s is committed and is the generator output for %d batches' % (name, nb), os.path.exists(p) and body(p) == B.lines(nb) and open(p).read().rstrip().endswith('plan'))
finally:
    for n in set(S.made_names()) - had:
        for f in glob.glob(os.path.join(S.MADE, n + '.*')): os.remove(f)
print('FAILED %d' % bad if bad else 'all ok'); sys.exit(1 if bad else 0)
