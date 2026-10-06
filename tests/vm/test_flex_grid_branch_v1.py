"""tests/vm/test_flex_grid_branch_v1.py -- FlexGrid step 9: the BRANCH at width W against the REAL branch_cell_v4sa (ledger #970).

The cell compares in1 with in2 as W-bit SIGNED values, picks the outcome (low / equal / high), and emits (a fixed constant, or in1) on the outcome's port(s). The ICM branch is the held-reference form: the first
arrival is the reference, every later one is compared with it. The cell is driven with in1 = the stream value and in2 = the reference (the generator's const_ref lowering); FlexGrid's branch gets the reference first,
then the value. Compared: which output port(s) fire and the value on each, for random routes, both emit sources the ICM can express (input / fixed 7-bit constant), at W = 4, 8, 18, 32, 36. Requires iverilog and
FAILS without it.
"""
import os
import random
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "nano"))
import flex_grid_v1 as fg  # noqa: E402
from icm_v3 import IcmV3Record  # noqa: E402

V = os.path.join(ROOT, "sub", "verilog")
WIDTHS = (4, 8, 18, 32, 36)
FACE = {1: "e", 2: "s"}          # RTL output port 1 -> the east consumer, port 2 -> the south consumer


def rtl_cases(w, cases, tmp_path):
    """cases: (routes (low, equal, high) as 2-bit port sets, emit_source 0|1, fixed, ref, val). Returns {case: (port1 value or None, port2 value or None)}."""
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    body = []
    for routes, es, fixed, ref, val in cases:
        cfg = (es << 2) | (routes[0] << 4) | (routes[1] << 6) | (routes[2] << 8)
        body.append(f"    run(32'h{cfg:X}, {w}'h{fixed:X}, {w}'h{ref & ((1 << w) - 1):X}, {w}'h{val & ((1 << w) - 1):X});")
    tb = f"""`timescale 1ns/1ps
module tb;
  parameter W = {w};
  reg clk = 0, rst = 1, freeze = 0, cfgv = 0, v1 = 0, v2 = 0, a1 = 0, a2 = 0; reg [31:0] cfgd = 0; reg [W-1:0] fx = 0, i1 = 0, i2 = 0;
  wire ackout, vo1, vo2; wire [W-1:0] d1, d2;
  branch_cell_v4sa #(.CELL_ID(16'd0), .WIDTH(W)) dut (.clk(clk), .rst(rst), .freeze_in(freeze), .cfg_valid(cfgv), .cfg_data(cfgd), .cfg_emit_fixed_value(fx),
      .in1_data(i1), .in1_valid(v1), .in2_data(i2), .in2_valid(v2), .ack_out(ackout), .data_out_1(d1), .valid_out_1(vo1), .ack_in_1(a1), .data_out_2(d2), .valid_out_2(vo2), .ack_in_2(a2));
  always #5 clk = ~clk;
  task run(input [31:0] c, input [W-1:0] f, input [W-1:0] r, input [W-1:0] v);
    begin
      cfgd = c; fx = f; cfgv = 1; @(posedge clk); #1; cfgv = 0;
      i1 = v; i2 = r; v1 = 1; v2 = 1; @(posedge clk); #1; v1 = 0; v2 = 0;
      $display("R %0d %h %0d %h", vo1, d1, vo2, d2);
      a1 = 1; a2 = 1; @(posedge clk); #1; a1 = 0; a2 = 0;
    end
  endtask
  initial begin repeat (3) @(posedge clk); #1 rst = 0;
{chr(10).join(body)}
    $finish; end
endmodule
"""
    f = tmp_path / f"tbbr{w}.v"
    f.write_text(tb)
    exe = tmp_path / f"tbbr{w}.vvp"
    c = subprocess.run(["iverilog", "-g2012", "-o", str(exe), str(f), os.path.join(V, "branch_cell_v4sa.v")], capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[:400]
    out = subprocess.run(["vvp", str(exe)], capture_output=True, text=True).stdout
    rows = [l.split() for l in out.splitlines() if l.startswith("R ")]
    assert len(rows) == len(cases), out[:300]
    return [(int(r[2], 16) if r[1] == "1" else None, int(r[4], 16) if r[3] == "1" else None) for r in rows]


def faces(bits):
    return [FACE[p] for p in (1, 2) if bits & (1 << (p - 1))]


def vm_case(w, routes, es, fixed, ref, val):
    cfg = {"upstream_dir": 3, "rolling_mode": 0}                                  # arrives from the west
    for n, rt in zip(("low", "equal", "high"), routes):
        cfg.update({f"value_source_{n}": 1 if es == 0 else 0, f"fixed_value_{n}": fixed, f"emit_{n}": 1, f"route_{n}": faces(rt)})
    recs = [IcmV3Record(cell_id="X", row=1, col=0, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["e"]}),
            IcmV3Record(cell_id="B", row=1, col=1, core="branch", core_config=cfg),
            IcmV3Record(cell_id="O1", row=1, col=2, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": []}),
            IcmV3Record(cell_id="O2", row=2, col=1, core="ram", core_config={"upstream_mask": ["n"], "downstream_mask": []})]
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        g = fg.FlexGrid(recs, width=w)
    m = (1 << w) - 1
    g.inject(1, 0, ref & m)
    for _ in range(6):
        g.tick()
    g.inject(1, 0, val & m)
    for _ in range(10):
        g.tick()
    o1, o2 = g.cells[(1, 2)], g.cells[(2, 1)]
    return (o1.ram_data_reg if o1.ram_data_valid else None, o2.ram_data_reg if o2.ram_data_valid else None)


def make_cases(w):
    r = random.Random(w)
    m = (1 << w) - 1
    refs = [0, 1, m, 1 << (w - 1), (1 << (w - 1)) - 1] + [r.getrandbits(w) for _ in range(3)]
    cases = []
    for _ in range(24):
        routes = tuple(r.choice((1, 2, 3)) for _ in range(3))
        es = r.choice((0, 1))
        fixed = r.randrange(0, min(0x80, m + 1))
        ref = r.choice(refs)
        val = r.choice([ref, (ref + 1) & m, (ref - 1) & m] + refs)
        cases.append((routes, es, fixed, ref, val))
    return cases


@pytest.mark.parametrize("w", WIDTHS)
def test_flexgrid_branch_equals_the_real_cell(w, tmp_path):
    cases = make_cases(w)
    rtl = rtl_cases(w, cases, tmp_path)
    bad = []
    for case, want in zip(cases, rtl):
        got = vm_case(w, *case)
        if got != want:
            bad.append((case, "vm", got, "rtl", want))
    assert not bad, f"width {w}: {len(bad)} of {len(cases)} differ, first: {bad[:2]}"


def test_the_comparison_bites_an_unsigned_compare(tmp_path):
    w = 18
    m = (1 << w) - 1
    # ref = 5, val = all ones (= -1 signed): signed says LOW, unsigned says HIGH. Route low -> port 1, high -> port 2.
    cases = [((1, 1, 2), 1, 0, 5, m)]
    rtl = rtl_cases(w, cases, tmp_path)
    assert rtl == [(m, None)]
    assert vm_case(w, *cases[0]) == rtl[0]


def test_flexgrid_no_longer_warns_about_branch_and_accumulator_but_the_std_grid_still_does():
    import warnings
    import unicell_super_automaton_v1 as vm
    recs = [IcmV3Record(cell_id="B", row=0, col=0, core="branch", core_config={"upstream_dir": 3, "route_low": ["e"], "emit_low": 1}),
            IcmV3Record(cell_id="A", row=0, col=1, core="accumulator", core_config={"inc_dir": ["w"], "step_amount": 1, "downstream_mask": []})]
    with warnings.catch_warnings(record=True) as w1:
        warnings.simplefilter("always")
        fg.FlexGrid(recs, width=18)
    assert not [x for x in w1 if "NOT yet verified" in str(x.message)]
    with warnings.catch_warnings(record=True) as w2:
        warnings.simplefilter("always")
        vm.SuperGrid(recs, width=18)
    assert [x for x in w2 if "NOT yet verified" in str(x.message)]
