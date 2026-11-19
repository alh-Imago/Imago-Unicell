"""lengthest_v1: the host-only length estimate, the dispatcher model and the width chooser (ledger #1411).  No board.  python3 test_lengthest_v1.py"""
import os, sys, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import scbatch, lengthest_v1 as E
bad = 0
def check(name, cond):
    global bad
    print('%-108s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)
P = json.load(open(os.path.join(HERE, 'profiles', 'example_2x8_nu3_v2.json')))
M = E.fit_model(P)
def tk(f): return scbatch.load_jobs(os.path.join(HERE, f))

# 1. length = instructions of the reference interpreter; the crc32 line fits the single-job runs
st = {L: E.task_steps(tk('jobs_curve_L%d_N1.json' % L)[0]) for L in (8, 20, 40, 80)}
check('instruction counts of the crc32 curve jobs: 1496 3721 7371 14671', [st[L] for L in (8, 20, 40, 80)] == [1496, 3721, 7371, 14671])
check('fit: about 133.5 clocks per instruction and 974 overhead', abs(M.cpi - 133.49) < 0.05 and abs(M.overhead - 974) < 5)
errs = [abs(M.clocks(M.work('crc32', st[L]), w) / cl[w] - 1) for L, N, cl in P['raw'] if N == 1 for w in range(4)]
check('single crc32 jobs, 16 runs (4 lengths x 4 widths): every one within 2%% of the card (worst %.1f%%)' % (100 * max(errs)), max(errs) < 0.02)

# 2. batches of identical jobs of the profile (the model of #1397 again, now from instruction counts)
e2 = []
for L, N, cl in P['raw']:
    for w, c in enumerate(cl):
        if w == 1 and N >= 4: continue                       # lw1 with 4 or more jobs is unexplained (#1399); not claimed
        e2.append(abs(E.simulate(M, [(M.work('crc32', st[L]), w)] * N) / c - 1))
check('identical-job batches (lw1 with N >= 4 left out, as in #1399): mean error under 2%%, worst under 6%% (%.1f%%, %.1f%%)' % (100 * sum(e2) / len(e2), 100 * max(e2)), sum(e2) / len(e2) < 0.02 and max(e2) < 0.06)

# 3. the dispatcher model
m4 = E.Model(100.0, 0.0, [1, 2, 4, 8], {1: 4, 2: 2, 3: 1}, 8)
check('one job: its own time', abs(E.simulate(m4, [(800.0, 0)]) - 800) < 1e-9 and abs(E.simulate(m4, [(800.0, 2)]) - 200) < 1e-9)
check('eight width-0 jobs run together; the ninth waits for a slice', E.simulate(m4, [(100.0, 0)] * 8) == 100 and E.simulate(m4, [(100.0, 0)] * 9) == 200)
check('head-of-line: a width-3 job at the head waits for ALL slices while narrow jobs behind it idle', E.simulate(m4, [(100.0, 0), (80.0, 3), (100.0, 0)]) > 100 + 10 + 100 - 1)
check('a width-2 job takes an aligned group of 4 (two of them fill 8 slices, a third waits)', E.simulate(m4, [(400.0, 2)] * 2) == 100 and E.simulate(m4, [(400.0, 2)] * 3) == 200)
try: E.simulate(m4, [(1.0, 4)]); ok = False
except ValueError: ok = True
check('a width the build cannot do is refused', ok)

# 4. the order is the planner's
check("submit order: equal widths keep (kind, job) order; mixed widths go widest first", E.submit_order(['b', 'a'], [1, 1], [0, 0]) == [1, 0] and E.submit_order(['a', 'b'], [5, 9], [0, 2]) == [1, 0])

# 5. the chooser on the two batches measured on the card (two-unit build): #1407 and #1408
m2 = M.with_units(2)
def run(f, margin=0.10):
    ts = tk(f); K = [t.kind for t in ts]; W = [m2.work(t.kind, E.task_steps(t)) for t in ts]
    return ts, K, W, E.choose_widths(m2, K, W, None, 'auto', margin)
ts, K, W, ws = run('jobs_order_test2.json')
check('batch of #1408 (one long vsum, eight tiny vgain): the long job wide (lw2), the tiny ones lw0 = the measured winner (36,230 vs 48,262 all lw2)', ws[K.index('vsum')] == 2 and all(w == 0 for w, k in zip(ws, K) if k == 'vgain'))
ts, K, W, ws = run('jobs_order_test.json')
check('batch of #1407 (balanced): all lw2 = the measured winner (65,313; the mix measured 72,086)', set(ws) == {2})
ts, K, W, ws0 = run('jobs_order_test.json', margin=0)
check('the same batch without the margin guard picks the mix (that is what the guard is for)', len(set(ws0)) > 1)
ts, K, W, ws = run('jobs_order_test2.json')
check('modelled time of the chosen widths <= every uniform width', all(E.batch_time(m2, K, W, ws) <= E.batch_time(m2, K, W, [u] * len(K)) + 1e-6 for u in range(4)))
# fixed widths and unknown lengths
f = [None] * len(K); f[0] = 1
check('a fixed width is never changed', E.choose_widths(m2, K, W, f)[0] == 1)
W2 = W[:]; W2[1] = None
check('a job with no length stays at width 0', E.choose_widths(m2, K, W2)[1] == 0)

# 6. the other kinds: a measured CPI per kind is used
mk = E.Model(100.0, 0.0, [1, 2], {1: 2}, 2, 2, {'vsum': 200.0})
check('kind_cpi: vsum 200 clocks per instruction, other kinds the crc32 value', mk.work('vsum', 10) == 2000 and mk.work('crc32', 10) == 1000)
raw = 'jobs_cpi_vsum.json lw0 clocks=%d  1 of 1 jobs correct\njobs_cpi_vsum.json lw0 clocks=%d  1 of 1 jobs correct\n' % (M.overhead + 635 * 150, M.overhead + 635 * 152)
kc = E.fit_kinds(P, raw)
check('fit_kinds: median of the repeats, (clocks - overhead) / steps -> vsum about 151', abs(kc['vsum'] - 151) < 0.1)
try: E.fit_kinds(P, 'jobs_cpi_vsum.json lw0 clocks=99  0 of 1 jobs correct'); ok = False
except ValueError: ok = True
check('a run with a wrong answer is an error, not a number', ok)

# 7. the planner
def cli(*a): return subprocess.run([sys.executable, os.path.join(HERE, 'scblocks.py'), '--plan', *a], capture_output=True, text=True, cwd=HERE)
base = ['jobs_order_test2.json', '--blocks', '1', '--lw', 'auto', '--slices', '8', '--unit-lw', '3']
o = cli(*base, '--estimate'); check('--estimate without --profile is refused', 'needs --profile' in o.stdout)
o = cli(*base, '--profile', 'example_2x8_nu3_v2', '--estimate')
check('--plan --estimate: the vsum job lw2 and submitted first, the vgain jobs lw0', o.returncode == 0 and 'vsum:lw2' in o.stdout and 'submit order: vsum lw2, vgain lw0' in o.stdout)
o = cli(*base, '--profile', 'example_2x8_nu3_v2')
check('without --estimate the profile rule of #1401 is used (one width for the batch)', 'jobs -> lw' in o.stdout and 'estimate (' not in o.stdout)
d = json.load(open(os.path.join(HERE, 'jobs_order_test2.json')))
for j in d['jobs']: j['lw'] = 'auto'
d['jobs'][1]['lw'] = 3                                                    # job 1 (a tiny vgain) asks for lw3 itself
import tempfile
with tempfile.NamedTemporaryFile('w', suffix='.json', dir=HERE, delete=False) as fh: json.dump(d, fh); name = fh.name
try: o = cli(os.path.basename(name), '--blocks', '1', '--slices', '8', '--unit-lw', '3', '--profile', 'example_2x8_nu3_v2', '--estimate')
finally: os.remove(name)
check('a width written in the job file stays (job 1 at lw3) while the jobs that say "auto" are chosen', o.returncode == 0 and 'vgain:lw3' in o.stdout and 'estimate (' in o.stdout)
print('FAILED %d' % bad if bad else 'ALL PASSED'); sys.exit(1 if bad else 0)
