"""
test_loader_v1.py — verifies the real loader/binder stage (`points.md
#375`), standalone, before checking `nano/workbench_v1.py`'s own
integration of it in `test_workbench_v1.py`.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nano"))

from loader_v1 import bind_shape, find_auto_placement  # noqa: E402
from dsl_compiler_v1 import compile_source  # noqa: E402

SENTINEL_DSL = """
program sentinel_prog {
    place s1 as sentinel at (0,0) {
        inc: n
        dec: s
        clear: s
        out: e
        cmp.threshold: 8
    }
}
"""


def _compile(src=SENTINEL_DSL):
    icm, diags = compile_source(src)
    assert diags == []
    return icm.records


def test_manual_mode_shifts_correctly():
    records = _compile()
    bound, diags = bind_shape(records, {}, row_offset=5, col_offset=5)
    assert diags == []
    assert [(r.row, r.col) for r in bound] == [(5, 5), (5, 6), (5, 7)]


def test_manual_mode_never_mutates_the_original_records():
    records = _compile()
    bind_shape(records, {}, row_offset=5, col_offset=5)
    assert [(r.row, r.col) for r in records] == [(0, 0), (0, 1), (0, 2)]


def test_manual_mode_detects_a_real_collision():
    records = _compile()
    occupied = {(5, 5): "existing"}
    bound, diags = bind_shape(records, occupied, row_offset=5, col_offset=5)
    assert bound is None
    assert "collides" in diags[0].problem
    assert "(5, 5)" in diags[0].problem


def test_auto_mode_finds_origin_on_an_empty_grid():
    records = _compile()
    bound, diags = bind_shape(records, {})
    assert diags == []
    assert [(r.row, r.col) for r in bound] == [(0, 0), (0, 1), (0, 2)]


def test_auto_mode_finds_the_next_free_spot_when_origin_is_occupied():
    records = _compile()
    occupied = {(0, 0): "x", (0, 1): "x", (0, 2): "x"}
    bound, diags = bind_shape(records, occupied)
    assert diags == []
    positions = [(r.row, r.col) for r in bound]
    assert all(p not in occupied for p in positions)


def test_auto_mode_reports_a_real_error_when_search_space_is_exhausted():
    records = _compile()
    occupied = {(r, c): "x" for r in range(3) for c in range(3)}
    bound, diags = bind_shape(records, occupied, search_bound=3)
    assert bound is None
    assert "no valid auto-placement" in diags[0].problem


def test_partial_offset_is_a_real_validation_error():
    records = _compile()
    bound, diags = bind_shape(records, {}, row_offset=5)   # col_offset omitted
    assert bound is None
    assert "must both be given" in diags[0].problem


def test_empty_shape_auto_places_at_origin_trivially():
    bound, diags = bind_shape([], {})
    assert diags == []
    assert bound == []


def test_find_auto_placement_directly_returns_none_when_exhausted():
    records = _compile()
    occupied = {(r, c): "x" for r in range(2) for c in range(2)}
    result = find_auto_placement(records, occupied, search_bound=2)
    assert result is None


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
