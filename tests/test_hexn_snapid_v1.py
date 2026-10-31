"""Tests for tools/hexn_snapid_v1.py (snapshot-ID table for layer 3, model)."""
import importlib.util, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("sid", os.path.join(ROOT, "tools", "hexn_snapid_v1.py")); S = importlib.util.module_from_spec(sp); sp.loader.exec_module(S)

def test_table_gives_stable_ids_and_refuses_or_reuses_when_full():
    T = S.SnapTable(IB=4, P=2, IDW=2, policy="refuse"); ids = [T.get((i, 0, 0), i) for i in range(6)]
    assert T.get((0, 0, 0), 9) == ids[0] and None in ids and T.refused > 0
    U = S.SnapTable(IB=4, P=2, IDW=2, policy="lru"); got = [U.get((i, 0, 0), i) for i in range(6)]
    assert None not in got and U.reused > 0 and max(got) < 4

def test_enough_ids_cost_nothing_and_too_few_hurt():
    w = S.V2.world3(300, 1); sp_ = [(150, 500)]
    base = S.score(w, sp_, 6)[0][0]; big = S.score(w, sp_, 6, S.SnapTable(IDW=7))[0][0]; tiny = S.score(w, sp_, 6, S.SnapTable(IDW=4, policy="lru"))[0][0]
    assert big == base and tiny < base - 0.1
