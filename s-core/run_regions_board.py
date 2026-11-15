#!/usr/bin/env python3
"""run_regions_board.py - check the v9 regions (base / limit) on a real Tang Nano 20K.

    python3 run_regions_board.py /dev/ttyUSB1

Needs a board built with --pool 5 (the V reply says version 6).  Runs the same twelve small programs as the simulation test
(region_cases.py): programs inside their region run normally; a fetch past the end of the region, a jump out of it and a load or
store beyond the data limit each end the task with the trap flag; a wild store must not land; and normal tasks after the aborted
ones still give the right answers.  Use a build with ONE slice (--slices 1) so every program runs on the same slice, one after
the other: that is what makes the 'recovers after an abort' and 'wild store did not land' checks meaningful.
(With more slices the traps still show, but the later checks may run on a different slice.)"""
import sys, time, argparse
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
import host_sc as hs
from region_cases import K, DL, layout

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('port'); ap.add_argument('--baud', type=int, default=115200)
    ap.add_argument('--expect', default='version=6,S=1', help='design the board must be running (default version=6,S=1: a one-slice build with regions)')
    a = ap.parse_args()
    b = hs.Board(a.port, a.baud)
    v = b.version(); print('board:', v)
    hs.check_design(v, hs.parse_expect(a.expect), 6, 'regions (a --pool 5 build)')
    words, ents = layout()
    if len(words) > v['imem_words']: sys.exit('the test programs need %d code words, the build has %d' % (len(words), v['imem_words']))
    b.reset(); b.load(0, words)
    for p, (name, src, exp, trap, trim) in enumerate(K):
        if trim is None: continue
        base, n = ents[p]; b.region(p, base, n - trim, DL)
    b.hold()
    for p in range(len(K)): b.submit(p, ents[p][0], 0, 0, p)
    b.go()
    if not b.wait_done(len(K), timeout=60): print('TIMEOUT: not all tasks finished')
    bad = 0
    for p, (name, src, exp, trap, trim) in enumerate(K):
        t = b.task(p)
        ok = (t['state'] == 3) and (bool(t['trap']) == trap) and (exp is None or t['a0'] == exp)
        bad += not ok
        print('%-30s state %d trap %d a0 %08x expect %s trap %d  %s' % (name, t['state'], t['trap'], t['a0'], ('%08x' % exp) if exp is not None else '--------', trap, 'ok' if ok else 'FAIL'))
    print('RESULT', 'PASS' if not bad else 'FAIL')

if __name__ == '__main__': main()
