"""KINTEX card (fpga/sc_top_k7_v1.v) in the whole-board simulation: the same sequencer test as test_seq_sim.py, but the host talks through the JTAG user register
(BSCANE2 model in fpga/tb_k7.v, scans of the byte link jtag_link_v1) and the far RAM is block RAM.  Cloned from test_seq_sim.py.  Needs iverilog.
(original text follows)  Batch SEQUENCER (hardware, fpga/batch_seq.v) in the whole-board simulation.
The host only writes the images of batch_demo.py into far RAM, opens the copy window and sends J (start); the state machine then reads the steps itself.
 1. the two-phase chain (phase 2 replaces the code store and the class regions): done, error 0, tag 0x600d, 28 steps, no job trapped, the 20 gathered
    result words equal the Python answer, the word past the block is untouched;
 2. four small scripts check the refusals: a WAIT that times out (error 6), a code load with a job in flight (error 7), a copy outside the window (error 1),
    a bad opcode (error 8).  The first two leave a job running; the sequencer reports and the job still finishes."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import host_sc as hs, sdt_host as H, batch as B, batch_demo as D
import test_k7_harness as F

def jcmd(a): return b'J' + a.to_bytes(3, 'little')
from scbatch import dec_A

ALEN = 24
V2 = True

def main():
    bad = 0
    def check(name, cond, extra=''):
        nonlocal bad
        print('%-90s %s %s' % (name, 'ok' if cond else 'FAIL', extra)); bad += (not cond)
    d = D.build(); img = d['layout'].image
    ent = d['links'][1].classes[0]['entry']                   # phase 2 leaves vstress as class 0 in the code store
    neg = {0x3400: B.Script().submit(4, ent, 0).wait(1).end(1),
           0x3440: B.Script().submit(5, ent, 0).load_code(0, 0x2200, 10).end(2),
           0x3480: B.Script().load_code(0, 0x100, 10).end(3),
           0x34C0: None}
    exe = F.build('k7seq')
    s = F.Script(); s.wait(0x3000)
    s.send(hs.cmd_V(), 8, 'V')
    s.send(H.c_D(*D.COPY_WINDOW))
    for a in sorted(img): s.send(H.c_w(a, img[a]), extra=0x40)
    for at, sc in neg.items():
        words = sc.words() if sc else [0xF, 0, 0, 0]
        for i, w in enumerate(words): s.send(H.c_w(at + i, w), extra=0x40)
    s.send(jcmd(d['entry']))
    s.wait(1_000_000); s.send(b'A', ALEN, 'A'); s.wait(1_500_000); s.send(b'A', ALEN, 'A')
    n = len(d['expected'])
    for tid in range(4): s.send(hs.cmd_Q(tid), 22, 'Q')
    for k in range(n + 1): s.send(H.c_r(d['results'] + k), 4, 'r')
    for at in sorted(neg):
        s.send(jcmd(at)); s.wait(400_000); s.send(b'A', ALEN, 'A')
    s.wait(500_000)
    for tid in (4, 5): s.send(hs.cmd_Q(tid), 22, 'Q')
    rx, errs = F.run(exe, s, tag='k7seq', maxcyc=400_000_000)
    pos = 0; got = []
    for kind, m in s.reps: got.append((kind, rx[pos:pos + m])); pos += m
    it = iter(got)
    def nxt(k):
        kk, b = next(it); assert kk == k, (kk, k); return b
    v = hs.dec_V(nxt('V'))
    check('board version %d' % (12 if V2 else 11), v['version'] == (12 if V2 else 11), str(v['version']))
    a1, a2 = dec_A(nxt('A')), dec_A(nxt('A'))
    check('chain finished by itself: done, not busy, error 0, tag 0x600d, 28 steps', a2['done'] and not a2['busy'] and a2['err'] == 0 and a2['tag'] == D.TAG and a2['steps'] == 28, str(a2))
    if V2:
        nwords = sum(st[3] for sc in d['scripts'] for st in sc.steps if st[0] in (B.LOAD_CODE, B.LOAD_DATA, B.SAVE))
        c = a2['clk']
        check('clock counters: total %d, copying %d, waiting %d, rest %d' % (c, a2['clk_copy'], a2['clk_wait'], c - a2['clk_copy'] - a2['clk_wait']), c > 0 and a2['clk_copy'] > 0 and a2['clk_wait'] > 0 and a2['clk_copy'] + a2['clk_wait'] < c)
        check('the copies cost at least 3 clocks per word (%d words in the chain; block RAM, no SDRAM waits)' % nwords, a2['clk_copy'] >= 3 * nwords, '%.1f clocks per word' % (a2['clk_copy'] / nwords))
        check('last step shown is the END step of the second script', a2['op'] == 0 and a2['pc'] == D.SCRIPT2 + 4 * 14, 'pc %#x op %d' % (a2['pc'], a2['op']))
    qs = [hs.dec_Q(nxt('Q')) for _ in range(4)]
    check('all four jobs finished, none trapped', all(q['state'] == 3 and not q['trap'] for q in qs), ' '.join('%d/%d' % (q['state'], q['trap']) for q in qs))
    block = [H.dec_r(nxt('r')) for _ in range(n)]; after = H.dec_r(nxt('r'))
    check('gathered results of both phases (%d words) equal the Python answer' % n, block == d['expected'], ' '.join('%x' % x for x in block[:3]) + ' ...')
    check('the word past the block was not written', after == 0xEEEEEEEE, '%08x' % after)
    for (at, _), (want, name) in zip(sorted(neg.items()), ((6, 'a WAIT that times out'), (7, 'a code load with a job in flight'), (1, 'a copy outside the window'), (8, 'a bad opcode'))):
        a = dec_A(nxt('A'))
        check('refused: %s -> error %d' % (name, want), a['done'] and not a['busy'] and a['err'] == want, str(a))
    q4, q5 = hs.dec_Q(nxt('Q')), hs.dec_Q(nxt('Q'))
    check('the jobs left running by those scripts still finish, no trap', q4['state'] == 3 and q5['state'] == 3 and not q4['trap'] and not q5['trap'], '%d %d' % (q4['state'], q5['state']))
    print('RESULT:', 'PASS' if not bad else 'FAIL (%d)' % bad)
    return 1 if bad else 0

if __name__ == '__main__': sys.exit(main())
