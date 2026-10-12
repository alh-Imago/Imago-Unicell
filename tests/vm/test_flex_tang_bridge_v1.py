"""Ledger #1098: the VM <-> Tang bridge (tools/flex_tang_bridge_v1.py): a VM save at the arrival of a result translates into the board's state file; a mid-pass save is refused;
the comparison accepts the right word and rejects a wrong one."""
import json
import os
import sys
import tempfile

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import flex_tang_bridge_v1 as B  # noqa: E402
import looped_cordic_v1 as L  # noqa: E402


def test_vm_save_translates_to_the_board_state_and_compares():
    d = tempfile.mkdtemp()
    save = os.path.join(d, "s.json")
    w, _ = B.vm_save(30, save)
    st = B.make_state(save, os.path.join(d, "st.json"))
    assert st["step"] == 30 and st["word"] == L.model(30)[29] & 0xFFFFFFFF == (w & 0xFFFFFFFF) and st["matches_independent_model"] and st["cell"] == "lp.fb19"
    res = os.path.join(d, "r.json")
    json.dump({"from_step": 30, "ran": 25, "word": L.model(55)[54] & 0xFFFFFFFF}, open(res, "w"))
    r = B.compare(save, res)
    assert r["match"] and r["tang_equals_model"] and r["final_step"] == 55
    json.dump({"from_step": 30, "ran": 25, "word": (L.model(55)[54] + 1) & 0xFFFFFFFF}, open(res, "w"))
    assert not B.compare(save, res)["match"]


def test_a_cut_inside_a_pass_is_refused():
    import flex_save_v1 as S
    from flex_grid_v1 import FlexGrid
    d = tempfile.mkdtemp()
    g, _ = L.new_grid(FlexGrid)
    for _ in range(30 * L.TICKS_PER_STEP + 7):          # 7 ticks into a pass: the word is inside a stage
        g.tick()
    save = os.path.join(d, "mid.json")
    S.save(g, FlexGrid(L.build_records()), L.build_doc(), save, step=30)
    with pytest.raises(SystemExit) as e:
        B.make_state(save, os.path.join(d, "x.json"))
    assert "ONE word" in str(e.value)
