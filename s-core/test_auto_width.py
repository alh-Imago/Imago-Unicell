"""Automatic width (ledger #1388): scblocks.resolve_auto and the lw field checks.  No board, no simulator.  python3 test_auto_width.py"""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import scbatch, scblocks as SB, jobcomp as C
bad = 0
def check(name, cond):
    global bad
    print('%-90s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)
def jobs(lw='auto'):
    t = scbatch.load_jobs(os.path.join(HERE, 'jobs_telemetry.json'))
    for x in t: x.lw = lw
    return t
quiet = lambda *a, **k: None
for S, U, want in [(4, 2, 2), (8, 3, 3), (4, 3, 2), (16, 2, 2), (2, 3, 1), (1, 3, 0)]:
    t = jobs(); SB.resolve_auto(t, S, U, say=quiet)
    check('slices %d, unit 2**%d lanes -> every job lw %d' % (S, U, want), {x.lw for x in t} == {want})
t = jobs(); t[0].lw = 1; SB.resolve_auto(t, 8, 3, say=quiet)
check('an explicit width is kept (job 0 lw 1, the rest auto -> 3)', t[0].lw == 1 and {x.lw for x in t[1:]} == {3})
t = jobs(); SB.resolve_auto(t, 8, 3, min_cost=150, say=quiet)
check('--auto-min-cost: cheap jobs stay at 0, costly ones widen', {x.lw for x in t} == {0, 3} and all((x.lw == 3) == (SB.cost(x) >= 150) for x in t))
t = jobs(0); t[0].lw = 3
try: SB.resolve_auto(t, 4, 2, say=quiet); ok = False
except C.JobCompError: ok = True
check('an explicit lw wider than the block is refused (it could never be placed)', ok)
try: C.Task('vsum', [1], lw=7); ok = False
except C.JobCompError: ok = True
check('Task(lw=7) is refused', ok)
try: C.compile([C.Task('vsum', [1], lw='auto')]); ok = False
except C.JobCompError: ok = True
check('compile() refuses an unresolved "auto"', ok)
d = json.load(open(os.path.join(HERE, 'jobs_telemetry.json'))); d['jobs'][0]['lw'] = 'auto'; d['jobs'][1]['lw'] = 2
p = tempfile.mktemp(suffix='.json'); json.dump(d, open(p, 'w'))
# the job file refers to programs by relative path: put the temp file next to the originals
q = os.path.join(HERE, '_tmp_auto_jobs.json'); json.dump(d, open(q, 'w'))
try: t = scbatch.load_jobs(q)
finally: os.remove(q); os.remove(p)
check('job file: "lw": "auto" and "lw": 2 are read', t[0].lw == 'auto' and t[1].lw == 2 and t[2].lw == 0)
print('RESULT:', 'PASS' if not bad else 'FAIL (%d)' % bad); sys.exit(1 if bad else 0)
