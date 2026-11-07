"""tests for tools/hexn_selftrain_v1.py (teacher-versus-self experiment, simulation only)"""
import os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
import hexn_selftrain_v1 as S, hexn_scorer_ref_v1 as R


def test_score_matches_scorer_reference():
    rnd = random.Random(4)
    for _ in range(300):
        W = [[[rnd.randint(-127, 127) for _ in range(16)] for _ in range(S.NS)] for _ in range(2)]; bias = rnd.randint(-300, 299)
        bins = [rnd.randrange(12) for _ in range(S.NS)]
        assert S.score(W, bias, bins)[0] == R.score(W, bias, bins)[0] >> 31


def test_zero_step_keeps_b_equal_to_a_and_ceiling_holds():
    r0 = S.experiment(seed=3, teacher_words=80, live_words=200, held_words=100, step=0, every=100)
    assert all(agr == 1.0 and dr == 0 for _, _, agr, dr, _ in r0["B"])
    r1 = S.experiment(seed=3, teacher_words=80, live_words=400, held_words=100, step=2, ceil=5, every=100)
    assert all(dr <= 5 for _, _, _, dr, _ in r1["B"])


def test_deterministic_and_teacher_beats_majority_guess():
    a = S.experiment(seed=3, teacher_words=150, live_words=100, held_words=300, every=100)
    b = S.experiment(seed=3, teacher_words=150, live_words=100, held_words=300, every=100)
    assert a == b
    assert a["A_accuracy"] > max(a["event_rate"], 1 - a["event_rate"])


def test_confident_label_rule_and_filter_option():
    assert S.confident([5, 5, 5, 5, 0, 0, 0, 0])            # event sure
    assert S.confident([0, 0, 0, 0, 0, 0, 0, -1])           # non-event sure even if the unknown were high
    assert not S.confident([5, 5, 5, 0, -1, 0, 0, 0])       # would flip with the unknown
    r = S.experiment(seed=3, teacher_words=80, live_words=200, held_words=100, every=100, conf_filter=True, vote=3, hold=2)
    assert len(r["B"]) == 1                          # 199 pairs, one checkpoint at 100


def test_hold_filter_and_vote_one_is_plain():
    det = [[3] * 8, [3] * 8, [4] * 8, [4] * 8, [4] * 8]
    h = S.hold_det(det, 2)
    assert h[0] == [-1] * 8 and h[1] == [3] * 8 and h[2] == [-1] * 8 and h[4] == [4] * 8
    assert S.hold_det(det, 1) == det
