"""Whole-board simulation: the duration profile must survive 'R' (reset).  Runs the same batch twice with R between;
at the second batch every task must have a duration prediction (10 of 10).  Catches the v4.0 bug where the known
bit was lost on every second sample of a class (found on the real board, ledger note in latest.md)."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, 'fpga'))
import test_board_sim as T, host_sc as hs
FINE = int(sys.argv[1]) if len(sys.argv) > 1 else 0          # 0 = whole-octave buckets, 1 = half-octave buckets
S, IMW, DMW, DIV = 2, 64, 16, 8
exe = T.build(S=S, IMW=IMW, DMW=DMW, DIV=DIV, FINE=FINE, tag='prof%d' % FINE)
names = T.fit_progs(IMW); kinds = names * 2
base, words = {}, []
for name, src in T.PROGS:
    if name in names: base[name] = len(words); words += T.rt.assemble(src)
rw = lambda n: ('D', n * 10 * DIV + 40 * DIV)
def batch():
    s = [('B', hs.cmd_R()), ('D', 2000)]
    s += [('B', hs.cmd_W(i, w)) for i, w in enumerate(words)]
    s += [('B', hs.cmd_P(t, base[k], 0, int(t in (4, 9)), names.index(k))) for t, k in enumerate(kinds)]
    return s + [('D', 3000000)]
seq = [('B', hs.cmd_V()), rw(8)] + batch() + batch() + [('B', hs.cmd_C()), rw(56)]; order = ['V', 'C']
for t in range(len(kinds)): seq += [('B', hs.cmd_Q(t)), rw(22)]; order.append('Q')
rep = hs.split_replies(T.run(exe, seq, tag='prof%d' % FINE), order)
known = sum(t['pred_known'] for t in rep[2:]); bad = sum(not (t['state'] == 3 and not t['trap']) for t in rep[2:])
print('second batch after R: %d of %d tasks had a duration prediction, %d bad tasks' % (known, len(kinds), bad))
print('second batch: waste_tail %d, waste_blocked %d, cyc %d' % (rep[1]['waste_tail'], rep[1]['waste_blocked'], rep[1]['cyc']))
print('RESULT', 'PASS' if known == len(kinds) and not bad else 'FAIL'); sys.exit(0 if known == len(kinds) and not bad else 1)
