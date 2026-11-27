#!/usr/bin/env python3
"""scwaves_v1.py - a design too big for one run, split into WAVES (ledger #1547).  Pure host-side functions: no card, no printing.

A run puts every job of the design into the card's far RAM at once, so the design must fit (code words, shared RAM, jobs per batch, far RAM: 65,536 words on the
block-RAM Kintex builds).  A bigger design is run in waves: the front end cuts the job list into waves that each fit, runs a wave, reads its answers, then feeds
the next wave.  Three cases use the same engine:
  1. many independent jobs        -> waves are consecutive slices of the job list, as long as each fits.
  2. one huge data set            -> the pieces made by `addbig` are just jobs; waves carry them and the shell combines their answers at the end.
  3. a pipeline (a job uses the answers of earlier jobs: `from=J` gives its input words, `argfrom=J` its arg) -> jobs are put in LEVELS (a job's level is one
     more than the highest level it reads from); a wave never mixes levels, and a level is run only after the level before it has been read back.
`fits(ids)` is a function the caller gives: True if those jobs (global numbers) can be planned as one run on the loaded build."""

class WaveError(Exception): pass

def deps_of(job):
    """the jobs this job reads from: {'from': J, 'argfrom': J}"""
    return sorted({job[k] for k in ('from', 'argfrom') if job.get(k) is not None})

def levels(jobs):
    """-> list of levels, each a list of job numbers (in order); raises WaveError for a reference to a missing job, to itself, or a cycle"""
    n = len(jobs); lvl = [None] * n
    for i, j in enumerate(jobs):
        for d in deps_of(j):
            if not isinstance(d, int) or d < 0 or d >= n: raise WaveError('job %d reads from job %r, which does not exist (jobs are numbered from 0)' % (i, d))
            if d == i: raise WaveError('job %d reads from itself' % i)
    def level(i, stack=()):
        if lvl[i] is not None: return lvl[i]
        if i in stack: raise WaveError('jobs read from each other in a circle: %s' % ' -> '.join(str(x) for x in stack + (i,)))
        ds = deps_of(jobs[i]); lvl[i] = 1 + max(level(d, stack + (i,)) for d in ds) if ds else 0
        return lvl[i]
    for i in range(n): level(i)
    out = [[] for _ in range(max(lvl) + 1)] if n else []
    for i in range(n): out[lvl[i]].append(i)
    return out

def split_level(ids, fits):
    """cut one level (a list of job numbers) into the fewest consecutive waves that each fit; a single job that does not fit alone is an error"""
    waves = []; start = 0
    while start < len(ids):
        if not fits(ids[start:start + 1]): raise WaveError('job %d does not fit on the loaded build even on its own' % ids[start])
        ok, k = 1, 2
        while start + ok < len(ids):                                   # grow by doubling until it no longer fits
            k = min(ok * 2, len(ids) - start)
            if fits(ids[start:start + k]): ok = k
            else: break
        else: k = None
        if start + ok < len(ids) and k is not None and k > ok:        # binary search between the last size that fitted and the first that did not
            lo, hi = ok, k
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if fits(ids[start:start + mid]): lo = mid
                else: hi = mid
            ok = lo
        waves.append(ids[start:start + ok]); start += ok
    return waves

def plan_waves(jobs, fits):
    """-> list of (level, [job numbers]) in the order they are run"""
    out = []
    for li, ids in enumerate(levels(jobs)):
        for w in split_level(ids, fits): out.append((li, w))
    return out

def has_refs(jobs): return any(deps_of(j) for j in jobs)

def resolve(job, got):
    """the job with its `from` inputs and `argfrom` arg filled in from the answers in `got` ({job number: [words]}); a copy, the original is not changed"""
    j = {k: v for k, v in job.items() if k not in ('from', 'argfrom')}
    if job.get('from') is not None:
        r = got.get(job['from'])
        if r is None: raise WaveError('the answer of job %d is not there yet' % job['from'])
        j['inputs'] = list(r)
    if job.get('argfrom') is not None:
        r = got.get(job['argfrom'])
        if not r: raise WaveError('the answer of job %d is not there yet' % job['argfrom'])
        j['arg'] = r[0]
    return j
