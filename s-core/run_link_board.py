#!/usr/bin/env python3
"""run_link_board.py - check the v11 code library window and the sclink stacks on a real Tang Nano 20K.

    python3 run_link_board.py /dev/ttyUSB1

Needs a board built with --pool 7 --code 256 --shared 256 (the V reply says version 8).  Any number of slices.
Same programs as the simulation (test_link_sim.py / link_cases.py): a library of sum, fill and recursive fib is called by nine program
classes (plus two clones); stacks live in private memory or in a shared window; a stack that overruns the private memory, a jump into
another class's code, and a library function reaching past its caller's window all end with the trap flag."""
import sys, argparse
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
import host_sc as hs
import link_cases as lc

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('port'); ap.add_argument('--baud', type=int, default=115200)
    ap.add_argument('--expect', default='', help='exact design wanted, e.g. version=9,S=6 (default: any design new enough)')
    a = ap.parse_args()
    b = hs.Board(a.port, a.baud)
    v = b.version(); print('board:', v)
    hs.check_design(v, hs.parse_expect(a.expect), 8, 'the code library window (a --pool 7 build)')
    info = b.shared_info()
    L = lc.build(shared_words=info['shared_words'], code_words=v['imem_words']); print(L.report())
    b.reset()
    b.shared_write(0, [0] * info['shared_words'])
    L.apply(b)
    ids = [c for c in sorted(lc.EXPECT) if c < 12]
    tasks = ids + [1, 12, 14, 0]
    b.hold()
    for t, c in enumerate(tasks): b.submit(t, L.classes[c]['entry'], 0, 0, c)
    b.go()
    if not b.wait_done(len(tasks), timeout=120): print('TIMEOUT: not all tasks finished')
    bad = 0
    for t, c in enumerate(tasks):
        q = b.task(t); exp, trap = lc.EXPECT[c]
        ok = q['state'] == 3 and bool(q['trap']) == trap and (exp is None or q['a0'] == exp)
        bad += not ok
        print('task %2d class %2d  state %d trap %d a0 %-9d expect %-9s trap %d  %s' % (t, c, q['state'], q['trap'], q['a0'], exp if exp is not None else '-', trap, 'ok' if ok else 'FAIL'))
    print('RESULT', 'PASS' if not bad else 'FAIL')

if __name__ == '__main__': main()
