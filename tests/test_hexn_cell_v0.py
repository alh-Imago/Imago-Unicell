"""Hex-N cell v0 (scoping prototype): the RTL against an independent Python model of docs/hex-n/cell-internals-v0.1.md, on random configs and inputs.
Requires iverilog. Not a decision about the open questions: it pins the assumptions in rtl/hexn_cell_v0.v."""
import os, random, shutil, subprocess, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACES, CH, TW = 6, 4, 3


def model(cfg_active, cfg_gate, cfg_thr, ins, not_of_in=0):
    out, fire = [], []
    for f in range(FACES):
        pc = sum(ins[f * CH + c] & cfg_active[f * CH + c] for c in range(CH))
        fr = int(pc >= cfg_thr[f])
        fire.append(fr)
        for c in range(CH):
            i = f * CH + c; a = ins[i]; gs = cfg_gate[i]
            g = (fr & a, fr | a, fr ^ a, (1 - a) if not_of_in else (1 - fr))[gs]
            out.append(g & cfg_active[i])
    return out, fire


def test_rtl_matches_model():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED"
    rnd = random.Random(7)
    N = FACES * CH
    cases = []
    for _ in range(300):
        act = [rnd.randint(0, 1) for _ in range(N)]; gate = [rnd.randint(0, 3) for _ in range(N)]
        thr = [rnd.randint(0, 5) for _ in range(FACES)]; ins = [rnd.randint(0, 1) for _ in range(N)]
        cases.append((act, gate, thr, ins))
    def bits(v): return sum(b << i for i, b in enumerate(v))
    lines = []
    for k, (act, gate, thr, ins) in enumerate(cases):
        g = sum(gv << (2 * i) for i, gv in enumerate(gate)); t = sum(tv << (3 * i) for i, tv in enumerate(thr))
        lines.append(f"    act = {N}'d{bits(act)}; gate = {2*N}'d{g}; thr = {FACES*TW}'d{t}; ib = {N}'d{bits(ins)}; tick = 1; @(posedge clk); #1 tick = 0; "
                     f"@(posedge clk); #1 $display(\"R %0d %0d\", ob, fire);")
    tb = f"""`timescale 1ns/1ps
module tb; reg clk = 0, rst = 1, tick = 0; always #5 clk = ~clk;
  reg [{N-1}:0] act, ib; reg [{2*N-1}:0] gate; reg [{FACES*TW-1}:0] thr; wire [{N-1}:0] ob; wire [{FACES-1}:0] fire;
  hexn_cell_v0 U(.clk(clk), .rst(rst), .tick(tick), .in_bus(ib), .out_bus(ob), .fire(fire), .cfg_active(act), .cfg_gate(gate), .cfg_thr(thr), .bias(16'd0));
  initial begin ib = 0; act = 0; gate = 0; thr = 0; repeat (3) @(posedge clk); #1 rst = 0;
{chr(10).join(lines)}
    $finish; end
endmodule
"""
    d = tempfile.mkdtemp(prefix="hexn_")
    try:
        open(os.path.join(d, "tb.v"), "w").write(tb)
        o = os.path.join(d, "o.vvp")
        c = subprocess.run(["iverilog", "-g2012", "-s", "tb", "-o", o, os.path.join(d, "tb.v"), os.path.join(ROOT, "rtl", "hexn_cell_v0.v")], capture_output=True, text=True)
        assert c.returncode == 0, c.stderr[:800]
        res = subprocess.run(["vvp", o], capture_output=True, text=True, timeout=300).stdout.split("\n")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    got = [l.split() for l in res if l.startswith("R ")]
    assert len(got) == len(cases)
    for k, ((act, gate, thr, ins), (_, ob, fi)) in enumerate(zip(cases, got)):
        out, fire = model(act, gate, thr, ins)
        assert int(ob) == bits(out) and int(fi) == bits(fire), (k, int(ob), bits(out), int(fi), bits(fire))
