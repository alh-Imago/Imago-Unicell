"""tests/vm/test_vm_mirror_v1.py -- points.md #601: real tests for
the MAN -> mirrored-VM construction. Uses the real, existing MAN file
and the real DSL compiler -- no mocking, matching this project's own
sim-first/real-verification discipline."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import vm_mirror_v1  # noqa: E402
import vm_ai_port_v1  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REAL_MAN = os.path.join(REPO_ROOT, "docs", "man", "mustang-f100-a10.man.json")


def test_load_mirror_bounds_matches_project_assemble_exactly():
    """Real, direct cross-check: this module must reuse
    project_assemble_v1's own grid_dims()/cell_positions(), not a
    reimplementation that could silently drift from what a real
    Quartus build would actually use."""
    sys.path.insert(0, os.path.join(REPO_ROOT, "tools"))
    import project_assemble_v1 as pa
    bounds = vm_mirror_v1.load_mirror_bounds(REAL_MAN, 10)
    rows, cols = pa.grid_dims(10)
    positions = set(pa.cell_positions(10, rows, cols))
    assert bounds.rows == rows
    assert bounds.cols == cols
    assert bounds.valid_positions == positions
    assert bounds.card_id == "mustang-f100-a10-01"


def test_load_mirror_bounds_rejects_zero_cells():
    try:
        vm_mirror_v1.load_mirror_bounds(REAL_MAN, 0)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_check_records_fit_empty_when_all_in_bounds():
    class FakeRecord:
        def __init__(self, cell_id, row, col):
            self.cell_id, self.row, self.col = cell_id, row, col
    bounds = vm_mirror_v1.load_mirror_bounds(REAL_MAN, 4)  # 2x2
    records = [FakeRecord(1, 0, 0), FakeRecord(2, 0, 1)]
    assert vm_mirror_v1.check_records_fit(records, bounds) == []


def test_check_records_fit_flags_out_of_bounds():
    class FakeRecord:
        def __init__(self, cell_id, row, col):
            self.cell_id, self.row, self.col = cell_id, row, col
    bounds = vm_mirror_v1.load_mirror_bounds(REAL_MAN, 1)  # 1x1, only (0,0) valid
    records = [FakeRecord(1, 5, 5)]
    problems = vm_mirror_v1.check_records_fit(records, bounds)
    assert len(problems) == 1
    assert "(5,5)" in problems[0]
    assert "outside the real" in problems[0]


def test_check_records_fit_flags_collisions():
    class FakeRecord:
        def __init__(self, cell_id, row, col):
            self.cell_id, self.row, self.col = cell_id, row, col
    bounds = vm_mirror_v1.load_mirror_bounds(REAL_MAN, 4)
    records = [FakeRecord(1, 0, 0), FakeRecord(2, 0, 0)]
    problems = vm_mirror_v1.check_records_fit(records, bounds)
    assert any("collides" in p for p in problems)


# ── VMSession.from_man() real end-to-end tests ──────────────────────

REAL_DSL_FITS = """
program fits {
    place r1 as ram_constant at (0, 0) {
        out: e
        init_data: 111
    }
    place r2 as ram_flowing at (0, 1) {
        in: w
        out: n
    }
}
"""

REAL_DSL_OUT_OF_BOUNDS = """
program too_big {
    place r1 as ram_constant at (0, 0) {
        out: e
        init_data: 111
    }
    place r2 as ram_flowing at (5, 5) {
        in: w
        out: n
    }
}
"""


def test_from_man_real_dsl_program_fits():
    session = vm_ai_port_v1.VMSession.from_man(REAL_MAN, 4, dsl=REAL_DSL_FITS)
    assert session.mirror_bounds is not None
    assert session.mirror_bounds.cells == 4
    assert (0, 0) in session.grid.cells
    assert (0, 1) in session.grid.cells


def test_from_man_real_dsl_program_out_of_bounds_raises():
    try:
        vm_ai_port_v1.VMSession.from_man(REAL_MAN, 2, dsl=REAL_DSL_OUT_OF_BOUNDS)
        assert False, "expected MirrorFitError"
    except vm_mirror_v1.MirrorFitError as e:
        assert any("(5,5)" in p for p in e.problems)


def test_from_man_requires_exactly_one_program_source():
    try:
        vm_ai_port_v1.VMSession.from_man(REAL_MAN, 2)
        assert False, "expected ValueError"
    except ValueError:
        pass
    try:
        vm_ai_port_v1.VMSession.from_man(REAL_MAN, 2, dsl=REAL_DSL_FITS, python="x = 1")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_from_man_free_mode_sessions_have_no_mirror_bounds():
    """Real, honest regression guard: from_dsl()/from_python()/
    from_icm_file() must NOT silently gain mirror_bounds -- only
    from_man() claims a real card correspondence."""
    session = vm_ai_port_v1.VMSession.from_dsl(REAL_DSL_FITS)
    assert session.mirror_bounds is None


# ── VMSession.from_llvm() / from_man(llvm=...) real end-to-end tests (points.md #823) ────────────────────────

REAL_LLVM_ADD = """define i32 @f(i32 %x, i32 %y) {
entry:
  %a = add i32 %x, %y
  ret i32 %a
}
"""

REAL_LLVM_BAD = """define i32 @f() {
entry:
  ret i32 %nonexistent
}
"""


def test_from_llvm_compiles_and_loads_a_real_running_grid():
    session = vm_ai_port_v1.VMSession.from_llvm(REAL_LLVM_ADD)
    assert session.diagnostics == []
    assert len(session.grid.cells) > 0
    assert hasattr(session, "llvm_result") and session.llvm_result is not None


def test_from_llvm_raises_compile_failure_with_real_diagnostics():
    try:
        vm_ai_port_v1.VMSession.from_llvm(REAL_LLVM_BAD)
        assert False, "expected CompileFailure"
    except vm_ai_port_v1.CompileFailure as e:
        assert len(e.diagnostics) > 0


def test_from_man_llvm_is_a_fourth_option_alongside_dsl_python_icm_path():
    """The LLVM frontend's own placer does not tile to project_assemble_v1's canonical N-cell layout, so a small
    cell count honestly fails the mirror check -- exactly the reason `from_llvm()` (above) and `from_man(llvm=)`
    are DIFFERENT code paths, not the same thing checked twice."""
    try:
        vm_ai_port_v1.VMSession.from_man(REAL_MAN, 6, llvm=REAL_LLVM_ADD)
        assert False, "expected MirrorFitError (this design does not tile canonically)"
    except vm_mirror_v1.MirrorFitError as e:
        assert e.problems  # a real, specific reason, not a bare failure


def test_from_man_llvm_counts_toward_the_exactly_one_of_check():
    try:
        vm_ai_port_v1.VMSession.from_man(REAL_MAN, 6, dsl=REAL_DSL_FITS, llvm=REAL_LLVM_ADD)
        assert False, "expected ValueError"
    except ValueError:
        pass
    try:
        vm_ai_port_v1.VMSession.from_man(REAL_MAN, 6)
        assert False, "expected ValueError (none given, now four options)"
    except ValueError as e:
        assert "llvm=" in str(e)


def test_from_man_llvm_with_a_bad_program_raises_compile_failure_not_mirror_error():
    """A compile error must surface as CompileFailure even under from_man() -- the mirror check never runs on a
    program that didn't compile in the first place."""
    try:
        vm_ai_port_v1.VMSession.from_man(REAL_MAN, 6, llvm=REAL_LLVM_BAD)
        assert False, "expected CompileFailure"
    except vm_ai_port_v1.CompileFailure:
        pass
