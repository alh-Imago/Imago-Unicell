#!/usr/bin/env python3
"""run_violations_board.py - check on a real Tang Nano 20K that every kind of memory/code violation stops the task, on every slice.

    python3 run_violations_board.py /dev/ttyUSB1 [--slices N]

Needs a board built with --pool 6 or 7 (V reply version 7 or higher).  Uses the same plan as the simulation (violation_cases.py,
test_violations_sim.py): ten rounds that fill every slice with a program that does one wrong thing (wild private store/load, shared store
or load past the window, shared access with no window, jump out of its code region), mixed with good programs, all kinds at once, and
guard words in the shared RAM that a stray store must not change.  A task must end with the trap flag (or without it for good programs),
good programs must give their right answer, guard words must be unchanged, and each round must have used every slice (counted from the
slot number the board reports for each task)."""
import sys, argparse
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
import host_sc as hs
import violation_cases as vc

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('port'); ap.add_argument('--baud', type=int, default=115200)
    ap.add_argument('--expect', default='version=7', help='design the board must be running (default: version 7 or higher)')
    ap.add_argument('--slices', type=int, default=0, help='number of slices (default: ask the board)')
    a = ap.parse_args()
    b = hs.Board(a.port, a.baud); b.flush_input()
    v = b.version(); print('board:', v)
    hs.check_design(v, hs.parse_expect(a.expect), 7, 'the shared data RAM (a --pool 6 or 7 build)')
    S = a.slices or v['S']
    ops, exp, cover = vc.plan(S)
    need = max((op[1] for op in ops if op[0] == 'wait_done'), default=0)
    results = {}
    for op in ops:
        if op[0] == 'send': b.s.write(op[1]); b.s.flush()
        elif op[0] == 'wait_clocks': b.s.flush(); hs.time.sleep(0.05)
        elif op[0] == 'wait_done':
            b.s.flush()
            if not b.wait_done(op[1], timeout=60): print('TIMEOUT waiting for', op[1], 'tasks to finish')
        elif op[0] == 'read':
            if op[1] == 'Q': results[op[3]] = b.task(op[2])
            else: b.s.write(hs.cmd_L(op[2])); results[op[3]] = hs.dec_L(b._rd(4))
        elif op[0] == 'round': print('...', op[1])
    ok = vc.evaluate(results, exp, cover, S)
    sys.exit(0 if ok else 1)

if __name__ == '__main__': main()
