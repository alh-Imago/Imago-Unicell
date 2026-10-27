"""Layer 3 model: alignment, weights, and the combined path beating the remote alone on the coupled synthetic world."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
import hexn_layer3_v1 as M
def test_alignment_groups_close_changes():
    ev = [(0, 0, 1), (1, 1, 5), (10, 0, 2), (30, 2, 3)]
    assert M.moments(ev, align=2) == [((0, 1), (1, 5)), ((0, 2),), ((2, 3),)]
def test_weights_sum_to_at_most_one_and_rank():
    m = M.Layer3(nch=1, L=2, masks=[(1,)])
    for i in range(30):
        for k in (1, 2, 3, 1, 2, 4):
            m.feed(i * 1000 + k, 0, k); m.flush()
    p, rem = m.predict()
    assert 0 < sum(w for _, w in p) + rem <= 1.0001 and rem >= 0
    m.feed(10 ** 6, 0, 1); m.flush(); p, _ = m.predict(); assert p[0][0] == ((0, 2),)
def test_decay_lets_new_habit_win():
    m = M.Layer3(nch=1, L=1, half=10, masks=[(1,)])
    t = 0
    for k in [1, 2] * 40 + [1, 3] * 40: t += 100; m.feed(t, 0, k); m.flush()
    t += 100; m.feed(t, 0, 1); m.flush(); assert m.predict()[0][0][0] == ((0, 3),)
def test_combined_beats_remote_alone():
    ev = M.world(); r = M.evaluate_remote(ev, only=(0,), L=3, masks=[(1,)]); c = M.evaluate_remote(ev, L=4)
    assert c["top1"] > r["top1"] + 0.08 and c["weight_on_truth"] > r["weight_on_truth"] + 0.08
    assert c["top1"] <= 0.875 + 0.03 and r["top1"] <= 0.75 + 0.03   # both stay at the ceilings of the world
