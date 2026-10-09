"""tests/vm/test_unit_live_feed_v1.py -- SensorTrix-style live feed into a running unit (simulation, iverilog).

The question: can a sensor reading go straight into a LIVE design instead of being replayed from the SD card?  A SensorTrix word is 32 bits: amount in bits 31..16, location in bits 15..0
(old full-cell stack: tests/vm/legacy_full_cell/test_sensortrix.py).  Here the "ESP32" does what a real sensor loop would do, one sample at a time, with NO reset and NO card between samples:
clear capture -> write the packed word into the playout RAM over SPI -> PLAY_COUNT -> play -> poll CAP_COUNT -> read the result.  The design keeps running throughout.
It also counts the clocks each sample takes (so the sample rate at the real SPI speed can be quoted from a measurement rather than a guess).  Requires iverilog."""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from test_spi_bridge_v1 import MASTER  # noqa: E402
import sd_unit_top_v1 as U  # noqa: E402

M32 = 0xFFFFFFFF


def pack(loc, amount):
    """SensorTrix: bits 31..16 amount, bits 15..0 location."""
    return ((amount & 0xFFFF) << 16) | (loc & 0xFFFF)


def run_live(icm, samples):
    """samples: list of items (one word per entry lane).  Returns (results, clocks_per_sample)."""
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="livefeed_")
    try:
        out = os.path.join(d, "out")
        U.build(icm, out, 2)
        lanes = len(samples[0])
        per = []
        for k, it in enumerate(samples):
            ws = "\n".join(f"    wbuf[{i}] = 32'd{w & M32};" for i, w in enumerate(it))
            per.append(f"""    t0 = $time;
    wr_reg(8'd2, 32'h8);
{ws}
    wr_words(16'd0, {lanes});
    wr_reg(8'd5, 32'd{lanes}); wr_reg(8'd2, 32'h4);
    poll_n = 0; rd_reg(8'd6); while (rv < 1 && poll_n < 4000) begin rd_reg(8'd6); poll_n = poll_n + 1; end
    rd_words(16'd0, 1);
    $display("S %0d %0d", rbuf[0], ($time - t0) / 10);""")
        tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0; always #5 clk = ~clk;
  reg key = 1'b0; wire SD_CLK, SD_CMD, SD_DAT3, SPI_MISO, READY; wire [5:0] LED_N; wire SD_DAT0 = 1'b1;
{MASTER.replace("wire miso;", "wire miso = SPI_MISO;")}
  unit_top T(.BOARD_CLK(clk), .KEY_S1(key), .SD_CLK(SD_CLK), .SD_CMD(SD_CMD), .SD_DAT0(SD_DAT0), .SD_DAT3(SD_DAT3), .SPI_SCLK(sclk), .SPI_CS_N(cs_n), .SPI_MOSI(mosi), .SPI_MISO(SPI_MISO), .READY(READY), .LED_N(LED_N));
  defparam T.INIT_DIV = 3; defparam T.FAST_DIV = 1; defparam T.RSTW = 3;
  time t0;
  initial begin
    repeat (40) @(negedge clk);
    wr_reg(8'd8, 32'd1); wr_reg(8'd9, 32'd1);
{chr(10).join(per)}
    $finish;
  end
  initial begin repeat (20000000) @(posedge clk); $display("GLOBAL TIMEOUT"); $finish; end
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
    rows = [(int(a), int(b)) for a, b in re.findall(r"^S (\d+) (\d+)$", res, re.M)]
    return [r[0] for r in rows], [r[1] for r in rows]


def test_sensor_words_pass_live_through_a_running_design_one_by_one():
    """A sweep of sensor readings (location 3, rising then falling amount) goes in one at a time with no reset; each comes out unchanged and decodes to the same (location, amount)."""
    amounts = [0, 100, 1200, 12800, 65535, 40000, 7, 0]
    samples = [[pack(3, a)] for a in amounts]
    got, clocks = run_live(os.path.join(ROOT, "nano", "examples", "small_relay_chain.icm-hier.json"), samples)
    assert got == [s[0] for s in samples], (got, samples)
    assert [(g & 0xFFFF, g >> 16) for g in got] == [(3, a) for a in amounts]
    assert len(clocks) == len(amounts) and max(clocks) < 200000


def test_four_sensor_channels_summed_live_by_the_reduction_tree():
    """Four sensors (locations 0..3) read together each round; the tree adds the four words, so the top half of the result is the total amount (location field sums to 0+1+2+3=6)."""
    rounds = [[10, 20, 30, 40], [1000, 2000, 3000, 4000], [5, 0, 0, 5]]
    samples = [[pack(loc, a) for loc, a in enumerate(r)] for r in rounds]
    got, _ = run_live(os.path.join(ROOT, "nano", "examples", "parallel_reduction_tree.icm-hier.json"), samples)
    assert [(g >> 16, g & 0xFFFF) for g in got] == [(sum(r), 6) for r in rounds]
