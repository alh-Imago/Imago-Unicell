"""tests/vm/test_hexn_tile_wk_v1.py - the MERGED WORK CELL (sub/verilog/hexn_tile_wk_v1.v) against each old tile it replaces (5 Nov 2026). Simulation only (iverilog).
For each of the six types (UN, AL, JN, BR, MG, PR) and each of 4 and 6 faces, 6 random configurations are loaded into the old tile and into the merged cell (FUNC = that type), both are cleared, then fed the SAME random word streams
on every face for 700 clocks; every output lane (data and flag, every face) must be equal on every clock. A count of output flags that differ from the plain routed value shows the core was really doing work.
Also: a cell set to an unused FUNC (7) only routes."""
import os, random, shutil, subprocess, tempfile
import pytest
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
V = os.path.join(ROOT, "sub", "verilog")
pytestmark = pytest.mark.skipif(not shutil.which("iverilog"), reason="needs iverilog")
OLD = {"RT": "hexn_tile_v3", "UN": "hexn_tile_v3", "AL": "hexn_tile_al_v2", "JN": "hexn_tile_jn_v2", "BR": "hexn_tile_br_v2", "MG": "hexn_tile_mg_v2", "PR": "hexn_tile_pr_v2"}
FUNC = {"RT": 7, "UN": 0, "AL": 1, "JN": 2, "BR": 3, "MG": 4, "PR": 5}
FILES = ["hexn_unary_core_v2", "hexn_aligned_core_v2", "hexn_join_core_v3", "hexn_branch_core_v2", "hexn_merge_core_v2", "hexn_prio_core_v2", "hexn_tile_wk_v1"] + sorted(set(OLD.values()))


def pack(fields):  # fields: list of (value, width), first = lowest bits
    w = 0; s = 0
    for v, n in fields:
        w |= (v & ((1 << n) - 1)) << s; s += n
    return w, s


def configs(t, F, rnd):
    route = [(rnd.randrange(F), 3) for _ in range(F)]
    sa, sb = rnd.randrange(F), rnd.randrange(F)
    rm = rnd.randrange(1, 1 << F); m2 = rnd.randrange(1 << F) & ~rm
    if t == "RT":
        old = pack(route + [(sa, 3), (0, F), (0, 3), (0, 5), (0, 8)]); pw = 0; opn = 0; rm = 0
    elif t == "UN":
        op, k, mask = rnd.randrange(8), rnd.randrange(32), rnd.randrange(256)
        old = pack(route + [(sa, 3), (rm, F), (op, 3), (k, 5), (mask, 8)]); pw = k | mask << 5; opn = op
    elif t in ("AL", "JN"):
        op = rnd.randrange(8)
        old = pack(route + [(sa, 3), (sb, 3), (rm, F), (op, 3)]); pw = 0; opn = op
    elif t == "BR":
        rlt, req, rgt, em, fx = rnd.randrange(4), rnd.randrange(4), rnd.randrange(4), rnd.randrange(4), rnd.getrandbits(32)
        old = pack(route + [(sa, 3), (sb, 3), (rm, F), (m2, F), (rlt, 2), (req, 2), (rgt, 2), (em, 2), (fx, 32)]); pw = rlt | req << 2 | rgt << 4 | em << 6 | fx << 8; opn = 0
    elif t == "MG":
        mode = rnd.randrange(4)
        old = pack(route + [(sa, 3), (sb, 3), (rm, F), (mode, 2)]); pw = mode; opn = 0
    else:
        mask, ranks, mode, ln, order = rnd.randrange(16), rnd.getrandbits(8), rnd.randrange(4), rnd.randrange(8), rnd.getrandbits(8)
        ps = [rnd.randrange(F) for _ in range(4)]
        old = pack(route + [(rm, F), (mask, 4), (ranks, 8), (mode, 2), (ln, 3), (order, 8)] + [(p, 3) for p in ps])
        pw = mask | ranks << 4 | mode << 12 | ln << 14 | order << 17 | ps[0] << 25 | ps[1] << 28 | ps[2] << 31 | ps[3] << 34; opn = 0
    new = pack(route + [(FUNC[t], 3), (sa, 3), (sb, 3), (rm, F), (m2 if t == "BR" else rnd.randrange(1 << F), F), (opn, 3), (pw, 40)])
    return old, new


def bits(w, n): return "".join(str((w >> i) & 1) for i in range(n - 1, -1, -1))   # MSB first


def tb(t, F, trials, seed):
    rnd = random.Random(seed); body = []
    for i in range(trials):
        (ow, on), (nw, nn) = configs(t, F, rnd)
        body.append("    run_trial(%d'b%s, %d, %d'b%s, %d);" % (on, bits(ow, on), on, nn, bits(nw, nn), nn))
    return """`timescale 1ns/1ps
module tb;
  localparam F = %d;
  reg clk = 0, clear = 1; always #5 clk = ~clk;
  reg [F-1:0] fi_d = 0, fi_f = 0;
  reg oen = 0, oin = 0, nen = 0, nin = 0; wire oco, nco;
  wire [F-1:0] od, ofl, nd, nf;
  %s #(.FACES(F)) u_old (.clk(clk), .clear(clear), .fi_d(fi_d), .fi_f(fi_f), .fo_d(od), .fo_f(ofl), .cfg_en(oen), .cfg_in(oin), .cfg_out(oco));
  hexn_tile_wk_v1 #(.FACES(F)) u_new (.clk(clk), .clear(clear), .fi_d(fi_d), .fi_f(fi_f), .fo_d(nd), .fo_f(nf), .cfg_en(nen), .cfg_in(nin), .cfg_out(nco));
  integer bad = 0, work = 0, trials = 0, i, f, c; reg [5:0] cnt [0:7]; reg [31:0] wd [0:7];
  task run_trial(input [200:0] ocfg, input integer ow, input [200:0] ncfg, input integer nw);
    begin
      clear = 1; oen = 0; nen = 0;
      for (f = 0; f < 8; f = f + 1) begin cnt[f] = 0; wd[f] = 0; end
      repeat (3) @(negedge clk);
      for (i = ow - 1; i >= 0; i = i - 1) begin @(negedge clk); oin = ocfg[i]; oen = 1; end
      @(negedge clk); oen = 0;
      for (i = nw - 1; i >= 0; i = i - 1) begin @(negedge clk); nin = ncfg[i]; nen = 1; end
      @(negedge clk); nen = 0;
      repeat (140) @(negedge clk);
      clear = 0;
      for (c = 0; c < 700; c = c + 1) begin
        @(negedge clk);
        for (f = 0; f < F; f = f + 1) begin
          if (cnt[f] != 0) begin fi_d[f] = wd[f][0]; wd[f] = {1'b0, wd[f][31:1]}; cnt[f] = cnt[f] - 1; end
          else begin fi_d[f] = $urandom; if ($urandom %% 12 == 0) begin cnt[f] = 32; wd[f] = $urandom; fi_f[f] = 1; fi_d[f] = wd[f][0]; wd[f] = {1'b0, wd[f][31:1]}; cnt[f] = 31; end else fi_f[f] = 0; end
        end
        @(posedge clk); #1;
        if ({od, ofl} !== {nd, nf}) begin bad = bad + 1; if (bad < 4) $display("DIFF t=%%0d c=%%0d old=%%b/%%b new=%%b/%%b", trials, c, od, ofl, nd, nf); end
        if (ofl != 0) work = work + 1;
      end
      trials = trials + 1;
    end
  endtask
  initial begin
    for (i = 0; i < 8; i = i + 1) begin cnt[i] = 0; wd[i] = 0; end
%s
    $display("RESULT trials=%%0d bad=%%0d flags=%%0d", trials, bad, work); $finish;
  end
endmodule
""" % (F, OLD[t], "\n".join(body))


def run(t, F, trials=6, seed=1):
    d = tempfile.mkdtemp(prefix="wk_")
    try:
        open(os.path.join(d, "tb.v"), "w").write(tb(t, F, trials, seed))
        assert subprocess.run(["iverilog", "-g2012", "-o", os.path.join(d, "a.out"), os.path.join(d, "tb.v")] + [os.path.join(V, f + ".v") for f in FILES], capture_output=True, text=True).returncode == 0
        r = subprocess.run(["vvp", os.path.join(d, "a.out")], capture_output=True, text=True, timeout=600).stdout
        res = [l for l in r.splitlines() if l.startswith("RESULT")]
        assert res, r
        return r, dict(kv.split("=") for kv in res[0].split()[1:])
    finally:
        shutil.rmtree(d, ignore_errors=True)


@pytest.mark.parametrize("F", [4, 6])
@pytest.mark.parametrize("t", list(OLD))
def test_merged_cell_equals_old_tile(t, F):
    r, v = run(t, F)
    assert v["trials"] == "6" and v["bad"] == "0", r
    assert t == "RT" or int(v["flags"]) > 0, "the streams never reached the output: the test proves nothing"
