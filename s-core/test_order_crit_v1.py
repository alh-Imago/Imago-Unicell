"""jobcomp_v2: submit order and the critical flag; scblocks --submit-order / --crit (ledger #1406).  No board.  python3 test_order_crit_v1.py"""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import scbatch, scblocks as SB, batch as B, jobcomp as C1, jobcomp_v2 as C2
bad = 0
def check(name, cond):
    global bad
    print('%-104s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)
def subs(plan, k=0): return [B.decode(st)[1] for st in plan.scripts[k].steps if st[0] == B.SUBMIT]
def tasks(f='jobs_order_test.json'): return scbatch.load_jobs(os.path.join(HERE, f))

# 1. nothing changes by default: same image as jobcomp.compile for the existing sets
for f in ('jobs_telemetry.json', 'jobs_many_small.json'):
    t = tasks(f)
    for x in t: x.lw = 1
    p1 = C1.compile(t[:12]); p2 = C2.compile(t[:12])
    check('%s: compile(order=kind, no crit) is identical to jobcomp.compile (image, steps, batches)' % f, p1.image == p2.image and p1.steps == p2.steps and p1.batches == p2.batches)

# 2. submit order
t = tasks(); p = C2.compile(t); s = subs(p)
check('default order: 9 jobs in one batch, the wide vsum job is submitted LAST (kinds sort vgain < vsum)', len(p.scripts) == 1 + 0 and len(s) == 9 and s[-1]['lw'] == 2 and all(f['lw'] == 0 for f in s[:-1]))
t = tasks(); p = C2.compile(t, order='width'); s = subs(p)
check("order='width': the wide job is submitted FIRST", s[0]['lw'] == 2 and all(f['lw'] == 0 for f in s[1:]))
check('task ids are still 0..8, each once (only the order of the steps changed)', sorted(f['tid'] for f in s) == list(range(9)))
try: C2.compile(tasks(), order='x'); ok = False
except C2.JobCompError: ok = True
check('an unknown order is refused', ok)

# 3. the critical flag: job file, bit 12 of w2, automatic mode
t = tasks(); t[3].crit = 1; p = C2.compile(t); s = subs(p)
check('a job with crit = 1 is submitted with the critical bit; the others without', sum(f['crit'] for f in s) == 1)
t = tasks(); plans = SB.plan_blocks(t, 1, crit_mode='wide'); s = subs(plans[0].plan)
check("--crit wide: only the wide job of a mixed-width batch is critical", sum(f['crit'] for f in s) == 1 and [f['lw'] for f in s if f['crit']] == [2])
t = tasks()
for x in t: x.lw = 1
plans = SB.plan_blocks(t, 1, crit_mode='wide')
check('--crit wide: nothing critical when every job of a batch has the same width', not any(f['crit'] for bp in plans for k in range(len(bp.plan.scripts)) for f in subs(bp.plan, k)))
t = tasks()
for x in t: x.lw = 1
t[0].crit = 1; plans = SB.plan_blocks(t, 1, crit_mode='wide')
check('a crit flag set by the user stays when --crit wide does nothing', sum(f['crit'] for bp in plans for k in range(len(bp.plan.scripts)) for f in subs(bp.plan, k)) == 1)

# 4. command line
def cli(*a): return subprocess.run([sys.executable, os.path.join(HERE, 'scblocks.py'), '--plan', *a], capture_output=True, text=True, cwd=HERE)
o = cli('jobs_order_test.json', '--blocks', '1', '--submit-order', 'width', '--crit', 'wide')
check('CLI --plan shows "vsum lw2 CRIT" first, then the vgain jobs', o.returncode == 0 and 'submit order: vsum lw2 CRIT, vgain lw0' in o.stdout)
o = cli('jobs_order_test.json', '--blocks', '1')
check('CLI --plan default order: vgain jobs first, vsum last', 'submit order: vgain lw0' in o.stdout and o.stdout.strip().split('\n')[-1].endswith('vsum lw2'))
# 5. crit in the job file
import json, tempfile
d = json.load(open(os.path.join(HERE, 'jobs_order_test.json'))); d['jobs'][0]['crit'] = 1
with tempfile.NamedTemporaryFile('w', suffix='.json', dir=HERE, delete=False) as fh: json.dump(d, fh); name = fh.name
try: t = scbatch.load_jobs(name); ok = t[0].crit == 1 and all(x.crit == 0 for x in t[1:])
finally: os.remove(name)
check('"crit": 1 in the job file is read', ok)
print('FAILED %d' % bad if bad else 'ALL PASSED'); sys.exit(1 if bad else 0)
