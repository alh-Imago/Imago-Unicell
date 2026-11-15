"""Whole-board simulation of the v11 library window + sclink stacks (POOL=7 top), through the UART pins.
Library functions (sum, fill, recursive fib) are called by several classes at once; stacks live in private memory or in a shared window;
a stack that overruns its memory, a jump into another class's code and a library function reaching past the caller's window all trap.
Usage: python3 test_link_sim.py [S]"""
import os, sys
os.environ['POOL'] = '7'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import test_board_sim as tbs, host_sc as hs
import link_cases as lc

def main(S=4, div=8):
    L = lc.build(code_words=256); print(L.report())
    exe = tbs.build(S=S, QD=16, IMW=256, DMW=16, DIV=div, tag='lnk', DSH=256)
    rep_wait = lambda n: ('D', n * 10 * div + 4 * div * 10)
    seq, order = [], []
    seq.append(('B', hs.cmd_V())); order.append('V'); seq.append(rep_wait(8))
    for c in L.commands(): seq.append(('B', c))
    seq.append(('B', hs.cmd_H()))
    ids = [c for c in sorted(lc.EXPECT) if c < 12]
    tasks = ids + [1, 12, 14, 0]            # a second wave: same classes again, reusing slices that just ran something else
    for tid, c in enumerate(tasks): seq.append(('B', hs.cmd_P(tid, L.classes[c]['entry'], 0, 0, c)))
    seq.append(('B', hs.cmd_G())); seq.append(('D', int(os.environ.get('WAITCLK', '900000'))))
    seq.append(('B', hs.cmd_C())); order.append('C'); seq.append(rep_wait(56))
    for t in range(len(tasks)): seq.append(('B', hs.cmd_Q(t))); order.append('Q'); seq.append(rep_wait(22))
    rx = tbs.run(exe, seq, tag='lnk')
    rep = hs.split_replies(rx, order)
    ver, cnt, q = rep[0], rep[1], rep[2:]
    print('board:', ver, '| done', cnt['done'], 'launch_err', cnt['launch_err'])
    bad = 0
    for t, (c, r) in enumerate(zip(tasks, q)):
        exp, trap = lc.EXPECT[c]
        ok = r['state'] == 3 and bool(r['trap']) == trap and (exp is None or r['a0'] == exp)
        bad += not ok
        print('task %2d class %d  state %d trap %d a0 %-9d expect %-9s trap %d  %s' % (t, c, r['state'], r['trap'], r['a0'], exp if exp is not None else '-', trap, 'ok' if ok else 'FAIL'))
    good = not bad and ver['version'] == 8 and cnt['done'] == len(tasks)
    print('RESULT', 'PASS' if good else 'FAIL'); return good

if __name__ == '__main__': sys.exit(0 if main(int(sys.argv[1]) if len(sys.argv) > 1 else 4) else 1)
