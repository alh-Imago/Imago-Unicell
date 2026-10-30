"""Tests for tools/hexn_baseline_v1.py (counted detector vs simple trained classifiers, Python model)."""
import importlib.util, os, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("bl", os.path.join(ROOT, "tools", "hexn_baseline_v1.py")); B = importlib.util.module_from_spec(sp); sp.loader.exec_module(B)

def test_deterministic():
    assert B.one(2, 4, 12, 0.15, 16) == B.one(2, 4, 12, 0.15, 16)

def test_rule_is_the_ceiling_and_template_beats_detector_on_average():
    rs = [B.one(s, 4, 12, 0.15, 16) for s in range(10)]
    assert st.mean(r["rule"] for r in rs) >= st.mean(r["tmpl"] for r in rs) - 0.02
    assert st.mean(r["tmpl"] for r in rs) > st.mean(r["detector"] for r in rs)  # recorded: 0.895 vs 0.836

def test_chance_level_sane():
    r = B.one(0, 8, 18, 0.5, 4)  # pure noise: everything near chance 1/8
    assert all(v < 0.35 for v in r.values())
