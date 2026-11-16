#!/usr/bin/env python3
"""Job input / result convention and result gathering on the Tang Nano 20K (design: fpga/build_tang.sh --pool 9 --slices 5 --code 128 --out pool13_5).
  python3 run_jobio_board.py /dev/ttyUSB1
Four jobs get headers and inputs from the host, run, and are checked (one is told it has no output space and must refuse); their results are copied into
one contiguous block of far RAM and compared with the Python answer; a shared-RAM stress job runs alone and then with a 256-word copy running.  Same
checks as test_jobio_sim.py.  Exit code 0 = all passed."""
import sys, time
import board_diag, sdt_host as H, host_sc as hs, jobio as J

STRESS_REPEATS = 400          # about 0.14 s of shared-RAM traffic on the board, so that the copy really overlaps it

def main(port, io=None):
    b = io if io is not None else hs.Board(port)
    bad = 0
    def check(name, cond, extra=''):
        nonlocal bad
        print('%-76s %s %s' % (name, 'ok' if cond else 'FAIL', extra)); bad += (not cond)
    def put(cmd): b.s.write(cmd); b.s.flush()
    def sh_r(a): put(hs.cmd_L(a)); return int.from_bytes(b._rd(4), 'little')
    def far_r(a): put(H.c_r(a)); return H.dec_r(b._rd(4))
    def copy(dir_, near, far, count, timeout=10.0):
        put(H.c_F(dir_, near, far, count)); t0 = time.time(); time.sleep(0.01)
        while True:
            put(H.c_N()); n = H.dec_N(b._rd(12))
            if n['done'] and not n['busy']: return n
            if time.time() - t0 > timeout: raise IOError('copy did not finish')
            time.sleep(0.01)
    def wait_task(tid, timeout=60.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            q = b.task(tid)
            if q['state'] == 3: return q
            time.sleep(0.02)
        board_diag.diagnose(b, tid)
        raise IOError('task %d did not finish' % tid)
    A = J.Job(0, 'vsum', [3 * i + 1 for i in range(12)], 1)
    B = J.Job(1, 'vscale', [100 + 7 * i for i in range(10)], 10)
    S = J.Job(2, 'vstress', [5, 6, 7, 8, 9, 10, 11, 12], 1, arg=STRESS_REPEATS)
    C = J.Job(3, 'vscale', [0xFFFFFFF0 + i for i in range(10)], 10, clone_of=1)
    D = J.Job(4, 'vsum', [9 + i for i in range(12)], 1, clone_of=0, hdr_out_len=0)
    jobs = [A, B, C, D]
    lk = J.build_link([A, B, S, C, D])
    v = b.version(); print('board version %d, %d slices; linked program: %d code words' % (v['version'], v['S'], len(lk.words)))
    if v['version'] < 10: print('Not the far-RAM design (need version 10): fpga/build_tang.sh --pool 9 --slices 5 --code 128 --out pool13_5'); return 2
    put(b'R'); time.sleep(0.2); put(hs.cmd_G())                  # R does not clear the scheduler's hold flag: release it so a hold left by an earlier session cannot stop the jobs
    for c in lk.commands(): b.s.write(c)
    for j in jobs + [S]:
        for c in J.prepare_cmds(lk, j): b.s.write(c)
    b.s.flush(); time.sleep(0.5)
    for tid, j in enumerate(jobs): put(hs.cmd_P(tid, lk.classes[j.cid]['entry'], 0, 0, j.cid))
    qs = [wait_task(t) for t in range(len(jobs))]
    for (j, name), q in zip(((A, 'vsum 12 words'), (B, 'vscale 10 words'), (C, 'vscale clone, wrapping data'), (D, 'vsum clone told: no output space')), qs):
        base = J.window_base(lk, j); status, nout = sh_r(base + J.F_STATUS), sh_r(base + J.F_NOUT)
        if j is D: check('%-34s refused: status 2, n_out 0' % name, status == 2 and nout == 0 and not q['trap'], 'status %d n_out %d' % (status, nout))
        else:      check('%-34s finished: status 1, n_out %d' % (name, len(j.expected())), status == 1 and nout == len(j.expected()) and not q['trap'], 'status %d n_out %d' % (status, nout))
    FAR = 0x1000
    put(H.c_D(FAR, 0x200))
    exp_n = [len(j.expected()) if j is not D else 0 for j in jobs]
    plan, total = J.stitch(lk, list(zip(jobs, exp_n)), FAR)
    ok = True
    for near, far, cnt in plan: n = copy(0, near, far, cnt); ok = ok and n['err'] == 0 and n['moved'] == cnt
    check('every result copied into the far block', ok)
    block = [far_r(FAR + k) for k in range(total)]
    want = A.expected() + B.expected() + C.expected()
    check('stitched block in far RAM = %d words, one after another, equal to the Python answer' % total, block == want, ' '.join('%x' % x for x in block[:4]) + ' ...')
    sb = J.window_base(lk, S)
    put(hs.cmd_P(10, lk.classes[2]['entry'], 0, 0, 2)); q10 = wait_task(10)
    o10 = sh_r(sb + S.out_off)
    check('stress job alone: result right', not q10['trap'] and o10 == S.expected()[0], 'out %d expect %d, %d clocks' % (o10, S.expected()[0], q10['end'] - q10['start']))
    put(hs.cmd_M(sb + S.out_off, 0)); put(hs.cmd_P(11, lk.classes[2]['entry'], 0, 0, 2)); time.sleep(0.003)
    n = copy(0, 0, FAR + 0x40, 256); still = b.task(11)['state'] != 3
    q11 = wait_task(11); o11 = sh_r(sb + S.out_off)
    check('a 256-word copy completed while the stress job was still running', n['err'] == 0 and n['moved'] == 256 and still, '' if still else 'job had already finished: raise STRESS_REPEATS')
    check('stress job with the copy running: result right', not q11['trap'] and o11 == S.expected()[0], 'out %d' % o11)
    d10, d11 = q10['end'] - q10['start'], q11['end'] - q11['start']
    check('the copy did not slow a job that uses the shared RAM (within 4 clocks)', abs(d10 - d11) <= 4, 'alone %d clocks, with a copy %d clocks' % (d10, d11))
    print('\nRESULT:', 'PASS' if not bad else 'FAIL (%d)' % bad)
    return 1 if bad else 0

if __name__ == '__main__': sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB1'))
