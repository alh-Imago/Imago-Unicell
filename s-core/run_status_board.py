#!/usr/bin/env python3
"""run_status_board.py - check the v12 read-out (status T, usage U, trap cause E) on a real Tang Nano 20K.

    python3 run_status_board.py /dev/ttyUSB1

Needs a board built with --pool 8 (the V reply says version 9).  The same programs and checks as the simulation (test_status_sim.py):
S+2 critical and 3 bulk long jobs; while they run the status must show every slice running, 2 critical and 3 bulk jobs waiting, and the
usage counters must all be moving; when they are done the board must look idle and the per-slice usage must add up to the board's own busy
counter; then one job per violation kind: each must report the right cause and address."""
import sys, time, argparse
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
import host_sc as hs
import status_cases as sc

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('port'); ap.add_argument('--baud', type=int, default=115200)
    ap.add_argument('--spin', type=int, default=20000, help='loop count of the long jobs (default 20000, about 0.2 s each)')
    ap.add_argument('--expect', default='version=9')
    a = ap.parse_args()
    b = hs.Board(a.port, a.baud); b.flush_input()
    v = b.version(); print('board:', v)
    hs.check_design(v, hs.parse_expect(a.expect), 9, 'the v12 read-out (a --pool 8 build)')
    S = v['S']; lk = sc.link(a.spin)
    if len(lk.words) > v['imem_words']: sys.exit('the test programs need %d code words, the build has %d' % (len(lk.words), v['imem_words']))
    b.reset(); b.load(0, lk.words); lk.apply(b, with_code=False)
    res = {}
    n_crit = S + 2; total = n_crit + 3
    b.hold()
    for t in range(n_crit): b.submit(t, lk.classes[1]['entry'], 0, 1, 1)
    for t in range(n_crit, total): b.submit(t, lk.classes[1]['entry'], 0, 0, 1)
    b.s.flush(); time.sleep(0.1)
    res['T_hold'] = b.status()
    b.go(); time.sleep(0.02)
    res['T_run'] = b.status(); res['U_run'] = b.usage()
    if not b.wait_done(total, timeout=120): print('TIMEOUT in phase 1')
    res['T_idle'] = b.status(); res['U_end'] = b.usage(); res['C_end'] = b.counters()
    for t in range(total): res['Q%d' % t] = b.task(t)
    b.hold()
    for i, c in enumerate(sc.WANT): b.submit(i, lk.classes[c]['entry'], 0, 0, c)
    b.go()
    if not b.wait_done(total + len(sc.WANT), timeout=60): print('TIMEOUT in phase 2')
    for i, c in enumerate(sc.WANT): res['E%d' % c] = b.trap_info(i); res['P2Q%d' % c] = b.task(i)
    sys.exit(0 if sc.evaluate(res, S, n_crit, a.spin) else 1)

if __name__ == '__main__': main()
