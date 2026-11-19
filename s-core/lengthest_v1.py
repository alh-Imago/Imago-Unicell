"""lengthest_v1: HOST-ONLY estimate of how long a job runs, and a width chooser that uses it (ledger #1411).  No board needed.

  length  = instructions the job executes, counted by running it through the reference interpreter (jobiss.py): exact for the job, no guess.
  clocks  = overhead + length x CPI / speed-up(width)          (CPI = clocks per instruction on one slice, fitted from the single-job runs of a card profile)
  batch   = a small model of the dispatcher (read from the RTL, ledger #1405): jobs are launched in SUBMIT order, each needs an aligned group of 2**w free
            slices (and, for w >= 1, a free fusion unit: at most `at_once[w]` jobs of that width run together); a head that does not fit blocks the queue
            (no skipping).  The model gives the finishing time of the batch for given widths.
  chooser = pick the width of each job (the ones that ask for "auto") that gives the smallest modelled batch time; ties go to the narrower width.

What is measured and what is not: CPI, overhead and the speed-ups come from crc32 single-job runs (#1385..#1397).  Other kinds of jobs are assumed to run at the
same CPI (a check against the batches of #1407/#1408 is in test_lengthest_v1.py and in ledger #1411: it is an estimate, not a measurement).
A job that the interpreter cannot run (multiply/divide, trap) gets no length; the chooser then leaves its width alone."""
import statistics, os
HERE = os.path.dirname(os.path.abspath(__file__))
import jobio as J, jobiss

class NoLength(Exception): pass

_cache = {}
def job_steps(kind, inputs, out_len=None, arg=0, imem=128, dsh=256):
    """instructions executed by one job (reference interpreter).  Raises NoLength if it cannot be run."""
    key = (kind, tuple(inputs), out_len, arg)
    if key not in _cache:
        try:
            job = J.Job(0, kind, list(inputs), out_len if out_len is not None else (len(inputs) if kind == 'vscale' else 1), arg=arg)
            lk = J.build_link([job], shared_words=dsh, code_words=imem)
            st, n, out, steps = jobiss.reference(lk, job)
        except Exception as e: raise NoLength('%s: %s' % (kind, e))
        if st != 1: raise NoLength('%s: reference run finished with status %d' % (kind, st))
        _cache[key] = steps
    return _cache[key]

def task_steps(t, imem=128, dsh=256): return job_steps(t.kind, t.inputs, getattr(t, 'out_len', None), getattr(t, 'arg', 0), imem, dsh)

class Model:
    """work(kind, steps) = clocks one slice needs for the instructions (CPI of the kind; kinds without their own value use the crc32 value); a job at width w
    takes overhead + work / speedup[w].  kind_cpi: {kind: clocks per instruction}, measured by cpi_run_v1.sh (otherwise every kind is assumed to run like crc32)."""
    def __init__(self, cpi, overhead, speedup, at_once, slices, units=None, kind_cpi=None):
        self.cpi, self.overhead, self.speedup, self.at_once, self.slices, self.units = cpi, overhead, list(speedup), dict(at_once), slices, units
        self.kind_cpi = dict(kind_cpi or {})
    def work(self, kind, steps): return steps * self.kind_cpi.get(kind, self.cpi)
    def clocks(self, work, w): return self.overhead + work / self.speedup[w]
    def wmax(self): return min(len(self.speedup) - 1, self.slices.bit_length() - 1)
    def cap(self, w): return self.slices if w == 0 else self.at_once.get(w, max(1, self.slices >> w))
    def with_units(self, units):
        """the same model on a build with another number of fusion units: how many jobs of a width run together = min(units, slices / 2**w) (ledger #1397/#1399: a width-w job needs one unit)"""
        return Model(self.cpi, self.overhead, self.speedup, {w: min(units, max(1, self.slices >> w)) for w in range(1, len(self.speedup))}, self.slices, units, self.kind_cpi)

def fit_model(profile, imem=128, dsh=256):
    """CPI and overhead from the N = 1 runs at width 0 stored in a profile ('raw': [L, N, [clocks per width]]): clocks = overhead + steps x CPI, a straight line
    through the crc32 jobs of lengths 8..80 (ordinary least squares).  Speed-ups and jobs-at-once come from the profile's own fit (sc_calibrate_v1).
    A profile may carry 'kind_cpi' ({kind: clocks per instruction}, from cpi_run_v1.sh)."""
    import scbatch
    pts = []
    for L, N, cl in profile['raw']:
        if N != 1: continue
        f = os.path.join(HERE, 'jobs_curve_L%d_N1.json' % L)             # the very job the card ran
        if not os.path.exists(f): continue
        t = scbatch.load_jobs(f)[0]; pts.append((task_steps(t, imem, dsh), cl[0]))
    if len(pts) < 2: raise NoLength('need at least two jobs_curve_L*_N1.json files next to the program to fit the clocks per instruction')
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cpi = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x in xs); ov = my - cpi * mx
    c = profile['card']
    return Model(cpi, ov, profile['speedup'], {int(k): v for k, v in profile['at_once'].items()}, c['slices'], c.get('units'), profile.get('kind_cpi'))

def simulate(m, jobs):
    """jobs: list of (work, w) in SUBMIT order -> modelled clocks until the last job ends.  Dispatcher rules of #1405: strict queue order, aligned group, best
    fit (the free aligned group inside the smallest free run), a head that does not fit waits for a job to end; a job of width >= 1 also needs a free unit."""
    S = m.slices; free = [True] * S; running = []; t = 0.0; end = 0.0
    def groups(w):
        g = 1 << w; res = []
        for a in range(0, S, g):
            if all(free[a:a + g]):
                lo = a
                while lo > 0 and free[lo - 1]: lo -= 1
                hi = a + g
                while hi < S and free[hi]: hi += 1
                res.append((hi - lo, a))
        return res
    queue = list(jobs)
    while queue or running:
        while queue:
            work, w = queue[0]
            if w > m.wmax(): raise ValueError('width %d is more than this build can do (%d)' % (w, m.wmax()))
            gs = groups(w)
            if not gs or (w >= 1 and sum(1 for r in running if r[2] == w) >= m.cap(w)): break
            _, a = min(gs); queue.pop(0)
            for k in range(a, a + (1 << w)): free[k] = False
            fin = t + m.clocks(work, w); running.append((fin, a, w)); end = max(end, fin)
        if not running: break
        fin, a, w = min(running); running.remove((fin, a, w)); t = fin
        for k in range(a, a + (1 << w)): free[k] = True
    return end

def submit_order(kinds, works, widths, order='auto'):
    """the order the planner writes the SUBMIT steps (jobcomp_v2.submit_sequence): 'kind' = (kind, job number); 'width' = widest, biggest first; 'auto' = width
    when the widths differ, else kind.  (jobcomp sorts by window size for 'width'; here by work, the same for the jobs of one kind.)"""
    idx = list(range(len(works)))
    if order == 'auto': order = 'width' if len(set(widths)) > 1 else 'kind'
    if order == 'width': return sorted(idx, key=lambda i: (-widths[i], -works[i], i))
    return sorted(idx, key=lambda i: (kinds[i], i))

def batch_time(m, kinds, works, widths, order='auto'):
    return simulate(m, [(works[i], widths[i]) for i in submit_order(kinds, works, widths, order)])

def choose_widths(m, kinds, works, fixed=None, order='auto', margin=0.10):
    """kinds, works: per job (work None = unknown length); fixed: list of widths (int) or None = choose.  Returns the widths.
    Starts: every job at one width; the k longest jobs at width a and the rest at width b (all k, a, b); then one job at a time is changed (longest first)
    while the modelled time drops.  Ties go to the narrower width.  Unknown lengths and fixed widths are never changed (a free job of unknown length gets 0).
    GUARD (margin): the model is good to a few percent on most batches but was 16% off on one measured batch (#1407), so a mix of widths is kept only if the
    model says it beats the best single width for the free jobs by at least `margin` (10%); otherwise the best single width is used."""
    n = len(works); fixed = fixed or [None] * n
    free = [i for i in range(n) if fixed[i] is None and works[i] is not None]
    est = [x if x is not None else 0 for x in works]
    base = [fixed[i] if fixed[i] is not None else 0 for i in range(n)]
    if not free: return base
    W = range(m.wmax() + 1)
    def T(ws): return batch_time(m, kinds, est, ws, order)
    byl = sorted(free, key=lambda i: (-est[i], i)); starts = []
    for a in W:
        for b in W:
            for k in range(len(byl) + 1):
                ws = base[:]
                for r, i in enumerate(byl): ws[i] = a if r < k else b
                starts.append(ws)
    best = None
    for ws in starts:
        t = T(ws); nar = sum(ws[i] for i in free)                          # equal time (within 1e-9): the narrower
        if best is None or t < best[0] - 1e-9 or (abs(t - best[0]) <= 1e-9 and nar < best[1]): best = (t, nar, ws)
    t, _, cur = best
    for _ in range(4):
        moved = False
        for i in byl:
            for w in W:
                if w == cur[i]: continue
                ws = cur[:]; ws[i] = w; t2 = T(ws)
                if t2 < t - 1e-9 or (abs(t2 - t) <= 1e-9 and w < cur[i]): cur, t, moved = ws, t2, True
        if not moved: break
    if margin and len({cur[i] for i in free}) > 1:
        uni = []
        for w in W:
            ws = base[:]
            for i in free: ws[i] = w
            uni.append((T(ws), w, ws))
        tu, _, wu = min(uni)
        if t > (1 - margin) * tu: return wu
    return cur


import re
KIND_LINE = re.compile(r'jobs_cpi_(\w+)\.json\s+lw0\s+clocks=(\d+)\s+(\d+) of (\d+) jobs correct')
def fit_kinds(profile, text, imem=128, dsh=256):
    """clocks per instruction of each kind from cpi_run_v1.sh output (job files jobs_cpi_<kind>.json at width 0): (clocks - overhead) / steps, median of the repeats.
    A run whose job was not correct is an error (a wrong answer must never become a number)."""
    import scbatch
    m = fit_model(profile, imem, dsh); got = {}
    for k, c, ok, n in KIND_LINE.findall(text):
        if ok != n: raise ValueError('run of %s: %s of %s jobs correct' % (k, ok, n))
        t = scbatch.load_jobs(os.path.join(HERE, 'jobs_cpi_%s.json' % k))[0]
        got.setdefault(k, []).append((int(c) - m.overhead) / task_steps(t, imem, dsh))
    return {k: round(statistics.median(v), 2) for k, v in got.items()}

def main(argv=None):
    import argparse, json, sc_calibrate_v1 as K
    ap = argparse.ArgumentParser(description='length estimate: fit the clocks per instruction of each kind from a card run, or show the model of a profile')
    ap.add_argument('cmd', choices=['fit-kinds', 'show']); ap.add_argument('--profile', required=True); ap.add_argument('--raw', help='cpi_run output (fit-kinds)')
    a = ap.parse_args(argv)
    p = K.load_profile(a.profile)
    if a.cmd == 'fit-kinds':
        if not a.raw: print('fit-kinds needs --raw FILE (the output of cpi_run_v1.sh)'); return 2
        p['kind_cpi'] = fit_kinds(p, open(a.raw).read()); K.save(p); print('kind_cpi stored in profile %s: %s' % (p['name'], p['kind_cpi'])); return 0
    m = fit_model(p)
    print('profile %s: crc32 %.2f clocks per instruction, overhead %.0f clocks, speed-up %s, jobs at once %s, %d slices per block' % (p['name'], m.cpi, m.overhead, m.speedup, m.at_once, m.slices))
    print('kinds measured: %s (others are assumed to run like crc32)' % (m.kind_cpi or 'none'))
    return 0

if __name__ == '__main__':
    import sys; sys.exit(main())
