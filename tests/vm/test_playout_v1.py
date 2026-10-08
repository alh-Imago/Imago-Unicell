"""tests/vm/test_playout_v1.py -- ledger #1036: playout_v1 / capture_v1 (fpga/verilog), a RAM that streams preloaded words into a design's entry ports and a RAM that takes its results.
1. playout alone: every lane gets its own words in order, with random consumer stalls (iverilog).
2. the 4-point Wasserstein-2 engine (ledger #1034) fed ONLY by playout and read ONLY from capture: the squared distances equal the reference. Requires iverilog."""
import json
import os
import random
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
V = os.path.join(ROOT, "fpga", "verilog")
RAMS = [os.path.join(V, "playout_v1.v"), os.path.join(V, "capture_v1.v")]


@pytest.fixture(scope="module")
def tmp():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="playout_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def sim(d, tb_text, files, cycles_limit=2_000_000):
    tb = os.path.join(d, "tb.v")
    open(tb, "w").write(tb_text)
    out = os.path.join(d, "tb.vvp")
    r = subprocess.run(["iverilog", "-g2012", "-o", out, tb] + files, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:1500]
    r = subprocess.run(["vvp", out], capture_output=True, text=True, timeout=3000)
    return r.stdout


def test_playout_gives_every_lane_its_own_words_in_order_under_stalls(tmp):
    lanes, items = 5, 7
    rng = random.Random(3)
    words = [[rng.getrandbits(32) for _ in range(lanes)] for _ in range(items)]
    loads = "\n".join(f"    wr_en=1; wr_addr={k * lanes + j}; wr_data=32'd{w}; @(negedge clk);" for k, row in enumerate(words) for j, w in enumerate(row))
    tb = f"""`timescale 1ns/1ps
module tb;
  reg clk=0, rst=1, wr_en=0, start=0; reg [9:0] wr_addr=0; reg [31:0] wr_data=0; reg [10:0] count={lanes * items};
  wire busy, done; wire [{lanes}*32-1:0] ld; wire [{lanes - 1}:0] lv; reg [{lanes - 1}:0] la=0;
  reg [31:0] lfsr=32'hACE1; integer got=0, cyc=0;
  playout_v1 #(.LANES({lanes}), .AW(10)) dut(.clk(clk), .rst(rst), .wr_en(wr_en), .wr_addr(wr_addr), .wr_data(wr_data), .start(start), .count(count), .busy(busy), .done(done), .lane_data(ld), .lane_valid(lv), .lane_ack(la));
  always #5 clk=~clk;
  integer j;
  always @(posedge clk) begin
    lfsr <= {{lfsr[30:0], lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]}};
    cyc <= cyc + 1;
    la <= lfsr[{lanes - 1}:0] & lfsr[{2 * lanes - 1}:{lanes}];
    for (j=0;j<{lanes};j=j+1) if (lv[j] && la[j]) $display("W %0d %0d", j, ld[j*32 +: 32]);
    if (done) begin $display("DONE %0d", cyc); $finish; end
  end
  initial begin
    repeat(4) @(negedge clk); rst=0; @(negedge clk); cfg_valid=1; @(negedge clk); cfg_valid=0; repeat(3) @(negedge clk);
{loads}
    wr_en=0; @(negedge clk); start=1; @(negedge clk); start=0;
    repeat(200000) @(posedge clk); $display("TIMEOUT"); $finish;
  end
endmodule
"""
    out = sim(tmp, tb, RAMS[:1])
    assert "DONE" in out and "TIMEOUT" not in out, out[-500:]
    got = {j: [] for j in range(lanes)}
    for m in re.finditer(r"^W (\d+) (\d+)$", out, re.M):
        got[int(m.group(1))].append(int(m.group(2)))
    for j in range(lanes):
        assert got[j] == [words[k][j] for k in range(items)], (j, got[j])


LIMIT = int(os.environ.get('PLAYOUT_LIMIT', '120000'))


def test_the_w2_engine_runs_from_playout_to_capture(tmp):
    import ot_w2_v1 as W
    import flex_rtl_harness_v1 as h
    from test_ot_w2_v1 import items, N, T
    g, ent, ex, consts = W.w2_grid(N, T)
    its = items(3, 2)
    d, r = h.build(tmp, "w2_pc", g.records())
    assert r.returncode == 0, r.stderr[:800]
    top = json.load(open(os.path.join(d, "ASSEMBLY.json")))["top"]
    text = open(os.path.join(d, top + ".v")).read()
    ports = sorted(set(re.findall(r"in_(\w+)_data", text)))
    outp = re.findall(r"out_(\w+)_data", text)
    assert len(set(outp)) == 1, outp
    outp = outp[0]
    port_of = lambda cell: re.sub(r"[^A-Za-z0-9_]", "_", cell)
    name_to_lane = {}
    for key, cell in ent.items():
        name_to_lane[key] = cell
    # lane order = the order of the engine's entry ports in the generated top
    import fp_block_runner_v1 as fb
    lane_ports = [fb.port(ent[k]) for k in sorted(ent)]
    assert sorted(lane_ports) == ports
    lanes = len(lane_ports)
    stream = {}
    for (xm, wm), (xn, wn) in its:
        for i in range(N):
            stream.setdefault(f"XM{i}", []).append(xm[i]); stream.setdefault(f"XN{i}", []).append(xn[i])
        for i in range(N - 1):
            stream.setdefault(f"WM{i}", []).append(wm[i]); stream.setdefault(f"WN{i}", []).append(wn[i])
    keys = sorted(ent)
    loads = "\n".join(f"    wr_en=1; wr_addr={k * lanes + j}; wr_data=32'd{stream[key][k]}; @(negedge clk);" for k in range(len(its)) for j, key in enumerate(keys))
    conn_in = ", ".join(f".in_{p}_data(ld[{j}*32 +: 32]), .in_{p}_valid(lv[{j}]), .in_{p}_ack(la[{j}])" for j, p in enumerate(lane_ports))
    tb = f"""`timescale 1ns/1ps
module tb;
  reg clk=0, rst=1, cfg_valid=0, wr_en=0, start=0; reg [9:0] wr_addr=0; reg [31:0] wr_data=0; reg [10:0] count={lanes * len(its)};
  wire busy, done; wire [{lanes}*32-1:0] ld; wire [{lanes - 1}:0] lv, la;
  wire [31:0] od; wire ov, oa; wire [10:0] ccount; reg [9:0] raddr=0; wire [32:0] rdat;
  playout_v1 #(.LANES({lanes}), .AW(10)) P(.clk(clk), .rst(rst), .wr_en(wr_en), .wr_addr(wr_addr), .wr_data(wr_data), .start(start), .count(count), .busy(busy), .done(done), .lane_data(ld), .lane_valid(lv), .lane_ack(la));
  capture_v1 #(.OUTS(1), .AW(10)) C(.clk(clk), .rst(rst), .clear(1'b0), .out_data(od), .out_valid(ov), .out_ack(oa), .count(ccount), .rd_addr(raddr), .rd_data(rdat));
  {top} dut(.clk(clk), .rst(rst), .cfg_valid(cfg_valid), {conn_in}, .out_{outp}_data(od), .out_{outp}_valid(ov), .out_{outp}_ack(oa));
  always #5 clk=~clk;
  integer n;
  initial begin
    repeat(4) @(negedge clk); rst=0; @(negedge clk); cfg_valid=1; @(negedge clk); cfg_valid=0; repeat(3) @(negedge clk);
{loads}
    wr_en=0; @(negedge clk); start=1; @(negedge clk); start=0;
    repeat({LIMIT}) begin @(posedge clk); if (ccount >= {len(its)}) begin repeat(5) @(posedge clk); n={len(its)}; end end
    $display("TIMEOUT count=%0d busy=%0d lv=%b issued=%0d", ccount, busy, lv, P.issued); $finish;
  end
  always @(posedge clk) if (ccount >= {len(its)}) begin
    $display("COUNT %0d", ccount);
    for (n=0; n<{len(its)}; n=n+1) begin raddr = n; repeat(2) @(posedge clk); $display("R %0d", rdat[31:0]); end
    $finish;
  end
endmodule
"""
    files = RAMS + [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".v") and not f.startswith("tb")]
    out = sim(tmp, tb, files)
    assert "TIMEOUT" not in out, out[-600:]
    got = [int(x) for x in re.findall(r"^R (\d+)$", out, re.M)]
    assert got == [W.w2_ref(*a, *b) for a, b in its]
