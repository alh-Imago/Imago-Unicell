"""STATUS READ INSIDE THE BLOCKS (ledger #1457): the same whole-board run through the old top (sc_top_k7_v10 + host_bridge_v11) and the new one (sc_top_k7_v11 +
host_bridge_v12 + blk_rd_v1).  Same job plan as test_fu_sim.py on 2 blocks of 4 slices (units on).  Before the run, in the middle of it and after it, every read command
(V C T U E Q N A I Z L, and r) is sent to block 0 and to block 1; EVERY reply byte of the two builds must be equal (so the replies and their clock-exact counters are the
same), and the jobs must give the Python answer on the new build.  Needs iverilog.  About 10 minutes.  Usage: python3 test_hubnarrow_v1.py"""
import os, sys, subprocess, shutil
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import host_sc as hs, sdt_host as H, jobcomp as C, scblocks as SB
import test_mb_harness as M
NB, S, ULW, NU = int(os.environ.get('NB', '2')), int(os.environ.get('S', '4')), 2, 2     # NB=4 S=2 also run (ledger #1457)
FAR_WORDS = 1 << 14
def build(tag, new):
    if not shutil.which('iverilog'): print('SKIP: iverilog not installed'); sys.exit(1)
    exe = os.path.join(HERE, tag + '.vvp'); F = os.path.join(HERE, 'fpga')
    if new:
        files = ['tb_k7fu3.v', 'sc_top_k7_v11.v', 'sc_block_v3.v', 'far_arb.v', 'jtag_link_v2.v', 'host_bridge_v12.v', 'blk_rd_v1.v', 'farram_bram_v1.v', 'batch_seq_v2.v', 'far_copy.v']; tb = 'tb_k7fu3'
    else:
        files = ['tb_k7fu2.v', 'sc_top_k7_v10.v', 'sc_block_v3.v', 'far_arb.v', 'jtag_link_v2.v', 'host_bridge_v11.v', 'farram_bram_v1.v', 'batch_seq_v2.v', 'far_copy.v']; tb = 'tb_k7fu'
    srcs = [os.path.join(F, f) for f in files] + [os.path.join(HERE, f) for f in ('sc_sys_v17.v', 'fit_search_tree.v', 'uc_core_v2v.v', 'uc_unitw%d.v' % (1 << ULW), 'uc_unith%d.v' % (1 << ULW))]
    subprocess.run(['iverilog', '-g2012', '-P%s.NB=%d' % (tb, NB), '-P%s.S=%d' % (tb, S), '-P%s.FZ=1' % tb, '-P%s.ULW=%d' % (tb, ULW), '-P%s.NU=%d' % (tb, NU), '-o', exe] + srcs, check=True)
    return exe
def osel(b): return b'O' + bytes([b])
def battery(s, tag):
    """every read command, to both blocks; returns nothing (replies are collected by M.run)"""
    for b in range(NB):
        s.send(osel(b))
        s.send(b'V', 8, '%s V%d' % (tag, b)); s.send(b'C', 56, '%s C%d' % (tag, b)); s.send(b'T', 8 + 4 * S, '%s T%d' % (tag, b)); s.send(b'U', 8 + 8 * S, '%s U%d' % (tag, b))
        for tid in (0, 1, 3): s.send(b'E' + tid.to_bytes(2, 'little'), 5, '%s E%d.%d' % (tag, b, tid)); s.send(hs.cmd_Q(tid), 22, '%s Q%d.%d' % (tag, b, tid))
        s.send(b'N', 12, '%s N%d' % (tag, b)); s.send(b'A', 24, '%s A%d' % (tag, b)); s.send(b'I', 4, '%s I%d' % (tag, b)); s.send(b'Z', 4, '%s Z%d' % (tag, b))
        s.send(b'L' + (0).to_bytes(2, 'little'), 4, '%s L%d' % (tag, b))
def script(plans, tasks):
    s = M.Script(); s.wait(0x3000)
    battery(s, 'pre')
    for c in SB.cmds_setup(plans):
        if c[:1] == b'w': s.send(c, extra=0x40)
        elif c == hs.cmd_R(): s.send(c); s.wait(200)
        else: s.send(c)
    for c in SB.cmds_start(plans): s.send(c)
    s.wait(150_000); battery(s, 'mid')
    s.wait(1_100_000)
    for bp in plans:
        c = SB.cmds_poll(bp); s.send(c[0]); s.send(c[1], 24, 'poll%d' % bp.block)
    battery(s, 'post')
    addrs = []
    for bp in plans:
        for li in range(len(bp.task_ids)):
            sa, ra, n = bp.plan.results[li]; addrs += [sa, sa + 1] + [ra + k for k in range(n)]
    for a in addrs:
        c = SB.cmd_read(None, a); s.send(c[0]); s.send(c[1], 4, 'r')
    return s, addrs
def run_build(new, plans, tasks):
    tag = 'hub_new' if new else 'hub_old'
    exe = build(tag, new); s, addrs = script(plans, tasks)
    rx, errs = M.run(exe, s, tag=tag, maxcyc=400_000_000)
    pos = 0; got = []
    for kind, m in s.reps: got.append((kind, rx[pos:pos + m])); pos += m
    return got, errs, addrs
def main():
    bad = 0
    def check(name, cond, extra=''):
        nonlocal bad
        print('%-100s %s %s' % (name, 'ok' if cond else 'FAIL', extra)); bad += (not cond)
    tasks = [C.Task('vsum', [3 * i + 1 for i in range(12)]), C.Task('vscale', [100 + 7 * i for i in range(10)], arg=10), C.Task('vstress', [4, 5, 6, 7, 8, 9], arg=9),
             C.Task('vsum', [5, 5, 5, 9, 1]), C.Task('vscale', [0xFFFFFFF0 + i for i in range(8)], arg=8), C.Task('vsum', list(range(20, 40))), C.Task('vstress', [11, 12, 13], arg=3)]
    LWS = [int(x) for x in os.environ.get('LWS', '2,1,2,0,2,1,0').split(',')]      # a job wider than a block (2**lw lanes > S slices without a fusion unit that fits) can never start: use LWS=1,1,1,0,1,1,0 with S=2
    for t, w in zip(tasks, LWS): t.lw = w
    plans = SB.plan_blocks(tasks, NB, imem=128, dsh=256, far_words=FAR_WORDS)
    old, e0, addrs = run_build(False, plans, tasks)
    new, e1, _ = run_build(True, plans, tasks)
    check('both builds ran with no link timeout', not e0 and not e1, str(e0 + e1))
    check('the same number of replies came back', len(old) == len(new), '%d %d' % (len(old), len(new)))
    diff = [(a[0], a[1], b[1]) for a, b in zip(old, new) if a != b]
    n_read = sum(1 for k, _ in old if ' ' in (k or ''))
    def first(x, y): return next((i for i in range(min(len(x), len(y))) if x[i] != y[i]), -1)
    check('EVERY reply byte of the %d status replies equal, old top against new top' % n_read, not diff, '; '.join('%s byte %d: %02x != %02x' % (k, first(x, y), x[first(x, y)], y[first(x, y)]) for k, x, y in diff[:8]))
    if diff: print('differing replies:', ' '.join(k for k, _, _ in diff))
    mem_o = {}; it_o = [(k, b) for k, b in old if k == 'r']
    for addr, (k, b) in zip(addrs, it_o): mem_o[addr] = H.dec_r(b)
    print('jobs on the OLD build:', 'right' if not SB.verify_all(tasks, plans, lambda x: mem_o[x]) else 'WRONG: ' + str(SB.verify_all(tasks, plans, lambda x: mem_o[x]))[:200])
    print('tasks per block:', [len(bp.task_ids) for bp in plans], ' blocks planned:', len(plans))
    mem = {}; it = [(k, b) for k, b in new if k == 'r']
    for addr, (k, b) in zip(addrs, it): mem[addr] = H.dec_r(b)
    bad_jobs = SB.verify_all(tasks, plans, lambda x: mem[x])
    check('all jobs give the Python answer on the new build', not bad_jobs, str(bad_jobs))
    post = {k: b for k, b in new if k and k.startswith('post C')}
    check('the C reply after the run shows work done (cycle counter and done count are not zero)', all(int.from_bytes(b[0:4], 'little') > 0 and (int.from_bytes(b[4:8], 'little') > 0 or len(plans[int(k[-1])].task_ids) == 0 if int(k[-1]) < len(plans) else True) for k, b in post.items()), str({k: (int.from_bytes(b[0:4], 'little'), int.from_bytes(b[4:8], 'little')) for k, b in post.items()}))
    print('RESULT:', 'PASS' if not bad else 'FAIL (%d)' % bad)
    return 1 if bad else 0
if __name__ == '__main__': sys.exit(main())
