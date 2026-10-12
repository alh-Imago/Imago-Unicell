"""Ledger #1092: the looped CORDIC (nano/looped_cordic_v1.py): VM against an independent Python model, the orbit is long, the ICM file is the hierarchical document, and the proven whole-grid checkpoint (v2) resumes it exactly from a cut in the middle of a pass."""
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


def test_checkpoint_v2_has_a_gap_on_flex_cell_extras_found_by_the_loop():
    """FINDING (ledger #1092): the proven whole-grid checkpoint v2 does NOT resume this loop from inside a pass. FlexCell keeps a few attributes outside SuperCell.checkpoint(): `_a_face`
    (which face carried an adder's first operand), and the merge state `merge_mode`, `_merge_order`, `_merge_rr`. The old 4-stage CORDIC never had an operand waiting at the cuts that were
    tried, so the gap did not show; the loop does. This test records the gap (restore -> a different answer); when a fuller save exists it should be replaced by one that expects equality."""
    g, _ = L.new_grid(FlexGrid)
    for _ in range(300 * L.TICKS_PER_STEP + 17):          # step 300, 17 ticks into the next pass: operands are waiting inside adders
        g.tick()
    path = os.path.join(tempfile.mkdtemp(), "c.json")
    v2.save_grid(g, path, "looped")
    g2 = FlexGrid(L.build_records())
    v2.restore_into(g2, path)
    missing = set()
    for pos in g.cells:
        missing |= {k for k in set(vars(g.cells[pos])) | set(vars(g2.cells[pos])) if vars(g.cells[pos]).get(k) != vars(g2.cells[pos]).get(k)}
    assert missing == {"_a_face", "merge_mode", "_merge_order", "_merge_rr"}
    a, b = L.run_steps(g, 20), L.run_steps(g2, 20)
    assert [v for _, v in a] == L.model(320)[300:320]       # the uninterrupted run is right
    assert a != b                                            # the restored one is not
