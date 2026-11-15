"""Whole-board simulation test of the v10 shared data RAM (POOL=6 top), through the UART pins.

Several slices run the same sum kernel on different windows of the shared RAM at once (the port arbiter is under load), a producer class
fills a window and a consumer class reads it back in a second phase, windows are guarded (a store one word past the end traps and does not
land; a class with no window traps; a window asked for beyond the RAM is clamped), and the host (commands M, L) loads the inputs and checks
every word afterwards.  Usage: python3 test_shared_sim.py [S]   (S slices, default 4)"""
import os, sys
os.environ.setdefault('POOL', '6')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import test_board_sim as tbs, host_sc as hs
from shared_cases import *

def main(S=4, div=8):
    exe = tbs.build(S=S, QD=16, IMW=256, DMW=16, DIV=div, tag='shr', DSH=256)
    words, base = layout()
    rep_wait = lambda n: ('D', n * 10 * div + 4 * div * 10)
    seq, order = [], []
    seq.append(('B', hs.cmd_V())); order.append('V'); seq.append(rep_wait(8))
    seq.append(('B', hs.cmd_Z())); order.append('Z'); seq.append(rep_wait(4))
    for i, w in enumerate(words): seq.append(('B', hs.cmd_W(i, w)))
    for a, v in preload().items(): seq.append(('B', hs.cmd_M(a, v)))
    for c, (kern, win) in CLASSES.items():
        if win: seq.append(('B', hs.cmd_X(c, win[0], win[1])))
    tid = 0; tasks = []
    for phase in (1, 2):
        seq.append(('B', hs.cmd_H()))
        for (ph, c, exp, trap) in TASKS:
            if ph != phase: continue
            seq.append(('B', hs.cmd_P(tid, base[CLASSES[c][0]], 0, 0, c))); tasks.append((tid, c, exp, trap)); tid += 1
        seq.append(('B', hs.cmd_G())); seq.append(('D', 400000))
    seq.append(('B', hs.cmd_C())); order.append('C'); seq.append(rep_wait(56))
    for (t, c, exp, trap) in tasks: seq.append(('B', hs.cmd_Q(t))); order.append('Q'); seq.append(rep_wait(22))
    em = expect_mem(); addrs = sorted(em)
    for a in addrs: seq.append(('B', hs.cmd_L(a))); order.append('L'); seq.append(rep_wait(4))
    rx = tbs.run(exe, seq, tag='shr')
    rep = hs.split_replies(rx, order)
    ver, info, cnt = rep[0], rep[1], rep[2]
    rt_ = rep[3:3 + len(tasks)]; mem = rep[3 + len(tasks):]
    print('board:', ver, info); print('counters: done', cnt['done'], 'launch_err', cnt['launch_err'])
    bad = 0
    for (t, c, exp, trap), q in zip(tasks, rt_):
        ok = q['state'] == 3 and bool(q['trap']) == trap and (exp is None or q['a0'] == exp)
        bad += not ok
        print('task %2d class %2d %-10s state %d trap %d a0 %08x expect %s trap %d  %s' % (t, c, CLASSES[c][0], q['state'], q['trap'], q['a0'], ('%08x' % exp) if exp is not None else '--------', trap, 'ok' if ok else 'FAIL'))
    mbad = [(a, v, em[a]) for a, v in zip(addrs, mem) if v != em[a]]
    for a, v, e in mbad: print('shared word %3d = %08x, expected %08x  FAIL' % (a, v, e))
    print('shared RAM: %d words checked, %d wrong' % (len(addrs), len(mbad)))
    good = (not bad and not mbad and ver['version'] >= 7 and cnt['done'] == len(tasks) and info['shared_words'] == 256)
    print('RESULT', 'PASS' if good else 'FAIL')
    return good

if __name__ == '__main__': sys.exit(0 if main(int(sys.argv[1]) if len(sys.argv) > 1 else 4) else 1)
