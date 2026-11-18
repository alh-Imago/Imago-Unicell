"""scblocks.py (the software outer allocator) against the simulated MULTI-BLOCK board: 7 different jobs of three kinds are split over 2 blocks, each block gets its own
far-RAM area and copy window, both chains run at the same time on the one far RAM, and every job's result is checked against the Python answer (ledger #1348).
The byte sequences are the ones scblocks.py sends to a real card (cmds_setup / cmds_start / cmds_poll / cmd_read).  Needs iverilog.  About 5 minutes."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import host_sc as hs, sdt_host as H, jobcomp as C, scblocks as SB
import test_mb_harness as M
from scbatch import dec_A
ALEN = 24
FAR_WORDS = 1 << 14                      # tb_k7mb: FAR_AW = 14

def main():
    bad = 0
    def check(name, cond, extra=''):
        nonlocal bad
        print('%-98s %s %s' % (name, 'ok' if cond else 'FAIL', extra)); bad += (not cond)
    tasks = [C.Task('vsum', [3 * i + 1 for i in range(12)]), C.Task('vscale', [100 + 7 * i for i in range(10)], arg=10), C.Task('vstress', [4, 5, 6, 7, 8, 9], arg=9),
             C.Task('vsum', [5, 5, 5, 9, 1]), C.Task('vscale', [0xFFFFFFF0 + i for i in range(8)], arg=8), C.Task('vsum', list(range(20, 40))), C.Task('vstress', [11, 12, 13], arg=3)]
    plans = SB.plan_blocks(tasks, 2, imem=128, dsh=256, far_words=FAR_WORDS)
    print(SB.report(tasks, plans))
    check('the jobs are spread over both blocks, every job in exactly one', len(plans) == 2 and sorted(i for bp in plans for i in bp.task_ids) == list(range(len(tasks))),
          ' / '.join(' '.join(map(str, bp.task_ids)) for bp in plans))
    a0, a1 = plans[0].plan, plans[1].plan
    check('the two far-RAM areas do not overlap', a0.window[0] + a0.window[1] <= a1.script_addrs[0] or a1.window[0] + a1.window[1] <= a0.script_addrs[0], '%#x+%#x, %#x+%#x' % (a0.window + a1.window))
    exe = M.build('mbjobs', NB=2, S=2)
    s = M.Script(); s.wait(0x3000)
    for c in SB.cmds_setup(plans):
        if c[:1] == b'w': s.send(c, extra=0x40)
        elif c == hs.cmd_R(): s.send(c); s.wait(200)
        else: s.send(c)
    for c in SB.cmds_start(plans): s.send(c)
    s.wait(1_200_000)
    for bp in plans:
        c = SB.cmds_poll(bp); s.send(c[0]); s.send(c[1], ALEN, 'A%d' % bp.block)
    addrs = []
    for bp in plans:
        for li in range(len(bp.task_ids)):
            sa, ra, n = bp.plan.results[li]; addrs += [sa, sa + 1] + [ra + k for k in range(n)]
    for a in addrs:
        c = SB.cmd_read(None, a); s.send(c[0]); s.send(c[1], 4, 'r')
    rx, errs = M.run(exe, s, tag='mbjobs', maxcyc=400_000_000)
    pos = 0; got = []
    for kind, m in s.reps: got.append((kind, rx[pos:pos + m])); pos += m
    it = iter(got)
    def nxt(k):
        kk, b = next(it); assert kk == k, (kk, k); return b
    for bp in plans:
        a = dec_A(nxt('A%d' % bp.block))
        check('block %d: chain finished by itself, error 0, end tag' % bp.block, a['done'] and not a['busy'] and a['err'] == 0 and a['tag'] == bp.plan.tag, str(a))
    mem = {addr: H.dec_r(nxt('r')) for addr in addrs}
    bad_jobs = SB.verify_all(tasks, plans, lambda x: mem[x])
    check('all %d jobs, split over two blocks, give the Python answer (job numbers in file order)' % len(tasks), not bad_jobs, str(bad_jobs))
    print('RESULT:', 'PASS' if not bad and not errs else 'FAIL (%d)' % (bad + len(errs)))
    return 1 if bad or errs else 0
if __name__ == '__main__': sys.exit(main())
