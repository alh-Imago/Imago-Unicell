"""tests/vm/test_hexn_ramcell_model_v1.py -- the Python twin of the RAM-routing cell (tools/hexn_ramcell_model_v1.py) against the RTL (sub/verilog/hexn_ramroute_v5.v), clock by clock, on random stimulus:
random data bits, word-start flags at random times (including a second flag in the middle of a word), hold mode with random delays and repeat mode. Needs iverilog."""
import os, random, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
from hexn_ramcell_model_v1 import RamCell

TB = """`timescale 1ns/1ps
module tb;
  reg clk = 0; reg [5:0] fi = 0; wire [5:0] fo; reg cfg_en = 0, cfg_in = 0; wire cfg_out;
  hexn_ramroute_v5 dut (.clk(clk), .fi(fi), .fo(fo), .cfg_en(cfg_en), .cfg_in(cfg_in), .cfg_out(cfg_out));
  reg [1:0] stim [0:%(n)d]; reg [35:0] cw; integer k;
  initial begin
    $readmemb("%(stim)s", stim);
    cw = 0; cw[17:0] = {3'd5,3'd4,3'd3,3'd2,3'd1,3'd0}; cw[19:18] = %(mode)d; cw[22:20] = 3'd0; cw[25:23] = 3'd3; cw[32:26] = %(dly)d; cw[35:33] = 3'd1;
    for (k = 35; k >= 0; k = k - 1) begin #5 clk = 0; cfg_en = 1; cfg_in = cw[k]; #5 clk = 1; end
    #5 clk = 0; cfg_en = 0; #5 clk = 1;
    for (k = 0; k < %(n)d; k = k + 1) begin #5 clk = 0; fi[0] = stim[k][0]; fi[1] = stim[k][1]; #5 clk = 1; #1 $display("O %%b", fo[3]); end
    $finish;
  end
endmodule
"""

def one(mode, dly, seed, n=400):
    rnd = random.Random(seed)
    din = [rnd.randrange(2) for _ in range(n)]
    ws = [0] * n
    t = rnd.randrange(0, 5)
    while t < n:
        ws[t] = 1; t += rnd.choice([20, 40, 70, 100, 150])      # includes flags inside a word (20 < 32)
    d = tempfile.mkdtemp(prefix="hexnrc_")
    try:
        with open(os.path.join(d, "stim.txt"), "w") as f:
            f.write("\n".join("%d%d" % (ws[i], din[i]) for i in range(n)) + "\n")
        open(os.path.join(d, "tb.v"), "w").write(TB % dict(n=n, stim=os.path.join(d, "stim.txt"), mode=mode, dly=dly))
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v"), os.path.join(ROOT, "sub", "verilog", "hexn_ramroute_v5.v")], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr
        r = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=300).stdout
    finally:
        shutil.rmtree(d, ignore_errors=True)
    rtl = [None if l.split()[1] == "x" else int(l.split()[1]) for l in r.splitlines() if l.startswith("O ")]   # x = a memory cell never written yet (the RTL memory is not reset); the twin shows 0
    cell = RamCell(mode, dly); py = []
    for i in range(n):
        py.append(cell.step(din[i], ws[i]))
    # the RTL output of the first edge after the flag-less start: the model returns q_old each edge, as the RTL does. The config load took a few clocks in mode != 0 with ws = 0, so the cell state differs only in cnt, which saturates: same.
    return rtl, py

def test_ramcell_model_matches_rtl():
    assert shutil.which("iverilog"), "iverilog is REQUIRED"
    for seed, (mode, dly) in enumerate([(1, 1), (1, 10), (1, 31), (1, 32), (1, 50), (1, 126), (2, 0), (2, 0)]):
        rtl, py = one(mode, dly, seed)
        assert len(rtl) == len(py) == 400
        bad = [i for i in range(400) if rtl[i] is not None and rtl[i] != py[i]]
        assert sum(1 for v in rtl if v is None) < 40, 'too many unknown outputs'
        assert not bad, "mode %d dly %d: %d clocks differ, first at %d" % (mode, dly, len(bad), bad[0])
