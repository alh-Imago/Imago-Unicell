"""tests/vm/test_hexn_kxlayer1_judge_v2.py - the v2 tool (v1 plus --carry). Fast tests plus a slow end-to-end simulation with carry-forward on (about 5 minutes)."""
import os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); sys.path.insert(0, os.path.join(ROOT, "tools"))
import pytest
import hexn_kxlayer1_judge_v1 as L1, hexn_kxlayer1_judge_v2 as L2, hexn_selftrain_v1 as S, hexn_scorer_ref_v1 as R


def test_v2_is_v1_unchanged_apart_from_carry():
    m1, s1, W1, b1 = L1.make_data(1, 3); m2, s2, W2, b2 = L2.make_data(1, 3)
    assert s1 == s2 and W1 == W2 and b1 == b2                                  # same data and weights as the proven tool
    rows = [[0, 3, -1, 6, 1, 2, 5, 4]]; assert L1.expected_results(W1, b1, rows) == L2.expected_results(W2, b2, rows)


def test_carry_changes_the_judge_word_only_where_there_was_no_class():
    rows = [[1, 2, 3, 4, 5, 6, 0, 1], [-1, 2, -1, 4, -1, 6, 0, -1], [-1, -1, 3, 4, 5, -1, 0, 1]]
    c = S.carry(rows, 2)
    assert c[1] == [1, 2, 3, 4, 5, 6, 0, 1] and c[2] == [1, 2, 3, 4, 5, 6, 0, 1]
    assert all(x == y for r0, r1 in zip(rows, c) for x, y in zip(r0, r1) if x >= 0)      # a given class is never altered
    W = L2.make_data(1, 1)[2]; bias = 0
    assert R.w_score(L2.bins_of(rows[1])) != R.w_score(L2.bins_of(c[1]))                  # the word the judge sees does change


@pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")
def test_end_to_end_in_simulation_with_carry():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "hexn_kxlayer1_judge_v2.py"), "sim", "--words", "4", "--dwell", "6", "--noise", "0.30", "--carry", "3"], capture_output=True, text=True, timeout=3000)
    assert "0 differ from the model" in r.stdout and "0 differ from the reference" in r.stdout and "carry-forward 3" in r.stdout and "LAYER 1 -> JUDGE PASS" in r.stdout, r.stdout + r.stderr[-800:]
