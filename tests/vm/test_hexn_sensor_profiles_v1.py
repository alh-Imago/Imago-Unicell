"""tests/vm/test_hexn_sensor_profiles_v1.py - per-sensor cleaning, the known-type table and the choice for unknown sensors, on the real 27 Oct recordings (model only)."""
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
import hexn_sensor_profiles_v1 as P, hexn_replay_carry_v1 as C


def test_specs_and_per_column_cleaning():
    assert P.parse("none") == ("none", 0) and P.parse("hold20") == ("hold", 20) and P.parse("carry3") == ("carry", 3)
    for bad in ("hold", "hold0", "carryx", "avg3"):
        with pytest.raises(ValueError): P.parse(bad)
    rows = [[1, 5, 2], [-1, 5, 2], [1, -1, 3], [1, 5, 2]]
    out = P.clean_columns(rows, ["carry1", "none", "hold2"])
    assert [r[0] for r in out] == [1, 1, 1, 1] and [r[1] for r in out] == [5, 5, -1, 5] and [r[2] for r in out] == [2, 2, 2, 2]
    assert P.clean_columns(rows, "none") == rows and P.clean_chain([2, -1, -1, 4], "carry1+hold1") == [2, 2, -1, 4]


@pytest.fixture(scope="module")
def streams(): return {name: (out, ref, nt) for name, out, ref, nt in C.collect()}


def test_blind_choice_on_the_real_recordings(streams):
    pick = {n: P.choose_blind(s[0])[0] for n, s in streams.items()}
    assert pick["light"] == "none" and pick["pot"] == "none"                       # steady: no cleaner earns its delay
    assert pick["therm raw"] == "hold20" and pick["therm med9"] == "hold20"        # chatter: the hold removes it
    assert pick["therm raw"] == P.KNOWN["thermistor"] and pick["light"] == P.KNOWN["light"] and pick["pot"] == P.KNOWN["pot"]


def test_blind_choice_takes_carry_when_there_are_gaps():
    stream = [3] * 40 + [-1, -1] + [3] * 40 + [5] * 40 + [-1] + [5] * 40
    spec, why = P.choose_blind(stream)
    assert spec.startswith("carry3") and why["no_class_share"] > 0.01


def test_taught_choice_on_the_real_recordings(streams):
    out, ref, nt = streams["therm raw"]; spec, info = P.choose_taught(out, ref, nt)
    assert spec == "hold20" and info["right"] >= 0.99
    for n in ("light", "pot"):
        out, ref, nt = streams[n]; assert P.choose_taught(out, ref, nt)[0] == "none"


def test_blind_choice_never_holds_on_short_runs_even_with_many_words():
    import hexn_kxlayer1_judge_v3 as L, hexn_bank_model_v2 as M
    for words, nz in ((40, 0.10), (400, 0.20), (400, 0.10)):
        m, samples, W, bias = L.make_data(1, words, noise=nz, dwell=6); cl = [[c for c, _ in M.classify(m, row)] for row in samples]
        for s in range(8): assert "hold" not in P.choose_blind([r[s] for r in cl])[0]       # classes last 6 to 12 steps: a hold of 3 or more costs a third of each run or more


def test_long_run_share():
    assert P.long_run_share([1] * 10 + [2] * 3 + [1] * 7, 5) == 17 / 20 and P.long_run_share([1, 2, 1, 2], 2) == 0.0
