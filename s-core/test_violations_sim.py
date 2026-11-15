"""Whole-board simulation of the violation test (violation_cases.py) on the v11 board design, through the UART pins.
Usage: python3 test_violations_sim.py [S]   (default 6)"""
import os, sys
os.environ.setdefault('POOL', '7')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import test_board_sim as tbs, host_sc as hs
import violation_cases as vc

def main(S=6, div=8):
    ops, exp, cover = vc.plan(S)
    exe = tbs.build(S=S, QD=16, IMW=128, DMW=16, DIV=div, tag='vio', DSH=256)
    rw = lambda n: ('D', n * 10 * div + 4 * div * 10)
    seq, order, tags = [('B', hs.cmd_V()), rw(8)], ['V'], []
    for op in ops:
        if op[0] == 'send': seq.append(('B', op[1]))
        elif op[0] == 'wait_clocks': seq.append(('D', op[1]))
        elif op[0] == 'wait_done': seq.append(('D', 300000))
        elif op[0] == 'read':
            if op[1] == 'Q': seq.append(('B', hs.cmd_Q(op[2]))); order.append('Q'); seq.append(rw(22))
            else: seq.append(('B', hs.cmd_L(op[2]))); order.append('L'); seq.append(rw(4))
            tags.append(op[3])
    rep = hs.split_replies(tbs.run(exe, seq, tag='vio'), order)
    print('board:', rep[0])
    return vc.evaluate(dict(zip(tags, rep[1:])), exp, cover, S)

if __name__ == '__main__': sys.exit(0 if main(int(sys.argv[1]) if len(sys.argv) > 1 else 6) else 1)
