"""score_shell_v4 waves (ledger #1547): a design too big for one run, many jobs, one huge data set, and a pipeline whose jobs read earlier answers.  No card: a fake card
answers each wave with the Python answers of the jobs it was given (so what is fed to it is what it computes on), can refuse a wave as too big for far RAM, or give a
wrong answer.  What this cannot show: that the real card behaves like the fake (the planner and scblocks are the real ones up to the call that talks to the card).  python3 test_score_waves_v1.py"""
import os, sys, io, json, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import score_shell_v4 as S, scwaves_v1 as WV, scbatch
bad = 0
def check(name, cond):
    global bad
    print('%-118s %s' % (name, 'ok' if cond else 'FAIL')); bad += (not cond)
def fresh():
    buf = io.StringIO(); sh = S.Shell(out=buf); sh.set['out'] = os.path.join(tempfile.mkdtemp(prefix='score_waves_'), 'r.json'); return sh, buf
def do(sh, buf, text): buf.truncate(0); buf.seek(0); sh.run_lines(text); return buf.getvalue()
class FakeCard:
    """answers a run: the Python answer of every job in the job file it is given; cap = most jobs it takes at once (else the far-RAM error); wrong = {call number: add 1 to every answer}"""
    def __init__(self, cap=None, wrong=(), fail_call=None): self.calls = []; self.cap = cap; self.wrong = set(wrong); self.fail_call = fail_call
    def __call__(self, args):
        tmp = args[1]; out = args[args.index('--out') + 1]; tasks = scbatch.load_jobs(tmp); self.calls.append(len(tasks)); n = len(self.calls)
        if '--far-words' in args:                                   # the real planner decides, as the real run would (before it touches the card)
            import scblocks, contextlib
            rest = args[2:]; k = rest.index('--out'); del rest[k:k + 2]; b = io.StringIO()
            with contextlib.redirect_stdout(b): rc = scblocks.main(['--plan', tmp] + rest)
            if rc: return rc, b.getvalue()
        if self.cap and len(tasks) > self.cap: return 2, 'block 0: its far-RAM area ends at 0x3000, past the far RAM (0x2400 words)\n'
        if self.fail_call == n: return 1, 'batch stopped: error 6\n'
        add = 1 if n in self.wrong else 0
        json.dump([{'job': i, 'kind': t.kind, 'result': [(w + add) & 0xFFFFFFFF for w in t.expected()]} for i, t in enumerate(tasks)], open(out, 'w'))
        return 0, 'all 1 blocks finished in 0.1 s\n  block 0: %d jobs, 10 steps, %d clocks = 0.1 ms\n%d of %d jobs correct\n' % (len(tasks), 100 * len(tasks), len(tasks), len(tasks))

# ---- the engine on its own
fits7 = lambda ids: len(ids) <= 7
check('waves: 20 independent jobs, 7 fit at once -> 7, 7, 6', [len(w) for _, w in WV.plan_waves([{} for _ in range(20)], fits7)] == [7, 7, 6])
check('waves: every size from 1 to 100 is cut into the fewest waves that fit, nothing lost or repeated', all(sum(len(w) for _, w in WV.plan_waves([{} for _ in range(n)], fits7)) == n and len(WV.plan_waves([{} for _ in range(n)], fits7)) == -(-n // 7) for n in list(range(1, 30)) + [50, 99, 100]))
check('levels: a job is one stage after the latest job it reads from', WV.levels([{}, {'from': 0}, {'from': 0, 'argfrom': 1}, {}]) == [[0, 3], [1], [2]])
for bad_jobs, word in (([{'from': 1}, {'from': 0}], 'circle'), ([{'from': 5}], 'does not exist'), ([{'from': 0}], 'itself')):
    try: WV.levels(bad_jobs); ok = False
    except WV.WaveError as e: ok = word in str(e)
    check('levels: %s is refused with a reason (%s)' % (bad_jobs, word), ok)
try: WV.plan_waves([{}], lambda ids: False); ok = False
except WV.WaveError as e: ok = 'does not fit' in str(e)
check('waves: a single job that fits nowhere is an error, not an endless loop', ok)
check('resolve: from= puts the answer words in as inputs, argfrom= the first word as arg; the original job is untouched', WV.resolve({'kind': 'k', 'from': 0, 'argfrom': 1}, {0: [5, 6], 1: [9]}) == {'kind': 'k', 'inputs': [5, 6], 'arg': 9})

# ---- 1. many independent jobs, the host planner cuts them by far RAM
sh, buf = fresh(); card = FakeCard(); sh._call_scblocks = card
do(sh, buf, '; '.join('add vsum seq %d 10 1' % i for i in range(40))); sh.set['far-words'] = 0x2300
o = do(sh, buf, 'waves'); check('waves command: 40 jobs, far RAM 0x2300 -> 3 waves (14, 14, 12), no card touched', '3 waves' in o and 'jobs 0-13 (14)' in o and not card.calls)
o = do(sh, buf, 'run')
check('run: the whole design is tried once (the real planner refuses: far RAM), then runs in 3 waves in order, each wave one call to the card with its own jobs', card.calls == [40, 14, 14, 12] and 'wave 3:' in o)
res = json.load(open(sh.set['out']))
check('run: the results of all 40 jobs are in one result file with the job numbers of the whole design', [r['job'] for r in res] == list(range(40)) and res[39]['result'] == [sum(range(39, 49))])
check('run: the final comparison covers all 40 jobs and every one matches', '40 of 40 jobs match' in o and 'DIFFERENT' not in o and '40 of 40 jobs correct' in o)
check('run: the run log records one run of 3 waves with the summed slowest-block clocks', sh.runlog[-1]['waves'] == 3 and sh.runlog[-1]['correct'] == 40 and sh.runlog[-1]['slowest'] == 14 * 100 + 14 * 100 + 12 * 100 and sh.runlog[-1]['finished'])
# a design that fits is one ordinary run, as before
sh1, buf1 = fresh(); c1 = FakeCard(); sh1._call_scblocks = c1; o = do(sh1, buf1, 'add vsum 1 2 3; add vsum 4 5; run')
check('a design that fits is a single call, no waves line (the proven path is unchanged)', c1.calls == [2] and 'waves:' not in o and 'waves' not in sh1.runlog[-1])

# ---- 2. the host plan is too hopeful: the card refuses, the wave is halved until it fits
sh2, buf2 = fresh(); c2 = FakeCard(cap=5); sh2._call_scblocks = c2
do(sh2, buf2, '; '.join('add vsum seq %d 6 1' % i for i in range(23)))
o = do(sh2, buf2, 'run')
check('card refuses the whole design (far RAM): the front end falls back to waves by itself and says why', 'does not fit the far RAM in one run' in o and 'waves:' in o)
check('card refuses a wave that was too big: it is split in two and the parts go on, until every wave fits', 'did not fit far RAM on the card; split into' in o and max(n for n in c2.calls[1:] if n <= 5) <= 5 and '23 of 23 jobs match' in o)
check('the halved waves still cover every job exactly once (sum of the wave sizes that were accepted = 23)', sum(n for n in c2.calls if n <= 5) == 23)

# ---- 3. one huge data set: addbig pieces are carried in waves and combined at the end
sh3, buf3 = fresh(); c3 = FakeCard(); sh3._call_scblocks = c3
do(sh3, buf3, 'addbig vsum seq 1 3000 1'); n_pieces = len(sh3.jobs); sh3.set['far-words'] = 0x2400
o = do(sh3, buf3, 'run')
check('addbig: 3000 words are cut into pieces and the pieces run in more than one wave', n_pieces > 16 and len(c3.calls) > 2 and sum(c3.calls[1:]) == n_pieces)
check('addbig: the answers of the pieces are combined across the waves and agree with the sum of the whole data (4501500)', 'MATCH' in o and 'DIFFERENT' not in o and '4501500' in o)

# ---- 4. a pipeline: each stage reads the answers of the one before
sh4, buf4 = fresh(); c4 = FakeCard(); sh4._call_scblocks = c4
do(sh4, buf4, 'add vsum seq 1 20 1; add vscale from=0 arg=3; add vsum from=1')
o = do(sh4, buf4, 'list'); check('list: a job that reads another shows where its input comes from', 'answer of job 0' in o and 'answer of job 1' in o)
o = do(sh4, buf4, 'waves'); check('waves: 3 stages, one wave each', '3 waves' in o and 'stage 1' in o and 'stage 3' in o)
o = do(sh4, buf4, 'run'); res4 = {r['job']: r['result'] for r in json.load(open(sh4.set['out']))}
check('run: stage by stage, one call to the card each, and the last stage used the real answer of the stage before', c4.calls == [1, 1, 1] and res4[2] == [sum(res4[1])] and res4[0] == [210])
check('run: the pipeline matches the reference chain at every stage', '3 of 3 jobs match' in o and 'DIFFERENT' not in o)
sh5, buf5 = fresh(); c5 = FakeCard(wrong=[1]); sh5._call_scblocks = c5
do(sh5, buf5, 'add vsum seq 1 20 1; add vscale from=0 arg=3; add vsum from=1'); o = do(sh5, buf5, 'run')
check('a wrong answer in stage 1 is fed on and shows as DIFFERENT (stage 1 and the stages built on it), not hidden', o.count('DIFFERENT') >= 2)
sh6, buf6 = fresh(); sh6._call_scblocks = FakeCard(fail_call=2)
do(sh6, buf6, 'add vsum seq 1 20 1; add vscale from=0 arg=3; add vsum from=1'); o = do(sh6, buf6, 'run')
check('a wave that does not finish stops the run with its number, nothing is compared, and the run log marks it not finished', 'wave 2 did not finish cleanly' in o and 'MATCH' not in o and sh6.runlog[-1]['finished'] is False)
o = do(sh4, buf4, 'add vsum from=9'); check('add from=J: a job that does not exist yet is refused', 'no such earlier job' in o)
o = do(sh4, buf4, 'add vsum 1 2 from=0'); check('add from=J with numbers is refused', 'takes its inputs from the answers' in o)
p = os.path.join(tempfile.mkdtemp(), 'pipe.json'); do(sh4, buf4, 'save ' + p)
shr, bufr = fresh(); do(shr, bufr, 'open ' + p); check('save and open keep the reads (from, argfrom, no literal inputs)', shr.jobs[1].get('from') == 0 and 'inputs' not in shr.jobs[1] and shr.jobs[1].get('arg') == 3)
shr._call_scblocks = FakeCard(); o = do(shr, bufr, 'run'); check('an opened pipeline file runs the same way', '3 of 3 jobs match' in o)
cyc = [{'kind': 'vsum', 'from': 1}, {'kind': 'vsum', 'from': 0}]; shc, bufc = fresh(); shc.jobs = cyc; o = do(shc, bufc, 'run'); check('a circle of reads is refused with the jobs named', 'circle' in o)
# ---- in a batch: the summary says waves
shb, bufb = fresh(); shb._call_scblocks = FakeCard(); bp = os.path.join(tempfile.mkdtemp(), 'w.score'); open(bp, 'w').write('add vsum seq 1 20 1\nadd vscale from=0 arg=3\nrun\n')
o = do(shb, bufb, 'batch ' + bp); check('batch: the run summary names the waves (2 stages, 2 waves) and the run is counted once', 'run 1: 2 of 2 jobs correct' in o and ', 2 waves' in o and len(shb.runlog) == 1)
# ---- `many`: a big design in one line
import time as _t
shm, bufm = fresh(); o = do(shm, bufm, 'many 5 vsum seq 1 4 1')
check('many: 5 jobs of 4 words, job i starts at START + i*COUNT (no repeated data), expected answers right', len(shm.jobs) == 5 and shm.jobs[2]['inputs']['seq'] == [9, 4, 1] and 'added 5 jobs' in o)
do(shm, bufm, 'new'); do(shm, bufm, 'many 3 vsum seq 10 4 1 stride=1 arg=2'); check('many: stride= and arg= are used', [j['inputs']['seq'][0] for j in shm.jobs] == [10, 11, 12] and shm.jobs[0]['arg'] == 2)
o = do(shm, bufm, 'many 0 vsum seq 1 4 1'); check('many: N = 0 is refused', 'N must be' in o)
o = do(shm, bufm, 'many 3 vsum 1 2 3'); check('many: without seq gives the usage', 'usage: many' in o)
o = do(shm, bufm, 'many 3 nosuchkind seq 1 4 1'); check('many: an unknown kind is refused before anything is added', 'unknown kind' in o and len(shm.jobs) == 3)
do(shm, bufm, 'new'); t0 = _t.time(); do(shm, bufm, 'many 1000 vsum seq 1 40 1'); w = shm._plan_waves() if False else None
check('many: 1000 jobs are added in one check, in a few seconds (%.1f s)' % (_t.time() - t0), len(shm.jobs) == 1000 and _t.time() - t0 < 30)
shm.set['far-words'] = 0x3000; o = do(shm, bufm, 'waves'); check('many then waves: 1000 jobs make a wave plan on the host without a card', 'wave plan: 1000 jobs in' in o)
print('FAILED %d' % bad if bad else 'ALL PASSED'); sys.exit(1 if bad else 0)
