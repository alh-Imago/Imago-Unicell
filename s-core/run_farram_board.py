#!/usr/bin/env python3
"""Check the far RAM (onboard SDRAM) with the cores, on the Tang Nano 20K.  Design: fpga/build_tang.sh --pool 9 --slices 5 --code 128 --out pool13_5
  python3 run_farram_board.py /dev/ttyUSB1
Checks (the same as test_farram_sim.py): shared RAM -> far -> shared round trip of the whole 256-word shared RAM; refused copies (outside the allowed
window, past the end) move nothing; far RAM survives a core reset; a program stored in far RAM is copied into the code store and runs; a copy
during a running job does not change the job's clock count.  Exit code 0 = all passed."""
import sys, time, random
import board_diag, sdt_host as H, host_sc as hs, sched_tests as st
rt = st.rt
LOOP = 2000          # the job must run for tens of milliseconds so that the copy really overlaps it (60 iterations end within one millisecond)

def main(port, S_expect=None, io=None, kset=None):
    b = io if io is not None else hs.Board(port)
    bad = 0
    def check(name, cond, extra=''):
        nonlocal bad
        print('%-72s %s %s' % (name, 'ok' if cond else 'FAIL', extra)); bad += (not cond)
    def put(cmd): b.s.write(cmd); b.s.flush()
    def far_status(): put(H.c_N()); return H.dec_N(b._rd(12))
    def copy(dir_, near, far, count, timeout=10.0):
        put(H.c_F(dir_, near, far, count)); t0 = time.time(); time.sleep(0.01)
        while True:
            n = far_status()
            if n['done'] and not n['busy']: return n
            if time.time() - t0 > timeout: raise IOError('copy did not finish')
            time.sleep(0.01)
    def far_r(a): put(H.c_r(a)); return H.dec_r(b._rd(4))
    def far_w(a, d): put(H.c_w(a, d))
    def sh_w(a, d): put(hs.cmd_M(a, d))
    def sh_r(a): put(hs.cmd_L(a)); return int.from_bytes(b._rd(4), 'little')
    def wait_task(tid, timeout=30.0):
        t0 = time.time()
        while time.time() - t0 < timeout:
            q = b.task(tid)
            if q['state'] == 3: return q
            time.sleep(0.05)
        board_diag.diagnose(b, tid)
        raise IOError('task %d did not finish' % tid)

    v = b.version()
    print('board version %d, %d slices' % (v['version'], v['S']))
    if v['version'] < 10:
        print('This is not the far-RAM design (version %d, need 10). Build and load: fpga/build_tang.sh --pool 9 --slices 5 --code 128 --out pool13_5' % v['version']); return 2
    if kset:                                                      # workaround for a build whose far RAM settings did not come up as the defaults
        put(H.c_K(*kset)); time.sleep(0.2); print('sent K %d %d %d (settings set by the runner)' % kset)
    put(H.c_I()); i = H.dec_I(b._rd(4)); check('far RAM initialised, settings cl/dly/inv = 2/1/0', i['init_done'] == 1 and (i['cl'], i['dly'], i['inv']) == (2, 1, 0), str(i))
    put(b'R'); time.sleep(0.2); put(hs.cmd_G())                  # R does not clear the scheduler's hold flag: release it so a hold left by an earlier session cannot stop the jobs                                    # a clean start for the cores (the far RAM is not touched by it)
    n = copy(0, 0, 0x100, 1); check('default window refuses a copy (err 1)', n['err'] == 1 and n['moved'] == 0, str(n))
    put(H.c_D(0x1000, 0x1000))                                    # copies may touch far words 0x1000 .. 0x1FFF
    rnd = random.Random(2026); DSH = 256
    pat = [rnd.getrandbits(32) for _ in range(DSH)]
    for k, w in enumerate(pat): sh_w(k, w)
    n = copy(0, 0, 0x1100, DSH); check('whole shared RAM (256 words) -> far RAM', n['err'] == 0 and n['moved'] == DSH, '%d clocks, %.1f per word' % (n['clocks'], n['clocks'] / DSH))
    for k in range(DSH): sh_w(k, 0)
    check('shared RAM wiped', all(sh_r(k) == 0 for k in range(0, DSH, 17)))
    n = copy(1, 0, 0x1100, DSH); check('far RAM -> shared RAM, all 256 words', n['err'] == 0 and n['moved'] == DSH)
    back = [sh_r(k) for k in range(DSH)]
    bad_k = [k for k in range(DSH) if back[k] != pat[k]]
    check('round trip exact: every word back as written', not bad_k, 'first wrong word %d' % bad_k[0] if bad_k else '')
    far_w(0xFFF, 0x11111111); far_w(0x2000, 0x22222222)           # sentinels just outside the window
    for name, args, err in (('far range starts below the window', (0, 0, 0xFFF, 2), 1), ('far range crosses the end of the window', (0, 0, 0x1FFF, 2), 1),
                            ('near range past the end of the shared RAM', (1, 0xFF, 0x1100, 2), 2), ('near range past the end of the code store', (2, 0x7F, 0x1100, 2), 2)):
        n = copy(*args); check('refused: ' + name, n['err'] == err and n['moved'] == 0, str(n))
    check('refused copies wrote nothing (sentinels outside the window intact)', far_r(0xFFF) == 0x11111111 and far_r(0x2000) == 0x22222222)
    put(b'R'); time.sleep(0.3)
    check('far RAM contents and the window survive a core reset', far_r(0x1100 + 7) == pat[7] and copy(0, 0, 0x1100, 1)['err'] == 0)
    # a program in far RAM -> code store -> runs
    prog = rt.assemble(st.k_sum(LOOP)); want = rt.iss(prog)['x'][10]
    for k, w in enumerate(prog): far_w(0x1200 + k, w)
    n = copy(2, 0, 0x1200, len(prog)); check('program image far RAM -> code store (%d words)' % len(prog), n['err'] == 0 and n['moved'] == len(prog))
    put(hs.cmd_P(0, 0, 0, 0, 0)); q0 = wait_task(0)
    check('the program loaded from far RAM runs, result right', not q0['trap'] and q0['a0'] == want, 'a0 %d expect %d' % (q0['a0'], want))
    put(hs.cmd_P(2, 0, 0, 0, 0)); q2 = wait_task(2)                  # the same job once more on the idle board: how much do two identical idle runs differ?
    put(hs.cmd_P(1, 0, 0, 0, 0)); time.sleep(0.003)
    n = copy(0, 0, 0x1300, 256)
    during = b.task(1)['state'] != 3                              # was the job still running when the copy finished?
    q1 = wait_task(1)
    check('a copy during a running job completes (job still running at that moment)', n['err'] == 0 and n['moved'] == 256 and during, '' if during else 'job had already finished: no real overlap, lengthen LOOP')
    d0, d2, d1 = q0['end'] - q0['start'], q2['end'] - q2['start'], q1['end'] - q1['start']
    # A few clocks of difference come from which core and which moment of the core's turn cycle a job starts on (seen on the card: 1 clock in 800,000);
    # a copy that really stole turns from a core would add hundreds.  NOTE: this job never touches the shared RAM, so this shows the copy does not
    # disturb fetching and computing; it does not yet cover the core's own shared-RAM accesses.
    check('the copy did not slow the job (within 4 clocks of the idle runs)', abs(d1 - d0) <= 4 and q1['a0'] == want, 'idle %d and %d, with a copy %d clocks' % (d0, d2, d1))
    print('\nRESULT:', 'PASS' if not bad else 'FAIL (%d)' % bad)
    return 1 if bad else 0

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('port', nargs='?', default='/dev/ttyUSB1')
    ap.add_argument('--k', default='', help='send the far RAM settings first, as cl,dly,inv (e.g. 2,1,0)')
    a = ap.parse_args()
    sys.exit(main(a.port, kset=tuple(int(x) for x in a.k.split(',')) if a.k else None))
