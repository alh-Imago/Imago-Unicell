#!/usr/bin/env python3
"""Batch script handler on the Tang Nano 20K (design: fpga/build_tang.sh --pool 9 --slices 5 --code 128 --out pool13_5; the far-RAM bitstream already loaded
is enough - the handler is host software, the card is not changed).
  python3 run_batch_board.py /dev/ttyUSB1
The host writes the two-phase chain of batch_demo.py (scripts, code images, window images) into far RAM and opens the copy window.  From then on batch.LiveExec
reads each step back out of far RAM and executes it with the same host commands as before; the dispatcher is untouched.  Phase 2 replaces the code store and the
class regions with different programs.  The four results, gathered in one far-RAM block, are compared with the Python answer.  Two negative controls follow:
a code load with a job in flight is refused (error 7), and a copy outside the window is refused by the card (error 1).  Same checks as test_batch_sim.py.
Exit code 0 = all passed."""
import sys, time
import board_diag, sdt_host as H, host_sc as hs, batch as B, batch_demo as D

def main(port, io=None):
    b = io if io is not None else hs.Board(port)
    bad = 0
    def check(name, cond, extra=''):
        nonlocal bad
        print('%-84s %s %s' % (name, 'ok' if cond else 'FAIL', extra)); bad += (not cond)
    def put(cmd): b.s.write(cmd); b.s.flush()
    def far_r(a): put(H.c_r(a)); return H.dec_r(b._rd(4))
    def wait_task(tid, timeout=60.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            q = b.task(tid)
            if q['state'] == 3: return q
            time.sleep(0.02)
        board_diag.diagnose(b, tid); raise IOError('task %d did not finish' % tid)
    v = b.version(); print('board version %d, %d slices' % (v['version'], v['S']))
    if v['version'] < 10: print('Not the far-RAM design (need version 10): fpga/build_tang.sh --pool 9 --slices 5 --code 128 --out pool13_5'); return 2
    d = D.build(); img = d['layout'].image
    put(b'R'); time.sleep(0.2); put(hs.cmd_G())
    put(H.c_D(*D.COPY_WINDOW))
    for a in sorted(img): b.s.write(H.c_w(a, img[a]))
    b.s.flush(); time.sleep(0.5)
    check('far RAM holds the first script (read back)', [far_r(D.SCRIPT1 + i) for i in range(4)] == list(d['scripts'][0].words()[:4]))
    log = []; ex = B.LiveExec(b, log=log)
    t0 = time.time(); err, tag, steps = ex.run(d['entry']); dt = time.time() - t0
    check('batch ran to END: error 0, tag %x, %d steps, %.2f s' % (D.TAG, steps, dt), err == 0 and tag == D.TAG, 'err %s tag %s steps %d' % (err, tag, steps))
    qs = [b.task(t) for t in range(4)]
    check('all four jobs finished, none trapped', all(q['state'] == 3 and not q['trap'] for q in qs), ' '.join('%d/%d' % (q['state'], q['trap']) for q in qs))
    n = len(d['expected']); block = [far_r(D.RESULTS + k) for k in range(n)]
    check('results of both phases, gathered in one far-RAM block (%d words), equal the Python answer' % n, block == d['expected'], ' '.join('%x' % x for x in block[:3]) + ' ...')
    n1 = len(d['jobs'][0].expected()) + len(d['jobs'][1].expected())
    check('phase 2 (new code store, new regions) gave the right words: its results are the last %d' % (n - n1), block[n1:] == d['expected'][n1:])
    # negative controls
    # 1. a code load with a job in flight must be refused before anything is sent
    s2 = B.Script().submit(4, d['links'][1].classes[0]['entry'], 0).load_code(0, 0x2200, 10).end(1)
    for i, w in enumerate(s2.words()): b.s.write(H.c_w(0x2000 + i, w))
    b.s.flush(); time.sleep(0.1)
    e2, _, _ = B.LiveExec(b).run(0x2000)
    check('LOAD_CODE with a job in flight is refused (error 7)', e2 == B.ERR_INFLIGHT, 'error %s' % e2)
    wait_task(4)
    # 2. a copy outside the window is refused by the card
    s3 = B.Script().load_code(0, 0x100, 10).end(2)
    for i, w in enumerate(s3.words()): b.s.write(H.c_w(0x2000 + i, w))
    b.s.flush(); time.sleep(0.1)
    e3, _, _ = B.LiveExec(b).run(0x2000)
    check('a copy outside the allowed far-RAM window is refused by the card (error 1)', e3 == 1, 'error %s' % e3)
    print('RESULT:', 'PASS' if not bad else 'FAIL (%d)' % bad)
    return 1 if bad else 0

if __name__ == '__main__':
    if len(sys.argv) != 2: print(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1]))
