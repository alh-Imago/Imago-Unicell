"""Tests for tools/hexn_ring_v1.py (Python model of ring design vs single bank)."""
import importlib.util, os, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("ring", os.path.join(ROOT, "tools", "hexn_ring_v1.py")); R = importlib.util.module_from_spec(sp); sp.loader.exec_module(R)

def test_single_bank_close_to_recorded():
    R.AW = 6
    m = st.mean(R.one_plain(s, 4, 12, 0.15, 16, 4, 1, True)["single"] for s in range(25))
    R.AW = 7
    assert 0.76 <= m <= 0.90  # recorded real-cell figure 0.824

def test_deterministic_and_compositional_sides_work():
    R.AW = 7
    a = R.one_comp(3, 2, 4, 9, 0.15, 16, True); b = R.one_comp(3, 2, 4, 9, 0.15, 16, True)
    assert a == b and a["sides_only"] > 0.2  # chance is 1/16

def test_sizes_formula():
    s, r = R.sizes(16, 18, 2, [4, 4])
    assert s["lanes"] == 288 and r["det"] == 24
