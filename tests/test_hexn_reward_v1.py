"""Reward-driven goal read (tools/hexn_reward_v1.py), abstract model: it learns to reach the desired goal, long contexts are slower under recognition errors, the teacher can be wrong up to 40 percent but not 60, and a constant step re-steers after a goal change far faster than a running mean. Python only, small seeds."""
import os, sys, random
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_reward_v1 as R
def mean_final(k, mode, p=0.0, q=0.0, seeds=6, **kw): return sum(R.curve(R.run(k, mode, p, q, seed=s, **kw), 700, 800) for s in range(seeds)) / seeds
def test_learns_to_steer_to_the_desired_goal():
    assert mean_final(1, "mean") > 0.9
def test_long_context_slower_with_recognition_errors():
    a = [R.first_reach(R.run(1, "mean", 0.2, 0.0, seed=s), 40) or 9999 for s in range(6)]; b = [R.first_reach(R.run(3, "mean", 0.2, 0.0, seed=s), 40) or 9999 for s in range(6)]
    assert sum(a) < sum(b)
def test_teacher_error_up_to_40_percent_ok_60_percent_inverts():
    assert mean_final(1, "mean", q=0.4) > 0.9 and mean_final(1, "mean", q=0.6) < 0.2
def test_goal_change_needs_a_constant_step_not_a_running_mean():
    m = sum(R.curve(R.run(1, "mean", n=500, flip=300, seed=s), 400, 500) for s in range(6)) / 6
    st = sum(R.curve(R.run(1, "step", n=500, flip=300, seed=s, alpha=0.1), 400, 500) for s in range(6)) / 6
    assert m < 0.2 and st > 0.85
