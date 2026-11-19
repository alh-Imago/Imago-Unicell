#!/usr/bin/env python3
"""make_curve_jobs_v1.py - job files for the width-curve test (ledger #1396).
One program (crc32), N identical-length jobs that fit ONE batch of one block, input length L words.
Writes jobs_curve_L<L>_N<N>.json.  Pairs that would not fit one batch (shared window 256 words) are left out.
Run:  python3 make_curve_jobs_v1.py     (writes the files next to jobs_many_small.json, whose crc32 program entry it reuses)"""
import json, random, subprocess, os
here = os.path.dirname(os.path.abspath(__file__)); os.chdir(here)
d = json.load(open('jobs_many_small.json'))
progs = [p for p in d['programs'] if p['name'] == 'crc32']
ex = [j for j in d['jobs'] if j['kind'] == 'crc32'][0]
extra = {k: v for k, v in ex.items() if k not in ('kind', 'inputs')}
made = []
for L in (8, 20, 40, 80):
    for N in (1, 2, 4, 8):
        r = random.Random(L * 100 + N)
        f = 'jobs_curve_L%d_N%d.json' % (L, N)
        json.dump({'programs': progs, 'jobs': [dict(kind='crc32', inputs=[r.randrange(1 << 24) for _ in range(L)], **extra) for _ in range(N)]}, open(f, 'w'))
        o = subprocess.run(['python3', 'scblocks.py', '--plan', f, '--blocks', '1'], capture_output=True, text=True).stdout
        if sum('batch' in l and 'jobs' in l for l in o.splitlines()) != 1: os.remove(f); continue
        made.append(f)
print(len(made), 'files:', ' '.join(made))
