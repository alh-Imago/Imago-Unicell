"""The own-program examples of ledger #1418 (vmin, vxor) on the host: registry checks, the reference interpreter against the Python answers, the edge cases.  No board.  python3 test_own_examples_v1.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import scbatch, jobio as J, jobiss, jobcomp_v2 as C
bad = 0
def check(name, cond):
    global bad
    print('%-100s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)
tasks = scbatch.load_jobs(os.path.join(HERE, 'jobs_own_examples2.json'))
check('jobs_own_examples2.json loads (register() ran: assembles, fits, trial run, agrees with the Python answer)', len(tasks) == 5)
def iss(t, out_len=None):
    j = J.Job(0, t.kind, t.inputs, out_len if out_len is not None else t.out_len, arg=t.arg)
    return jobiss.reference(J.build_link([j]), j)
for i, t in enumerate(tasks):
    st, n, out, steps = iss(t)
    check('job %d %s %s arg %d: interpreter gives status 1 and the Python answer %s' % (i, t.kind, t.inputs[:4], t.arg, t.expected()[:4]), st == 1 and out == t.expected() and n == len(t.expected()))
st, n, out, steps = iss(tasks[3], out_len=2)
check('vxor with room for 2 of 4 outputs: refused (status 2, nothing produced)', st == 2 and n == 0)
check('vmin of an empty input is 0; of all-ones words is the smaller one (4294967294)', tasks[2].expected() == [0] and tasks[1].expected() == [4294967294])
p = C.compile(tasks)
check('the five jobs compile into one plan (one batch)', len(p.scripts) >= 1)
print('FAILED %d' % bad if bad else 'ALL PASSED'); sys.exit(1 if bad else 0)
