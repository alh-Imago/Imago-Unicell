"""Tests for tools/hexn_store_v7.py (reference with variable look-back). The RTL comparison needs iverilog."""
import importlib.util, os, shutil, tempfile, pytest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("chk7", os.path.join(ROOT, "tools", "hexn_store_v7_check_v1.py")); C = importlib.util.module_from_spec(sp); sp.loader.exec_module(C)

@pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog missing")
def test_reference_equals_rtl_v6_with_evictions():
    d = tempfile.mkdtemp(); params = dict(IB=7, RB=4); cmds = C.stream(1, 800)
    a, sa = C.rtl(cmds, 1, params, d); b, sb = C.model(cmds, 1, params)
    assert a == b and sa == sb and sa.split()[-1] != "0"      # evictions happened and still equal

def test_lookback_setting_equals_a_smaller_build():
    cmds = C.stream(9, 600); p = dict(IB=10, RB=9)
    for k in (1, 2, 4): assert C.model(cmds, 1, p, LMAX=k, lookback=k) == C.model(cmds, 1, p, LMAX=8, lookback=k)

def test_lookback_default_is_3_and_is_capped_by_lmax():
    import hexn_store_v7 as M
    assert M.StoreV7().lookback == 3 and M.StoreV7(LMAX=2, lookback=5).lookback == 2
