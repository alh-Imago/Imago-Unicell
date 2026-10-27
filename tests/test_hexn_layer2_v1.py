"""Layer 2 first model on the real recordings (tools/hexn_layer2_v1.py): clean IR presses give a perfect next-key prediction, and at 15 percent damaged frames the hold clearly beats no hold. Python only."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import hexn_layer2_v1 as L2
def test_clean_perfect():
    a, u, pr, rc = L2.ir_run(0.0, True, 5); assert (a, pr, rc) == (1.0, 1.0, 1.0)
def test_hold_beats_no_hold_under_damage():
    nh = L2.ir_run(0.15, False, 40)[0]; wh = L2.ir_run(0.15, True, 40)[0]; assert wh > nh + 0.3
def test_round2_order_equals_round1():
    ps = L2.ir_presses(); assert [k for k, _ in ps[21:]] == [k for k, _ in ps[:len(ps) - 21]]
