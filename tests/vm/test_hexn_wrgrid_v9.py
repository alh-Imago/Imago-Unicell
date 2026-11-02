"""tests/vm/test_hexn_wrgrid_v9.py -- the catalogue planner (tools/hexn_wrgrid_v9.py): every task with the new cores places, routes and simulates to the word-level reference; the planner's rules are checked; a deliberate fault is caught."""
import os, sys, copy
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_wrgrid_v9 as G


def _plan(name, n=9):
    nodes, ins, outs = G.tasks9()[name]
    return G.plan9(nodes, ins, outs, n, n), nodes, ins, outs


def test_all_tasks_9_and_11():
    for n in (9, 11):
        for name in G.tasks9():
            P, nodes, ins, outs = _plan(name, n)
            ok, why = G.check_task(P, nodes, ins, outs)
            assert ok, (n, name, why)


def test_dynamic_output_forces_join_and_static_can_align():
    P, *_ = _plan("branch_merge_add")
    assert P.modes["m"] == "self" and P.modes["r"] == "join"            # the arbitrating merge has no fixed output time: the add after it must join
    P, *_ = _plan("or_join")
    assert P.modes["u"] == "aligned" and P.modes["v"] == "direct"       # known timing: a short even gap can still be aligned


def test_refusals():
    N = G.Node9
    import pytest
    for nodes, why in (([N("p", "prio", ["a", "b", "c", "d"])], "hex"), ([N("m", "mul", ["a", "b"])], "not built")):
        try: G.plan9(nodes, ["a", "b", "c", "d"], ["p" if nodes[0].kind == "prio" else "m"], 9, 9, tries=2)
        except RuntimeError as e: assert why in str(e), str(e)
        else: raise AssertionError("should have been refused: " + why)


def test_latch_is_planned_and_routed_but_not_simulated():
    N = G.Node9
    P = G.plan9([N("l", "latch", ["s", "c", "t"])], ["s", "c", "t"], ["l"], 9, 9)
    assert any(i["op"] == "latch" for i in P.g.work.values()) and len(P.paths) == 4


def test_fault_is_caught():
    P, nodes, ins, outs = _plan("branch_route")
    ok, _ = G.check_task(P, nodes, ins, outs); assert ok
    P2 = copy.deepcopy(P)
    for i in P2.g.work.values():
        if i["op"] == "branch": i["cfg"] = dict(i["cfg"], route_gt=1)    # gt now goes to the wrong output
    ok, why = G.check_task(P2, nodes, ins, outs); assert not ok
