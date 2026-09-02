"""tests/tools/test_walker_sim_cli_v1.py -- points.md #602: real tests
for the simulated Walker's CLI, mirroring the pattern already
established for man_generate_v1/project_assemble_v1's own CLIs."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nano"))

import walker_sim_cli_v1  # noqa: E402
import walker_sim_v1  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REAL_MAN = os.path.join(REPO_ROOT, "docs", "man", "mustang-f100-a10.man.json")

GRID4_DSL = """
program grid4 {
    place r1 as ram_constant at (0, 0) {
        out: e
        init_data: 1
    }
    place r2 as ram_flowing at (0, 1) {
        in: w
        out: s
    }
    place r3 as ram_flowing at (1, 1) {
        in: n
        out: w
    }
    place r4 as ram_flowing at (1, 0) {
        in: e
        out: n
    }
}
"""


def test_run_with_dsl_file(tmp_path):
    dsl_path = tmp_path / "grid4.dsl"
    dsl_path.write_text(GRID4_DSL)
    out = tmp_path / "shape.json"
    result = walker_sim_cli_v1.run(REAL_MAN, 4, str(out), dsl_file=str(dsl_path))
    assert result["cells_discovered"] == 4
    assert result["edges_discovered"] == 4
    shape = json.loads(out.read_text())
    assert shape["card_id"] == "mustang-f100-a10-01"


def test_run_requires_exactly_one_source(tmp_path):
    out = tmp_path / "shape.json"
    try:
        walker_sim_cli_v1.run(REAL_MAN, 4, str(out))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_run_with_icm_file(tmp_path):
    """Real, end-to-end round trip: compile once to a real .icm file,
    then load it via --icm instead of recompiling from DSL."""
    from dsl_compiler_v1 import compile_source
    icm, diags = compile_source(GRID4_DSL)
    assert diags == []
    icm_path = tmp_path / "grid4.icm"
    icm.save(str(icm_path))

    out = tmp_path / "shape.json"
    result = walker_sim_cli_v1.run(REAL_MAN, 4, str(out), icm_path=str(icm_path))
    assert result["cells_discovered"] == 4


def test_main_cli_end_to_end(tmp_path, capsys):
    dsl_path = tmp_path / "grid4.dsl"
    dsl_path.write_text(GRID4_DSL)
    out = tmp_path / "shape.json"
    old_argv = sys.argv
    sys.argv = [
        "walker_sim_cli_v1.py", "--man", REAL_MAN, "--cells", "4",
        "--dsl-file", str(dsl_path), "-o", str(out),
    ]
    try:
        rc = walker_sim_cli_v1.main()
    finally:
        sys.argv = old_argv
    assert rc == 0
    assert out.exists()
    captured = capsys.readouterr()
    assert "Cells discovered: 4" in captured.out


def test_main_cli_bad_origin_returns_nonzero(tmp_path, capsys):
    dsl_path = tmp_path / "grid4.dsl"
    dsl_path.write_text(GRID4_DSL)
    out = tmp_path / "shape.json"
    old_argv = sys.argv
    sys.argv = [
        "walker_sim_cli_v1.py", "--man", REAL_MAN, "--cells", "4",
        "--dsl-file", str(dsl_path), "--start-row", "9", "--start-col", "9", "-o", str(out),
    ]
    try:
        rc = walker_sim_cli_v1.main()
    finally:
        sys.argv = old_argv
    assert rc == 1
    assert not out.exists()
