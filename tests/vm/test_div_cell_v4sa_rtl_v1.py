"""tests/vm/test_div_cell_v4sa_rtl_v1.py -- ledger #1070: the flex divider cell's own bench (sub/verilog/tb_div_cell_v4sa.v) at several WIDTH / STEPS.

RTL only: nothing here touches FlexGrid (which still refuses the division core). Needs iverilog and fails loudly without it rather than skipping (#965)."""
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V = os.path.join(ROOT, "sub", "verilog")

CONFIGS = [(32, 1), (18, 1), (4, 1), (8, 3), (36, 4), (18, 18), (5, 2), (12, 3)]


@pytest.mark.parametrize("width,steps", CONFIGS)
def test_bench_passes(width, steps, tmp_path):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is required (see current/START.md)"
    exe = str(tmp_path / "t")
    c = subprocess.run(["iverilog", "-g2012", f"-Ptb_div_cell_v4sa.WIDTH={width}", f"-Ptb_div_cell_v4sa.STEPS={steps}", "-o", exe,
                        os.path.join(V, "div_cell_v4sa.v"), os.path.join(V, "tb_div_cell_v4sa.v")], capture_output=True, text=True)
    assert c.returncode == 0, c.stderr
    out = subprocess.run(["vvp", exe], capture_output=True, text=True, timeout=600).stdout
    assert f"PASS: div_cell_v4sa W={width} K={steps}" in out, out[-600:]
    assert "FAIL" not in out
