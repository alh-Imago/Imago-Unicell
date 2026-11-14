#!/usr/bin/env python3
"""run_board.py - drive the S-Core design on a Tang Nano 20K over the USB serial port.

    pip install pyserial
    python3 run_board.py /dev/ttyUSB0          (Windows: COM5 etc.; the BL616 shows up as two ports: try the second)

It checks the link, loads six small kernels into the instruction memory, submits 12 tasks, waits for them, reads the
task table back and compares every result with the independent instruction-set simulator.  Close any terminal program
that has the port open first."""
import sys, math, argparse
sys.path.insert(0, __file__.rsplit('/', 1)[0] if '/' in __file__ else '.')
import sched_tests as st
import host_sc as hs
rt = st.rt

PROGS = [('sum', st.k_sum(60)), ('fib', st.k_fib(40)), ('crc', st.k_crc(0x1234567, 2)),
         ('gcd', st.k_gcd(1071, 462)), ('mul', st.k_mul(4321, 8765)), ('sort', st.k_sort(8, 99999))]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('port'); ap.add_argument('--baud', type=int, default=115200)
    ap.add_argument('--clk', type=float, default=27e6)
    ap.add_argument('--lw', type=int, default=None, help='log2 of bits per cycle per task (0 = narrowest, lets S tasks run side by side)')
    ap.add_argument('--nohold', action='store_true', help='do not use hold/go even if the board supports it (tasks then start as they arrive)')
    a = ap.parse_args()
    b = hs.Board(a.port, a.baud)
    v = b.version(); print('board:', v)
    lw = a.lw if a.lw is not None else min(2, int(math.log2(v['S'])))   # default: widest group that fits, up to 4 bits/cycle
    words, base, exp, names = [], {}, {}, []
    for name, src in PROGS:                            # as many kernels as fit the instruction memory, in order
        w = rt.assemble(src)
        if len(words) + len(w) <= v['imem_words']:
            base[name] = len(words); words += w; exp[name] = rt.iss(w)['x'][10]; names.append(name)
    print('kernels loaded (%d words):' % len(words), ', '.join(names))
    b.reset(); b.load(0, words)
    kinds = names * 2
    use_hold = v['version'] >= 5 and not a.nohold      # board version 5 = hold/go: load all tasks first, then release them together
    if use_hold: b.hold()
    for tid, k in enumerate(kinds):
        b.submit(tid, base[k], lw, crit=int(tid in (4, 9)), prog=names.index(k))
    if use_hold: b.go()
    print('submitted %d tasks at width %d bit(s) per cycle%s; waiting...' % (len(kinds), 1 << lw, ', released together with go' if use_hold else ''))
    if not b.wait_done(len(kinds), timeout=120): print('TIMEOUT: not all tasks finished')
    c = b.counters(); print('counters:', c)
    bad = 0
    for tid, k in enumerate(kinds):
        t = b.task(tid); ok = (t['state'] == 3 and not t['trap'] and t['a0'] == exp[k]); bad += not ok
        print('task %2d %-4s slot %d  %8d clocks (%.2f ms)  a0 %08x expect %08x  %s' %
              (tid, k, t['slot'], t['end'] - t['start'], (t['end'] - t['start']) / a.clk * 1e3, t['a0'], exp[k], 'ok' if ok else 'FAIL'))
    ends = [b.task(t) for t in range(len(kinds))]
    mk = max(t['end'] for t in ends) - min(t['start'] for t in ends)
    known = sum(t['pred_known'] for t in ends)
    starts = sorted(t['start'] for t in ends)
    print('start spread: first %d, last %d (%d clocks apart); slots used: %s' % (starts[0], starts[-1], starts[-1] - starts[0], sorted(set(t['slot'] for t in ends))))
    print('SUMMARY batch %d clocks (%.2f ms) | waste_tail %d | waste_blocked %d | tasks with a duration prediction: %d of %d' % (mk, mk / a.clk * 1e3, c['waste_tail'], c['waste_blocked'], known, len(kinds)))
    print('RESULT', 'PASS' if (not bad and c['done'] == len(kinds) and c['launch_err'] == 0) else 'FAIL')

if __name__ == '__main__': main()
