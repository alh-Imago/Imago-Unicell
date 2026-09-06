"""tests/tools/test_project_assemble_yosys_v1.py -- points.md #663: real
tests for project_assemble_v1.py's new target='yosys' path. No test
coverage existed for this tool before this entry (a real, standing gap,
not backfilled in full here -- scoped to the new yosys functionality
specifically, not the whole tool's pre-existing target='quartus' path).
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))

import project_assemble_v1 as pa  # noqa: E402

REPO_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
MAN_PATH = os.path.join(REPO_ROOT, "docs", "man", "mustang-f100-a10.man.json")


def test_generate_yosys_script_excludes_the_issp_probe():
    script = pa.generate_yosys_script("top_test", ["adder_cell_v4.v", "debug_issp_probe_v1.v", "ram_cell_v4.v"])
    assert "debug_issp_probe_v1.v" not in script
    assert "read_verilog adder_cell_v4.v" in script
    assert "read_verilog ram_cell_v4.v" in script


def test_generate_yosys_script_targets_the_real_supported_family():
    script = pa.generate_yosys_script("top_test", ["adder_cell_v4.v"])
    assert "synth_intel_alm -top top_test -family cyclone10gx" in script
    assert "stat" in script


def test_generate_yosys_script_states_the_real_arria10_scope_limit():
    """Points.md #663: the honest scope note must actually be in the
    generated script, not just in the tool's own console output --
    someone reading only the .ys file later should still see it."""
    script = pa.generate_yosys_script("top_test", ["adder_cell_v4.v"])
    assert "Arria 10" in script
    assert "NOT a real" in script


def test_assemble_yosys_target_writes_ys_not_qsf(tmp_path):
    result = pa.assemble(MAN_PATH, 2, str(tmp_path), shell="vix", target="yosys")
    assert result["target"] == "yosys"
    assert os.path.exists(os.path.join(str(tmp_path), f"{result['top_name']}.ys"))
    assert not os.path.exists(os.path.join(str(tmp_path), f"{result['top_name']}.qsf"))
    assert not os.path.exists(os.path.join(str(tmp_path), f"{result['top_name']}.sdc"))


def test_assemble_quartus_target_unchanged(tmp_path):
    """Real, necessary regression -- adding target='yosys' must not
    change the default target='quartus' behavior at all."""
    result = pa.assemble(MAN_PATH, 2, str(tmp_path), shell="vix")
    assert result["target"] == "quartus"
    assert os.path.exists(os.path.join(str(tmp_path), f"{result['top_name']}.qsf"))
    assert os.path.exists(os.path.join(str(tmp_path), f"{result['top_name']}.sdc"))
    assert not os.path.exists(os.path.join(str(tmp_path), f"{result['top_name']}.ys"))


def test_assemble_rejects_yosys_with_probe(tmp_path):
    try:
        pa.assemble(MAN_PATH, 2, str(tmp_path), shell="vix", target="yosys", probe_name="DEBUG_PROBE")
    except ValueError as e:
        assert "yosys" in str(e) and "probe" in str(e).lower()
    else:
        raise AssertionError("expected ValueError combining target='yosys' with a real probe")


def test_assemble_rejects_unknown_target(tmp_path):
    try:
        pa.assemble(MAN_PATH, 2, str(tmp_path), shell="vix", target="vivado")
    except ValueError as e:
        assert "unknown target" in str(e)
    else:
        raise AssertionError("expected ValueError for an unrecognized target")


def test_yosys_script_actually_runs_end_to_end(tmp_path):
    """Points.md #663: the real, decisive test -- does the generated
    script actually synthesize against the real project RTL through a
    real Yosys binary, not just look plausible. Skipped gracefully (not
    failed) if Yosys isn't installed in this environment -- this is a
    real external-tool dependency, not something to fake."""
    if shutil.which("yosys") is None:
        import pytest
        pytest.skip("yosys not installed in this environment")

    result = pa.assemble(MAN_PATH, 2, str(tmp_path), shell="vix", target="yosys")
    ys_file = f"{result['top_name']}.ys"
    proc = subprocess.run(["yosys", ys_file], cwd=str(tmp_path), capture_output=True,
                           text=True, timeout=180)
    assert proc.returncode == 0, f"real yosys run failed:\n{proc.stdout[-3000:]}\n{proc.stderr[-2000:]}"
    assert "Number of cells:" in proc.stdout, "expected a real stat report in the yosys output"
    assert os.path.exists(os.path.join(str(tmp_path), f"{result['top_name']}_synth_cyclone10gx.v")), \
        "expected the real post-synth netlist to actually be written"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
