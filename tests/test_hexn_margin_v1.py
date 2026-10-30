"""Tests for tools/hexn_margin_v1.py (margin answer rule for the counted detector, Python model)."""
import importlib.util, os, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("mg", os.path.join(ROOT, "tools", "hexn_margin_v1.py")); M = importlib.util.module_from_spec(sp); sp.loader.exec_module(M)

def test_margin_rule_beats_strict_rule():
    rs = [M.one(s, 8, 18, 0.15, 16) for s in range(8)]
    assert st.mean(r["C"] for r in rs) > st.mean(r["A"] for r in rs) + 0.02  # recorded: 0.909 vs 0.873

def test_full_and_capped_margin_agree_and_always_answer():
    r = M.one(1, 4, 12, 0.15, 16)
    assert abs(r["C"] - r["D"]) < 0.02 and r["Ccov"] == 1.0 and r["Dcov"] == 1.0

def test_fair_template_stays_ahead():
    rs = [M.one(s, 8, 18, 0.15, 16) for s in range(8)]
    assert st.mean(r["T2"] for r in rs) > st.mean(r["C"] for r in rs)  # recorded: 0.945 vs 0.909
