"""Whole-board simulation test of the v9 regions (base / limit checks), through the UART pins (POOL=5 top, one slice).

One slice runs ten small programs back to back, so every program starts on the slice the previous one just left.  Each program class
has a region (host command B) except the last, which has none and must get the whole store.  The checks:
  * a program inside its region runs normally (a0 correct, no trap);
  * a fetch past the end of the region, a jump out of it, a store or load beyond the data limit each end the task with the trap flag;
  * a wild store must NOT land (a later program reads the word it would have aliased to);
  * after the aborted tasks, normal tasks on the same slice still compute the right answers (write counters are cleared at start)."""
import os, sys
os.environ.setdefault('POOL', '5')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import test_board_sim as tbs, host_sc as hs
from region_cases import K, DL, layout

def main():
    div = 8
    exe = tbs.build(S=1, IMW=128, DMW=16, DIV=div, tag='reg')
    seq = []
    words_all, ents = layout()
    assert len(words_all) <= 128
    rep_wait = lambda n: ('D', n * 10 * div + 4 * div * 10)
    seq.append(('B', hs.cmd_V())); order = ['V']; seq.append(rep_wait(8))
    for i, w in enumerate(words_all): seq.append(('B', hs.cmd_W(i, w)))
    for p, (name, src, exp, trap, trim) in enumerate(K):
        if trim is None or os.environ.get('NOREGION'): continue   # no region for this class (NOREGION=1: negative control, no regions at all)
        base, n = ents[p]
        seq.append(('B', hs.cmd_B(p, base, n - trim, DL)))
    seq.append(('B', hs.cmd_H()))
    for p in range(len(K)): seq.append(('B', hs.cmd_P(p, ents[p][0], 0, 0, p)))
    seq.append(('B', hs.cmd_G())); seq.append(('D', 600000))
    seq.append(('B', hs.cmd_C())); order.append('C'); seq.append(rep_wait(56))
    for p in range(len(K)): seq.append(('B', hs.cmd_Q(p))); order.append('Q'); seq.append(rep_wait(22))
    rx = tbs.run(exe, seq, tag='reg')
    rep = hs.split_replies(rx, order)
    ver, cnt, tasks = rep[0], rep[1], rep[2:]
    print('version reply:', ver); print('counters: done', cnt['done'], 'launch_err', cnt['launch_err'])
    bad = 0
    for p, ((name, src, exp, trap, trim), t) in enumerate(zip(K, tasks)):
        ok = (t['state'] == 3) and (bool(t['trap']) == trap) and (exp is None or t['a0'] == exp)
        bad += not ok
        print('%-22s state %d trap %d a0 %08x expect %s trap %d  %s' % (name, t['state'], t['trap'], t['a0'], ('%08x' % exp) if exp is not None else '--------', trap, 'ok' if ok else 'FAIL'))
    print('RESULT', 'PASS' if (not bad and ver['version'] >= 6 and cnt['done'] == len(K)) else 'FAIL')

if __name__ == '__main__': main()
