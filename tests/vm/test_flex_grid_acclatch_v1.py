"""tests/vm/test_flex_grid_acclatch_v1.py -- FlexGrid step 8: the ACCUMULATOR (continuous and pulse mode) and the LATCH at width W against the REAL accumulator_cell_v4sa / latch_cell_v4sa (ledger #970).

Each real cell is driven with a pulse sequence (inc / dec, or set / clear / toggle), every offer acknowledged, and the value it offers after each pulse is compared with what a FlexGrid accumulator / latch holds
after the same pulses. The accumulator's step is 8 bits and its threshold 16 bits. Until #973 they were zero-extended with replications of (WIDTH-8) / (WIDTH-16), which go negative below 16 bits (the real cell did not
elaborate there); now the step is assigned straight to the data width and the threshold is compared with |total| in a wider space, so the cell builds and works at every width. Requires iverilog and FAILS without it.
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
WIDTHS = (4, 8, 12, 16, 18, 32, 36)


def need_iverilog():
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"


def compile_run(tb, srcs, path):
    path.write_text(tb)
    exe = str(path) + ".vvp"
    c = subprocess.run(["iverilog", "-g2012", "-o", exe, str(path)] + [os.path.join(V, s) for s in srcs], capture_output=True, text=True)
    if c.returncode:
        return None, c.stderr
    return subprocess.run(["vvp", exe], capture_output=True, text=True).stdout, ""


def rtl_acc(w, step, pulse_mode, threshold, pulses, tmp_path):
    """pulses: 'i' / 'd'. Returns the list of offers (None where the cell offered nothing: pulse mode, no threshold hit)."""
    need_iverilog()
    cfg = step | (pulse_mode << 8) | (threshold << 9)
    body = "\n".join(f"    pulse({1 if p == 'i' else 0}, {1 if p == 'd' else 0});" for p in pulses)
    tb = f"""`timescale 1ns/1ps
module tb;
  parameter W = {w};
  reg clk = 0, rst = 1, freeze = 0, cfgv = 0, inc = 0, dec = 0, ackin = 0; reg [31:0] cfgd = 0;
  wire ackout, vout; wire [W-1:0] dout;
  accumulator_cell_v4sa #(.CELL_ID(16'd0), .WIDTH(W)) dut (.clk(clk), .rst(rst), .freeze_in(freeze), .cfg_valid(cfgv), .cfg_data(cfgd), .inc_pulse(inc), .dec_pulse(dec), .ack_out(ackout), .data_out(dout), .valid_out(vout), .ack_in(ackin));
  always #5 clk = ~clk;
  task pulse(input i, input d);
    begin
      inc = i; dec = d; @(posedge clk); #1; inc = 0; dec = 0;
      if (vout) $display("O %h", dout); else $display("O none");
      ackin = 1; @(posedge clk); #1; ackin = 0;
    end
  endtask
  initial begin repeat (3) @(posedge clk); #1 rst = 0;
    cfgd = 32'h{cfg:08X}; cfgv = 1; @(posedge clk); #1; cfgv = 0;
{body}
    $finish; end
endmodule
"""
    out, err = compile_run(tb, ["accumulator_cell_v4sa.v"], tmp_path / f"tbacc_{w}_{step}_{pulse_mode}_{threshold}.v")
    assert out is not None, err[:300]
    return [None if l.split()[1] == "none" else int(l.split()[1], 16) for l in out.splitlines() if l.startswith("O ")]


def vm_acc(w, step, pulse_mode, threshold, pulses):
    recs = [IcmV3Record(cell_id="I", row=1, col=0, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["e"]}),
            IcmV3Record(cell_id="D", row=0, col=1, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["s"]}),
            IcmV3Record(cell_id="A", row=1, col=1, core="accumulator", core_config={"inc_dir": ["w"], "dec_dir": ["n"], "step_amount": step, "pulse_mode": pulse_mode, "threshold": threshold, "downstream_mask": []})]
    g = fg.FlexGrid(recs, width=w)
    a = g.cells[(1, 1)]
    out = []
    for p in pulses:
        g.inject(*((1, 0) if p == "i" else (0, 1)), 1)
        for _ in range(6):
            g.tick()
        if pulse_mode:
            if a.acc_pulse_pending:
                out.append(a.acc_out_buffer)
                a.acc_pulse_pending = False
            else:
                out.append(None)
        else:
            out.append(a.acc_total & ((1 << w) - 1))
    return out


@pytest.mark.parametrize("w", WIDTHS)
def test_continuous_accumulator_equals_the_real_cell(w, tmp_path):
    r = random.Random(w)
    bad = []
    for step in (1, 7, 255):
        pulses = [r.choice("id") for _ in range(30)] + ["i"] * 8 + ["d"] * 20
        rtl = rtl_acc(w, step, 0, 0, pulses, tmp_path)
        mine = vm_acc(w, step, 0, 0, pulses)
        if mine != rtl:
            bad.append((step, [hex(x) for x in mine[:6]], [hex(x) for x in rtl[:6]]))
    assert not bad, f"width {w}: {bad[:2]}"


@pytest.mark.parametrize("w", WIDTHS)
def test_pulse_mode_accumulator_equals_the_real_cell(w, tmp_path):
    r = random.Random(w + 3)
    bad = []
    for step, threshold in ((3, 10), (5, 1000), (255, 300), (1, 0)):
        pulses = [r.choice("iid") for _ in range(60)]
        rtl = rtl_acc(w, step, 1, threshold, pulses, tmp_path)
        mine = vm_acc(w, step, 1, threshold, pulses)
        if mine != rtl:
            bad.append((step, threshold, mine[:8], rtl[:8]))
    assert not bad, f"width {w}: {bad[:2]}"


def test_the_accumulator_wraps_at_the_data_width_not_at_32(tmp_path):
    w = 18
    rtl = rtl_acc(w, 255, 0, 0, ["i"] * 1100, tmp_path)         # 1100 * 255 = 280,500 > 2^18 = 262,144: wraps
    assert rtl[-1] == (1100 * 255) % (1 << w) and rtl[-1] != 1100 * 255
    assert vm_acc(w, 255, 0, 0, ["i"] * 1100)[-1] == rtl[-1]


def test_the_accumulator_now_builds_and_works_below_16_bits_and_a_big_threshold_is_never_cut_down(tmp_path):
    """#973: width 8 used to fail to elaborate. Now it builds; a 16-bit threshold larger than the data can reach (300 at 8 bits) simply never fires -- it is NOT truncated to 44 -- and a step wider than the data
    wraps like the total (255 at 4 bits acts as 15)."""
    rtl = rtl_acc(8, 5, 1, 300, ["i"] * 100, tmp_path)         # |total| <= 128 < 300: no event, ever
    assert all(x is None for x in rtl), rtl[:5]
    assert vm_acc(8, 5, 1, 300, ["i"] * 100) == rtl
    rtl4 = rtl_acc(4, 255, 0, 0, ["i"] * 5, tmp_path)           # step 255 -> 15 at 4 bits: total = 15, 14, 13, ... (mod 16)
    assert rtl4 == [15, 14, 13, 12, 11], rtl4
    assert vm_acc(4, 255, 0, 0, ["i"] * 5) == rtl4
    fg.FlexGrid([IcmV3Record(cell_id="A", row=0, col=0, core="accumulator", core_config={"inc_dir": ["w"], "step_amount": 1, "downstream_mask": []})], width=8)


def rtl_latch(w, events, tmp_path):
    need_iverilog()
    body = "\n".join(f"    ev({1 if e == 's' else 0}, {1 if e == 'c' else 0}, {1 if e == 't' else 0});" for e in events)
    tb = f"""`timescale 1ns/1ps
module tb;
  parameter W = {w};
  reg clk = 0, rst = 1, freeze = 0, cfgv = 0, s = 0, c = 0, t = 0, ackin = 0; reg [31:0] cfgd = 0;
  wire ackout, vout; wire [W-1:0] dout;
  latch_cell_v4sa #(.CELL_ID(16'd0), .WIDTH(W)) dut (.clk(clk), .rst(rst), .freeze_in(freeze), .cfg_valid(cfgv), .cfg_data(cfgd), .set_in(s), .clear_in(c), .toggle_in(t), .ack_out(ackout), .data_out(dout), .valid_out(vout), .ack_in(ackin));
  always #5 clk = ~clk;
  task ev(input a, input b, input d);
    begin
      s = a; c = b; t = d; @(posedge clk); #1; s = 0; c = 0; t = 0;
      $display("O %h", dout);
      ackin = 1; @(posedge clk); #1; ackin = 0;
    end
  endtask
  initial begin repeat (3) @(posedge clk); #1 rst = 0;
    cfgv = 1; @(posedge clk); #1; cfgv = 0;
{body}
    $finish; end
endmodule
"""
    out, err = compile_run(tb, ["latch_cell_v4sa.v"], tmp_path / f"tblatch_{w}.v")
    assert out is not None, err[:300]
    return [int(l.split()[1], 16) for l in out.splitlines() if l.startswith("O ")]


def vm_latch(w, events):
    recs = [IcmV3Record(cell_id="S", row=1, col=0, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["e"]}),
            IcmV3Record(cell_id="C", row=0, col=1, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["s"]}),
            IcmV3Record(cell_id="T", row=2, col=1, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["n"]}),
            IcmV3Record(cell_id="L", row=1, col=1, core="latch", core_config={"set_dir": ["w"], "clear_dir": ["n"], "toggle_dir": ["s"], "downstream_mask": []})]
    g = fg.FlexGrid(recs, width=w)
    out = []
    for e in events:
        g.inject(*{"s": (1, 0), "c": (0, 1), "t": (2, 1)}[e], 1)
        for _ in range(6):
            g.tick()
        out.append(g.cells[(1, 1)].latch_state & 1)
    return out


@pytest.mark.parametrize("w", (4, 8, 18, 32, 36))
def test_latch_equals_the_real_cell_at_every_width(w, tmp_path):
    r = random.Random(w)
    events = [r.choice("sctt") for _ in range(40)]
    assert vm_latch(w, events) == rtl_latch(w, events, tmp_path)


def test_the_comparison_bites_a_mirror_whose_threshold_is_cut_to_the_width(tmp_path):
    # a threshold of 300 at 8 bits cut to its low 8 bits would be 44 and would fire; the real cell never fires
    rtl = rtl_acc(8, 5, 1, 300, ["i"] * 100, tmp_path)
    assert all(x is None for x in rtl)
    cut = 300 & 0xFF
    total, fired = 0, False
    for _ in range(100):
        total = ((total + 5 + 128) & 0xFF) - 128
        fired |= abs(total) >= cut
    assert fired


def test_the_comparison_bites_an_accumulator_that_does_not_wrap_at_the_width(tmp_path):
    w = 18
    rtl = rtl_acc(w, 255, 0, 0, ["i"] * 1100, tmp_path)
    assert rtl[-1] != 1100 * 255
