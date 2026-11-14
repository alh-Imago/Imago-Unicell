#!/usr/bin/env python3
"""Tests and experiments for sc_sys_v3 (request table + watcher, task table, priority dispatcher).

Gate for every run: all tasks completed, none trapped, every a0 equals the reference simulator's,
zero overlapping/misaligned allocations (launch_err), and every injected peripheral event logged once
with the right payload.
"""
import os, random, subprocess, sys, statistics as stt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sched_tests as st          # kernels, workloads, reference results

HERE = os.path.dirname(os.path.abspath(__file__))
S = 32
KINDS = ['sum', 'fib', 'crc', 'gcd', 'mul', 'sort']   # program-class id given at submit
_built = {}

def build(S_, prio, bestfit, longest=0, guard=8, maxpass=8, v4=False, dmw=1024, fine=0, v5=False, v6=False, v7=False, v8=False):
    v7 = v7 or v8
    v6 = v6 or v7
    v5 = v5 or v6
    v4 = v4 or v5
    key = (S_, prio, bestfit, longest, guard, maxpass, v4, dmw, fine, v5, v6, v7, v8)
    if key not in _built:
        d = os.path.join(HERE, 'vl%s_S%d_P%d_B%d_L%d_G%d_M%d' % ((('8' if v8 else '7' if v7 else '6' if v6 else '5' if v5 else '4' if v4 else '3'),) + key[:6]) + ('_D%d' % dmw) + ('_F' if fine else ''))
        r = subprocess.run(['verilator', '--binary', '--timing', '-Wno-fatal', '-Wno-lint', '-Wno-WIDTH', '-Wno-UNOPTFLAT',
                            '-Wno-INITIALDLY', '-Wno-BLKSEQ', '-Wno-CASEINCOMPLETE', '-Wno-MULTIDRIVEN', '-Wno-BLKANDNBLK',
                            '--top-module', 'tb_sys8' if v8 else 'tb_sys7' if v7 else 'tb_sys6' if v6 else 'tb_sys5' if v5 else 'tb_sys4' if v4 else 'tb_sys3', '-GS=%d' % S_, '-GPRIO=%d' % prio, '-GBESTFIT=%d' % bestfit, '-GLONGEST=%d' % longest, '-GFINE=%d' % fine,
                            '-GDMW=%d' % dmw if v4 else '-GGUARD=%d' % guard, '-GGUARD=%d' % guard, '-GMAXPASS=%d' % maxpass, '-O2', '--Mdir', d, '-o', 'simv',
                            os.path.join(HERE, 'tb_sys8.v' if v8 else 'tb_sys7.v' if v7 else 'tb_sys6.v' if v6 else 'tb_sys5.v' if v5 else 'tb_sys4.v' if v4 else 'tb_sys3.v'), os.path.join(HERE, 'sc_sys_v8.v' if v8 else 'sc_sys_v7.v' if v7 else 'sc_sys_v6.v' if v6 else 'sc_sys_v5.v' if v5 else 'sc_sys_v4.v' if v4 else 'sc_sys_v3.v'),
                            os.path.join(HERE, 'uc_core_v2t.v' if v8 else 'uc_core_v2s.v' if v5 else 'uc_core_fp.v' if v4 else 'uc_core_rw.v')], capture_output=True, text=True)
        if r.returncode: print(r.stdout[-1500:], r.stderr[-1500:]); sys.exit(1)
        _built[key] = os.path.join(d, 'simv')
    return _built[key]

def run3(tasks, lws, arrivals, cfg, nevents=0, tag='v3', profile=None, v4=False, dmw=1024, fine=0, v5=False, v6=False, v7=False, v8=False):
    exe = build(S, *cfg, v4=v4, dmw=dmw, fine=fine, v5=v5, v6=v6, v7=v7, v8=v8) if (v4 or v5 or v6 or v7 or v8) else build(S, *cfg, fine=fine)
    image, bases = [], []
    for t in tasks:
        bases.append(len(image)); image += t['words']
    hexf, tskf, outf = [os.path.join(HERE, '%s.%s' % (tag, e)) for e in ('img', 'tsk', 'out')]
    open(hexf, 'w').write('\n'.join('%08x' % w for w in image) + '\n')
    open(tskf, 'w').write('\n'.join('%08x\n%08x\n%08x' % (arrivals[i], bases[i], lws[i] | (int(tasks[i]['critical']) << 8) | (KINDS.index(tasks[i]['kind']) << 9))
                                    for i in range(len(tasks))) + '\n')
    extra = []
    if profile is not None:
        pf = os.path.join(HERE, tag + '.prof'); open(pf, 'w').write('\n'.join('%07x' % v for v in profile) + '\n'); extra = ['+profin=' + pf]
    subprocess.run([exe] + extra + ['+prog=' + hexf, '+tasks=' + tskf, '+ntasks=%d' % len(tasks), '+nevents=%d' % nevents, '+out=' + outf],
                   check=True, capture_output=True)
    res = dict(c={}, e=[], x=[], p=[])
    for line in open(outf):
        p = line.split()
        if p[0] == 'c':
            tid, lw, crit, arr, stt_, en, a0, trap, state, slot, pred = map(int, p[1:])
            res['c'][tid] = dict(lw=lw, crit=crit, arrival=arr, start=stt_, end=en, a0=a0, trap=trap, state=state, slot=slot, pred=pred)
        elif p[0] == 'e': res['e'].append(tuple(map(int, p[1:])))
        elif p[0] == 'p': res['p'].append(int(p[2]))
        elif p[0] == 'x': res['x'].append(tuple(map(int, p[1:])))
        else: res[p[0]] = int(p[1])
    return res

def gate(tasks, res, nevents=0):
    errs = []
    if res['completed'] != len(tasks): errs.append('only %d/%d completed' % (res['completed'], len(tasks)))
    if res['launch_err']: errs.append('%d bad allocations' % res['launch_err'])
    for t in tasks:
        c = res['c'].get(t['tid'])
        if c is None or c['state'] != 3: errs.append('task %d not done' % t['tid']); continue
        if c['trap']: errs.append('task %d trapped' % t['tid'])
        elif c['a0'] != t['expect']: errs.append('task %d (%s) a0 %08x != %08x' % (t['tid'], t['kind'], c['a0'], t['expect']))
    if nevents:
        if res['events'] != nevents: errs.append('%d/%d events logged' % (res['events'], nevents))
        sent = {(line, data): cyc for line, data, cyc in res['x']}
        got = {}
        for line, data, cyc in res['e']: got.setdefault((line, data), []).append(cyc)
        for k, setc in sent.items():
            if k not in got: errs.append('event %s lost' % (k,))
            elif len(got[k]) != 1: errs.append('event %s logged %d times' % (k, len(got[k])))
            elif not (0 <= got[k][0] - setc <= 8): errs.append('event %s served after %d cycles' % (k, got[k][0] - setc))
    return errs

def metrics(tasks, res):
    c = res['c']
    mk = max(v['end'] for v in c.values())
    lat = lambda sel: [c[t['tid']]['end'] - c[t['tid']]['arrival'] for t in tasks if sel(t)]
    mean = lambda v: sum(v) / len(v) if v else float('nan')
    tot = S * res['total_cycles']
    return dict(makespan=mk, util=res['busy_slice_cycles'] / tot,
                lat_crit=mean(lat(lambda t: t['critical'])), lat_bulk=mean(lat(lambda t: not t['critical'])),
                max_wait=max(v['start'] - v['arrival'] for v in c.values()),
                w_blocked=res['waste_blocked'] / tot, w_tail=res['waste_tail'] / tot,
                search=res['search_cycles'] / res['total_cycles'])

def main():
    # ---- 1. correctness gate, random widths and arrivals, every dispatcher configuration, with events
    print('== gate: random widths/arrivals + 40 injected peripheral events, all 4 configurations ==')
    bad = 0
    for cfg in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        for seed in range(4):
            tasks = st.make_workload(300 + seed, 40)
            rng = random.Random(seed)
            lws = [rng.randrange(0, 6) for _ in tasks]
            arr = sorted(rng.randrange(0, 4000) for _ in tasks)
            res = run3(tasks, lws, arr, cfg, nevents=40)
            errs = gate(tasks, res, 40)
            bad += bool(errs)
            print('  PRIO=%d BESTFIT=%d seed %d: makespan %6d  %s' % (cfg[0], cfg[1], seed, max(v['end'] for v in res['c'].values()),
                  'OK' if not errs else 'FAIL ' + '; '.join(errs[:3])))
    if bad: print('gate failures'); sys.exit(1)

    # ---- 2. regression against the earlier strict-FIFO array (v2, LA=1) on the seed-7 workload
    tasks = st.make_workload(7, 48); n = len(tasks)
    print('\n== regression: v3 as a single FIFO with first-fit vs earlier strict FIFO (seed-7 workload) ==')
    for name, f, want in [('all W=8', lambda t: 3, 46217), ('crit 8 / bulk 2', lambda t: 3 if t['critical'] else 1, 74685)]:
        res = run3(tasks, [f(t) for t in tasks], [0] * n, (0, 0))
        assert not gate(tasks, res)
        mk = max(v['end'] for v in res['c'].values())
        print('  %-18s v3 %6d   earlier %6d   (%+.2f%%)' % (name, mk, want, 100 * (mk - want) / want))

if __name__ == '__main__':
    main()
