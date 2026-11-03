"""tests/vm/test_hexn_cross_v2.py - hexn_cross_v2 (shift-register serial->parallel, 3 Nov 2026) gives exactly the outputs of hexn_cross_v1 on random serial streams, including words restarted mid-way and a clear (iverilog)."""
import os, random, shutil, subprocess, tempfile
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); V = os.path.join(ROOT, "sub", "verilog")
pytestmark = pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")


def test_s2p_v2_equals_v1_on_random_streams():
    rnd = random.Random(3); n = 4000; ds = []; fs = []; t = 0
    while t < n:
        if rnd.random() < 0.2: gap = rnd.randrange(1, 40); ds += [rnd.randrange(2) for _ in range(gap)]; fs += [0] * gap; t += gap          # noise without a flag
        ln = rnd.choice([32, 32, 32, 20, 5]); w = [rnd.randrange(2) for _ in range(ln)]; ds += w; fs += [1] + [0] * (ln - 1); t += ln         # full or restarted words
    ds, fs = ds[:n], fs[:n]; clr = [1 if i in (900, 2500) else 0 for i in range(n)]
    L = ["`timescale 1ns/1ps", "module tb; reg clk=0; always #5 clk=~clk; reg ds=0, fs=0, clear=0; wire [31:0] d1, d2; wire v1, v2; integer i; reg [%d:0] D, F, C;" % (n - 1),
         "hexn_s2p_v1 a(.clk(clk),.clear(clear),.ds(ds),.fs(fs),.data(d1),.valid(v1)); hexn_s2p_v2 b(.clk(clk),.clear(clear),.ds(ds),.fs(fs),.data(d2),.valid(v2));",
         "initial begin D = %d'b%s; F = %d'b%s; C = %d'b%s; for (i=0;i<%d;i=i+1) begin ds=D[%d-i]; fs=F[%d-i]; clear=C[%d-i]; @(posedge clk); #1; $display(\"%%0d %%b %%h %%b %%h\", i, v1, d1, v2, d2); end $finish; end endmodule" % (
             n, "".join(map(str, ds)), n, "".join(map(str, fs)), n, "".join(map(str, clr)), n, n - 1, n - 1, n - 1)]
    d = tempfile.mkdtemp(prefix="x2_")
    try:
        open(os.path.join(d, "tb.v"), "w").write("\n".join(L)); o = os.path.join(d, "o")
        c = subprocess.run(["iverilog", "-g2012", "-o", o, os.path.join(d, "tb.v"), os.path.join(V, "hexn_cross_v1.v"), os.path.join(V, "hexn_cross_v2.v")], capture_output=True, text=True); assert c.returncode == 0, c.stderr[:600]
        out = subprocess.run(["vvp", o], capture_output=True, text=True).stdout.splitlines()
    finally:
        shutil.rmtree(d, ignore_errors=True)
    rows = [l.split() for l in out if l and l[0].isdigit()]; assert len(rows) == n
    nvalid = 0
    for i, v1, d1, v2, d2 in rows:
        if v1 == "1" or v2 == "1": nvalid += 1
        assert v1 == v2 and (v1 == "0" or d1 == d2), (i, v1, d1, v2, d2)
    assert nvalid > 20                                                          # the stream really contained complete words
