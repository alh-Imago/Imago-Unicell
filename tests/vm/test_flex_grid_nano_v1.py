"""tests/vm/test_flex_grid_nano_v1.py -- FlexGrid step 2: the flex NANO at width W, checked against the REAL RTL cell (ledger #966).

The flex nano (sub/verilog/nano_cell_v4sa.v) has a WIDTH parameter, so the real cell can be built at WIDTH = 4, 8, 18, 32, 36 and used as the ORACLE: for every topology the flex
generator translates, and many operand pairs, the RTL's result must equal what a FlexGrid(width=W) computes through the nano. (Until now the VM was the oracle for the flex hardware;
here the hardware is the oracle for the VM variant, and at W != 32 this is the first time the VM's width behaviour is checked against the RTL and not against a spec I wrote.)
Also: the std VM still refuses a nano at another width (unchanged); a FlexGrid refuses a nano the generator does not translate; the test bites (a mask forced back to 32 bits fails).
This test REQUIRES iverilog and FAILS without it (the flex suites that skip silently are a hazard recorded in #965).
"""
import os
import random
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "nano"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import flex_grid_v1 as fg  # noqa: E402
import flexsub_icm_generate_v1 as planner  # noqa: E402
import unicell_super_automaton_v1 as vm  # noqa: E402
from icm_v3 import IcmV3Record  # noqa: E402

CELL = os.path.join(ROOT, "sub", "verilog", "nano_cell_v4sa.v")
WIDTHS = (4, 8, 18, 32, 36)
TOPOLOGIES = sorted(planner.NANO_TOPOLOGIES)


def pairs(w, seed):
    r = random.Random(seed * 100 + w)
    m = (1 << w) - 1
    fixed = [(0, 0), (m, 0), (0, m), (m, m), (1 << (w - 1), 1), (0x5555555555 & m, 0xAAAAAAAAAA & m)]
    return fixed + [(r.getrandbits(w), r.getrandbits(w)) for _ in range(6)]


def rtl_results(w, cases, tmp_path):
    """Run the real nano_cell_v4sa at WIDTH=w over (topology, a, b) cases: configure, load the held operand A, present the flowing operand B, read the result, acknowledge."""
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    body = []
    for topo, a, b in cases:
        body.append(f"    run(10'h{topo:X}, {w}'h{a:X}, {w}'h{b:X});")
    tb = f"""`timescale 1ns/1ps
module tb;
  parameter W = {w};
  reg clk = 0, rst = 1, freeze = 0, cfgv = 0, ldh = 0, vin = 0, ackin = 0;
  reg [31:0] cfgd = 0; reg [W-1:0] hin = 0, fin = 0;
  wire ackout, vout; wire [W-1:0] dout;
  nano_cell_v4sa #(.CELL_ID(16'd0), .WIDTH(W)) dut (.clk(clk), .rst(rst), .freeze_in(freeze), .cfg_valid(cfgv), .cfg_data(cfgd),
      .hold_in_data(hin), .load_hold(ldh), .flow_in_data(fin), .valid_in(vin), .ack_out(ackout), .data_out(dout), .valid_out(vout), .ack_in(ackin));
  always #5 clk = ~clk;
  task run(input [9:0] topo, input [W-1:0] a, input [W-1:0] b);
    begin
      cfgd = {{22'b0, topo}}; cfgv = 1; @(posedge clk); #1; cfgv = 0;
      hin = a; ldh = 1; @(posedge clk); #1; ldh = 0;
      fin = b; vin = 1; @(posedge clk); #1; vin = 0;
      if (!vout) $display("NOVALID %h", topo);
      $display("R %h %h %h %h", topo, a, b, dout);
      ackin = 1; @(posedge clk); #1; ackin = 0;
    end
  endtask
  initial begin
    repeat (3) @(posedge clk); #1 rst = 0;
{chr(10).join(body)}
    $finish;
  end
endmodule
"""
    f = tmp_path / f"tb_{w}.v"
    f.write_text(tb)
    exe = tmp_path / f"tb_{w}.vvp"
    c = subprocess.run(["iverilog", "-g2012", "-o", str(exe), str(f), CELL], capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[:400]
    out = subprocess.run(["vvp", str(exe)], capture_output=True, text=True).stdout
    assert "NOVALID" not in out, out[:300]
    res = {}
    for line in out.splitlines():
        if line.startswith("R "):
            _, t, a, b, d = line.split()
            res[(int(t, 16), int(a, 16), int(b, 16))] = int(d, 16)
    assert len(res) == len(set(cases)), (len(res), len(cases))
    return res


def ram(cid, r, c, up, down):
    return IcmV3Record(cell_id=cid, row=r, col=c, core="ram", core_config={"upstream_mask": up, "downstream_mask": down})


def vm_nano(topo, a, b, w, grid_cls=fg.FlexGrid, mutate=None):
    """X(1,0) -> nano(1,1) <- Y(0,1); nano -> E(1,2). A is injected first (the held operand), B later; returns what E receives."""
    recs = [ram("X", 1, 0, [], ["e"]), ram("Y", 0, 1, [], ["s"]),
            IcmV3Record(cell_id="N", row=1, col=1, core="nano", core_config={"routing_mask": ["e"], "topology": topo, "ready": 1}), ram("E", 1, 2, ["w"], [])]
    g = grid_cls(recs, width=w) if grid_cls is not None else None
    if mutate:
        mutate(g)
    for _ in range(4):
        g.tick()
    g.inject(1, 0, a)
    for _ in range(12):
        g.tick()
    g.inject(0, 1, b)
    for _ in range(40):
        g.tick()
    e = g.cells[(1, 2)]
    return e.ram_data_reg if e.ram_data_valid else None


@pytest.mark.parametrize("w", WIDTHS)
def test_flexgrid_nano_equals_the_real_rtl_cell_at_every_width(w, tmp_path):
    cases = [(t, a, b) for t in TOPOLOGIES for a, b in pairs(w, t)]
    rtl = rtl_results(w, cases, tmp_path)
    bad = []
    for t, a, b in cases:
        got = vm_nano(t, a, b, w)
        if got != rtl[(t, a, b)]:
            bad.append((hex(t), hex(a), hex(b), "vm", None if got is None else hex(got), "rtl", hex(rtl[(t, a, b)])))
    assert not bad, f"width {w}: {len(bad)} of {len(cases)} differ, first: {bad[:2]}"


def test_the_comparison_bites_a_grid_whose_mask_is_forced_back_to_32_bits_disagrees_with_the_rtl(tmp_path):
    w = 18
    cases = [(t, a, b) for t in TOPOLOGIES for a, b in pairs(w, t)]
    rtl = rtl_results(w, cases, tmp_path)

    def widen(g):
        g.mask = 0xFFFFFFFF
        for c in g.cells.values():
            c.mask = 0xFFFFFFFF
            if c._nano is not None:
                c._nano.mask = 0xFFFFFFFF
    wrong = sum(1 for t, a, b in cases if vm_nano(t, a, b, w, mutate=widen) != rtl[(t, a, b)])
    assert wrong > 0, "forcing the mask back to 32 bits changed nothing: the test would not catch a missing width"


def test_the_std_vm_still_refuses_the_nano_at_other_widths_and_flex_accepts_it():
    rec = IcmV3Record(cell_id="N", row=0, col=0, core="nano", core_config={"routing_mask": ["e"], "topology": 0x2C})
    with pytest.raises(ValueError, match="nano core is not available at width 18"):
        vm.SuperGrid([rec], width=18)
    assert fg.FlexGrid([rec], width=18).width == 18
    assert fg.FlexGrid([rec], width=36).width == 36


@pytest.mark.parametrize("cfg,why", [({"routing_mask": ["e"], "topology": 0x123}, "topology"),
                                     ({"routing_mask": ["e"], "topology": 0x2C, "a_reemit_in": 1}, "relay"),
                                     ({"routing_mask": ["e"], "topology": 0x2C, "dynamic_route_en": 1}, "relay")])
def test_a_nano_the_flex_generator_does_not_translate_is_refused_at_other_widths(cfg, why):
    rec = IcmV3Record(cell_id="N", row=0, col=0, core="nano", core_config=cfg)
    with pytest.raises(ValueError, match="flex nano at width 18"):
        fg.FlexGrid([rec], width=18)
    assert fg.FlexGrid([rec], width=32).width == 32          # at 32 nothing is restricted (the std nano model, as always)


def test_known_rtl_defect_an_unconfigured_flex_nano_still_captures(tmp_path):
    """FINDING (ledger #970): nano_cell_v4sa captures on `valid_in` with no `armed` check (like the sequencer did before #956): an UNCONFIGURED cell handed a value offers a result (valid_out = 1) although its
    ack_out (ready) is low. The generated designs are safe because they gate valid_in with the cell's ready. Pinned so a fix is noticed."""
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    tb = """`timescale 1ns/1ps
module tb;
  reg clk=0,rst=1,freeze=0,cfgv=0,ldh=0,vin=0,ackin=0; reg [31:0] cfgd=0; reg [31:0] hin=0, fin=0;
  wire ackout,vout; wire [31:0] dout;
  nano_cell_v4sa #(.CELL_ID(16'd0),.WIDTH(32)) dut(.clk(clk),.rst(rst),.freeze_in(freeze),.cfg_valid(cfgv),.cfg_data(cfgd),.hold_in_data(hin),.load_hold(ldh),.flow_in_data(fin),.valid_in(vin),.ack_out(ackout),.data_out(dout),.valid_out(vout),.ack_in(ackin));
  always #5 clk=~clk;
  initial begin repeat(3) @(posedge clk); #1 rst=0;
    hin=32'h1234; ldh=1; @(posedge clk); #1 ldh=0;
    fin=32'h00FF; vin=1; @(posedge clk); #1 vin=0;
    $display("U %b %b", ackout, vout);
    $finish; end
endmodule
"""
    f = tmp_path / "tb_unarmed.v"
    f.write_text(tb)
    subprocess.run(["iverilog", "-g2012", "-o", str(tmp_path / "u.vvp"), str(f), CELL], check=True, capture_output=True)
    out = subprocess.run(["vvp", str(tmp_path / "u.vvp")], capture_output=True, text=True).stdout
    assert "U 0 1" in out, f"the unconfigured nano no longer offers a result (ack_out=0, valid_out=1): the defect looks FIXED -- update this test. got: {out[:80]}"
