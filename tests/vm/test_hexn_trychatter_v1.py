"""tests/vm/test_hexn_trychatter_v1.py - scores for the single-sensor try-both test (model only). Fast, on small made-up streams."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_trychatter_v1 as T


def test_scores_on_a_chattering_stream():
    ref = [1] * 60 + [2] * 60
    raw = list(ref); raw[10] = 2; raw[20] = 2; raw[30] = 2; raw[64] = 1; raw[80] = 1         # single-step chatter
    res, pick = T.evaluate("x", raw, ref, 0, cands=("none", "hold3"))
    assert res["hold3"]["truth"] > res["none"]["truth"] and res["hold3"]["changes"] < res["none"]["changes"]
    assert pick["truth"] == "hold3" and pick["cost3"] == "hold3"                               # the cost sees the chatter
    assert pick["agree"] == "none" or res["none"]["agree"] >= res["hold3"]["agree"] - 0.05     # the agreement score does not reward removing it


def test_a_clean_stream_needs_no_cleaner():
    ref = [1] * 50 + [2] * 50 + [3] * 50; res, pick = T.evaluate("x", list(ref), ref, 0, cands=("none", "hold3", "hold10"))
    assert pick["truth"] == "none" and pick["cost3"] == "none" and pick["cost10"] == "none"


def test_guard_blocks_a_hold_on_short_runs():
    raw = ([1] * 8 + [2] * 8) * 12                                       # classes last 8 steps: a hold of 3 or more delays by a third of a run or more
    assert not T.allowed(raw, "hold3") and T.allowed(raw, "carry3") and T.allowed(raw, "none")
    long = [1] * 400 + [2] * 400; assert T.allowed(long, "hold20") and T.allowed(long, "carry3+hold10")
