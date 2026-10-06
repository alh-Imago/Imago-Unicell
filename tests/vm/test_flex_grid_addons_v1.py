"""tests/vm/test_flex_grid_addons_v1.py -- FlexGrid step 4: the add-on chain (nibble mask, shifts, invert) at width W against the REAL flex cells (ledger #967).

In the flex family mask and shift are separate cores (mask_cell_v4sa, shift_stage_v4sa; both width-parameterised) and invert is wiring. The std add-on chain is defined on 32-bit lanes and the std VM refuses it
at other widths; FlexGrid runs the SAME chain on W bits (flex_grid_v1.flex_addons) and this test checks each stage against the real RTL at W = 4, 8, 18, 32, 36, and the whole chain as the composition
of the RTL stages. `lane_cut` has no W-bit definition and no cell, so it is refused. Requires iverilog and FAILS without it.
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
import unicell_super_automaton_v1 as vm  # noqa: E402
from icm_v3 import IcmV3Record  # noqa: E402

V = os.path.join(ROOT, "sub", "verilog")
WIDTHS = (4, 8, 18, 32, 36)
XBITS = set()   # (width, mask_en) combinations where the real mask cell drove an unknown (x) bit
COARSE = (1, 2, 4, 8, 12, 16, 20, 24, 28)


def run_iverilog(tb, files, tmp_path, name):
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    f = tmp_path / f"{name}.v"
    f.write_text(tb)
    exe = tmp_path / f"{name}.vvp"
    c = subprocess.run(["iverilog", "-g2012", "-o", str(exe), str(f)] + [os.path.join(V, x) for x in files], capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[:500]
    return subprocess.run(["vvp", str(exe)], capture_output=True, text=True).stdout


def values(w, n=10):
    r = random.Random(w)
    m = (1 << w) - 1
    return [0, m, 1, 1 << (w - 1), 0x5555555555 & m, 0xAAAAAAAAAA & m] + [r.getrandbits(w) for _ in range(n)]


def rtl_mask(w, cases, tmp_path):
    """cases: (mask_en, nibble_mask, value) -> data_out of the real mask_cell_v4sa."""
    body = "\n".join(f"    run({e}, 8'h{nm:02X}, {w}'h{v:X});" for e, nm, v in cases)
    tb = f"""`timescale 1ns/1ps
module tb;
  parameter W = {w};
  reg clk = 0, rst = 1, freeze = 0, cfgv = 0, vin = 0, ackin = 0; reg [31:0] cfgd = 0; reg [W-1:0] din = 0;
  wire ackout, vout; wire [W-1:0] dout;
  mask_cell_v4sa #(.CELL_ID(16'd0), .WIDTH(W)) dut (.clk(clk), .rst(rst), .freeze_in(freeze), .cfg_valid(cfgv), .cfg_data(cfgd), .data_in(din), .valid_in(vin), .ack_out(ackout), .data_out(dout), .valid_out(vout), .ack_in(ackin));
  always #5 clk = ~clk;
  task run(input e, input [7:0] nm, input [W-1:0] v);
    begin
      cfgd = {{23'b0, nm, e}}; cfgv = 1; @(posedge clk); #1; cfgv = 0;
      din = v; vin = 1; @(posedge clk); #1; vin = 0;
      $display("R %h %h %h %h", e, nm, v, dout);
      ackin = 1; @(posedge clk); #1; ackin = 0;
    end
  endtask
  initial begin repeat (3) @(posedge clk); #1 rst = 0;
{body}
    $finish; end
endmodule
"""
    out = run_iverilog(tb, ["mask_cell_v4sa.v"], tmp_path, f"mask{w}")
    res = {}
    for line in out.splitlines():
        if line.startswith("R "):
            _, e, nm, v, d = line.split()
            res[(int(e, 16), int(nm, 16), int(v, 16))] = int(d.lower().replace("x", "0"), 16)
            if "x" in d.lower():
                XBITS.add((w, int(e, 16)))
    assert len(res) == len(set(cases))
    return res


def rtl_shift(w, direction, vals, tmp_path):
    """A shift_stage_v4sa for every SHIFT_AMT 0..31 at once (same input); returns {(amt, value): out}."""
    body = "\n".join(f"    run({w}'h{v:X});" for v in vals)
    tb = f"""`timescale 1ns/1ps
module tb;
  parameter W = {w};
  reg clk = 0, rst = 1, freeze = 0, cfgv = 0, vin = 0, ackin = 0; reg [31:0] cfgd = 0; reg [W-1:0] din = 0;
  wire [31:0] ackout, vout; wire [32*W-1:0] dout;
  genvar k;
  generate for (k = 0; k < 32; k = k + 1) begin : S
    shift_stage_v4sa #(.CELL_ID(16'd0), .WIDTH(W), .SHIFT_AMT(k), .DIRECTION({direction})) dut (.clk(clk), .rst(rst), .freeze_in(freeze), .cfg_valid(cfgv), .cfg_data(cfgd),
       .data_in(din), .valid_in(vin), .ack_out(ackout[k]), .data_out(dout[k*W +: W]), .valid_out(vout[k]), .ack_in(ackin));
  end endgenerate
  integer j;
  always #5 clk = ~clk;
  task run(input [W-1:0] v);
    begin
      cfgv = 1; @(posedge clk); #1; cfgv = 0;
      din = v; vin = 1; @(posedge clk); #1; vin = 0;
      for (j = 0; j < 32; j = j + 1) $display("R %0d %h %h", j, v, dout[j*W +: W]);
      ackin = 1; @(posedge clk); #1; ackin = 0;
    end
  endtask
  initial begin repeat (3) @(posedge clk); #1 rst = 0;
{body}
    $finish; end
endmodule
"""
    out = run_iverilog(tb, ["shift_stage_v4sa.v"], tmp_path, f"shift{w}_{direction}")
    res = {}
    for line in out.splitlines():
        if line.startswith("R "):
            _, a, v, d = line.split()
            res[(int(a), int(v, 16))] = int(d, 16)
    assert len(res) == 32 * len(set(vals))
    return res


@pytest.mark.parametrize("w", WIDTHS)
def test_the_nibble_mask_equals_the_real_mask_cell(w, tmp_path):
    r = random.Random(w + 1)
    cases = [(1, nm, v) for nm in (0, 1, 2, 0x0F, 0x10, 0x55, 0xAA, 0xFF, 0xE0, 0xA5, r.getrandbits(8)) for v in values(w, 4)] + [(0, 0xFF, v) for v in values(w, 3)]
    rtl = rtl_mask(w, cases, tmp_path)
    keep = (1 << min(w, 32)) - 1 if w > 32 else (1 << w) - 1   # at W > 32 the real cell's nibble 8+ is x (see the pinned defect below): compare the defined 32 bits there
    cmp = lambda e, x: x & keep if (w > 32 and e) else x
    bad = [(e, hex(nm), hex(v), hex(fg.flex_addons(v, {"mask_en": e, "nibble_mask": nm}, w)), hex(rtl[(e, nm, v)])) for e, nm, v in cases if cmp(e, fg.flex_addons(v, {"mask_en": e, "nibble_mask": nm}, w)) != cmp(e, rtl[(e, nm, v)])]
    assert not bad, f"width {w}: mask differs from the RTL: {bad[:3]}"


@pytest.mark.parametrize("w", WIDTHS)
@pytest.mark.parametrize("direction", [0, 1])
def test_the_shifts_equal_the_real_shift_stage_for_every_total(w, direction, tmp_path):
    vals = values(w, 3)
    rtl = rtl_shift(w, direction, vals, tmp_path)
    bad = []
    for fine in range(4):
        for amt in (0,) + COARSE:
            total = fine + amt
            if total > 31:
                continue
            for v in vals:
                got = fg.flex_addons(v, {"shift_en": 1, "direction": direction, "shift_fine": fine, "shift_amt": amt}, w)
                if got != rtl[(total, v)]:
                    bad.append((fine, amt, hex(v), hex(got), hex(rtl[(total, v)])))
    assert not bad, f"width {w} dir {direction}: shift differs from the RTL: {bad[:3]}"


@pytest.mark.parametrize("w", WIDTHS)
def test_the_whole_chain_equals_the_rtl_stages_composed(w, tmp_path):
    r = random.Random(w + 7)
    cfgs = []
    for _ in range(40):
        cfgs.append({"mask_en": r.getrandbits(1) if w <= 32 else 0, "nibble_mask": r.getrandbits(8), "shift_en": r.getrandbits(1), "direction": r.getrandbits(1),
                     "shift_fine": r.getrandbits(2), "shift_amt": r.choice((0,) + COARSE), "invert_en": r.getrandbits(1)})
    vals = values(w, 2)
    masks = rtl_mask(w, [(c["mask_en"], c["nibble_mask"], v) for c in cfgs for v in vals], tmp_path)
    shifts = {d: rtl_shift(w, d, sorted(set(masks.values())), tmp_path) for d in (0, 1)}
    m = (1 << w) - 1
    bad = []
    for c in cfgs:
        for v in vals:
            x = masks[(c["mask_en"], c["nibble_mask"], v)]
            if c["shift_en"]:
                total = c["shift_fine"] + (c["shift_amt"] if c["shift_amt"] in COARSE else 0)
                x = shifts[c["direction"]][(total, x)] if total <= 31 else x
            if c["invert_en"]:
                x = ~x & m
            if fg.flex_addons(v, c, w) != x:
                bad.append((c, hex(v)))
    assert not bad, f"width {w}: chain differs from composed RTL stages: {bad[:2]}"


def test_through_a_flexgrid_cell_the_addon_is_applied_at_width_18():
    recs = [IcmV3Record(cell_id="X", row=0, col=0, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["e"]}),
            IcmV3Record(cell_id="M", row=0, col=1, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": ["e"]}, addon_config={"mask_en": 1, "nibble_mask": 0b1, "invert_en": 1}),
            IcmV3Record(cell_id="E", row=0, col=2, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": []})]
    g = fg.FlexGrid(recs, width=18)
    g.inject(0, 0, 0x2ABCD)
    for _ in range(20):
        g.tick()
    e = g.cells[(0, 2)]
    assert e.ram_data_valid and e.ram_data_reg == (~(0x2ABCD & ~0xF) & 0x3FFFF)


def test_std_vm_still_refuses_addons_at_other_widths_and_flexgrid_refuses_lane_cut():
    cfg = {"mask_en": 1, "nibble_mask": 1}
    with pytest.raises(ValueError):
        vm.apply_addons(5, cfg, 18)
    recs = [IcmV3Record(cell_id="M", row=0, col=0, core="ram", core_config={"upstream_mask": [], "downstream_mask": ["e"]}, addon_config={"shift_en": 1, "direction": 1, "shift_amt": 8, "lane_cut": 1})]
    with pytest.raises(ValueError, match="lane_cut"):
        fg.FlexGrid(recs, width=18)
    fg.FlexGrid(recs, width=32)


def test_the_comparison_bites_a_chain_that_ignores_the_width(tmp_path):
    w = 18
    vals = values(w, 3)
    rtl = rtl_shift(w, 0, vals, tmp_path)
    # a left shift computed on 32 bits and not cut back to W bits would keep bits above W
    wrong = sum(1 for v in vals if (v << 4) & 0xFFFFFFFF != rtl[(4, v)])
    assert wrong > 0


def test_known_rtl_defect_the_mask_cell_has_no_mask_bit_for_nibbles_above_7(tmp_path):
    """FINDING (ledger #967): mask_cell_v4sa keeps nibble_mask in an 8-bit reg but instantiates NIBBLES = ceil(W/4) nibbles, so at W > 32 nibble 8 reads nibble_mask[8] (out of range) and its output is x
    while the mask is enabled. Pinned here so a fix is noticed. The mirror treats nibbles above 7 as never masked (the natural reading); at W <= 32 nothing is affected."""
    for w in (18, 32):
        XBITS.clear()
        rtl_mask(w, [(1, 0xFF, 0xFFFFFFFF & ((1 << w) - 1))], tmp_path)
        assert (w, 1) not in XBITS, f"unexpected x at width {w}"
    XBITS.clear()
    rtl_mask(36, [(1, 0xFF, (1 << 36) - 1)], tmp_path)
    assert (36, 1) in XBITS, "the width-36 mask cell no longer drives x for nibble 8: the defect looks FIXED -- update the test and the mirror's note"
