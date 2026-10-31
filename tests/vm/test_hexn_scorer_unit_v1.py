"""tests/vm/test_hexn_scorer_unit_v1.py -- Hex-N (1 Nov 2026): the batch scorer inside the SD+SPI small unit. A simulated ESP32 (SPI master from test_spi_bridge_v1) loads the table with LOAD words, a bias, and 100 SCORE words
through the playout RAM, plays them, reads the results back from the capture RAM and compares them with the bit-exact Python reference. Requires iverilog."""
import os, re, shutil, subprocess, sys, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "tools"))
from test_spi_bridge_v1 import MASTER  # noqa: E402
import hexn_scorer_unit_v1 as G, hexn_scorer_ref_v1 as R  # noqa: E402

def test_scorer_unit_over_spi_matches_reference():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    rng = np.random.default_rng(5); W = rng.integers(-60, 61, size=(2, R.NS, 16)); bias = 17
    words = R.table_words(W) + [R.w_bias(bias)]; n = 100; exp = []
    for _ in range(n):
        b = rng.integers(0, 12, size=R.NS); words.append(R.w_score(b)); exp.append(R.score(W, bias, b)[0])
    d = tempfile.mkdtemp(prefix="hexnsc_")
    try:
        out = os.path.join(d, "out"); G.build(out, 2)
        stim = []
        for off in range(0, len(words), 16):
            chunk = words[off:off + 16]
            stim.append("\n".join(f"    wbuf[{i}] = 32'd{w};" for i, w in enumerate(chunk)) + f"\n    wr_words(16'd{off}, {len(chunk)});")
        tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0; always #5 clk = ~clk;
  reg key = 1'b0; wire SD_CLK, SD_CMD, SD_DAT3, SPI_MISO, READY; wire [5:0] LED_N; wire SD_DAT0 = 1'b1;
{MASTER.replace("wire miso;", "wire miso = SPI_MISO;")}
  unit_top T(.BOARD_CLK(clk), .KEY_S1(key), .SD_CLK(SD_CLK), .SD_CMD(SD_CMD), .SD_DAT0(SD_DAT0), .SD_DAT3(SD_DAT3), .SPI_SCLK(sclk), .SPI_CS_N(cs_n), .SPI_MOSI(mosi), .SPI_MISO(SPI_MISO), .READY(READY), .LED_N(LED_N));
  defparam T.INIT_DIV = 3; defparam T.FAST_DIV = 1; defparam T.RSTW = 3;
  integer j, k;
  initial begin
    repeat (40) @(negedge clk);
    wr_reg(8'd2, 32'h8);
{chr(10).join(stim)}
    wr_reg(8'd5, 32'd{len(words)}); wr_reg(8'd2, 32'h4);
    poll_n = 0; rd_reg(8'd6); while (rv < {n} && poll_n < 4000) begin rd_reg(8'd6); poll_n = poll_n + 1; end
    $display("CAP %0d", rv);
    for (j = 0; j < {n}; j = j + 16) begin rd_words(j, {n} - j < 16 ? {n} - j : 16); for (k = 0; k < 16; k = k + 1) if (j + k < {n}) $display("S %0d %0d", j + k, rbuf[k]); end
    $finish;
  end
  initial begin repeat (8000000) @(posedge clk); $display("GLOBAL TIMEOUT"); $finish; end
endmodule
"""
        open(os.path.join(d, "tb.v"), "w").write(tb)
        files = [os.path.join(out, f) for f in open(os.path.join(out, "FILES.txt")).read().split()]
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + files, capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        res = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=1800).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert "GLOBAL TIMEOUT" not in res, res[-400:]
    got = {int(a): int(b) for a, b in re.findall(r"^S (\d+) (\d+)$", res, re.M)}
    assert [got.get(i) for i in range(n)] == exp, (res[-500:])
