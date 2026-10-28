"""Board test top hexn_tang_cardtest_v5 in simulation: (1) on an empty test region it must run the whole sequence (PUT/GET, save, tier reset, restore, GET) with zero errors, counters equal to the bit-true reference, and no byte of the card outside the region touched; (2) with one non-empty block in the region it must REFUSE and write nothing. tools/hexn_tang_cardtest_check_v5.py is what to run on a real serial capture."""
import os, re, shutil, subprocess, sys, tempfile
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_tang_cardtest_check_v5 as C
SRCS = ["rtl/tb_hexn_tang_cardtest_v5.v", "rtl/hexn_tang_cardtest_v5.v", "rtl/hexn_tier_v5.v", "rtl/hexn_sdram_v1.v", "rtl/hexn_uart_v1.v", "fpga/verilog/sd_spi_v1.v", "fpga/verilog/sd_card_model_v1.v", "rtl/sim/sdram_model_v1.v", "rtl/sim/rpll_model.v"]
def sim(**params):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog and vvp are required"
    out = os.path.join(tempfile.mkdtemp(), "ct.vvp")
    d = ["-Ptb_hexn_tang_cardtest_v5.%s=%d" % (k, v) for k, v in params.items()]
    subprocess.run(["iverilog", "-g2012", "-o", out] + d + [os.path.join(ROOT, s) for s in SRCS], check=True, capture_output=True)
    return subprocess.run(["vvp", out], capture_output=True, text=True, timeout=3000).stdout
P = dict(KW=18, VW=18, FB=3, RAMB=3, LB=5, LOW=3, N=120, M=40)
def test_empty_region_runs_and_matches_reference():
    o = sim(**P, SD_BASE=40)
    assert "CARDTEST SIM DONE" in o, o[-1500:]
    v, lines = C.judge(re.search(r"REPORT(.*)", o).group(1), **P)
    assert v == "PASS", lines
def test_non_empty_region_is_refused_and_nothing_is_written():
    for poison in (0, 3, 31):
        o = sim(**P, SD_BASE=40, POISON=poison)
        assert "CARDTEST SIM DONE" in o, o[-1500:]   # includes: no byte changed outside the region or in the refused region
        v, lines = C.judge(re.search(r"REPORT(.*)", o).group(1), **P)
        assert v == "REFUSED", lines
        h, _ = C.parse(re.search(r"REPORT(.*)", o).group(1)); assert h[1] == 1 and h[2] == 40 + poison, h
def test_erase_build_wipes_only_the_region_then_runs():
    o = sim(**P, SD_BASE=40, POISON=7, ERASE=1)
    assert "CARDTEST SIM DONE" in o, o[-1500:]   # includes: nothing outside the region changed
    v, lines = C.judge(re.search(r"REPORT(.*)", o).group(1), **P)
    assert v == "PASS", lines
    assert any("wiped" in x for x in lines), lines
