"""MULTI-BLOCK Kintex top (fpga/sc_top_k7_v8.v: NB x sc_block, one host bridge with the O (select block) command, one far-RAM arbiter) in the whole-board
simulation, through the simulated JTAG link (ledger #1347).  Needs iverilog.  Usage:  python3 test_mb_sim.py [one|only1|both|all]   (default all)
 one   NB = 1: the existing k7 sequencer test (test_k7_sim.py) run unchanged against the NB = 1 build; it must pass with the same clock counts.
 only1 NB = 2, the two-phase demo chain run on block 1 ONLY (block 0 is selected for nothing but a check): block 1 finishes (28 steps, tag, four jobs, results
       equal the Python answer), block 0 stays untouched (sequencer idle, no step run, its job table empty).
 both  NB = 2, the same chain started on BOTH blocks one after the other (two J commands) and run at the same time, sharing the one far RAM: both finish with
       the right answer; the clock counts of each block are printed (they differ from a lone block only by the waiting for the shared far RAM)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import host_sc as hs, sdt_host as H, batch as B, batch_demo as D
import test_mb_harness as M
from scbatch import dec_A

def jcmd(a): return b'J' + a.to_bytes(3, 'little')
def osel(b): return b'O' + bytes([b])
ALEN = 24

def run_one():
    import test_k7_sim as T
    class FF:
        Script = M.Script
        @staticmethod
        def build(tag='k7'): return M.build(tag, NB=1, S=2)
        run = staticmethod(M.run)
    T.F = FF
    return T.main()

def run_two(starts, tag):
    """starts = list of blocks that get the J command; the images are written through block 1 (to use its far-RAM path) when 1 is in starts, else block 0."""
    bad = 0
    def check(name, cond, extra=''):
        nonlocal bad
        print('%-98s %s %s' % (name, 'ok' if cond else 'FAIL', extra)); bad += (not cond)
    d = D.build(); img = d['layout'].image; n = len(d['expected'])
    exe = M.build(tag, NB=2, S=2)
    s = M.Script(); s.wait(0x3000)
    s.send(osel(0)); s.send(hs.cmd_V(), 8, 'V0')
    s.send(osel(1)); s.send(hs.cmd_V(), 8, 'V1')
    s.send(osel(starts[0]))
    s.send(osel(3))                                                  # a block number past NB: must be ignored (stay on the selected block)
    for b in (0, 1):                                                 # each block has its own copy window
        s.send(osel(b)); s.send(H.c_D(*D.COPY_WINDOW))
    s.send(osel(starts[0]))
    for a in sorted(img): s.send(H.c_w(a, img[a]), extra=0x40)
    for b in starts:
        s.send(osel(b)); s.send(jcmd(d['entry']))
    s.wait(1_000_000)
    for b in (0, 1):
        s.send(osel(b)); s.send(b'A', ALEN, 'A%d' % b)
    s.wait(1_500_000)
    for b in (0, 1):
        s.send(osel(b)); s.send(b'A', ALEN, 'A%d' % b)
        for tid in range(4): s.send(hs.cmd_Q(tid), 22, 'Q%d' % b)
    s.send(osel(1))
    for k in range(n + 1): s.send(H.c_r(d['results'] + k), 4, 'r')
    rx, errs = M.run(exe, s, tag=tag, maxcyc=400_000_000)
    pos = 0; got = []
    for kind, m in s.reps: got.append((kind, rx[pos:pos + m])); pos += m
    it = iter(got)
    def nxt(k):
        kk, b = next(it); assert kk == k, (kk, k); return b
    v0, v1 = hs.dec_V(nxt('V0')), hs.dec_V(nxt('V1'))
    check('block 0 and block 1 both answer V (version 12, 2 slices)', v0['version'] == 12 and v1['version'] == 12 and v0['S'] == 2 and v1['S'] == 2, '%s %s' % (v0['version'], v1['version']))
    a = {}; q = {}
    for b in (0, 1): nxt('A%d' % b)                                  # first poll: not checked
    for b in (0, 1):
        a[b] = [None, dec_A(nxt('A%d' % b))]
        q[b] = [hs.dec_Q(nxt('Q%d' % b)) for _ in range(4)]
    for b in (0, 1):
        a2 = a[b][1]
        if b in starts:
            check('block %d: chain finished by itself, error 0, tag 0x600d, 28 steps' % b, a2['done'] and not a2['busy'] and a2['err'] == 0 and a2['tag'] == D.TAG and a2['steps'] == 28, str(a2))
            check('block %d: all four jobs finished, none trapped' % b, all(x['state'] == 3 and not x['trap'] for x in q[b]), ' '.join('%d/%d' % (x['state'], x['trap']) for x in q[b]))
        else:
            check('block %d (not started): sequencer idle, no step run, no job done' % b, not a2['busy'] and not a2['done'] and a2['steps'] == 0 and all(x['state'] != 3 for x in q[b]), str(a2))
    block = [H.dec_r(nxt('r')) for _ in range(n)]; after = H.dec_r(nxt('r'))
    check('gathered results (%d words) equal the Python answer' % n, block == d['expected'], ' '.join('%x' % x for x in block[:3]) + ' ...')
    check('the word past the block was not written', after == 0xEEEEEEEE, '%08x' % after)
    if len(starts) == 2:
        print('board clocks of the chain: block 0 %d, block 1 %d (a lone block took 89837 in test_k7_sim)' % (a[0][1]['clk'], a[1][1]['clk']))
    print('RESULT:', 'PASS' if not bad else 'FAIL (%d)' % bad)
    return 1 if bad else 0

def main():
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    rc = 0
    if what in ('one', 'all'): print('== NB=1, existing k7 test'); rc |= run_one()
    if what in ('only1', 'all'): print('== NB=2, chain on block 1 only'); rc |= run_two([1], 'mb_only1')
    if what in ('both', 'all'): print('== NB=2, chain on both blocks at once'); rc |= run_two([0, 1], 'mb_both')
    return rc
if __name__ == '__main__': sys.exit(main())
