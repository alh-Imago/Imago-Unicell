#!/usr/bin/env python3
"""run_shared_board.py - check the v10 shared data RAM on a real Tang Nano 20K.

    python3 run_shared_board.py /dev/ttyUSB1

Needs a board built with --pool 6 (--shared 256 or larger; the V reply says version 7).  Any number of slices.
What it does (the same programs and checks as the simulation, test_shared_sim.py):
  * the host loads inputs into the shared RAM (command M) and gives each program class a window (command X);
  * eight sum tasks (four windows, two tasks each) run at once on the shared RAM; a producer fills a window, and in a second phase a
    consumer class reads the same window back;
  * a store one word past a window's end, a load past its length, an access by a class with no window, and a window asked for beyond the
    RAM (clamped) all end the task with the trap flag and the stray store must not land;
  * the host reads 81 words back (command L) and compares every one."""
import sys, argparse
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
import host_sc as hs
from shared_cases import *

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('port'); ap.add_argument('--baud', type=int, default=115200)
    ap.add_argument('--expect', default='version=7', help='design the board must be running (default version=7)')
    a = ap.parse_args()
    b = hs.Board(a.port, a.baud)
    v = b.version(); print('board:', v)
    hs.check_design(v, hs.parse_expect(a.expect), 7, 'the shared data RAM (a --pool 6 build)')
    info = b.shared_info(); print('shared RAM:', info)
    if info['shared_words'] < 256 or info['window_log2'] != 14: sys.exit('this test needs a shared RAM of at least 256 words (build with --shared 256)')
    words, base = layout()
    if len(words) > v['imem_words']: sys.exit('the test programs need %d code words, the build has %d (use --code 128 or more)' % (len(words), v['imem_words']))
    b.reset(); b.load(0, words)
    b.shared_write(0, [0] * info['shared_words'])            # a reset keeps the shared RAM: clear it so stale results from an earlier run cannot pass
    b.shared_write_map(preload())
    for c, (kern, win) in CLASSES.items():
        if win: b.shared_region(c, *win)
    tid, tasks = 0, []
    for phase in (1, 2):
        b.hold()
        first = len(tasks)
        for (ph, c, exp, trap) in TASKS:
            if ph != phase: continue
            b.submit(tid, base[CLASSES[c][0]], 0, 0, c); tasks.append((tid, c, exp, trap)); tid += 1
        b.go()
        if not b.wait_done(len(tasks), timeout=60): print('TIMEOUT in phase', phase)
    bad = 0
    for (t, c, exp, trap) in tasks:
        q = b.task(t)
        ok = q['state'] == 3 and bool(q['trap']) == trap and (exp is None or q['a0'] == exp)
        bad += not ok
        print('task %2d class %2d %-10s state %d trap %d a0 %08x expect %s trap %d  %s' % (t, c, CLASSES[c][0], q['state'], q['trap'], q['a0'], ('%08x' % exp) if exp is not None else '--------', trap, 'ok' if ok else 'FAIL'))
    em = expect_mem(); addrs = sorted(em)
    got = [b.shared_read(a_, 1)[0] for a_ in addrs]
    mbad = [(a_, g, em[a_]) for a_, g in zip(addrs, got) if g != em[a_]]
    for a_, g, e in mbad: print('shared word %3d = %08x, expected %08x  FAIL' % (a_, g, e))
    print('shared RAM: %d words checked, %d wrong' % (len(addrs), len(mbad)))
    print('RESULT', 'PASS' if not bad and not mbad else 'FAIL')

if __name__ == '__main__': main()
