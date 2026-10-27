"""Promotion level (tools/hexn_promote_v1.py): a fixed running total of sightings promotes noise at high noise rates; N sightings inside a window of W blocks does not. Python only, synthetic stream."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_promote_v1 as P
def test_running_total_fails_at_high_noise():
    fp, al, w = P.run(5, 0.3, 30, 3000); assert fp > 10
def test_window_rule_holds_and_still_learns_new_routine():
    fp, al, w = P.run_w(3, 20, 0.3, 30, 3000); assert fp < 0.5
    assert al <= 4 and w < 260
def test_wider_window_more_false_promotions():
    a = P.run_w(3, 10, 0.6, 30, 3000)[0]; b = P.run_w(3, 80, 0.6, 30, 3000)[0]; assert a < b
