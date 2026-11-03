"""tests/vm/test_hexn_latch_card_v1.py -- the LATCH tile v2 (one word per pulse, 3 Nov 2026): the word-level LatchTwin (tools/hexn_twins_v2.py, used by the planner v20 and the VM v5)
against the RTL (hexn_tile_lt_v2 on hexn_latch_core_v3), tick for tick, on random pulse schedules on the W (set), N (clear) and S (toggle) faces; plus the planner's latch designs."""
import os, random, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import hexn_twins_v2 as T
import pytest


def _rtl(pulses, nclk):
    """pulses {tick: (set, clear, toggle)} -> list of (tick, bit) at the tile's E data lane when the flag is high (tick = clock count from 1)"""
    d = tempfile.mkdtemp(prefix="lt2_")
    try:
        L = ["`timescale 1ns/1ps", "module tb; reg clk=0; always #5 clk=~clk; reg clear=0,cfg_en=0,cfg_in=0; reg [3:0] fd=0, ff=0; wire [3:0] od, of; wire co; integer t=0, i;",
             "hexn_tile_lt_v2 #(.FACES(4)) u (.clk(clk),.clear(clear),.fi_d(fd),.fi_f(ff),.fo_d(od),.fo_f(of),.cfg_en(cfg_en),.cfg_in(cfg_in),.cfg_out(co));",
             "reg [24:0] word; initial begin word=0; word[12+:3]=3; word[15+:3]=0; word[18+:3]=2; word[21+:4]=4'b0010; @(posedge clk); cfg_en=1; for(i=24;i>=0;i=i-1) begin cfg_in=word[i]; @(posedge clk); #1; end cfg_en=0; end",
             "reg go=0; initial begin repeat (40) @(posedge clk); go=1; end",
             "always @(posedge clk) if (go) begin t<=t+1; if (of[1]) $display(\"E %0d %0d\", t+1, od[1]); end",
             "always @(posedge clk) if (go) case (t+1)"]
        for tk, (s, c, g) in sorted(pulses.items()):
            L.append("  %d: begin ff[3] <= %d; ff[0] <= %d; ff[2] <= %d; end" % (tk, s, c, g))
            L.append("  %d: begin ff <= 0; end" % (tk + 1)) if (tk + 1) not in pulses else None
        L += ["  default: ff <= ff; endcase", "initial begin #%d $finish; end endmodule" % ((nclk + 60) * 10)]
        tb = os.path.join(d, "tb.v"); open(tb, "w").write("\n".join(x for x in L if x))
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-o", o, tb, os.path.join(ROOT, "sub/verilog/hexn_tile_lt_v2.v"), os.path.join(ROOT, "sub/verilog/hexn_latch_core_v3.v")], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr
        out = subprocess.run(["vvp", o], capture_output=True, text=True).stdout
        return [(int(l.split()[1]), int(l.split()[2])) for l in out.splitlines() if l.startswith("E ")]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _twin(pulses, nclk):
    tw = T.LatchTwin(); out = []; pend = None
    for t in range(1, nclk + 1):
        s, c, g = pulses.get(t, (0, 0, 0))
        o = tw.step(t, {"W": (0, s), "N": (0, c), "S": (0, g)})
        if o["E"][1]: out.append((t + 2, o["E"][0]))      # +1: the twin's outputs are seen by the NEXT tick; +1: this testbench sets a pulse at the clock BEFORE the tile sees it (a constant shift of the whole schedule, so the comparison is of the spacing and the words)
    return out


@pytest.mark.parametrize("seed", [1, 2, 3, 4])
def test_latch_twin_equals_rtl(seed):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    rnd = random.Random(seed); pulses = {}; t = 5; nclk = 0
    for _ in range(10):
        t += rnd.choice([1, 2, 3, 30, 31, 32, 33, 40, 70])
        pulses[t] = rnd.choice([(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1), (1, 1, 1)])
        t += 1
    nclk = t + 60
    a = _rtl(pulses, nclk); b = _twin(pulses, nclk)
    assert a == b, (pulses, a, b)
    assert a, "no word at all"


def test_latch_tile_v2_testbench_passes():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    d = tempfile.mkdtemp(prefix="lt2tb_")
    try:
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-o", o, os.path.join(ROOT, "tests/hexn_tile_lt_v2_tb.v"), os.path.join(ROOT, "sub/verilog/hexn_tile_lt_v2.v"), os.path.join(ROOT, "sub/verilog/hexn_latch_core_v3.v")], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr
        out = subprocess.run(["vvp", o], capture_output=True, text=True).stdout
        assert "PASS" in out and "FAIL" not in out, out
    finally:
        shutil.rmtree(d, ignore_errors=True)


def test_planner_latch_designs_and_vm():
    import hexn_pattern_designer_v10 as D, hexn_bases_v12 as B, hexn_wrgrid_v20 as G
    N = G.Node9
    base = D.make_base({"n": 7, "counts": {"UN": 2, "AL": 5, "BR": 1, "LT": 1}, "ram": "none"})
    br = N("br", "branch", ["y", "c"], ["lo", "hi"], cfg=dict(route_lt=1, route_eq=1, route_gt=1, emit=1))
    t = ([br, N("r", "latch", ["x", "lo"])], ["x", "y", "c"], ["r"])
    P = B.fits(base, t); assert P
    cap = G.simulate9(P, dict(x=100, y=37, c=1000), ["r"])["r"]
    assert [w for _, w in cap] == [1, 0] and cap[1][0] - cap[0][0] > 32          # set by x, cleared by the branch result about 40 ticks later
    t3 = ([N("r", "latch", ["x", "y", "z"])], ["x", "y", "z"], ["r"]); P3 = B.fits(base, t3); assert P3
    assert [w for _, w in G.simulate9(P3, dict(x=1, y=2, z=3), ["r"])["r"]] == [1]   # pulses closer than 32 ticks: one report
