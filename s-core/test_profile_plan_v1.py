"""Per-batch automatic width from a card profile (scblocks --lw auto --profile, ledger #1401).  No board.  python3 test_profile_plan_v1.py"""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import scbatch, scblocks as SB, jobcomp as C, sc_calibrate_v1 as K
bad = 0
def check(name, cond):
    global bad
    print('%-100s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)
quiet = lambda *a, **k: None
prof = K.load_profile(os.path.join(HERE, 'profiles', 'example_2x8_nu3_v2.json'))
def tasks(f, lw='auto'):
    t = scbatch.load_jobs(os.path.join(HERE, f))
    for x in t: x.lw = lw
    return t

# every job of a batch gets the profile's width for that many jobs (capped at the unit width and the block); the batches are the ones compile() makes
for f in ('jobs_many_small.json', 'jobs_telemetry.json', 'jobs_fu_G.json'):
    t = tasks(f); plans = SB.plan_blocks(t, 2, profile=prof, slices=8, unit_lw=3, say=quiet); ok = True; n = 0
    for bp in plans:
        for b in bp.plan.batches:
            ws = {t[bp.task_ids[i]].lw for i in b}; n += 1
            ok &= (ws == {min(K.best_width(prof, len(b)), 3)})
    check('%s: all %d batches got one width = profile.best_width(jobs in the batch)' % (f, n), ok and not any(x.lw == 'auto' for x in t))

# explicit widths are kept
t = tasks('jobs_many_small.json'); t[0].lw = 1; SB.plan_blocks(t, 2, profile=prof, slices=8, unit_lw=3, say=quiet)
check('an explicit width (job 0 at lw 1) is kept, the rest still resolved', t[0].lw == 1 and all(isinstance(x.lw, int) for x in t))

# the unit width caps the profile's choice (a profile saying lw 3 on a build whose unit is 4 lanes would never be placed)
t = tasks('jobs_telemetry.json'); SB.plan_blocks(t, 2, profile=prof, slices=8, unit_lw=2, say=quiet)
check('capped at the unit width: unit 2**2 lanes -> no job above lw 2', max(x.lw for x in t) == 2)

# a profile for another number of slices is refused
t = tasks('jobs_telemetry.json')
try: SB.plan_blocks(t, 2, profile=prof, slices=4, unit_lw=2, say=quiet); ok = False
except C.JobCompError: ok = True
check('a profile made for 8 slices is refused on a 4-slice board', ok)

# without a profile an unresolved "auto" is still refused by compile (the old safety)
try: SB.plan_blocks(tasks('jobs_telemetry.json'), 2); ok = False
except C.JobCompError: ok = True
check('no profile, auto not resolved -> compile refuses (unchanged)', ok)

# command line
def cli(*a): return subprocess.run([sys.executable, os.path.join(HERE, 'scblocks.py'), '--plan', *a], capture_output=True, text=True, cwd=HERE)
o = cli('jobs_many_small.json', '--blocks', '2', '--lw', 'auto', '--profile', 'profiles/example_2x8_nu3_v2.json')
check('CLI --plan prints the width per batch', o.returncode == 0 and 'batch 0: 6 jobs -> lw 2' in o.stdout and 'batch 2: 8 jobs -> lw 0' in o.stdout)
o = cli('jobs_many_small.json', '--blocks', '2', '--lw', 'auto', '--profile', 'profiles/example_2x8_nu3_v2.json', '--auto-min-cost', '5')
check('CLI: --profile with --auto-min-cost is refused', o.returncode == 2)
o = cli('jobs_many_small.json', '--blocks', '2', '--profile', 'profiles/example_2x8_nu3_v2.json')
check('CLI: a profile without --lw auto is not used and says so', o.returncode == 0 and 'no job asks for auto width' in o.stdout)
print('FAILED %d' % bad if bad else 'ALL PASSED'); sys.exit(1 if bad else 0)
