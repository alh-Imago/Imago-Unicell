"""Your own programs on the simulated board (whole board, hardware batch sequencer v2, SDRAM model).  Needs iverilog.
jobs_own_example.json: three programs registered from files (vmax, vprefix with Python answers; copy with the interpreter as the reference) mixed with a built-in
(vsum) in two batches.  The images go into far RAM, J starts the chain, and the status, n_out and outputs of EVERY job are read back and checked by plan.verify.
So this compares what the RTL cores computed with the Python answers and the interpreter's answer, for programs that did not exist when the board design was made."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import host_sc as hs, sdt_host as H, jobcomp as C, scbatch as SB
import test_farram_sim as F
from test_seq_sim import jcmd

def main():
    bad = 0
    def check(name, cond, extra=''):
        nonlocal bad
        print('%-92s %s %s' % (name, 'ok' if cond else 'FAIL', extra)); bad += (not cond)
    tasks = SB.load_jobs(os.path.join(HERE, 'jobs_own_example.json'))
    p = C.compile(tasks, wait_k=1000); print(p.report())
    exe = F.build('own', seq=2)
    s = F.Script(); s.wait(0x3000)
    s.send(H.c_D(*p.window))
    for a in sorted(p.image): s.send(H.c_w(a, p.image[a]), extra=0x40)
    s.send(jcmd(p.entry))
    for _ in range(2): s.wait(1_500_000); s.send(b'A', 24, 'A')
    first = min(sa for (sa, ra, n) in p.results.values()); last = max(ra + n for (sa, ra, n) in p.results.values())
    for a in range(first, last): s.send(H.c_r(a), 4, 'r')
    rx, errs = F.run(exe, s, tag='own', maxcyc=200_000_000)
    pos = 0; got = []
    for kind, m in s.reps: got.append((kind, rx[pos:pos + m])); pos += m
    a = [SB.dec_A(b) for k, b in got if k == 'A'][-1]; rs = [H.dec_r(b) for k, b in got if k == 'r']
    check('chain done by itself: error 0, end tag, %d steps, %d board clocks' % (p.steps, a['clk']), a['done'] and not a['busy'] and a['err'] == 0 and a['tag'] == p.tag and a['steps'] == p.steps, str(a))
    mem = {first + k: v for k, v in enumerate(rs)}
    problems = p.verify(lambda x: mem.get(x, 0xEEEEEEEE))
    check('all %d jobs (vmax, vprefix, copy, vsum): status 1, n_out and outputs equal the answers' % len(tasks), not problems, str(problems[:3]))
    for i, t in enumerate(tasks):
        sa, ra, n = p.results[i]; out = [mem.get(ra + k) for k in range(n)]
        print('   job %d %-8s -> %s' % (i, t.kind, ' '.join('%x' % x for x in out[:6]) + (' ...' if n > 6 else '')))
    check('SDRAM model reports no timing violations', not errs, repr(errs[:2]))
    print('RESULT:', 'PASS' if not bad else 'FAIL (%d)' % bad)
    return 1 if bad else 0

if __name__ == '__main__': sys.exit(main())
