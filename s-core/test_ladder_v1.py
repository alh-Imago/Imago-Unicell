"""The ladder of LADDER.md on the host: the job files load, give the answers the guide promises, compile; ladder_show compares a result file; the exercise of step 5 works.  No board.  python3 test_ladder_v1.py"""
import os, sys, json, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import scbatch, jobcomp_v2 as C, jobio as J, jobiss, progs
bad = 0
def check(name, cond):
    global bad
    print('%-104s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)
def want(f): return [t.expected() for t in scbatch.load_jobs(os.path.join(HERE, f))]
check('step 1: vsum 1+2+3+4 = 10', want('ladder_1_one_job.json') == [[10]])
check('step 2: 60, 99 and the running total 1 3 6 10 15', want('ladder_2_three_jobs.json') == [[60], [99], [1, 3, 6, 10, 15]])
check('step 3: 5050, 134650, 242, 9649', want('ladder_3_more_data.json') == [[5050], [134650], [242], [9649]])
check('step 5: vcount 3, 0, 50', want('ladder_5_my_program.json') == [[3], [0], [50]])
for f, nb in (('ladder_1_one_job.json', 1), ('ladder_2_three_jobs.json', 1), ('ladder_3_more_data.json', 1), ('ladder_5_my_program.json', 1)):
    p = C.compile(scbatch.load_jobs(os.path.join(HERE, f))); check('%s compiles (%d batches)' % (f, len(p.scripts)), len(p.scripts) >= 1)
check('step 3 needs two batches (the host splits it)', len(C.compile(scbatch.load_jobs(os.path.join(HERE, 'ladder_3_more_data.json'))).scripts) == 2)
# ladder_show: right and wrong card results
def show(f, res):
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as fh: json.dump(res, fh); n = fh.name
    try: return subprocess.run([sys.executable, os.path.join(HERE, 'ladder_show.py'), os.path.join(HERE, f), n], capture_output=True, text=True)
    finally: os.remove(n)
r = show('ladder_2_three_jobs.json', [{'job': 0, 'kind': 'vsum', 'result': [60]}, {'job': 1, 'kind': 'vmax', 'result': [99]}, {'job': 2, 'kind': 'vprefix', 'result': [1, 3, 6, 10, 15]}])
check('ladder_show: a right result file says MATCH for all three jobs, exit 0', r.returncode == 0 and r.stdout.count('MATCH') == 3 and '3 of 3 jobs match' in r.stdout)
r = show('ladder_2_three_jobs.json', [{'job': 0, 'kind': 'vsum', 'result': [60]}, {'job': 1, 'kind': 'vmax', 'result': [98]}, {'job': 2, 'kind': 'vprefix', 'result': [1, 3, 6, 10, 15]}])
check('ladder_show: a wrong number says DIFFERENT and exit 1', r.returncode == 1 and 'DIFFERENT' in r.stdout and '2 of 3 jobs match' in r.stdout)
# the exercise of step 5: count the inputs SMALLER than arg, by swapping one comparison
src = open(os.path.join(HERE, 'programs', 'vcount.s')).read()
assert 'bgeu t5,t0,skip' in src
mine = src.replace('bgeu t5,t0,skip', 'bgeu t0,t5,skip')
def vcountless(inputs, arg, out_len): return [sum(1 for x in inputs if x < (arg & 0xFFFFFFFF))]
progs.register('vcountless', mine, expect=vcountless, out=1, replace=True)
j = J.Job(0, 'vcountless', [5, 50, 500, 5000], 1, arg=100)
st, n, out, steps = jobiss.reference(J.build_link([j]), j)
check('step 5 exercise: swapping the comparison counts the inputs below arg (2 of 5,50,500,5000 below 100), interpreter agrees', st == 1 and out == [2] and vcountless([5, 50, 500, 5000], 100, 1) == [2])
print('FAILED %d' % bad if bad else 'ALL PASSED'); sys.exit(1 if bad else 0)
