"""
test_gpu_array_v1.py — verifies `gpu_array_v1.py`'s vectorized offer-
pass selector (`points.md #216` item 3, `#361`) is a genuine, exact
equivalent to `SuperGrid.tick()`'s own already-tested Pass 4 readiness
check -- not just "it runs," a real tick-by-tick comparison against the
manual condition, across every real composed tile this session built.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from gpu_array_v1 import (  # noqa: E402
    compute_ready_mask, VectorizedOfferSelector, DEVICE_NAME, HAS_GPU,
)
from composed_tile_library_v1 import composed_tile_library, place_composed  # noqa: E402
from super_tile_library_v1 import super_tile_library, place  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402
from unicell_automaton_v1 import N  # noqa: E402


def _manual_ready_positions(grid):
    """The exact readiness condition `SuperGrid.tick()`'s own Pass 4
    uses, reproduced here by hand (not imported) so the comparison is a
    genuine, independent check, not the same code compared to itself."""
    out = []
    for pos, cell in grid.cells.items():
        if cell.core == "nano" or cell.pending_ack != 0:
            continue
        _value, valid, downstream = cell._offer_state()
        if valid and downstream != 0:
            out.append(pos)
    return sorted(out)


def test_backend_detection_reports_something_real():
    assert DEVICE_NAME in ("CPU (NumPy)",) or "GPU" in DEVICE_NAME or HAS_GPU
    # this sandbox has no CUDA hardware -- confirmed directly (nvidia-smi
    # absent, cupy not installed), so the honest expectation here is the
    # CPU fallback specifically, not just "some backend was picked"
    assert DEVICE_NAME == "CPU (NumPy)"
    assert HAS_GPU is False


def test_compute_ready_mask_basic():
    mask = compute_ready_mask([0, 1, 0, 5], [True, True, False, True])
    assert list(mask) == [True, False, False, False]


def test_empty_grid_returns_empty_list():
    selector = VectorizedOfferSelector(SuperGrid([]))
    assert selector.ready_positions() == []


def test_sentinel_matches_manual_condition_across_many_ticks():
    tile = composed_tile_library.get("sentinel")
    records = place_composed(tile, 0, 0, {"inc": "n", "dec": "s", "clear": "s", "out": "e"},
                              {"cmp.threshold": 8})
    grid = SuperGrid(records)
    for i in range(20):
        manual = _manual_ready_positions(grid)
        vectorized = sorted(VectorizedOfferSelector(grid).ready_positions())
        assert manual == vectorized, f"tick {i}: manual={manual} vectorized={vectorized}"
        grid.tick()


def test_dual_threshold_monitor_fanout_matches_manual_condition():
    tile = composed_tile_library.get("dual_threshold_monitor")
    records = place_composed(tile, 0, 0, {
        "inc": "n", "dec": "s", "clear_low": "s", "out_low": "w",
        "clear_high": "n", "out_high": "e",
    }, {"cmp_low.threshold": 3, "cmp_high.threshold": 10})
    grid = SuperGrid(records)
    for i in range(20):
        manual = _manual_ready_positions(grid)
        vectorized = sorted(VectorizedOfferSelector(grid).ready_positions())
        assert manual == vectorized, f"tick {i}: manual={manual} vectorized={vectorized}"
        grid.tick()


def test_twin_sentinel_nested_matches_manual_condition():
    tile = composed_tile_library.get("twin_sentinel")
    records = place_composed(tile, 0, 0, {
        "s1_inc": "n", "s1_dec": "s", "s1_clear": "s", "s1_out": "e",
        "s2_inc": "n", "s2_dec": "s", "s2_clear": "s", "s2_out": "e",
    }, {"s1.cmp.threshold": 8, "s2.cmp.threshold": 4})
    grid = SuperGrid(records)
    for i in range(20):
        manual = _manual_ready_positions(grid)
        vectorized = sorted(VectorizedOfferSelector(grid).ready_positions())
        assert manual == vectorized, f"tick {i}: manual={manual} vectorized={vectorized}"
        grid.tick()


def test_nano_cells_are_correctly_excluded_from_the_vectorized_selection():
    # nano never participates in the generic offer pass at all (#337's
    # own design) -- confirm the vectorized selector correctly excludes
    # it, not just happens to for cores that have no nano cell present.
    tile = super_tile_library.get("nano_gate")
    rec = place(tile, 0, 0, {"out": "e"}, params={"topology": 0x24})
    grid = SuperGrid([rec])
    assert VectorizedOfferSelector(grid).ready_positions() == []


def test_vectorized_selector_never_mutates_grid_state():
    # a real, important safety property: this is a read-only query,
    # never called from inside SuperGrid.tick() itself (#361's own
    # stated design) -- confirm calling it repeatedly doesn't change
    # anything about the grid's own state.
    tile = composed_tile_library.get("sentinel")
    records = place_composed(tile, 0, 0, {"inc": "n", "dec": "s", "clear": "s", "out": "e"},
                              {"cmp.threshold": 8})
    grid = SuperGrid(records)
    acc = grid.cells[(0, 0)]
    for _ in range(5):
        acc.deliver({N: 1}, None)
    before = {pos: (cell.pending_ack, cell.core) for pos, cell in grid.cells.items()}
    for _ in range(5):
        VectorizedOfferSelector(grid).ready_positions()
    after = {pos: (cell.pending_ack, cell.core) for pos, cell in grid.cells.items()}
    assert before == after


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
