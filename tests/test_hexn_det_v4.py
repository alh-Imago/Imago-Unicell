"""Tests for rtl/hexn_det_v4.v (signed total and margin detector) and tools/hexn_det_v4_model_v1.py. Refuses to pass without iverilog (like the other RTL checks)."""
import importlib.util, os, shutil, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(ROOT, "tools", n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def test_rtl_matches_independent_model_including_saturation():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog missing: this check must not be skipped"
    C = load("hexn_det_v4_check_v1")
    for nb, aw in ((12, 7), (18, 7), (18, 6), (12, 5)):  # the last two saturate
        last, out = C.check(nb, aw)
        assert "PASS" in last, out

def test_hardware_arithmetic_model_reproduces_recorded_real_cell_figure_and_v4_gain():
    M = load("hexn_det_v4_model_v1")
    rs = [M.one(s, 4, 12, 0.15, 16) for s in range(25)]
    assert abs(st.mean(r["H3"] for r in rs) - 0.824) < 0.02       # recorded real-cell figure 0.824
    assert st.mean(r["H4_7"] for r in rs) > st.mean(r["H3"] for r in rs) + 0.05  # recorded model: 0.922 vs 0.824
