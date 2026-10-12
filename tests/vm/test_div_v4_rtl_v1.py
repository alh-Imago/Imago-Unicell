"""tests/vm/test_div_v4_rtl_v1.py -- ledger #1073: the cardinal division core (div_cell_v4 with its addon chain, div_cell_v4c without) in iverilog,
the cell bench at several STEPS (bits per clock), and the carrier bench with the division core (core 15) on both carriers. Requires iverilog."""
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


@pytest.mark.parametrize("steps", [1, 3, 4, 32])
@pytest.mark.parametrize("cell", ["div_cell_v4", "div_cell_v4c"])
def test_div_cell_bench(tmp_path, cell, steps):
    defs = [f"CELL={cell}", f"STEPS={steps}"] + (["HAS_ADDON"] if cell == "div_cell_v4" else [])
    o = sim(tmp_path, "tb_div_cell_v4", ["tb_div_cell_v4.v", cell + ".v"] + ADD, defs)
    assert f"PASS: div cell v4/v4c STEPS={steps} " in o and "FAIL" not in o, o


@pytest.mark.parametrize("v", ["v1", "v1d"])
def test_carrier_runs_the_division_core(tmp_path, v):
    other = "unicell_vix_carrier_v1d.v" if v == "v1" else "unicell_vix_carrier_v1.v"
    allv = sorted(f for f in os.listdir(V) if f.endswith(".v") and not f.startswith("tb_") and f != other)
    o = sim(tmp_path, "tb_vix_carrier_new_cores_v1", ["tb_vix_carrier_new_cores_v1.v"] + allv, [f"CARRIER=unicell_vix_carrier_{v}"])
    assert "div (15)" in o and "PASS: carrier new cores" in o and "FAIL" not in o, o[-600:]
