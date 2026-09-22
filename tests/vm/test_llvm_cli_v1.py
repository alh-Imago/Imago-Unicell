"""tests/vm/test_llvm_cli_v1.py — points.md #823: the LLVM IR CLI (`nano/llvm_cli_v1.py`), the first CLI entry
point for `llvm_dag_frontend_v1.compile_llvm_via_dag` (previously only reachable via direct Python calls, unlike
the DSL's own `dsl_cli_v1.py`). Exercises the CLI's `main()` directly -- exit codes, stderr diagnostics, the saved
file, and the `--man`/`--cells` mirror check -- and confirms the saved file genuinely round-trips through the real
VM, not just that `save()` didn't raise.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import llvm_cli_v1  # noqa: E402
from icm_v3 import IcmV3File  # noqa: E402
from unicell_super_automaton_v1 import SuperGrid  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REAL_MAN = os.path.join(REPO_ROOT, "docs", "man", "mustang-f100-a10.man.json")

ADD_PROGRAM = """define i32 @f(i32 %x, i32 %y) {
entry:
  %a = add i32 %x, %y
  ret i32 %a
}
"""

BAD_PROGRAM = """define i32 @f() {
entry:
  ret i32 %nonexistent
}
"""


def _write(tmp_path, text, name="prog.ll"):
    p = os.path.join(tmp_path, name)
    with open(p, "w") as f:
        f.write(text)
    return p


def test_a_plain_compile_succeeds_and_saves_a_loadable_correct_program(tmp_path, capsys):
    src = _write(tmp_path, ADD_PROGRAM)
    out = os.path.join(tmp_path, "out.icm")
    rc = llvm_cli_v1.main([src, "-o", out])
    captured = capsys.readouterr()
    assert rc == 0
    assert "compiled" in captured.out and out in captured.out
    assert os.path.exists(out)

    icm = IcmV3File.load(out)
    grid = SuperGrid(icm.records)
    srcs = [(r.row, r.col) for r in icm.records if r.core == "ram" and not r.core_config.get("upstream_mask")]
    assert len(srcs) == 2
    grid.cells[srcs[0]].ram_data_reg, grid.cells[srcs[0]].ram_data_valid = 6, True
    grid.cells[srcs[1]].ram_data_reg, grid.cells[srcs[1]].ram_data_valid = 7, True
    # cross-check against a DIRECT compile of the same source, for the real result-cell position: heuristics on
    # core_config shape (e.g. "an adder with no downstream face") are not reliable here -- an adder's own
    # downstream_mask can be set even when it names the design's own logical result port, not a further hop.
    import llvm_dag_frontend_v1 as F
    direct, _ = F.compile_llvm_via_dag(ADD_PROGRAM)
    result_pos = direct.result_cell
    for _ in range(50):
        grid.tick()
        c = grid.cells[result_pos]
        if getattr(c, f"{c.core}_data_valid", None):
            assert getattr(c, f"{c.core}_out_buffer", None) == 13
            return
    assert False, "never fired"


def _face_count(cfg, key):
    return len(cfg.get(key) or [])


def test_the_default_output_path_is_source_stem_dot_icm(tmp_path, capsys):
    src = _write(tmp_path, ADD_PROGRAM)
    rc = llvm_cli_v1.main([src])
    assert rc == 0
    assert os.path.exists(os.path.join(tmp_path, "prog.icm"))


def test_a_compile_error_exits_nonzero_and_prints_diagnostics_to_stderr(tmp_path, capsys):
    src = _write(tmp_path, BAD_PROGRAM)
    rc = llvm_cli_v1.main([src, "-o", os.path.join(tmp_path, "out.icm")])
    captured = capsys.readouterr()
    assert rc == 1
    assert "compile failed" in captured.err
    assert not os.path.exists(os.path.join(tmp_path, "out.icm"))


def test_a_missing_source_file_exits_with_a_clear_error(tmp_path, capsys):
    rc = llvm_cli_v1.main([os.path.join(tmp_path, "nope.ll")])
    captured = capsys.readouterr()
    assert rc == 2
    assert "could not read" in captured.err


def test_man_and_cells_must_be_given_together(tmp_path, capsys):
    src = _write(tmp_path, ADD_PROGRAM)
    rc = llvm_cli_v1.main([src, "--man", REAL_MAN])
    assert rc == 2
    rc2 = llvm_cli_v1.main([src, "--cells", "6"])
    assert rc2 == 2


def test_a_mirror_mismatch_is_a_compile_failure_exit_code_not_a_silent_save(tmp_path, capsys):
    """The LLVM placer's own cells don't tile to project_assemble_v1's canonical layout for a tiny cell count --
    this must be reported and must exit non-zero, and must NOT still write the output file."""
    src = _write(tmp_path, ADD_PROGRAM)
    out = os.path.join(tmp_path, "out.icm")
    rc = llvm_cli_v1.main([src, "-o", out, "--man", REAL_MAN, "--cells", "6"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "mirror check failed" in captured.err
    assert not os.path.exists(out)


def test_a_bad_man_path_with_cells_given_is_reported_cleanly(tmp_path, capsys):
    src = _write(tmp_path, ADD_PROGRAM)
    rc = llvm_cli_v1.main([src, "--man", os.path.join(tmp_path, "nope.json"), "--cells", "6"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "error loading MAN file" in captured.err
