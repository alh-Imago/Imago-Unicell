"""Tests for tools/hexn_judge_int_v1.py (the neural core's judge in whole numbers) and tools/hexn_connect4_blend_v2.py."""
import importlib.util, os, random
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(ROOT, "tools", n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
JI = load("hexn_judge_int_v1")

def test_integer_judge_follows_the_float_judge():
    P = JI.positions(200); F = JI.JudgeFloat(); I = JI.JudgeInt(6, 6)
    fv = np.array([F.value(b) for b in P]); iv = np.array([I.value(b) for b in P])
    assert np.abs(fv - iv).mean() < 0.03 and np.corrcoef(fv, iv)[0, 1] > 0.995
    big = np.abs(fv) > 0.1; assert np.all(np.sign(fv[big]) == np.sign(iv[big]))

def test_cost_counts_and_word_sizes():
    c = JI.JudgeInt(6, 6).cost()
    assert c["adds_first_layer"] == 43 * 64 and c["macs_second_layer"] == 64 and c["W1_word"] <= 9 and c["weight_bits_total"] < 80000

def test_whole_stack_player_with_judge_leaf_finishes_games():
    B = load("hexn_connect4_blend_v2"); rnd = random.Random(1)
    for name in ("hexM3j", "hexH3j", "plainJ3"):
        r = B.game(B.make(name), B.opponent("noisy2"), rnd); assert r in (0, 1, 2)
