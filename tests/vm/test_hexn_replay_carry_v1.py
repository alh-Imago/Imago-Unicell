"""tests/vm/test_hexn_replay_carry_v1.py - single-stream carry-forward and hold used on the recorded-data replay (tools/hexn_replay_carry_v1.py). Fast."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_replay_carry_v1 as C


def test_carry1_fills_only_no_class_within_k():
    o = [2, -1, -1, -1, 5, -1]
    assert C.carry1(o, 2) == [2, 2, 2, -1, 5, 5] and C.carry1(o, 0) == o and C.carry1([-1, 3], 5) == [-1, 3]


def test_hold1_ignores_a_short_glitch_and_follows_a_real_change():
    o = [3, 3, 4, 3, 3, 4, 4, 4]
    assert C.hold1(o, 2) == [3, 3, 3, 3, 3, 3, 4, 4] and C.hold1(o, 1) == o
    assert C.hold1([3, -1, 3], 2) == [3, 3, 3]


def test_score_counts_no_class_as_wrong():
    r, nn, chg, best = C.score([1, 1, -1, 1], [1, 1, 1, 1], 2)
    assert r == 0.5 and nn == 0.5 and chg == 2 and best == 1
