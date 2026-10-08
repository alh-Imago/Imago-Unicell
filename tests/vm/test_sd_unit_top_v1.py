"""tests/vm/test_sd_unit_top_v1.py -- ledger #1036: tools/sd_unit_top_v1.py wraps a flex design (an ICM) in the SD-card + ESP32-SPI unit and writes a Tang Nano top + pin file.
Here: a small adder design (X, Y -> adder -> E); the GENERATED unit_top.v is simulated with a simulated SD card and a simulated ESP32 (SPI master): load the operands from the card, play,
read the sums over SPI, save them to the card. Also: the pin file carries the SD and SPI pins; the top synthesises for the Gowin target (yosys). Requires iverilog."""
import json
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
import flex_rtl_harness_v1 as h  # noqa: E402
from test_flex_commutative_tie_v1 import tie  # noqa: E402
from test_spi_bridge_v1 import MASTER  # noqa: E402
import sd_unit_top_v1 as U  # noqa: E402

V = os.path.join(ROOT, "fpga", "verilog")


@pytest.fixture(scope="module")
def built():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="unittop_")
    icm = os.path.join(d, "adder.icm")
    h.IcmV3File(name="adder", records=tie("adder")).save(icm)
    out = os.path.join(d, "out")
    U.build(icm, out, 2)
    yield out
    shutil.rmtree(d, ignore_errors=True)


def test_generated_files_and_pins(built):
    info = json.load(open(os.path.join(built, "lanes.json")))
    assert info["entries"] == ["X", "Y"] and info["exits"] == ["E"] and info["lanes"] == 2
    cst = open(os.path.join(built, "unit_top.cst")).read()
    for name, pin in (("SD_CLK", 83), ("SD_CMD", 82), ("SD_DAT0", 84), ("SD_DAT3", 81), ("SPI_SCLK", 74), ("SPI_CS_N", 73), ("SPI_MOSI", 75), ("SPI_MISO", 76), ("READY", 77), ("BOARD_CLK", 4)):
        assert f'IO_LOC "{name}" {pin};' in cst
    assert 'IO_PORT "SD_DAT0" IO_TYPE=LVCMOS33 PULL_MODE=UP;' in cst
    files = open(os.path.join(built, "FILES.txt")).read().split()
    assert all(os.path.exists(os.path.join(built, f)) for f in files) and "unit_top.v" in files


def test_the_generated_top_does_load_play_read_save(built):
    pairs = [(5, 3), (0xFFFFFFFF, 1), (123456, 654321)]
    words = [w for a, b in pairs for w in (a, b)]                 # lane order = entries X, Y
    init = "\n".join(f"    card.mem[{16 * 512 + 4 * n + k}] = 8'd{(w >> (8 * k)) & 255};" for n, w in enumerate(words) for k in range(4))
    tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0; always #5 clk = ~clk;
  wire SD_CLK, SD_CMD, SD_DAT3, SPI_MISO, READY; wire [5:0] LED_N; wire SD_DAT0;
{MASTER.replace("wire miso;", "wire miso = SPI_MISO;")}
  unit_top T(.BOARD_CLK(clk), .KEY_S1(1'b0), .SD_CLK(SD_CLK), .SD_CMD(SD_CMD), .SD_DAT0(SD_DAT0), .SD_DAT3(SD_DAT3), .SPI_SCLK(sclk), .SPI_CS_N(cs_n), .SPI_MOSI(mosi), .SPI_MISO(SPI_MISO), .READY(READY), .LED_N(LED_N));
  defparam T.INIT_DIV = 3; defparam T.FAST_DIV = 1; defparam T.RSTW = 3;
  sd_card_model_v1 #(.SDHC(1), .BLOCKS(20)) card(.sclk(SD_CLK), .mosi(SD_CMD), .cs_n(SD_DAT3), .miso(SD_DAT0));
  integer j;
  initial begin
    for (j = 0; j < 20*512; j = j + 1) card.mem[j] = 8'h00;
{init}
    repeat (40) @(negedge clk);
    rd_reg(8'd0); $display("ID %h", rv);
    wait_status(32'h1); $display("LED %b READY %b", LED_N, READY);
    wr_reg(8'd3, 32'd16); wr_reg(8'd4, 32'd1); wr_reg(8'd2, 32'h1); wait_status(32'h10);
    wr_reg(8'd5, 32'd{len(words)}); wr_reg(8'd2, 32'h4);
    poll_n = 0; rd_reg(8'd6); while (rv < {len(pairs)} && poll_n < 400) begin rd_reg(8'd6); poll_n = poll_n + 1; end
    rd_words(16'd0, {len(pairs)});
    for (j = 0; j < {len(pairs)}; j = j + 1) $display("S %0d", rbuf[j]);
    wr_reg(8'd2, 32'h10); wr_reg(8'd3, 32'd17); wr_reg(8'd4, 32'd1); wr_reg(8'd2, 32'h2); wait_status(32'h10);
    for (j = 0; j < {len(pairs)}; j = j + 1) $display("C %0d", {{card.mem[17*512 + 4*j + 3], card.mem[17*512 + 4*j + 2], card.mem[17*512 + 4*j + 1], card.mem[17*512 + 4*j]}});
    $finish;
  end
  initial begin repeat (4000000) @(posedge clk); $display("GLOBAL TIMEOUT"); $finish; end
endmodule
"""
    d = tempfile.mkdtemp(prefix="unittopsim_")
    try:
        open(os.path.join(d, "tb.v"), "w").write(tb)
        files = [os.path.join(built, f) for f in open(os.path.join(built, "FILES.txt")).read().split()] + [os.path.join(V, "sd_card_model_v1.v")]
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + files, capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        out = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=1200).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert "GLOBAL TIMEOUT" not in out and "ID 57320001" in out, out[-400:]
    assert "LED 100001 READY 1" in out, out[:300]   # LED4 (MOSI seen), LED3 (SD up), LED2 (SCLK seen), LED1 (CS seen) lit; LED0 heartbeat off this early; LED5 unused
    want = [(a + b) & 0xFFFFFFFF for a, b in pairs]
    assert [int(x) for x in re.findall(r"^S (\d+)$", out, re.M)] == want
    assert [int(x) for x in re.findall(r"^C (\d+)$", out, re.M)] == want


@pytest.mark.skipif(not shutil.which("yosys"), reason="yosys not installed")
def test_the_generated_top_synthesises_for_gowin(built):
    files = [os.path.join(built, f) for f in open(os.path.join(built, "FILES.txt")).read().split()]
    r = subprocess.run(["yosys", "-q", "-p", f"read_verilog -sv {' '.join(files)}; hierarchy -top unit_top; synth_gowin -top unit_top -noiopads; tee -o {built}/stat.txt stat"], capture_output=True, text=True)
    assert r.returncode == 0, (r.stderr or r.stdout)[-800:]
    stat = open(os.path.join(built, "stat.txt")).read()
    assert "DPX9" in stat                                          # the playout / capture RAMs became block RAM
    lut = sum(int(m.group(1)) for m in re.finditer(r"^\s+LUT[1-4]\s+(\d+)", stat, re.M))
    assert 0 < lut < 20736


def test_the_cordic_example_runs_one_item_at_a_time_through_the_generated_top():
    """nano/examples/cordic_z_convergence (36 cells) holds ONE item at a time, so the unit paces it (MAX_OUT = 1): the next angle enters only after the previous result is captured.
    Angles from a simulated card -> generated unit_top -> results read over SPI; they equal FlexGrid's and the repo's anchor (z0 = 50000 -> -404)."""
    from hierarchical_icm_prototype_loader import load_hierarchical, flatten
    import flex_grid_v1 as fg
    path = os.path.join(ROOT, "nano", "examples", "cordic_z_convergence.icm-hier.json")
    d = tempfile.mkdtemp(prefix="unitcordic_")
    try:
        built = os.path.join(d, "out")
        U.build(path, built, 2)
        angles = [50000, -50000, 0, 12345, -12345, 90000]
        records, _ = flatten(load_hierarchical(path))
        ic = next(x for x in records if x.io_name == "z_input")
        oc = next(x for x in records if x.io_name == "z_output")
        s32 = lambda v: (v & 0xFFFFFFFF) - (1 << 32) if v & 0x80000000 else v & 0xFFFFFFFF

        def flex_z(z0):
            g = fg.FlexGrid(records)
            for _ in range(6):
                g.tick()
            g.inject(ic.row, ic.col, z0 & 0xFFFFFFFF)
            for _ in range(200):
                g.tick()
                o = g.cells[(oc.row, oc.col)]
                if o.ram_data_valid:
                    return s32(o.ram_data_reg)
        want = [flex_z(z) for z in angles]
        assert want[0] == -404
        init = "\n".join(f"    card.mem[{16 * 512 + 4 * n + k}] = 8'd{((z & 0xFFFFFFFF) >> (8 * k)) & 255};" for n, z in enumerate(angles) for k in range(4))
        tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0; always #5 clk = ~clk;
  wire SD_CLK, SD_CMD, SD_DAT3, SPI_MISO, READY; wire [5:0] LED_N; wire SD_DAT0;
{MASTER.replace("wire miso;", "wire miso = SPI_MISO;")}
  unit_top T(.BOARD_CLK(clk), .KEY_S1(1'b0), .SD_CLK(SD_CLK), .SD_CMD(SD_CMD), .SD_DAT0(SD_DAT0), .SD_DAT3(SD_DAT3), .SPI_SCLK(sclk), .SPI_CS_N(cs_n), .SPI_MOSI(mosi), .SPI_MISO(SPI_MISO), .READY(READY), .LED_N(LED_N));
  defparam T.INIT_DIV = 3; defparam T.FAST_DIV = 1; defparam T.RSTW = 3;
  sd_card_model_v1 #(.SDHC(1), .BLOCKS(20)) card(.sclk(SD_CLK), .mosi(SD_CMD), .cs_n(SD_DAT3), .miso(SD_DAT0));
  integer j;
  initial begin
    for (j = 0; j < 20*512; j = j + 1) card.mem[j] = 8'h00;
{init}
    repeat (40) @(negedge clk);
    wait_status(32'h1);
    wr_reg(8'd3, 32'd16); wr_reg(8'd4, 32'd1); wr_reg(8'd2, 32'h1); wait_status(32'h10);
    wr_reg(8'd2, 32'h8); wr_reg(8'd8, 32'd1); wr_reg(8'd9, 32'd1);
    wr_reg(8'd5, 32'd{len(angles)}); wr_reg(8'd2, 32'h4);
    poll_n = 0; rd_reg(8'd6); while (rv < {len(angles)} && poll_n < 3000) begin rd_reg(8'd6); poll_n = poll_n + 1; end
    $display("CAP %0d polls %0d", rv, poll_n);
    rd_words(16'd0, {len(angles)});
    for (j = 0; j < {len(angles)}; j = j + 1) $display("S %0d", rbuf[j]);
    $finish;
  end
  initial begin repeat (6000000) @(posedge clk); $display("GLOBAL TIMEOUT"); $finish; end
endmodule
"""
        open(os.path.join(d, "tb.v"), "w").write(tb)
        files = [os.path.join(built, f) for f in open(os.path.join(built, "FILES.txt")).read().split()] + [os.path.join(V, "sd_card_model_v1.v")]
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v")] + files, capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:1500]
        out = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=1800).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    assert "GLOBAL TIMEOUT" not in out, out[-400:]
    got = [s32(int(x)) for x in re.findall(r"^S (\d+)$", out, re.M)]
    assert got == want, (got, want)
