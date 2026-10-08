"""Second output ports of the flex adder (carry_out) and multiplier (data_out_hi), ledger #974.

Alan's ruling: a cell that produces two results gets two ports. Each port has its own valid/ack, a new
round needs BOTH consumed, and the port is silent unless its config bit is set. The bench
(sub/verilog/tb_second_port_v4sa.v, WIDTH 8 so every case is hand-checkable) covers: disabled = silent,
carry word 0/1, subtract carry = not-borrow, independent acks, a held second port blocking the next
round, and the multiplier's high word. Run against both multiplier builds (LUT and DSP stand-in).
"""
import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SUBV = os.path.join(ROOT, "sub", "verilog")
ADDER_V1 = os.path.join(ROOT, "fpga", "verilog", "adder_v1.v")


def _run(mul_files, tmp_path):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    out = str(tmp_path / "sp.vvp")
    cmd = ["iverilog", "-g2012"] + (["-DDSP"] if "mul_cell_v4sa_dsp.v" in mul_files else []) + [ "-s", "tb_second_port_v4sa", "-o", out, os.path.join(SUBV, "tb_second_port_v4sa.v"),
           os.path.join(SUBV, "adder_cell_v4sa.v"), ADDER_V1] + [os.path.join(SUBV, f) for f in mul_files]
    c = subprocess.run(cmd, capture_output=True, text=True)
    assert c.returncode == 0, c.stderr
    return subprocess.run(["vvp", out], capture_output=True, text=True).stdout


@pytest.mark.parametrize("mul_files", [["mul_cell_v4sa.v"], ["mul_cell_v4sa_dsp.v", "tb_mul_cell_v4sa_dsp.v"]], ids=["lut_mul", "dsp_mul"])
def test_second_ports(mul_files, tmp_path):
    out = _run(mul_files, tmp_path)
    assert "FAIL" not in out, out
    assert "ALL PASS" in out, out
    assert len(re.findall(r"^PASS", out, re.M)) >= 14


def test_multiword_add_from_carry_port(tmp_path):
    """Three 8-bit adders make a 16-bit add: ADD0's carry_out feeds ADD2 with ADD1's sum (400 pairs incl. the carry edge cases)."""
    assert shutil.which("iverilog") and shutil.which("vvp")
    out = str(tmp_path / "cc.vvp")
    c = subprocess.run(["iverilog", "-g2012", "-o", out, os.path.join(SUBV, "tb_carry_chain_v4sa.v"),
                        os.path.join(SUBV, "adder_cell_v4sa.v"), ADDER_V1], capture_output=True, text=True)
    assert c.returncode == 0, c.stderr
    r = subprocess.run(["vvp", out], capture_output=True, text=True, timeout=120).stdout
    assert "FAIL" not in r and "ALL PASS (400" in r, r


@pytest.mark.parametrize("t1,t2,w", [(10, 10, 8), (7, 5, 4), (300, 300, 18), (1000, 1000, 32), (65535, 3, 32)])
def test_accumulator_cascade_gear_ratio(tmp_path, t1, t2, w):
    """Two pulse-mode accumulators in cascade fire once per T1*T2 input events (1,000,000 > the 16-bit threshold a single cell can hold)."""
    assert shutil.which("iverilog") and shutil.which("vvp")
    out = str(tmp_path / "ac.vvp")
    c = subprocess.run(["iverilog", "-g2012", "-P", f"tb_acc_cascade_v4sa.T1={t1}", "-P", f"tb_acc_cascade_v4sa.T2={t2}", "-P", f"tb_acc_cascade_v4sa.W={w}",
                        "-o", out, os.path.join(SUBV, "tb_acc_cascade_v4sa.v"), os.path.join(SUBV, "accumulator_cell_v4sa.v")], capture_output=True, text=True)
    assert c.returncode == 0, c.stderr
    r = subprocess.run(["vvp", out], capture_output=True, text=True, timeout=300).stdout
    assert "FAIL" not in r and f"period {t1 * t2} input events" in r, r
