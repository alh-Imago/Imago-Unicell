#!/usr/bin/env python3
"""System-level tests and scheduling experiments for the S-Core array (sc_sys.v).

Every task is a small RV32I program that leaves its answer in a0.  The reference
RV32I simulator (runtests.iss) provides the expected a0 and the instruction count.
A run PASSES only if every task completed, none trapped, and every a0 matches.

Usage: python3 sched_tests_v2.py            # correctness sweep + policy experiments
"""
import os, random, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runtests as rt

HERE = os.path.dirname(os.path.abspath(__file__))
S_DEFAULT = 32

# ------------------------------------------------------------------ task kernels (answer in a0)
def k_sum(n):
    return f"""li a0,0
li t0,1
li t1,{n+1}
loop: add a0,a0,t0
addi t0,t0,1
bne t0,t1,loop
ebreak"""

def k_fib(n):
    return f"""li t0,0
li t1,1
li t2,{n}
loop: beqz t2,done
add t3,t0,t1
mv t0,t1
mv t1,t3
addi t2,t2,-1
j loop
done: mv a0,t0
ebreak"""

def k_crc(seed, nw):
    return f"""li s0,0xFFFFFFFF
li s1,0xEDB88320
li t0,0
li t1,{nw}
li s2,{seed}
word: xor s0,s0,s2
li t2,32
bit: andi t3,s0,1
srli s0,s0,1
beqz t3,nox
xor s0,s0,s1
nox: addi t2,t2,-1
bnez t2,bit
addi s2,s2,0x111
addi t0,t0,1
bne t0,t1,word
xori a0,s0,-1
ebreak"""

def k_gcd(a, b):
    return f"""li a3,{a}
li a4,{b}
gcd: beq a3,a4,done
blt a3,a4,less
sub a3,a3,a4
j gcd
less: sub a4,a4,a3
j gcd
done: mv a0,a3
ebreak"""

def k_mul(a, b):
    return f"""li a0,0
li a1,{a}
li a2,{b}
mul: andi t0,a2,1
beqz t0,skip
add a0,a0,a1
skip: slli a1,a1,1
srli a2,a2,1
bnez a2,mul
ebreak"""

def k_sort(n, seed):
    return f"""li s0,{n}
li t0,0
li t1,{seed}
li t2,1103515245
fill: add t1,t1,t2
srli t3,t1,3
xor t2,t2,t3
slli t4,t0,2
andi t5,t1,1023
sw t5,0(t4)
addi t0,t0,1
bne t0,s0,fill
outer: li s1,0
li t0,0
addi s2,s0,-1
inner: slli t4,t0,2
lw t5,0(t4)
lw t6,4(t4)
bge t6,t5,noswap
sw t6,0(t4)
sw t5,4(t4)
li s1,1
noswap: addi t0,t0,1
bne t0,s2,inner
bnez s1,outer
li a0,0
li t0,0
hash: slli t4,t0,2
lw t5,0(t4)
slli a0,a0,1
xor a0,a0,t5
addi t0,t0,1
bne t0,s0,hash
ebreak"""

def make_task(rng):
    kind = rng.choice(['sum', 'fib', 'crc', 'gcd', 'mul', 'sort'])
    if kind == 'sum':  return kind, k_sum(rng.randrange(30, 150))
    if kind == 'fib':  return kind, k_fib(rng.randrange(20, 120))
    if kind == 'crc':  return kind, k_crc(rng.getrandbits(31), rng.randrange(1, 5))
    if kind == 'gcd':  return kind, k_gcd(rng.randrange(200, 3000), rng.randrange(200, 3000))
    if kind == 'mul':  return kind, k_mul(rng.randrange(1000, 90000), rng.randrange(1000, 90000))
    return kind, k_sort(rng.randrange(6, 13), rng.getrandbits(30))

def make_workload(seed, n_tasks, crit_frac=0.25):
    """Returns a list of dicts: kind, words, expect_a0, instret, critical."""
    rng = random.Random(seed)
    out = []
    for t in range(n_tasks):
        kind, src = make_task(rng)
        words = rt.assemble(src)
        ref = rt.iss(words)
        out.append(dict(tid=t, kind=kind, words=words, expect=ref['x'][10], instret=ref['instret'],
                        critical=rng.random() < crit_frac))
    return out

# ------------------------------------------------------------------ build + run
_compiled = {}
def compile_sys(S, disp=(1, 8, 0)):
    """Build the system simulator with Verilator (about 100x faster than iverilog here)."""
    key = (S,) + tuple(disp)
    if key not in _compiled:
        d = os.path.join(HERE, 'vl_S%d_LA%d_MP%d_R%d' % key)
        r = subprocess.run(['verilator', '--binary', '--timing', '-Wno-fatal', '-Wno-lint', '-Wno-WIDTH', '-Wno-UNOPTFLAT',
                            '-Wno-INITIALDLY', '-Wno-BLKSEQ', '-Wno-CASEINCOMPLETE', '-Wno-MULTIDRIVEN',
                            '--top-module', 'tb_sys', '-GS=%d' % S, '-GLA=%d' % disp[0],
                            '-GMAXPASS=%d' % disp[1], '-GRESERVE=%d' % disp[2], '-O2', '--Mdir', d, '-o', 'simv',
                            os.path.join(HERE, 'tb_sys_v2.v'), os.path.join(HERE, 'sc_sys_v2.v'),
                            os.path.join(HERE, 'uc_core_rw.v')], capture_output=True, text=True)
        if r.returncode: print(r.stdout[-2000:], r.stderr[-2000:]); sys.exit(1)
        _compiled[key] = os.path.join(d, 'simv')
    return _compiled[key]

def run_system(tasks, lws, arrivals, S=S_DEFAULT, tag='run', disp=(1, 8, 0)):
    """tasks: workload list; lws: requested log2 width per task; arrivals: cycle per task."""
    exe = compile_sys(S, disp)
    image, bases = [], []
    for t in tasks:
        bases.append(len(image)); image += t['words']
    assert len(image) < 8192, 'program image too large'
    hexf, tskf, outf = [os.path.join(HERE, '%s.%s' % (tag, e)) for e in ('img', 'tsk', 'out')]
    open(hexf, 'w').write('\n'.join('%08x' % w for w in image) + '\n')
    open(tskf, 'w').write('\n'.join('%08x\n%08x\n%08x' % (arrivals[i], bases[i], lws[i] | (int(tasks[i]['critical']) << 8)) for i in range(len(tasks))) + '\n')
    subprocess.run([exe, '+prog=' + hexf, '+tasks=' + tskf, '+ntasks=%d' % len(tasks), '+out=' + outf],
                   check=True, capture_output=True)
    res = dict(c={})
    for line in open(outf):
        p = line.split()
        if p[0] == 'c':
            tid, lw, arr, st, en, a0, trap = map(int, p[1:])
            res['c'][tid] = dict(lw=lw, arrival=arr, start=st, end=en, a0=a0, trap=trap)
        else: res[p[0]] = int(p[1])
    return res

def check(tasks, res):
    errs = []
    if res['completed'] != len(tasks): errs.append('only %d/%d completed' % (res['completed'], len(tasks)))
    for t in tasks:
        c = res['c'].get(t['tid'])
        if c is None: errs.append('task %d missing' % t['tid']); continue
        if c['trap']: errs.append('task %d (%s) trapped' % (t['tid'], t['kind']))
        elif c['a0'] != t['expect']: errs.append('task %d (%s) a0 %08x != %08x' % (t['tid'], t['kind'], c['a0'], t['expect']))
    return errs

def metrics(tasks, res, S):
    mk = max(c['end'] for c in res['c'].values())
    lat = lambda sel: [res['c'][t['tid']]['end'] - res['c'][t['tid']]['arrival'] for t in tasks if sel(t)]
    mean = lambda v: sum(v) / len(v) if v else float('nan')
    return dict(makespan=mk,
                util=res['busy_slice_cycles'] / (S * res['total_cycles']),
                lat_crit=mean(lat(lambda t: t['critical'])),
                lat_bulk=mean(lat(lambda t: not t['critical'])),
                lat_all=mean(lat(lambda t: True)))

# ------------------------------------------------------------------ experiments
def main():
    S = S_DEFAULT
    failures = 0

    # 1. correctness: random workloads, random widths per task, random arrivals
    print('== correctness sweep: random widths per task, random arrivals, S=%d ==' % S)
    for seed in range(6):
        tasks = make_workload(100 + seed, 40)
        rng = random.Random(seed)
        lws = [rng.randrange(0, 6) for _ in tasks]
        arr = sorted(rng.randrange(0, 4000) for _ in tasks)
        res = run_system(tasks, lws, arr, S, 'corr')
        errs = check(tasks, res)
        print('  seed %d: %d tasks, makespan %d cycles  %s' % (seed, len(tasks), max(c['end'] for c in res['c'].values()),
              'OK' if not errs else 'FAIL ' + '; '.join(errs[:3])))
        failures += bool(errs)
    if failures:
        print('correctness failures - stopping'); sys.exit(1)

    # 2. policy comparison on one workload, everything submitted at t=0
    tasks = make_workload(7, 48)
    ncrit = sum(t['critical'] for t in tasks)
    tot_instr = sum(t['instret'] for t in tasks)
    print('\n== policies, batch arrival: %d tasks (%d critical), %d instructions of work, S=%d ==' % (len(tasks), ncrit, tot_instr, S))
    pols = [('all W=1', lambda t: 0), ('all W=2', lambda t: 1), ('all W=4', lambda t: 2),
            ('all W=8', lambda t: 3), ('all W=16', lambda t: 4), ('all W=32', lambda t: 5),
            ('crit 16 / bulk 2', lambda t: 4 if t['critical'] else 1),
            ('crit 32 / bulk 1', lambda t: 5 if t['critical'] else 0),
            ('crit 8 / bulk 1', lambda t: 3 if t['critical'] else 0),
            ('crit 8 / bulk 2', lambda t: 3 if t['critical'] else 1)]
    print('  %-18s %9s %6s %12s %12s' % ('policy', 'makespan', 'util', 'lat critical', 'lat bulk'))
    rows = {}
    for name, f in pols:
        res = run_system(tasks, [f(t) for t in tasks], [0] * len(tasks), S, 'pol')
        errs = check(tasks, res)
        if errs: print('  %-18s FAIL %s' % (name, '; '.join(errs[:2]))); failures += 1; continue
        m = metrics(tasks, res, S); rows[name] = m
        print('  %-18s %9d %5.0f%% %12.0f %12.0f' % (name, m['makespan'], 100 * m['util'], m['lat_crit'], m['lat_bulk']))

    # dispatcher overhead: launch gaps for the all-W=1 run
    res = run_system(tasks, [0] * len(tasks), [0] * len(tasks), S, 'gap')
    starts = sorted(c['start'] for c in res['c'].values())[:S]
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    print('\n  dispatcher: first %d launches (all W=1) are %d-%d cycles apart (a 1-bit task runs thousands of cycles)' %
          (len(starts), min(gaps), max(gaps)))

    # 3. staggered arrivals: a steady stream, critical tasks want low latency
    print('\n== staggered arrivals (one task every ~%d cycles), S=%d ==' % (350, S))
    rng = random.Random(3)
    arr, t0 = [], 0
    for _ in tasks:
        t0 += rng.randrange(150, 550); arr.append(t0)
    print('  %-18s %9s %6s %12s %12s' % ('policy', 'makespan', 'util', 'lat critical', 'lat bulk'))
    for name, f in pols:
        res = run_system(tasks, [f(t) for t in tasks], arr, S, 'stg')
        errs = check(tasks, res)
        if errs: print('  %-18s FAIL %s' % (name, '; '.join(errs[:2]))); failures += 1; continue
        m = metrics(tasks, res, S)
        print('  %-18s %9d %5.0f%% %12.0f %12.0f' % (name, m['makespan'], 100 * m['util'], m['lat_crit'], m['lat_bulk']))
    sys.exit(1 if failures else 0)

if __name__ == '__main__':
    main()
