"""Layer 2 on the real routine recordings (tools/hexn_layer2_v2.py): the recordings decode to the expected number of presses, every pressed block is a routine except the one with the extra key 4 in run 3, and the goal key is predicted at chance with a history of 1 or 2 events and perfectly with 3 (leave one run out). Python only."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_layer2_v2 as L2v
def test_press_counts():
    r = L2v.runs(); assert [len(x) for x in r] == [56, 56, 65]
def test_goal_needs_three_events():
    L2v.R = L2v.runs(); clean = lambda rr, rnd: [k for k, _ in rr]
    for k, want in ((1, 0.5), (2, 0.5), (3, 1.0), (4, 1.0)):
        a, u, n, gr, gu, gn = L2v.evaluate(clean, k, 1); assert gn == 44 and abs(gr / gn - want) < 1e-9, (k, gr, gn)
def test_hold_one_beats_no_hold_under_damage():
    import random, hexn_layer2_v1 as L2, hexn_exact_v1 as X
    L2v.R = L2v.runs(); m = X.model("direct0"); p = 0.15
    nh = L2v.evaluate(lambda rr, r: [c for _, c in L2.raw_events(L2.ir_stream(rr, p, r, m)[0])], 3, 20); h1 = L2v.evaluate(lambda rr, r: [c for _, c in L2.hold_events(L2.ir_stream(rr, p, r, m)[0], 1, 1)], 3, 20)
    assert h1[3] / h1[5] > nh[3] / nh[5] + 0.1
