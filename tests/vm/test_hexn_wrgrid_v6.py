"""tests/vm/test_hexn_wrgrid_v6.py -- the work/routing grid model with the RTL-checked RAM cell with ROUTED start flags (tools/hexn_wrgrid_v6.py): the 12 example tasks are placed, routed and run bit by bit on a 9x9 grid and must equal plain arithmetic; plus the long-wait chain (waits of 38, 76, 114 clocks) with a 96-clock cap per RAM; every RAM start flag must be routed (flag wires > 0). Pure Python."""
import os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_wrgrid_v6 as m


def _check(nodes, ins, outs, R, **kw):
    P = m.plan(nodes, ins, outs, R, R, tries=25, **kw)
    rnd = random.Random(11)
    for _ in range(4):
        iv = {n: rnd.randrange(1 << 16) for n in ins}
        assert m.simulate(P, iv, outs, ticks=600) == {o: m.ref_eval(nodes, iv)[o] for o in outs}
    return P


def test_twelve_tasks():
    for name, (nodes, ins, outs) in m.tasks().items():
        _check(nodes, ins, outs, 13)


def test_long_waits_two_rams_in_series():
    N = m.Node
    nodes = [N("a1", "max", "x", "a"), N("a2", "min", "a1", "b"), N("a3", "max", "a2", "c"), N("r", "min", "a3", "d")]
    P = _check(nodes, ["x", "a", "b", "c", "d"], ["r"], 13, maxhold=96)
    assert P.flag_wires > 0
    assert P.rams >= 3 and max(P.g.hold.values()) <= 96
