"""tests/vm/test_spi_bridge_v1.py -- ledger #1036: spi_bridge_v1 + sd_unit_v1 driven by a simulated ESP32 (an SPI master) around a tiny two-lane adder design.
Registers (ID, scratch, status), words written straight into the playout RAM over SPI and results read back over SPI, and the SD path (load from a simulated card, play, save back to the card).
SCLK is clk/16 (the bridge's stated limit). Requires iverilog."""
import os
import re
import shutil
import subprocess
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V = os.path.join(ROOT, "fpga", "verilog")
UNIT = ["sd_unit_v1.v", "sd_stream_v1.v", "sd_spi_v1.v", "spi_bridge_v1.v", "playout_v1.v", "capture_v1.v", "sd_card_model_v1.v"]

ADD2 = """module add2(input [63:0] ld, input [1:0] lv, output [1:0] la, output [31:0] od, output ov, input oa);
  assign ov = &lv; assign od = ld[31:0] + ld[63:32]; assign la = {2{ov & oa}};
endmodule
"""

# the simulated ESP32: SPI mode 0, half period 8 clocks (SCLK = clk/16)
MASTER = """
  reg sclk = 0, cs_n = 1, mosi = 0; wire miso;
  reg [7:0] rxb; reg [31:0] rv; reg [31:0] wbuf [0:15]; reg [31:0] rbuf [0:15];
  integer sp_i, sp_k;
  task spi_byte(input [7:0] tx);
    begin
      for (sp_i = 7; sp_i >= 0; sp_i = sp_i - 1) begin
        mosi = tx[sp_i]; repeat (8) @(negedge clk);
        sclk = 1; rxb = {rxb[6:0], miso}; repeat (8) @(negedge clk);
        sclk = 0;
      end
    end
  endtask
  task begin_t; begin repeat (4) @(negedge clk); cs_n = 0; repeat (4) @(negedge clk); end endtask
  task end_t;   begin repeat (4) @(negedge clk); cs_n = 1; repeat (4) @(negedge clk); end endtask
  task wr_reg(input [7:0] a, input [31:0] d);
    begin begin_t; spi_byte(8'h01); spi_byte(a); spi_byte(d[31:24]); spi_byte(d[23:16]); spi_byte(d[15:8]); spi_byte(d[7:0]); end_t; end
  endtask
  task rd_reg(input [7:0] a);
    begin begin_t; spi_byte(8'h02); spi_byte(a); spi_byte(8'h00);
      spi_byte(8'h00); rv[31:24] = rxb; spi_byte(8'h00); rv[23:16] = rxb; spi_byte(8'h00); rv[15:8] = rxb; spi_byte(8'h00); rv[7:0] = rxb; end_t; end
  endtask
  task wr_words(input [15:0] a, input integer n);
    begin begin_t; spi_byte(8'h03); spi_byte(a[15:8]); spi_byte(a[7:0]);
      for (sp_k = 0; sp_k < n; sp_k = sp_k + 1) begin spi_byte(wbuf[sp_k][31:24]); spi_byte(wbuf[sp_k][23:16]); spi_byte(wbuf[sp_k][15:8]); spi_byte(wbuf[sp_k][7:0]); end
      end_t; end
  endtask
  task rd_words(input [15:0] a, input integer n);
    begin begin_t; spi_byte(8'h04); spi_byte(a[15:8]); spi_byte(a[7:0]); spi_byte(8'h00);
      for (sp_k = 0; sp_k < n; sp_k = sp_k + 1) begin
        spi_byte(8'h00); rbuf[sp_k][31:24] = rxb; spi_byte(8'h00); rbuf[sp_k][23:16] = rxb; spi_byte(8'h00); rbuf[sp_k][15:8] = rxb; spi_byte(8'h00); rbuf[sp_k][7:0] = rxb; end
      end_t; end
  endtask
  integer poll_n;
  task wait_status(input [31:0] mask);       // poll STATUS until (status & mask) == mask
    begin poll_n = 0; rd_reg(8'd1);
      while ((rv & mask) != mask && poll_n < 400) begin rd_reg(8'd1); poll_n = poll_n + 1; end
    end
  endtask
"""


def run(tmp, name, body, extra_decl="", card_init="", cycles=3_000_000):
    tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1;
  wire sd_clk, sd_mosi, sd_miso, sd_cs_n, ready_line;
  wire [63:0] ld; wire [1:0] lv, la; wire [31:0] od; wire ov, oa;
  always #5 clk = ~clk;
{MASTER}
{extra_decl}
  sd_unit_v1 #(.LANES(2), .OUTS(1), .AW(10), .INIT_DIV(3), .FAST_DIV(1)) U(.clk(clk), .rst(rst), .sd_clk(sd_clk), .sd_mosi(sd_mosi), .sd_miso(sd_miso), .sd_cs_n(sd_cs_n),
      .spi_sclk(sclk), .spi_cs_n(cs_n), .spi_mosi(mosi), .spi_miso(miso), .lane_data(ld), .lane_valid(lv), .lane_ack(la), .out_data(od), .out_valid(ov), .out_ack(oa), .ready_line(ready_line));
  add2 D(.ld(ld), .lv(lv), .la(la), .od(od), .ov(ov), .oa(oa));
  sd_card_model_v1 #(.SDHC(1), .BLOCKS(4)) card(.sclk(sd_clk), .mosi(sd_mosi), .cs_n(sd_cs_n), .miso(sd_miso));
  integer j;
  initial begin
    for (j = 0; j < 4*512; j = j + 1) card.mem[j] = 8'h00;
{card_init}
    repeat (6) @(negedge clk); rst = 0; repeat (6) @(negedge clk);
{body}
    $finish;
  end
  initial begin repeat ({cycles}) @(posedge clk); $display("GLOBAL TIMEOUT"); $finish; end
endmodule
"""
    d = os.path.join(tmp, name)
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "add2.v"), "w").write(ADD2)
    open(os.path.join(d, "tb.v"), "w").write(tb)
    o = os.path.join(d, "o.vvp")
    r = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v"), os.path.join(d, "add2.v")] + [os.path.join(V, f) for f in UNIT], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:1500]
    return subprocess.run(["vvp", o], capture_output=True, text=True, timeout=1200).stdout


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="spibr_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def test_registers_over_spi(tmp):
    out = run(tmp, "regs", """
    rd_reg(8'd0); $display("ID %h", rv);
    wr_reg(8'd7, 32'hDEADBEEF); rd_reg(8'd7); $display("SCR %h", rv);
    wr_reg(8'd3, 32'h00001234); rd_reg(8'd3); $display("SB %h", rv);
    wr_reg(8'd4, 32'h00000005); rd_reg(8'd4); $display("NB %h", rv);
    wr_reg(8'd5, 32'h0000000C); rd_reg(8'd5); $display("PC %h", rv);
    wait_status(32'h1); $display("STATUS %h polls %0d", rv, poll_n);
    rd_reg(8'd6); $display("CAP %h", rv);
    rd_reg(8'd10); $display("DID %h", rv);
    """)
    assert "DID 00000000" in out, "register 10 reads 0 when no design ID is set"
    assert "ID 57320001" in out and "SCR deadbeef" in out and "SB 00001234" in out and "NB 00000005" in out and "PC 0000000c" in out, out[:600]
    m = re.search(r"STATUS ([0-9a-f]{8})", out)
    assert m and int(m.group(1), 16) & 1, "the SD card must come up (ready bit)"
    assert "CAP 00000000" in out


def test_words_in_over_spi_results_out_over_spi(tmp):
    a = [5, 0xFFFFFFFF, 0x12345678, 7]
    b = [3, 1, 0x9ABCDEF0, 0]
    words = [w for pair in zip(a, b) for w in pair]
    body = "\n".join(f"    wbuf[{k}] = 32'd{w};" for k, w in enumerate(words)) + f"""
    wr_words(16'd0, {len(words)});
    wr_reg(8'd5, 32'd{len(words)});
    wr_reg(8'd2, 32'h4);
    poll_n = 0; rd_reg(8'd6); while (rv < {len(a)} && poll_n < 400) begin rd_reg(8'd6); poll_n = poll_n + 1; end
    $display("CAP %0d", rv);
    rd_words(16'd0, {len(a)});
    for (j = 0; j < {len(a)}; j = j + 1) $display("R %0d", rbuf[j]);
    wait_status(32'h20); $display("PLAYDONE %h", rv);
    """
    out = run(tmp, "words", body)
    assert f"CAP {len(a)}" in out, out[:500]
    got = [int(x) for x in re.findall(r"^R (\d+)$", out, re.M)]
    assert got == [(x + y) & 0xFFFFFFFF for x, y in zip(a, b)]
    m = re.search(r"PLAYDONE ([0-9a-f]{8})", out)
    assert m and int(m.group(1), 16) & 0x20, "the play-done sticky bit must be set"


def test_sd_load_play_save_all_over_spi(tmp):
    a = [100, 200, 300]
    b = [1, 2, 3]
    words = [w for pair in zip(a, b) for w in pair]
    init = "\n".join(f"    card.mem[{4 * n + k}] = 8'd{(w >> (8 * k)) & 255};" for n, w in enumerate(words) for k in range(4))
    body = f"""
    wait_status(32'h1);
    wr_reg(8'd3, 32'd0); wr_reg(8'd4, 32'd1); wr_reg(8'd2, 32'h1); wait_status(32'h10); $display("LOADED %h", rv);
    wr_reg(8'd5, 32'd{len(words)}); wr_reg(8'd2, 32'h4);
    poll_n = 0; rd_reg(8'd6); while (rv < {len(a)} && poll_n < 600) begin rd_reg(8'd6); poll_n = poll_n + 1; end
    wr_reg(8'd3, 32'd1); wr_reg(8'd4, 32'd1); wr_reg(8'd2, 32'h2); wait_status(32'h10); $display("SAVED %h", rv);
    for (j = 0; j < {len(a)}; j = j + 1) $display("C %0d", {{card.mem[512 + 4*j + 3], card.mem[512 + 4*j + 2], card.mem[512 + 4*j + 1], card.mem[512 + 4*j]}});
    """
    out = run(tmp, "sd", body, card_init=init, cycles=6_000_000)
    assert "GLOBAL TIMEOUT" not in out, out[-300:]
    m = re.search(r"LOADED ([0-9a-f]{8})", out)
    assert m and int(m.group(1), 16) & 0x10, out[:400]
    m = re.search(r"SAVED ([0-9a-f]{8})", out)
    assert m and int(m.group(1), 16) & 0x10, out[:600]
    assert [int(x) for x in re.findall(r"^C (\d+)$", out, re.M)] == [x + y for x, y in zip(a, b)]


def test_the_w2_engine_driven_only_by_a_simulated_esp32(tmp):
    """The whole small unit as it would be used: the 4-point W2 engine behind sd_unit_v1; a simulated ESP32 over SPI loads blocks 16.. from the card, starts the play, waits for the results,
    saves them to block 17, and reads them back over SPI. Blocks 16/17 (not 0) because a real FAT32 card keeps its partition table in block 0."""
    import json
    import sys
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import flex_rtl_harness_v1 as h
    import fp_block_runner_v1 as fb
    import ot_w2_v1 as W
    from test_ot_w2_v1 import items, N, T
    g, ent, ex, consts = W.w2_grid(N, T)
    its = items(3, 1)
    d, r = h.build(tmp, "w2_spi", g.records())
    assert r.returncode == 0, r.stderr[:800]
    top = json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"]
    text = open(os.path.join(d, top + ".v")).read()
    outp = set(re.findall(r"out_(\w+)_data", text))
    assert len(outp) == 1
    outp = outp.pop()
    keys = sorted(ent)
    lane_ports = [fb.port(ent[k]) for k in keys]
    lanes = len(lane_ports)
    stream = {}
    for (xm, wm), (xn, wn) in its:
        for i in range(N):
            stream.setdefault(f"XM{i}", []).append(xm[i]); stream.setdefault(f"XN{i}", []).append(xn[i])
        for i in range(N - 1):
            stream.setdefault(f"WM{i}", []).append(wm[i]); stream.setdefault(f"WN{i}", []).append(wn[i])
    words = [stream[key][k] for k in range(len(its)) for key in keys]
    base = 16 * 512
    card_init = "\n".join(f"    card.mem[{base + 4 * n + b}] = 8'd{(w >> (8 * b)) & 255};" for n, w in enumerate(words) for b in range(4))
    conn_in = ", ".join(f".in_{p}_data(ld[{j}*32 +: 32]), .in_{p}_valid(lv[{j}]), .in_{p}_ack(la[{j}])" for j, p in enumerate(lane_ports))
    tb = f"""`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, cfg_valid = 0;
  wire sd_clk, sd_mosi, sd_miso, sd_cs_n, ready_line;
  wire [{lanes}*32-1:0] ld; wire [{lanes - 1}:0] lv, la; wire [31:0] od; wire ov, oa;
  always #5 clk = ~clk;
{MASTER}
  sd_unit_v1 #(.LANES({lanes}), .OUTS(1), .AW(10), .INIT_DIV(3), .FAST_DIV(1)) U(.clk(clk), .rst(rst), .sd_clk(sd_clk), .sd_mosi(sd_mosi), .sd_miso(sd_miso), .sd_cs_n(sd_cs_n),
      .spi_sclk(sclk), .spi_cs_n(cs_n), .spi_mosi(mosi), .spi_miso(miso), .lane_data(ld), .lane_valid(lv), .lane_ack(la), .out_data(od), .out_valid(ov), .out_ack(oa), .ready_line(ready_line));
  {top} dut(.clk(clk), .rst(rst), .cfg_valid(cfg_valid), {conn_in}, .out_{outp}_data(od), .out_{outp}_valid(ov), .out_{outp}_ack(oa));
  sd_card_model_v1 #(.SDHC(1), .BLOCKS(20)) card(.sclk(sd_clk), .mosi(sd_mosi), .cs_n(sd_cs_n), .miso(sd_miso));
  integer j;
  initial begin
    for (j = 0; j < 20*512; j = j + 1) card.mem[j] = 8'h00;
{card_init}
    repeat (6) @(negedge clk); rst = 0; @(negedge clk); cfg_valid = 1; @(negedge clk); cfg_valid = 0; repeat (6) @(negedge clk);
    rd_reg(8'd0); $display("ID %h", rv);
    wait_status(32'h1);
    wr_reg(8'd3, 32'd16); wr_reg(8'd4, 32'd1); wr_reg(8'd2, 32'h1); wait_status(32'h10); $display("LOADED %h", rv);
    wr_reg(8'd5, 32'd{lanes * len(its)}); wr_reg(8'd2, 32'h4);
    poll_n = 0; rd_reg(8'd6); while (rv < {len(its)} && poll_n < 2000) begin rd_reg(8'd6); poll_n = poll_n + 1; end
    $display("CAP %0d polls %0d", rv, poll_n);
    rd_words(16'd0, {len(its)});
    for (j = 0; j < {len(its)}; j = j + 1) $display("S %0d", rbuf[j]);
    wr_reg(8'd2, 32'h10);
    wr_reg(8'd3, 32'd17); wr_reg(8'd4, 32'd1); wr_reg(8'd2, 32'h2); wait_status(32'h10); $display("SAVED %h", rv);
    for (j = 0; j < {len(its)}; j = j + 1) $display("C %0d", {{card.mem[17*512 + 4*j + 3], card.mem[17*512 + 4*j + 2], card.mem[17*512 + 4*j + 1], card.mem[17*512 + 4*j]}});
    $finish;
  end
  initial begin repeat (2500000) @(posedge clk); $display("GLOBAL TIMEOUT"); $finish; end
endmodule
"""
    tbp = os.path.join(tmp, "tb_w2spi.v")
    open(tbp, "w").write(tb)
    o = os.path.join(tmp, "tb_w2spi.vvp")
    files = [os.path.join(V, f) for f in UNIT] + [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".v") and not f.startswith("tb")]
    c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, tbp] + files, capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[:1500]
    out = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=3000).stdout
    assert "GLOBAL TIMEOUT" not in out, out[-400:]
    assert "ID 57320001" in out
    ref = [W.w2_ref(*a, *b) for a, b in its]
    assert [int(x) for x in re.findall(r"^S (\d+)$", out, re.M)] == ref, out[-600:]
    assert [int(x) for x in re.findall(r"^C (\d+)$", out, re.M)] == ref
