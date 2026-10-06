"""tests/vm/test_flex_grid_compare_v1.py -- FlexGrid step 7: the COMPARATOR at width W against the REAL compare_cell_v4sa (ledger #970, #971).

Result = 1 when signed(data) >= threshold (both W-bit signed), else 0. Since #971 the threshold has its OWN WIDTH-bit port, cfg_threshold (before, it was read from the fixed 32-bit cfg_data, so above 32 bits its upper
bits were undefined and the result x). Requires iverilog and FAILS without it.
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


def signed(v, w):
    v &= (1 << w) - 1
    return v - (1 << w) if v >> (w - 1) else v


def thresholds(w):
    top = (1 << (w - 1)) - 1                    # the largest W-bit signed threshold (now loadable at every width)
    return sorted({0, 1, -1, 2, -2, top, -top - 1, top // 2, -(top // 2)})


def rtl_results(w, cases, tmp_path):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    body = "\n".join(f"    run({w}'h{t & ((1 << w) - 1):X}, {w}'h{v & ((1 << w) - 1):X});" for t, v in cases)
    tb = f"""`timescale 1ns/1ps
module tb;
  parameter W = {w};
  reg clk = 0, rst = 1, freeze = 0, cfgv = 0, vin = 0, ackin = 0; reg [W-1:0] cfgt = 0; reg [W-1:0] din = 0;
  wire ackout, vout; wire [W-1:0] dout;
  compare_cell_v4sa #(.CELL_ID(16'd0), .WIDTH(W)) dut (.clk(clk), .rst(rst), .freeze_in(freeze), .cfg_valid(cfgv), .cfg_data(32'h0), .cfg_threshold(cfgt), .data_in(din), .valid_in(vin), .ack_out(ackout), .data_out(dout), .valid_out(vout), .ack_in(ackin));
  always #5 clk = ~clk;
  task run(input [W-1:0] t, input [W-1:0] v);
    begin
      cfgt = t; cfgv = 1; @(posedge clk); #1; cfgv = 0;
      din = v; vin = 1; @(posedge clk); #1; vin = 0;
      $display("R %h %h %h", t, v, dout);
      ackin = 1; @(posedge clk); #1; ackin = 0;
    end
  endtask
  initial begin repeat (3) @(posedge clk); #1 rst = 0;
{body}
    $finish; end
endmodule
"""
    f = tmp_path / f"tbcmp{w}.v"
    f.write_text(tb)
    exe = tmp_path / f"tbcmp{w}.vvp"
    c = subprocess.run(["iverilog", "-g2012", "-o", str(exe), str(f), os.path.join(V, "compare_cell_v4sa.v")], capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[:400]
    out = subprocess.run(["vvp", str(exe)], capture_output=True, text=True).stdout
    res = {}
    for line in out.splitlines():
        if line.startswith("R "):
            _, t, v, d = line.split()
            res[(int(t, 16), int(v, 16))] = d.lower()
    return res


def vm_result(t, v, w):
    recs = [IcmV3Record(cell_id="X", row=0, col=0, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["e"]}),
            IcmV3Record(cell_id="C", row=0, col=1, core="comparator", core_config={"upstream_mask": ["w"], "downstream_mask": ["e"], "threshold": t}),
            IcmV3Record(cell_id="E", row=0, col=2, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": []})]
    g = fg.FlexGrid(recs, width=w)
    for _ in range(3):
        g.tick()
    g.inject(0, 0, v & ((1 << w) - 1))
    for _ in range(20):
        g.tick()
    e = g.cells[(0, 2)]
    return e.ram_data_reg if e.ram_data_valid else None


@pytest.mark.parametrize("w", WIDTHS)
def test_flexgrid_comparator_equals_the_real_cell(w, tmp_path):
    r = random.Random(w)
    m = (1 << w) - 1
    cases = [(t, v) for t in thresholds(w) for v in [0, m, 1 << (w - 1), (1 << (w - 1)) - 1, 1, m - 1] + [r.getrandbits(w) for _ in range(4)]]
    rtl = rtl_results(w, cases, tmp_path)
    bad = []
    for t, v in cases:
        want = rtl[(t & m, v & m)]
        got = vm_result(t, v, w)
        if "x" in want or got is None or int(want, 16) != got:
            bad.append((t, hex(v), "vm", got, "rtl", want))
    assert not bad, f"width {w}: {len(bad)} of {len(cases)} differ, first: {bad[:3]}"


def test_the_comparison_bites_an_unsigned_compare(tmp_path):
    w = 18
    cases = [(-1, 5), (-1, (1 << w) - 1), (1, (1 << w) - 2)]
    rtl = rtl_results(w, cases, tmp_path)
    unsigned_mirror = [1 if (v & ((1 << w) - 1)) >= (t & ((1 << w) - 1)) else 0 for t, v in cases]
    assert unsigned_mirror != [int(rtl[(t & ((1 << w) - 1), v & ((1 << w) - 1))], 16) for t, v in cases]


def test_a_threshold_wider_than_32_bits_now_loads_at_width_36(tmp_path):
    """#971: the threshold has its own W-bit port, so at W = 36 thresholds beyond the 32-bit range work in the real cell and in FlexGrid (before: x). Every result is defined and equal."""
    w = 36
    m = (1 << w) - 1
    ts = [1 << 34, -(1 << 34), (1 << 35) - 1, -(1 << 35), (1 << 32), -(1 << 32) - 1]
    vs = [0, 1 << 33, 1 << 34, (1 << 34) + 1, m, (1 << 35), (1 << 35) - 1, m - (1 << 33)]
    cases = [(t, v) for t in ts for v in vs]
    rtl = rtl_results(w, cases, tmp_path)
    assert not any("x" in d for d in rtl.values())
    for t, v in cases:
        assert vm_result(t, v, w) == int(rtl[(t & m, v & m)], 16), (t, v)
    # and a sign-extended 32-bit word could NOT have expressed these: the thresholds below really are beyond the 32-bit signed range
    assert all(abs(t) > (1 << 31) for t in ts)


def test_flexgrid_builds_a_comparator_at_every_width():
    rec = IcmV3Record(cell_id="C", row=0, col=0, core="comparator", core_config={"upstream_mask": ["w"], "downstream_mask": ["e"], "threshold": 0})
    for w in (4, 8, 18, 32, 36):
        fg.FlexGrid([rec], width=w)
