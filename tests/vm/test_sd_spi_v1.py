"""tests/vm/test_sd_spi_v1.py -- ledger #1036: sd_spi_v1 (fpga/verilog), an SD card in SPI mode with RAW 512-byte blocks, against sd_card_model_v1 (a behavioural card, simulation only).
Bring-up (CMD0/8/55+41/58), reading a block into 128 little-endian words, writing 128 words to a block, for a block-addressed (SDHC) and a byte-addressed card. Requires iverilog."""
import os
import re
import shutil
import subprocess
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V = os.path.join(ROOT, "fpga", "verilog")
FILES = [os.path.join(V, "sd_spi_v1.v"), os.path.join(V, "sd_card_model_v1.v")]


def word(block, k):
    return (block * 0x01010101 + k * 0x00010203 + 0x0A0B0C0D) & 0xFFFFFFFF


TB = """`timescale 1ns/1ps
module tb;
  reg clk=0, rst=1, rd_req=0, wr_req=0; reg [31:0] block=0;
  wire sd_clk, sd_mosi, sd_miso, sd_cs_n, ready, error, busy, block_done, w_valid; wire [4:0] err_code; wire [31:0] w_data; wire [6:0] w_index, src_addr;
  reg [31:0] src [0:127]; reg [31:0] src_data=0;
  always @(posedge clk) src_data <= src[src_addr];
  sd_spi_v1 #(.INIT_DIV(3), .FAST_DIV(1)) dut(.clk(clk), .rst(rst), .sd_clk(sd_clk), .sd_mosi(sd_mosi), .sd_miso(sd_miso), .sd_cs_n(sd_cs_n), .ready(ready), .error(error), .err_code(err_code),
      .busy(busy), .rd_req(rd_req), .wr_req(wr_req), .block(block), .block_done(block_done), .w_valid(w_valid), .w_data(w_data), .w_index(w_index), .src_addr(src_addr), .src_data(src_data));
  sd_card_model_v1 #(.SDHC(__SDHC__), .BLOCKS(8), .V1(__V1__)) card(.sclk(sd_clk), .mosi(sd_mosi), .cs_n(sd_cs_n), .miso(sd_miso));
  always #5 clk=~clk;
  integer i, j, k, n;
  always @(posedge clk) if (w_valid) $display("W %0d %0d", w_index, w_data);
  initial begin
    for (i = 0; i < 8; i = i + 1) for (j = 0; j < 128; j = j + 1) begin
      k = i*0 + j;
      card.mem[i*512 + j*4 + 0] = (i*8'h01 + j*8'h03 + 8'h0D) & 8'hFF;
      card.mem[i*512 + j*4 + 1] = (i*8'h01 + j*8'h02 + 8'h0C) & 8'hFF;
      card.mem[i*512 + j*4 + 2] = (i*8'h01 + j*8'h01 + 8'h0B) & 8'hFF;
      card.mem[i*512 + j*4 + 3] = (i*8'h01 + j*8'h00 + 8'h0A) & 8'hFF;
    end
    for (j = 0; j < 128; j = j + 1) src[j] = 32'hC0DE0000 + j*32'h00010001;
    repeat(4) @(negedge clk); rst = 0;
    n = 0; while (!ready && !error && n < 400000) begin @(posedge clk); n = n + 1; end
    $display("READY %0d ERR %0d CODE %0d", ready, error, err_code);
    @(negedge clk); block = 6; rd_req = 1; @(negedge clk); rd_req = 0;
    n = 0; while (!block_done && !error && n < 400000) begin @(posedge clk); n = n + 1; end
    $display("RDDONE %0d ERR %0d CODE %0d", block_done, error, err_code);
    @(negedge clk); @(negedge clk); block = 3; wr_req = 1; @(negedge clk); wr_req = 0;
    n = 0; while (!block_done && !error && n < 400000) begin @(posedge clk); n = n + 1; end
    $display("WRDONE %0d ERR %0d CODE %0d", block_done, error, err_code);
    for (j = 0; j < 128; j = j + 1)
      $display("M %0d %0d", j, {card.mem[3*512 + j*4 + 3], card.mem[3*512 + j*4 + 2], card.mem[3*512 + j*4 + 1], card.mem[3*512 + j*4 + 0]});
    $finish;
  end
endmodule
"""


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="sdspi_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.mark.parametrize("sdhc", [1, 0])
def test_bring_up_read_a_block_and_write_a_block(tmp, sdhc):
    tb = os.path.join(tmp, f"tb{sdhc}.v")
    open(tb, "w").write(TB.replace("__SDHC__", str(sdhc)).replace("__V1__", str(1 - sdhc)))
    out_f = os.path.join(tmp, f"tb{sdhc}.vvp")
    r = subprocess.run(["iverilog", "-g2012", "-o", out_f, tb] + FILES, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:1500]
    out = subprocess.run(["vvp", out_f], capture_output=True, text=True, timeout=600).stdout
    assert "READY 1 ERR 0" in out, out[:400]
    assert "RDDONE 1 ERR 0" in out, out[:600]
    assert "WRDONE 1 ERR 0" in out, out[:900]
    got = {int(a): int(b) for a, b in re.findall(r"^W (\d+) (\d+)$", out, re.M)}
    # the card's bytes for block 6, word j: b0=(6+3j+13) b1=(6+2j+12) b2=(6+j+11) b3=(6+10), little endian
    exp = {j: ((6 + 10) & 255) << 24 | ((6 + j + 11) & 255) << 16 | ((6 + 2 * j + 12) & 255) << 8 | ((6 + 3 * j + 13) & 255) for j in range(128)}
    assert got == exp
    wrote = {int(a): int(b) for a, b in re.findall(r"^M (\d+) (\d+)$", out, re.M)}
    assert wrote == {j: (0xC0DE0000 + j * 0x00010001) & 0xFFFFFFFF for j in range(128)}


def test_the_w2_unit_card_to_card(tmp):
    """The small unit, all in simulation: input words on the SD card (block 0) -> sd_stream -> playout RAM -> the 4-point W2 engine -> capture RAM -> sd_stream -> the card (block 1).
    The two squared distances read back from the card equal the reference."""
    import json
    import sys
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import flex_rtl_harness_v1 as h
    import fp_block_runner_v1 as fb
    import ot_w2_v1 as W
    from test_ot_w2_v1 import items, N, T
    g, ent, ex, consts = W.w2_grid(N, T)
    its = items(3, 1)                                       # 1 + the identical pair = 2 items
    d, r = h.build(tmp, "w2_sd", g.records())
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
    words = [stream[key][k] for k in range(len(its)) for key in keys]               # item-major, lane-minor
    card_init = "\n".join(f"    card.mem[{4 * n + b}] = 8'd{(w >> (8 * b)) & 255};" for n, w in enumerate(words) for b in range(4))
    conn_in = ", ".join(f".in_{p}_data(ld[{j}*32 +: 32]), .in_{p}_valid(lv[{j}]), .in_{p}_ack(la[{j}])" for j, p in enumerate(lane_ports))
    tb = f"""`timescale 1ns/1ps
module tb;
  reg clk=0, rst=1, cfg_valid=0, start=0, cmd_load=0, cmd_save=0; reg [31:0] start_block=0; reg [15:0] nblocks=1;
  wire sd_clk, sd_mosi, sd_miso, sd_cs_n, busy, done, ready, error; wire [4:0] err_code;
  wire pl_wr_en; wire [9:0] pl_wr_addr; wire [31:0] pl_wr_data; wire [9:0] cap_rd_addr; wire [32:0] rdat;
  wire pbusy, pdone; wire [{lanes}*32-1:0] ld; wire [{lanes - 1}:0] lv, la; wire [31:0] od; wire ov, oa; wire [10:0] ccount;
  sd_stream_v1 #(.AW(10), .INIT_DIV(3), .FAST_DIV(1)) SS(.clk(clk), .rst(rst), .sd_clk(sd_clk), .sd_mosi(sd_mosi), .sd_miso(sd_miso), .sd_cs_n(sd_cs_n),
      .cmd_load(cmd_load), .cmd_save(cmd_save), .start_block(start_block), .nblocks(nblocks), .busy(busy), .done(done), .ready(ready), .error(error), .err_code(err_code),
      .pl_wr_en(pl_wr_en), .pl_wr_addr(pl_wr_addr), .pl_wr_data(pl_wr_data), .cap_rd_addr(cap_rd_addr), .cap_rd_data(rdat[31:0]));
  sd_card_model_v1 #(.SDHC(1), .BLOCKS(4)) card(.sclk(sd_clk), .mosi(sd_mosi), .cs_n(sd_cs_n), .miso(sd_miso));
  playout_v1 #(.LANES({lanes}), .AW(10)) P(.clk(clk), .rst(rst), .wr_en(pl_wr_en), .wr_addr(pl_wr_addr), .wr_data(pl_wr_data), .start(start), .count(11'd{lanes * len(its)}), .busy(pbusy), .done(pdone), .lane_data(ld), .lane_valid(lv), .lane_ack(la));
  capture_v1 #(.OUTS(1), .AW(10)) C(.clk(clk), .rst(rst), .clear(1'b0), .out_data(od), .out_valid(ov), .out_ack(oa), .count(ccount), .rd_addr(cap_rd_addr), .rd_data(rdat));
  {top} dut(.clk(clk), .rst(rst), .cfg_valid(cfg_valid), {conn_in}, .out_{outp}_data(od), .out_{outp}_valid(ov), .out_{outp}_ack(oa));
  always #5 clk=~clk;
  integer n, j;
  initial begin
    for (j = 0; j < 4*512; j = j + 1) card.mem[j] = 8'h00;
{card_init}
    repeat(4) @(negedge clk); rst=0; @(negedge clk); cfg_valid=1; @(negedge clk); cfg_valid=0;
    n = 0; while (!ready && !error && n < 300000) begin @(negedge clk); n = n + 1; end
    $display("READY %0d ERR %0d", ready, error);
    start_block = 0; nblocks = 1; cmd_load = 1; @(negedge clk); cmd_load = 0;
    n = 0; while (!done && !error && n < 300000) begin @(negedge clk); n = n + 1; end
    $display("LOADED %0d ERR %0d", done, error);
    repeat(3) @(negedge clk); start = 1; @(negedge clk); start = 0;
    n = 0; while (ccount < {len(its)} && n < {{LIMIT}}) begin @(negedge clk); n = n + 1; end
    $display("CAPTURED %0d", ccount);
    repeat(4) @(negedge clk);
    start_block = 1; nblocks = 1; cmd_save = 1; @(negedge clk); cmd_save = 0;
    n = 0; while (!done && !error && n < 300000) begin @(negedge clk); n = n + 1; end
    $display("SAVED %0d ERR %0d", done, error);
    for (j = 0; j < {len(its)}; j = j + 1) $display("R %0d", {{card.mem[512 + 4*j + 3], card.mem[512 + 4*j + 2], card.mem[512 + 4*j + 1], card.mem[512 + 4*j]}});
    $finish;
  end
endmodule
""".replace("{LIMIT}", os.environ.get("PLAYOUT_LIMIT", "120000"))
    files = FILES + [os.path.join(V, "playout_v1.v"), os.path.join(V, "capture_v1.v"), os.path.join(V, "sd_stream_v1.v")] + [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".v") and not f.startswith("tb")]
    tbp = os.path.join(tmp, "tb_unit.v")
    open(tbp, "w").write(tb)
    o = os.path.join(tmp, "tb_unit.vvp")
    c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, tbp] + files, capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[:1500]
    out = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=3000).stdout
    assert "READY 1 ERR 0" in out and "LOADED 1 ERR 0" in out, out[:500]
    assert f"CAPTURED {len(its)}" in out, out[:600]
    assert "SAVED 1 ERR 0" in out, out[:800]
    got = [int(x) for x in re.findall(r"^R (\d+)$", out, re.M)]
    assert got == [W.w2_ref(*a, *b) for a, b in its]
