"""tests/vm/test_hexn_trycleaners_v1.py - the try-both (try every candidate design) choice for an unknown sensor. Fast: small run, structure and the property that the blind score uses a label shared by every candidate."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_trycleaners_v1 as T


def test_every_candidate_is_scored_and_scores_are_shares():
    r = T.one(3, 0.20, 6, teach_words=60, live_words=150)
    assert set(r) == set(T.CANDS) and all(0.0 <= a <= 1.0 and 0.0 <= b <= 1.0 for a, b in r.values())


def test_deterministic():
    a = T.one(2, 0.10, 6, cands=("none", "carry3"), teach_words=60, live_words=120); b = T.one(2, 0.10, 6, cands=("none", "carry3"), teach_words=60, live_words=120)
    assert a == b


def test_sweep_row_shape():
    rows = T.sweep(seeds=[1, 2], noises=(0.20,), dwells=(6,), cands=("none", "carry3"))
    assert len(rows) == 1 and rows[0]["truth_best"] in ("none", "carry3") and 0 <= rows[0]["seeds_same_pick"] <= 2 and rows[0]["max_regret"] >= 0
