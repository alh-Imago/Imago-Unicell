"""Ledger #1092-#1093: the looped CORDIC (nano/looped_cordic_v1.py): VM against an independent Python model, the orbit is long, the ICM file is the hierarchical document, and the name-keyed save (flex_save_v1) resumes it exactly from a cut in the middle of a pass where checkpoint v2 could not."""
import os
import sys
import tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "nano"))
import looped_cordic_v1 as L  # noqa: E402
import mixed_grid_checkpoint_v2 as v2  # noqa: E402
from flex_grid_v1 import FlexGrid  # noqa: E402


def test_model_orbit_is_long_and_the_undrifted_loop_is_not():
    assert len(set(L.model(1200))) == 1200
    assert L.model(8, drift=0)[2:] == [-5856, 5668, -5856, 5668, -5856, 5668]      # the trivial cycle of #1090, reached after three passes


def test_vm_matches_the_model_for_1000_steps_at_40_ticks_each():
    g, _ = L.new_grid(FlexGrid)
    seen = L.run_steps(g, 1000)
    assert [v for _, v in seen] == L.model(1000)
    assert {b[0] - a[0] for a, b in zip(seen, seen[1:])} == {L.TICKS_PER_STEP}


def test_icm_file_is_the_hierarchical_document_and_builds_the_same_grid():
    p = os.path.join(tempfile.mkdtemp(), "l.icm-hier.json")
    L.save_icm(p)
    recs, _ = L.flatten(L.load_hierarchical(p))
    assert len(recs) == len(L.build_records()) == 61
    assert len(FlexGrid(recs).cells) == 61
    committed = os.path.join(ROOT, "nano", "examples", "looped_cordic_v1.icm-hier.json")
    assert open(committed).read() == open(p).read(), "regenerate nano/examples/looped_cordic_v1.icm-hier.json with looped_cordic_v1.save_icm"


def _grid_from_design(doc):
    import json
    path = os.path.join(tempfile.mkdtemp(), "d.icm-hier.json")
    json.dump(doc, open(path, "w"))
    recs, _ = L.flatten(L.load_hierarchical(path))
    return FlexGrid(recs)


def test_checkpoint_v2_gap_is_closed_by_the_name_keyed_save_v1():
    """Ledger #1092 recorded that checkpoint v2 cannot resume this loop from inside a pass. Ledger #1093: flex_save_v1 (design model + state diff keyed by cell name) can: cut at step 300 plus
    17 ticks (operands waiting inside adders), load into a grid built ONLY from the design inside the save, and the next 20 steps equal both the uninterrupted run and the Python model."""
    import json
    import flex_save_v1 as S
    g, _ = L.new_grid(FlexGrid)
    for _ in range(300 * L.TICKS_PER_STEP + 17):
        g.tick()
    doc = L.build_doc()
    path = os.path.join(tempfile.mkdtemp(), "s.json")
    pay = S.save(g, FlexGrid(L.build_records()), doc, path, step=300)
    # the state part holds running state only: no programming word (mask, mode, constant) of any cell appears in it
    keys = {k for d in pay["state"].values() for k in d}
    assert not [k for k in keys if k.endswith("_mask") or k in ("merge_mode", "_merge_order", "core", "row", "col", "cell_id")]
    assert {"_a_face", "_merge_rr"} <= keys                      # the two things checkpoint v2 lost are in
    saved = S.read(path)
    g2 = _grid_from_design(saved["design"])
    assert S.load_state(g2, saved) == 300
    a, b = L.run_steps(g, 20), L.run_steps(g2, 20)
    assert a == b and [v for _, v in a] == L.model(320)[300:320]


def test_save_v1_refuses_a_changed_file():
    import json
    import flex_save_v1 as S
    g, _ = L.new_grid(FlexGrid)
    path = os.path.join(tempfile.mkdtemp(), "s.json")
    S.save(g, FlexGrid(L.build_records()), L.build_doc(), path)
    p = json.load(open(path)); p["tick"] += 1; json.dump(p, open(path, "w"))
    try:
        S.read(path)
    except ValueError as e:
        assert "state hash" in str(e)
    else:
        raise AssertionError("a changed save was accepted")
