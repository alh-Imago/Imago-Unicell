"""Direct mode: a sensor pin wired to the Tang feeds the design itself -- no ESP32, no playout RAM, no host in the path.
The generated unit_top (reduction tree, built with --direct so it powers up in direct mode) is simulated with only the clock, the sensor pins and the LEDs;
the SPI pins sit idle. LED5 lights when the design's result carries at least one sensor's worth, LED4 at two. Also: without --direct the sensor pins do nothing."""
import os, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import sd_unit_top_v1 as U

ICM = os.path.join(ROOT, "nano", "examples", "parallel_reduction_tree.icm-hier.json")

TB = r"""
`timescale 1ns/1ps
module tb;
  reg clk = 0; always #18.5 clk = ~clk;
  reg [1:0] sens = 2'b00;
  wire [5:0] led_n; wire spi_miso, ready, sd_clk, sd_cmd, sd_dat3;
  unit_top #(.INIT_DIV(34), .FAST_DIV(2), .RSTW(8)) dut (.BOARD_CLK(clk), .KEY_S1(1'b0), .SENS(sens), .SD_CLK(sd_clk), .SD_CMD(sd_cmd), .SD_DAT0(1'b1), .SD_DAT3(sd_dat3),
      .SPI_SCLK(1'b0), .SPI_CS_N(1'b1), .SPI_MOSI(1'b0), .SPI_MISO(spi_miso), .READY(ready), .LED_N(led_n));
  task settle; begin #4_000_000; end endtask      // 4 ms: several 1 ms feed ticks plus the design's latency
  initial begin
    settle; $display("S00 led5=%b led4=%b res=%h cnt=%0d", ~led_n[5], ~led_n[4], dut.U.live_result, dut.U.live_count > 2);
    sens = 2'b01; settle; $display("S01 led5=%b led4=%b res=%h", ~led_n[5], ~led_n[4], dut.U.live_result);
    sens = 2'b11; settle; $display("S11 led5=%b led4=%b res=%h", ~led_n[5], ~led_n[4], dut.U.live_result);
    sens = 2'b00; settle; $display("S00b led5=%b led4=%b res=%h", ~led_n[5], ~led_n[4], dut.U.live_result);
    $finish;
  end
endmodule
"""

def run(direct):
    d = tempfile.mkdtemp()
    U.build(ICM, d, 2, direct)
    files = [os.path.join(d, f) for f in open(os.path.join(d, "FILES.txt")).read().split()]
    open(os.path.join(d, "tbd.v"), "w").write(TB)
    o = os.path.join(d, "sim.vvp")
    c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tbd.v")] + files, capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[:800]
    r = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=600)
    return {l.split()[0]: l for l in r.stdout.splitlines() if l.startswith("S")}


def test_sensor_pins_drive_the_design_with_no_esp32():
    out = run(1)
    # location sum of the four tree lanes is 1+2+3+4 = 10; each active sensor adds 8192 to the amount
    assert "led5=0 led4=0 res=0000000a" in out["S00"], out["S00"]
    assert "led5=1 led4=0 res=2000000a" in out["S01"], out["S01"]
    assert "led5=1 led4=1 res=4000000a" in out["S11"], out["S11"]
    assert "led5=0 led4=0 res=0000000a" in out["S00b"], out["S00b"]


def test_without_the_direct_flag_the_pins_do_nothing():
    out = run(0)
    assert all("led5=0" in l and "led4=0" in l for l in out.values()), out
