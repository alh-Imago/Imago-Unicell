"""Tests for rtl/hexn_store_v6.v (LRU eviction clone of store v5). Needs iverilog."""
import importlib.util, os, shutil, tempfile, pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("chk", os.path.join(ROOT, "tools", "hexn_store_v6_check_v1.py")); C = importlib.util.module_from_spec(sp); sp.loader.exec_module(C)
pytestmark = pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog missing")

def test_v6_equals_v5_when_the_heap_never_fills():
    d = tempfile.mkdtemp(); ev, w = C.stim(1, 400); big = {"IB": 10, "RB": 9}
    l5, _ = C.run(True, w, big, d); l6, _ = C.run(False, w, big, d)
    assert l5[:-1] == l6[:-1]

def test_v6_keeps_learning_after_a_change_when_v5_cannot():
    d = tempfile.mkdtemp(); ev, w = C.stim(2, 2400, switch=1200); small = {"IB": 7, "RB": 4}
    l5, _ = C.run(True, w, small, d); l6, _ = C.run(False, w, small, d); sp_ = [(1400, 2400)]
    assert C.score(ev, l6, sp_)[0] > C.score(ev, l5, sp_)[0] + 0.3     # recorded 0.594 against 0.098
