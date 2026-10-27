"""Tests for our own SDRAM controller (rtl/hexn_sdram_v1.v): the long random read/write/refresh test against our rule-checking SDRAM model, and the board self-test top (hexn_tang_sdramtest_v1) with a stand-in PLL. Needs iverilog (the test FAILS, not skips, without it)."""
import os, shutil, subprocess, tempfile
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
def sim(srcs, name):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog and vvp are required"
    out = os.path.join(tempfile.mkdtemp(), name + ".vvp")
    subprocess.run(["iverilog", "-g2012", "-o", out] + [os.path.join(ROOT, s) for s in srcs], check=True, capture_output=True)
    return subprocess.run(["vvp", out], capture_output=True, text=True, timeout=1800).stdout
def test_controller_against_model():
    o = sim(["rtl/tb_hexn_sdram_v1.v", "rtl/hexn_sdram_v1.v", "rtl/sim/sdram_model_v1.v"], "sdram")
    assert "SDRAM TEST PASS" in o, o[-1500:]
    assert "rule violations 0, data mismatches 0" in o, o[-1500:]
def test_board_selftest_logic():
    o = sim(["rtl/tb_hexn_tang_sdramtest_v1.v", "rtl/hexn_tang_sdramtest_v1.v", "rtl/hexn_sdram_v1.v", "rtl/sim/sdram_model_v1.v", "rtl/sim/rpll_model.v"], "selftest")
    assert "SDRAM SELFTEST PASS" in o, o[-1500:]
