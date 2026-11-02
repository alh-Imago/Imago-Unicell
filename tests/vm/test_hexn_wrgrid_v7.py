"""tests/vm/test_hexn_wrgrid_v7.py -- the SELF-TIMED (join) work/routing grid model (tools/hexn_wrgrid_v7.py): the 12 example tasks are placed by shortest path only (no alignment planning) and run bit by bit through the
join cores (two FIFO cells per two-input core, AND of the 'have' flags); results must equal plain arithmetic, on a 7x7 grid, for several random inputs. Pure Python."""
import os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_wrgrid_v7 as m
from hexn_wrgrid_v6 import tasks, ref_eval


def test_twelve_tasks_self_timed():
    for name, (nodes, ins, outs) in tasks().items():
        P = m.plan7(nodes, ins, outs, 7, 7)
        rnd = random.Random(21)
        for _ in range(4):
            iv = {n: rnd.randrange(1 << 16) for n in ins}
            res, st = m.simulate7(P, iv, outs)
            assert res == {o: ref_eval(nodes, iv)[o] for o in outs}, name
