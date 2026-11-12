"""Re-run of the v3 duration-profile comparison (FIFO vs longest-first cold vs warm).  Reconstructed script:
the original was an inline run, so the workload parameters here (48 tasks, widths, stagger range) are my choice,
and the point is the SAME script run on the unfixed and on the fixed sc_sys_v3.v."""
import sys, random
import sched_tests as st, sched_tests_v3 as v3
def mk(res): return max(v['end'] for v in res['c'].values())
tot = 0; better = 0
print('arrival  widths seed      FIFO     cold     warm   warm_vs_FIFO')
for arrival in ('batch', 'stagger'):
  for widths in ('uni', 'mixed'):
    for seed in (1, 3, 7):
        def setup(sd):
            tasks = st.make_workload(sd, 48); rng = random.Random(sd * 7 + 1)
            lws = [3] * len(tasks) if widths == 'uni' else [rng.randrange(0, 4) for _ in tasks]
            arr = [0] * len(tasks) if arrival == 'batch' else sorted(rng.randrange(0, 20000) for _ in tasks)
            return tasks, lws, arr
        tasks, lws, arr = setup(seed)
        fifo = v3.run3(tasks, lws, arr, (1, 1, 0)); assert not v3.gate(tasks, fifo)
        cold = v3.run3(tasks, lws, arr, (1, 1, 1)); assert not v3.gate(tasks, cold)
        t2, l2, a2 = setup(seed + 100)
        learn = v3.run3(t2, l2, a2, (1, 1, 1)); assert not v3.gate(t2, learn)
        warm = v3.run3(tasks, lws, arr, (1, 1, 1), profile=[0] * 0 + [0] * 0 or None) if False else v3.run3(tasks, lws, arr, (1, 1, 1), tag='v3w', profile=learn['p'])
        assert not v3.gate(tasks, warm)
        f, c, w = mk(fifo), mk(cold), mk(warm); tot += 1; better += w < f
        print('%-8s %-6s s%d  %8d %8d %8d   %+.1f%%' % (arrival, widths, seed, f, c, w, 100 * (w - f) / f))
print('warm better than FIFO in %d of %d' % (better, tot))
