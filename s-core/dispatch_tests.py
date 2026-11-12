#!/usr/bin/env python3
"""Dispatcher policy matrix: strict FIFO vs overtaking vs reserved region vs both.

Tasks are submitted in natural order (no host-side reordering).  Every run goes through the same
correctness gate as sched_tests_v2.py (all tasks complete, none trap, every a0 matches the reference).
Results are means over several workloads.
"""
import os, random, statistics as stt, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sched_tests_v2 as st

S = 32
SEEDS = [21, 22, 23, 24, 25]
NTASKS = 48

VARIANTS = [  # name, (LA, MAXPASS, RESERVE)
    ('strict FIFO',              (1, 8, 0)),
    ('overtake 4',               (4, 16, 0)),
    ('overtake 16',              (16, 32, 0)),
    ('reserve 8, strict',        (1, 8, 8)),
    ('reserve 8 + overtake 16',  (16, 32, 8)),
    ('reserve 16 + overtake 16', (16, 32, 16)),
]
WIDTHS = [  # name, function task -> log2 width
    ('all W=8',          lambda t: 3),
    ('crit 8 / bulk 4',  lambda t: 3 if t['critical'] else 2),
    ('crit 16 / bulk 4', lambda t: 4 if t['critical'] else 2),
    ('crit 32 / bulk 1', lambda t: 5 if t['critical'] else 0),
]

def one(tasks, f, arrivals, disp, tag):
    res = st.run_system(tasks, [f(t) for t in tasks], arrivals, S, tag, disp)
    errs = st.check(tasks, res)
    if errs:
        print('CORRECTNESS FAILURE', disp, errs[:3]); sys.exit(1)
    m = st.metrics(tasks, res, S)
    waits = [c['start'] - c['arrival'] for c in res['c'].values()]
    m['max_wait'] = max(waits)
    return m

def table(title, arrivals_fn):
    print('\n== %s (mean of %d workloads of %d tasks, S=%d) ==' % (title, len(SEEDS), NTASKS, S))
    wl = [(sd, st.make_workload(sd, NTASKS)) for sd in SEEDS]
    for wname, f in WIDTHS:
        print('\n  widths: %s' % wname)
        print('  %-26s %9s %6s %11s %10s %10s' % ('dispatcher', 'makespan', 'util', 'lat critical', 'lat bulk', 'worst wait'))
        for vname, disp in VARIANTS:
            ms = []
            for sd, tasks in wl:
                ms.append(one(tasks, f, arrivals_fn(sd, tasks), disp, 'dp'))
            g = lambda k: stt.mean(m[k] for m in ms)
            print('  %-26s %9.0f %5.0f%% %11.0f %10.0f %10.0f' % (vname, g('makespan'), 100 * g('util'), g('lat_crit'), g('lat_bulk'), g('max_wait')))
        sys.stdout.flush()

def batch(sd, tasks): return [0] * len(tasks)
def staggered(sd, tasks):
    rng = random.Random(sd)
    out, t0 = [], 0
    for _ in tasks:
        t0 += rng.randrange(150, 550); out.append(t0)
    return out

if __name__ == '__main__':
    table('batch arrival (all submitted at t=0)', batch)
    table('staggered arrival (one task every ~350 cycles)', staggered)
