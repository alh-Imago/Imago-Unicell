"""Tests for tools/hexn_layer2_base_v1.py (layer 2 store against simple sequence predictors, Python model)."""
import importlib.util, os, statistics as st
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("l2b", os.path.join(ROOT, "tools", "hexn_layer2_base_v1.py")); L = importlib.util.module_from_spec(sp); sp.loader.exec_module(L)

def run(arm, kind, spans, n=5): return [st.mean(r[i] for r in [L.preq(L.ARMS[arm](), L.stream(s, kind), spans) for s in range(n)]) for i in range(len(spans))]

def test_store_without_promotion_filter_and_large_table_equals_ngram3():
    a = run("store N=1 KCAP 1024", "ORDER2", [(300, 700)]); b = run("ngram3", "ORDER2", [(300, 700)])
    assert abs(a[0] - b[0]) < 0.01      # recorded 0.902 against 0.902

def test_promotion_filter_costs_accuracy():
    a = run("store N=3", "ORDER2", [(100, 200)]); b = run("store N=1", "ORDER2", [(100, 200)])
    assert b[0] > a[0] + 0.04           # recorded 0.863 against 0.772

def test_lru_fixes_the_full_table_after_a_switch():
    a = run("store N=1", "SWITCH", [(500, 700)]); b = run("store N=1 KCAP 128 LRU", "SWITCH", [(500, 700)])
    assert b[0] > a[0] + 0.2            # recorded 0.864 against 0.338
