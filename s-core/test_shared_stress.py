"""Stress test of the v10 shared RAM arbiter: the host reads one shared word nonstop (every other clock) while S slices run sum kernels on
their own windows, and every host read must return the right value and every task the right answer.  A host request takes the port
from the slices; a slice whose clock was taken must retry.  Usage: python3 test_shared_stress.py [S] [hammer_word]"""
import os, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from shared_cases import *
S = int(sys.argv[1]) if len(sys.argv) > 1 else 4
HAM = int(sys.argv[2]) if len(sys.argv) > 2 else 40          # word 40: inside sum window 1 (input word 8): the hammer reads what a slice is also reading
d = '/tmp/vl_stress%d' % S
f = HERE
r = subprocess.run(['verilator', '--binary', '--timing', '-Wno-fatal', '-Wno-lint', '-Wno-WIDTH', '-Wno-UNOPTFLAT', '-Wno-INITIALDLY', '-Wno-BLKSEQ',
    '-Wno-CASEINCOMPLETE', '-Wno-MULTIDRIVEN', '-Wno-BLKANDNBLK', '--top-module', 'tb_sys10', '-GS=%d' % S, '-O2', '--Mdir', d, '-o', 'simv',
    f + '/tb_sys10.v', f + '/sc_sys_v10.v', f + '/uc_core_v2v.v'], capture_output=True, text=True)
if r.returncode: print(r.stdout[-1500:], r.stderr[-1500:]); sys.exit(1)
words, base = layout()
open('/tmp/st_prog.hex', 'w').write('\n'.join('%08x' % w for w in words) + '\n')
tasks = [(c, sum_of(c)) for c in range(4)] * 2          # 8 sum tasks, windows of classes 0..3
open('/tmp/st_tasks.hex', 'w').write('\n'.join('%08x\n%08x\n%08x' % (0, base['sum16'], (c << 9)) for c, _ in tasks) + '\n')
pre = preload()
open('/tmp/st_shared.hex', 'w').write('\n'.join('%08x\n%08x' % (a, v) for a, v in pre.items()) + '\n')
open('/tmp/st_regions.hex', 'w').write('\n'.join('%08x\n%08x\n%08x' % (c, CLASSES[c][1][0], CLASSES[c][1][1]) for c in range(4)) + '\n')
assert HAM in pre
out = subprocess.run([d + '/simv', '+prog=/tmp/st_prog.hex', '+tasks=/tmp/st_tasks.hex', '+ntasks=%d' % len(tasks), '+shared=/tmp/st_shared.hex', '+nshared=%d' % len(pre),
    '+regions=/tmp/st_regions.hex', '+nregions=4', '+hammer=%d' % HAM, '+out=/tmp/st_out.txt'], capture_output=True, text=True)
print(out.stdout[-800:])
L = open('/tmp/st_out.txt').read().splitlines()
done = L[0].split(); ham = L[1].split()
t = [l.split() for l in L if l.startswith('t ')]; m = {int(l.split()[1]): int(l.split()[2]) for l in L if l.startswith('m ')}
bad = 0
for (c, exp), tt in zip(tasks, t):
    ok = int(tt[2]) == exp & 0xFFFFFFFF and tt[3] == '0'
    bad += not ok
    if not ok: print('task class', c, 'a0', tt[2], 'expect', exp, 'trap', tt[3], 'FAIL')
for a in range(4):
    if m[32 * a + 16] != sum_of(a): print('window', a, 'result', m[32 * a + 16], 'expect', sum_of(a), 'FAIL'); bad += 1
hbad = int(ham[3]); hreads = int(ham[1])
print('S', S, 'tasks done', done[1], 'launch_err', done[3], '| host reads during the run', hreads, 'wrong', hbad, '| task/window errors', bad)
ok = (bad == 0 and hbad == 0 and hreads > 100 and int(done[1]) == len(tasks))
print('RESULT', 'PASS' if ok else 'FAIL'); sys.exit(0 if ok else 1)
