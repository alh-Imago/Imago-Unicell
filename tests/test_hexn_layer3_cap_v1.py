"""Tests for tools/hexn_layer3_cap_v1.py and tools/hexn_layer3_l2in_v1.py (layer 3 model: bounded table, layer 2 signals as extra channels)."""
import importlib.util, os, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(n):
    sp = importlib.util.spec_from_file_location(n, os.path.join(ROOT, "tools", n + ".py")); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
C = load("hexn_layer3_cap_v1"); X = load("hexn_layer3_l2in_v1")

def test_refusing_new_entries_when_full_hurts_after_a_rule_change():
    sp = [(900, 1300)]; r = {}
    for pol in ("lru", "newest-drop"): r[pol] = st.mean(C.score(C.world2(300, s, 150), sp, 400, pol)[0][0] for s in range(2))
    assert r["lru"] > r["newest-drop"] + 0.03

def test_unbounded_cap_none_equals_a_large_cap():
    sp = [(200, 600)]; a = C.score(C.world2(300, 1, 150), sp, None, "lru")[0][0]; b = C.score(C.world2(300, 1, 150), sp, 10 ** 6, "lru")[0][0]
    assert a == b

def test_layer2_verdict_channels_run_and_change_little_here():
    sp = [(200, 600)]; w = C.world2(300, 1, 150); a = X.run(w, sp, ())[0]; b = X.run(w, sp, (0, 1, 2))[0]
    assert 0.4 < a <= 1.0 and abs(a - b) < 0.15
