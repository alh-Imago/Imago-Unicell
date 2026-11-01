"""tests/vm/test_config_gate_v1.py -- config gate v1 and the arithmetic-block prototype (1 Nov 2026), simulation only (iverilog). Spec: Project doc claude/config-gate-spec.md.
Gate: raw cell drops a word offered on the cfg clock (control); with the gate none is lost, in-flight words finish on the old config, a second request is flagged, a drain timeout keeps the old config, reset reopens. Run with SETTLE=1 and SETTLE=0. Arithmetic block: add / sub / signed >= against the arithmetic, shared and naive variants.
The slow-consumer test (T6) stands in for a busy divider; the real divider cell is NOT tested here."""
import os, shutil, subprocess
import pytest
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE)); S = os.path.join(ROOT, "sub", "verilog"); F = os.path.join(ROOT, "fpga", "verilog")
pytestmark = pytest.mark.skipif(shutil.which("iverilog") is None, reason="iverilog missing")


def sim(tmp_path, files, params=()):
    out = str(tmp_path / "a.vvp")
    cmd = ["iverilog", "-g2012"] + [f"-P{p}" for p in params] + ["-o", out] + files
    r = subprocess.run(cmd, capture_output=True, text=True); assert r.returncode == 0, r.stderr
    return subprocess.run(["vvp", out], capture_output=True, text=True).stdout


@pytest.mark.parametrize("settle", [1, 0])
def test_config_gate(tmp_path, settle):
    o = sim(tmp_path, [f"{S}/config_gate_v1.v", f"{S}/tb_config_gate_v1.v", f"{S}/adder_cell_v4s.v", f"{S}/flex_sub_bridge_v1.v", f"{F}/adder_v1.v"], [f"tb_config_gate_v1.SETTLE={settle}"])
    assert f"ALL CONFIG GATE TESTS PASS (SETTLE={settle})" in o and "FAIL" not in o, o


def test_arith_block(tmp_path):
    o = sim(tmp_path, [f"{S}/arith_block_v1.v", f"{S}/tb_arith_block_v1.v", f"{S}/adder_cell_v4s.v", f"{F}/adder_v1.v"])
    assert "ALL ARITH BLOCK TESTS PASS" in o and "MISMATCH" not in o, o


def test_arith_block_v2(tmp_path):
    """v2: add, sub, ge, 3-way compare, accumulate; shared and naive vs the arithmetic, modes 0/1 vs adder_cell_v4s, accumulate vs the real accumulator_cell_v4s (continuous mode, 32-bit)."""
    o = sim(tmp_path, [f"{S}/arith_block_v2.v", f"{S}/tb_arith_block_v2.v", f"{S}/adder_cell_v4s.v", f"{S}/accumulator_cell_v4s.v", f"{F}/adder_v1.v"])
    assert "ALL ARITH BLOCK V2 TESTS PASS" in o and "MISMATCH" not in o, o
