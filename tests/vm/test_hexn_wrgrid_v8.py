"""tests/vm/test_hexn_wrgrid_v8.py -- the MIXED grid model (tools/hexn_wrgrid_v8.py): one-input cores direct, two-input serial cores aligned by a short even detour when they can be and joined (two FIFO cells) when not, compare / min / max always joined. The 12 example tasks must equal plain arithmetic on a 9x9 grid; all three kinds of core must occur across the tasks; forcing every serial core to join must still be right. Pure Python."""
import os, random, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_wrgrid_v8 as m
from hexn_wrgrid_v6 import tasks, ref_eval


def _ok(P, nodes, ins, outs):
    rnd = random.Random(17)
    for _ in range(4):
        iv = {n: rnd.randrange(1 << 16) for n in ins}
        res, st = m.simulate7(P, iv, outs)
        assert res == {o: ref_eval(nodes, iv)[o] for o in outs}


def test_mixed_twelve_tasks_and_all_kinds_present():
    kinds = set()
    for name, (nodes, ins, outs) in tasks().items():
        P = m.plan7(nodes, ins, outs, 9, 9)
        _ok(P, nodes, ins, outs)
        kinds |= set(P.modes.values())
    assert kinds == {"direct", "aligned", "join"}


def test_forced_join_still_right():
    for name in ("sum4", "mac", "chain8"):
        nodes, ins, outs = tasks()[name]
        P = m.plan7(nodes, ins, outs, 9, 9, mode_force="join")
        _ok(P, nodes, ins, outs)
