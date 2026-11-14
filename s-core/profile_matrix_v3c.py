"""Whole-octave (coarse) vs half-octave (FINE) duration buckets, v3 simulator, same workloads as profile_matrix_v3b.py.
coarse warm must equal the 'warm' column of matrix_v3b_after_fix.txt (sanity check that FINE=0 changed nothing)."""
import random
import sched_tests as st, sched_tests_v3 as v3
mk = lambda r: max(v['end'] for v in r['c'].values())
print('arrival  widths seed      FIFO  coarse_warm  fine_cold  fine_warm   fine_vs_FIFO  fine_vs_coarse')
nb = 0; n = 0; nc = 0
for arrival in ('batch', 'stagger'):
  for widths in ('uni', 'mixed'):
    for seed in (1, 3, 7):
        def setup(sd):
            tasks = st.make_workload(sd, 48); rng = random.Random(sd * 7 + 1)
            lws = [3] * len(tasks) if widths == 'uni' else [rng.randrange(0, 4) for _ in tasks]
            arr = [0] * len(tasks) if arrival == 'batch' else sorted(rng.randrange(0, 20000) for _ in tasks)
            return tasks, lws, arr
        tasks, lws, arr = setup(seed); t2, l2, a2 = setup(seed + 100)
        learn = v3.run3(t2, l2, a2, (1, 1, 1))
        res = {}
        for name, cfg, kw in [('fifo', (1, 1, 0), {}), ('cw', (1, 1, 1), dict(tag='v3w', profile=learn['p'])),
                              ('fc', (1, 1, 1), dict(fine=1)), ('fw', (1, 1, 1), dict(fine=1, tag='v3x', profile=learn['p']))]:
            r = v3.run3(tasks, lws, arr, cfg, **kw); assert not v3.gate(tasks, r), name; res[name] = mk(r)
        n += 1; nb += res['fw'] < res['fifo']; nc += res['fw'] < res['cw']
        print('%-8s %-6s s%d  %8d  %11d  %9d  %9d   %+6.1f%%   %+6.1f%%' % (arrival, widths, seed, res['fifo'], res['cw'], res['fc'], res['fw'],
              100 * (res['fw'] - res['fifo']) / res['fifo'], 100 * (res['fw'] - res['cw']) / res['cw']))
print('fine warm beats FIFO in %d of %d; beats coarse warm in %d of %d' % (nb, n, nc, n))
