#!/usr/bin/env python3
"""Hardware batch sequencer on the Tang Nano 20K (design: fpga/build_tang.sh --pool 10 --slices 4 --code 128 --out pool14_4; board version 11).
  python3 run_seq_board.py /dev/ttyUSB1
The host writes the two-phase chain of batch_demo.py into far RAM, opens the copy window and sends J (start); the state machine on the card then walks the scripts
alone while the host only polls A.  Checks as test_seq_sim.py: the chain finishes with error 0 and the end tag, every job is correct, the 20 gathered words equal the
Python answer; then four scripts that must be refused: a WAIT that times out (6), a code load with a job in flight (7), a copy outside the window (1), a bad
opcode (8).  Exit code 0 = all passed."""
import sys, time
import board_diag, sdt_host as H, host_sc as hs, batch as B, batch_demo as D
from scbatch import c_J, dec_A, a_len, SEQ_ERR, CLK_HZ

def main(port, io=None, timeout_case=True):
    b = io if io is not None else hs.Board(port)
    bad = 0
    def check(name, cond, extra=''):
        nonlocal bad
        print('%-88s %s %s' % (name, 'ok' if cond else 'FAIL', extra)); bad += (not cond)
    def put(cmd): b.s.write(cmd); b.s.flush()
    def far_r(a): put(H.c_r(a)); return H.dec_r(b._rd(4))
    v = b.version()
    def poll(limit=30.0):
        t0 = time.time(); time.sleep(0.02)
        while True:
            put(b'A'); a = dec_A(b._rd(a_len(v['version'])))
            if a['done'] and not a['busy']: a['secs'] = time.time() - t0; return a
            if time.time() - t0 > limit: a['secs'] = limit; a['timeout'] = True; return a
            time.sleep(0.02)
    def wait_task(tid, timeout=60.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            q = b.task(tid)
            if q['state'] == 3: return q
            time.sleep(0.02)
        board_diag.diagnose(b, tid); raise IOError('task %d did not finish' % tid)
    print('board version %d, %d slices' % (v['version'], v['S']))
    if v['version'] < 11: print('Not the batch-sequencer design (need version 11): fpga/build_tang.sh --pool 10 --slices 4 --code 128 --out pool14_4'); return 2
    d = D.build(); img = d['layout'].image
    ent = d['links'][1].classes[0]['entry']
    neg = [(0x3400, B.Script().submit(4, ent, 0).wait(1).end(1), 6, 'a WAIT that times out'),
           (0x3440, B.Script().submit(5, ent, 0).load_code(0, 0x2200, 10).end(2), 7, 'a code load with a job in flight'),
           (0x3480, B.Script().load_code(0, 0x100, 10).end(3), 1, 'a copy outside the allowed window'),
           (0x34C0, None, 8, 'a bad opcode')]
    put(b'R'); time.sleep(0.2); put(hs.cmd_G())
    put(H.c_D(*D.COPY_WINDOW))
    for a in sorted(img): b.s.write(H.c_w(a, img[a]))
    for at, sc, _, _ in neg:
        for i, w in enumerate(sc.words() if sc else [0xF, 0, 0, 0]): b.s.write(H.c_w(at + i, w))
    b.s.flush(); time.sleep(0.5)
    check('far RAM holds the first script (read back)', [far_r(D.SCRIPT1 + i) for i in range(4)] == list(d['scripts'][0].words()[:4]))
    put(c_J(d['entry'])); a = poll()
    check('chain finished by itself: error 0, tag %x, 28 steps, %.2f s (host only polled)' % (D.TAG, a['secs']), not a.get('timeout') and a['err'] == 0 and a['tag'] == D.TAG and a['steps'] == 28, str({k: a[k] for k in ('err', 'tag', 'steps')}))
    if 'clk' in a:
        c = a['clk']; sec = c / CLK_HZ
        check('clock counters: total %d clocks = %.3f ms; copying %d, waiting %d, rest %d' % (c, 1000 * sec, a['clk_copy'], a['clk_wait'], c - a['clk_copy'] - a['clk_wait']),
              c > 0 and a['clk_copy'] > 0 and a['clk_wait'] > 0 and a['clk_copy'] + a['clk_wait'] <= c)
        check('the board time is not longer than the time the host measured (%.3f s)' % a['secs'], sec <= a['secs'] + 0.05, '%.3f s on the board' % sec)
        put(b'A'); a2 = dec_A(b._rd(a_len(v['version'])))
        check('counters hold their values after the run ends', a2['clk'] == c and a2['steps'] == a['steps'])
    qs = [b.task(t) for t in range(4)]
    check('all four jobs finished, none trapped', all(q['state'] == 3 and not q['trap'] for q in qs), ' '.join('%d/%d' % (q['state'], q['trap']) for q in qs))
    n = len(d['expected']); block = [far_r(D.RESULTS + k) for k in range(n)]
    check('results of both phases, gathered in one far-RAM block (%d words), equal the Python answer' % n, block == d['expected'], ' '.join('%x' % x for x in block[:3]) + ' ...')
    n1 = len(d['jobs'][0].expected()) + len(d['jobs'][1].expected())
    check('phase 2 (new code store, new regions) gave the right words: its results are the last %d' % (n - n1), block[n1:] == d['expected'][n1:])
    for at, sc, want, name in neg:
        if want == 6 and not timeout_case: continue
        put(c_J(at)); a = poll()
        check('refused: %s -> error %d (%s)' % (name, want, SEQ_ERR[want]), not a.get('timeout') and a['err'] == want, 'got error %d' % a['err'])
        if want in (6, 7):
            for t in ((4,) if want == 6 else (5,)): wait_task(t)
    put(c_J(d['entry'])); a = poll()
    check('the sequencer runs the chain again after the refusals (still healthy)', not a.get('timeout') and a['err'] == 0 and a['tag'] == D.TAG)
    print('RESULT:', 'PASS' if not bad else 'FAIL (%d)' % bad)
    return 1 if bad else 0

if __name__ == '__main__':
    if len(sys.argv) != 2: print(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1]))
