"""Tests for tools/hexn_deadband_v1.py (where the counted detector loses information, Python model)."""
import importlib.util, os, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("db", os.path.join(ROOT, "tools", "hexn_deadband_v1.py")); D = importlib.util.module_from_spec(sp); sp.loader.exec_module(D)

def test_template_weights_with_ones_threshold_is_the_nearest_template():
    for s in range(6): r = D.one(s, 8, 18, 0.15, 16); assert r["V7"] == r["T2"]  # exact: the detector can express the template classifier

def test_signed_total_helps_and_dead_band_does_not_matter():
    rs = [D.one(s, 8, 18, 0.15, 16) for s in range(10)]; mu = lambda k: st.mean(r[k] for r in rs)
    assert mu("V2") > mu("V1") + 0.005      # recorded 0.928 vs 0.913
    assert abs(mu("V4") - mu("V2")) < 0.02  # recorded 0.932 vs 0.928
