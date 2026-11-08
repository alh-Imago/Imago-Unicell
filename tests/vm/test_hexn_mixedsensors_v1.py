"""tests/vm/test_hexn_mixedsensors_v1.py - the mixed gap and chatter sensor set (model only). Fast: the chatter generator and a small run."""
import os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_mixedsensors_v1 as X


def test_chatter_column_only_flips_near_changes_and_never_gives_no_class():
    truth = [1] * 100 + [2] * 100; out = X.chatter_col(truth, random.Random(1), w=8, flip=0.0)
    assert all(c >= 0 for c in out) and all(out[i] == truth[i] for i in list(range(0, 91)) + list(range(110, 200)))
    assert set(out[92:108]) <= {1, 2} and len(set(out[92:108])) == 2


def test_small_run_returns_every_strategy_with_one_cleaner_per_sensor():
    res, picks = X.run(1, 0.20, nwords=150, tw=60)
    assert set(res) == {"none", "carry3", "hold10", "oracle", "blind cost", "blind judge"} and all(0 <= v <= 1 for v in res.values())
    assert all(len(p) == 8 for p in picks.values())
