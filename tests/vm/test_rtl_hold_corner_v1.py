"""tests/vm/test_rtl_hold_corner_v1.py -- ledger #1035: the HOLD ram mode and the CORNER core in the v4 / v4c RTL (fpga/verilog), run in iverilog, plus the carrier regression (core 11 added). Requires iverilog."""
import glob
import os
import shutil
import subprocess

import pytest

V = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "fpga", "verilog")
ADD = ["invert_addon_v1.v", "nibble_mask_addon_v1.v", "shift_lane_addon_v1.v"]


def sim(tmp_path, top, files, defs=()):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    out = str(tmp_path / "sim")
    cmd = ["iverilog", "-g2012", "-s", top, "-o", out] + [f"-D{d}" for d in defs] + [os.path.join(V, f) for f in files]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=V)
    assert r.returncode == 0, r.stderr
    return subprocess.run(["vvp", out], capture_output=True, text=True, cwd=V, timeout=300).stdout


@pytest.mark.parametrize("cell", ["ram_cell_v4", "ram_cell_v4c"])
def test_hold_mode(tmp_path, cell):
    o = sim(tmp_path, "tb_ram_hold_v4", ["tb_ram_hold_v4.v", cell + ".v"] + ADD, [f"CELL={cell}"])
    assert "PASS: HOLD" in o and "FAIL" not in o, o


@pytest.mark.parametrize("cell", ["ram_cell_v4", "ram_cell_v4c"])
def test_existing_ram_testbench_still_passes(tmp_path, cell):
    o = sim(tmp_path, "tb_" + cell, ["tb_" + cell + ".v", cell + ".v"] + ADD)
    assert "PASS" in o and "FAIL" not in o, o


@pytest.mark.parametrize("cell", ["corner_cell_v4", "corner_cell_v4c"])
def test_corner_cell(tmp_path, cell):
    o = sim(tmp_path, "tb_corner_cell_v4", ["tb_corner_cell_v4.v", "corner_cell_v4.v", "corner_cell_v4c.v"], [f"CELL={cell}"])
    assert "PASS: corner cell" in o and "FAIL" not in o, o


@pytest.mark.parametrize("v", ["v1", "v1d"])
def test_carriers_still_pass_with_the_corner_core(tmp_path, v):
    allv = sorted(f for f in os.listdir(V) if f.endswith(".v") and not f.startswith("tb_") and f not in ("unicell_vix_carrier_v1.v", "unicell_vix_carrier_v1d.v"))
    o = sim(tmp_path, f"tb_unicell_vix_carrier_{v}", [f"tb_unicell_vix_carrier_{v}.v", f"unicell_vix_carrier_{v}.v"] + allv)
    assert ("PASS" in o or "ALL CHECKS PASSED" in o) and "FAIL" not in o, o[-800:]
