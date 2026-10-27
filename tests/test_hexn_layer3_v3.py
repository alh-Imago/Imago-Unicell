"""Layer 3's feedback applied to layer 2: rewards alone leave layer 2 at chance; rewards plus the goal event let it steer."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import hexn_layer3_v2 as V2, hexn_layer3_v3 as M
def avg(kw, a, b, n=4): return sum(V2.share(M.run(seed=s, n=400, **kw), a, b) for s in range(n)) / n
def test_goal_event_lets_layer2_steer():
    assert abs(avg(dict(mode="l2"), 200, 400) - 0.5) < 0.08
    assert avg(dict(mode="l2fb", glvl=2), 200, 400) > 0.9
def test_layer2_with_feedback_matches_layer3():
    assert avg(dict(mode="l2fb", glvl=2), 200, 400) > avg(dict(mode="l3"), 200, 400) - 0.05
