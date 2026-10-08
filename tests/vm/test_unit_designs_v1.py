"""tests/vm/test_unit_designs_v1.py -- ledger #1036: the other small example designs run through the generated SD+SPI unit (words fed over the simulated ESP32's SPI, no card needed):
the 4-lane parallel reduction tree (sum of four words) and the relay chain (the word comes out unchanged). Both also fit the Tang Nano 20K (measured in docs/playout_capture_v1.md). Requires iverilog."""
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from test_spi_bridge_v1 import MASTER  # noqa: E402
import sd_unit_top_v1 as U  # noqa: E402

V = os.path.join(ROOT, "fpga", "verilog")
M32 = 0xFFFFFFFF


def run_unit(icm, items, expect):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="unitdes_")
    try:
        out = os.path.join(d, "out")
        U.build(icm, out, 2)
        lanes = len(items[0])
        words = [w & M32 for it in items for w in it]
        n = len(items)
        loads = "\n".join(f"    wbuf[{i}] = 32'd{w};" for i, w in enumerate(words))
        tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0; always #5 clk = ~clk;
  wire SD_CLK, SD_CMD, SD_DAT3, SPI_MISO, READY; wire [5:0] LED_N; wire SD_DAT0 = 1'b1;
{MASTER.replace("wire miso;", "wire miso = SPI_MISO;")}
  unit_top T(.BOARD_CLK(clk), .SD_CLK(SD_CLK), .SD_CMD(SD_CMD), .SD_DAT0(SD_DAT0), .SD_DAT3(SD_DAT3), .SPI_SCLK(sclk), .SPI_CS_N(cs_n), .SPI_MOSI(mosi), .SPI_MISO(SPI_MISO), .READY(READY), .LED_N(LED_N));
  defparam T.INIT_DIV = 3; defparam T.FAST_DIV = 1; defparam T.RSTW = 3;
  integer j;
  initial begin
{loads}
    repeat (40) @(negedge clk);
    wr_reg(8'd2, 32'h8); wr_reg(8'd8, 32'd1); wr_reg(8'd9, 32'd1);
    wr_words(16'd0, {len(words)});
    wr_reg(8'd5, 32'd{len(words)}); wr_reg(8'd2, 32'h4);
    poll_n = 0; rd_reg(8'd6); while (rv < {n} && poll_n < 4000) begin rd_reg(8'd6); poll_n = poll_n + 1; end
    $display("CAP %0d", rv);
    rd_words(16'd0, {n});
    for (j = 0; j < {n}; j = j + 1) $display("S %0d", rbuf[j]);
    $finish;
  end
  initial begin repeat (8000000) @(posedge clk); $display("GLOBAL TIMEOUT"); $finish; end
endmodule
"""
        # wr_words reads the words from wbuf[0..15]: feed them in blocks of 16
        blocks, k = "", 0
        # (re-emit the stimulus so the load is split into 16-word writes)
        stim = []
        for off in range(0, len(words), 16):
            chunk = words[off:off + 16]
            stim.append("\n".join(f"    wbuf[{i}] = 32'd{w};" for i, w in enumerate(chunk)) + f"\n    wr_words(16'd{off}, {len(chunk)});")
        tb = tb.replace(loads + "\n    repeat (40) @(negedge clk);", "    repeat (40) @(negedge clk);")
        tb = tb.replace("    wr_words(16'd0, %d);\n" % len(words), "\n".join(stim) + "\n")
        open(os.path.join(d, "tb.v"), "w").write(tb)
        files = [os.path.join(out, f) for f in open(os.path.join(out, "FILES.txt")).read().split()]
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + files, capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        res = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=1800).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert "GLOBAL TIMEOUT" not in res, res[-400:]
    got = [int(x) for x in re.findall(r"^S (\d+)$", res, re.M)]
    assert got == [e & M32 for e in expect], (got, expect)


def test_parallel_reduction_tree_sums_four_words():
    items = [[1, 2, 3, 4], [10, 20, 30, 40], [0xFFFFFFFF, 1, 5, 5], [123456, 654321, 7, 9]]
    run_unit(os.path.join(ROOT, "nano", "examples", "parallel_reduction_tree.icm-hier.json"), items, [sum(i) for i in items])


def test_small_relay_chain_passes_the_word_through():
    items = [[7], [123456789], [0], [0xFFFFFFFF]]
    run_unit(os.path.join(ROOT, "nano", "examples", "small_relay_chain.icm-hier.json"), items, [i[0] for i in items])
