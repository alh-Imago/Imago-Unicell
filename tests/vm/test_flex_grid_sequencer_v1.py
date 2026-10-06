"""tests/vm/test_flex_grid_sequencer_v1.py -- FlexGrid step 6: the SEQUENCER at width W against the REAL sequencer_cell_v4sa (ledger #970).

The flex sequencer is free-running in the design (the generator ties its advance to the cell's own ready), but the cell itself only advances on advance_in and offers value_for_index(next index) after
each pulse, so after configuration the first pulse offers VALUE_1 and the pulses wrap through SEQUENCE_LEN+1 values. The VM's sequencer offers VALUE_0 first and advances on each drain; the generator
rotates the stored values to reconcile the two. Here the real cell is driven with advance pulses and its offers compared with what a FlexGrid sequencer (consumed by a relay and read by the host)
delivers, with that one-step rotation applied. The stored values are 8 bits wide in the RTL and zero-extended to the data width; below 8 bits the RTL cell does not even elaborate (it replicates a
negative count), so FlexGrid refuses a sequencer at width < 8. Requires iverilog and FAILS without it.
"""
import os
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
WIDTHS = (8, 18, 32, 36)
CONFIGS = [((0x11, 0x22, 0x33, 0x44), 3), ((0xAA, 0x55, 0, 0), 1), ((0xFF, 0, 0, 0), 0), ((1, 2, 3, 0), 2), ((0, 0, 0, 0), 3), ((0x80, 0x7F, 0xFF, 0x01), 3)]


def rtl_offers(w, values, len_m1, n, tmp_path):
    """configure, read the post-config buffer, then n times: advance pulse, read the offer, acknowledge. Returns (initial buffer, [offers])."""
    assert shutil.which("iverilog") and shutil.which("vvp"), "iverilog is REQUIRED (this test must not skip silently)"
    cfg = sum(v << (8 * k) for k, v in enumerate(values))
    tb = f"""`timescale 1ns/1ps
module tb;
  parameter W = {w};
  reg clk = 0, rst = 1, freeze = 0, cfgv = 0, adv = 0, ackin = 0; reg [31:0] cfgd = 0; reg [1:0] lm1 = 0;
  wire ackout, vout; wire [W-1:0] dout;
  sequencer_cell_v4sa #(.CELL_ID(16'd0), .WIDTH(W)) dut (.clk(clk), .rst(rst), .freeze_in(freeze), .cfg_valid(cfgv), .cfg_data(cfgd), .cfg_seq_len_m1(lm1), .advance_in(adv), .ack_out(ackout), .data_out(dout), .valid_out(vout), .ack_in(ackin));
  always #5 clk = ~clk;
  integer i;
  initial begin
    repeat (3) @(posedge clk); #1 rst = 0;
    cfgd = 32'h{cfg:08X}; lm1 = {len_m1}; cfgv = 1; @(posedge clk); #1; cfgv = 0;
    $display("I %h", dout);
    for (i = 0; i < {n}; i = i + 1) begin
      adv = 1; @(posedge clk); #1; adv = 0;
      if (!vout) $display("NOVALID");
      $display("O %h", dout);
      ackin = 1; @(posedge clk); #1; ackin = 0;
    end
    $finish;
  end
endmodule
"""
    f = tmp_path / f"tbseq_{w}_{len_m1}_{cfg:08x}.v"
    f.write_text(tb)
    exe = tmp_path / (f.stem + ".vvp")
    c = subprocess.run(["iverilog", "-g2012", "-o", str(exe), str(f), os.path.join(V, "sequencer_cell_v4sa.v")], capture_output=True, text=True)
    assert c.returncode == 0, c.stderr[:400]
    out = subprocess.run(["vvp", str(exe)], capture_output=True, text=True).stdout
    assert "NOVALID" not in out
    init = [int(l.split()[1], 16) for l in out.splitlines() if l.startswith("I ")]
    offers = [int(l.split()[1], 16) for l in out.splitlines() if l.startswith("O ")]
    assert len(init) == 1 and len(offers) == n, out[:300]
    return init[0], offers


def vm_offers(w, values, len_m1, n):
    recs = [IcmV3Record(cell_id="S", row=0, col=0, core="sequencer", core_config={"VALUE_0": values[0], "VALUE_1": values[1], "VALUE_2": values[2], "VALUE_3": values[3], "SEQUENCE_LEN": len_m1, "downstream_mask": ["e"]}),
            IcmV3Record(cell_id="E", row=0, col=1, core="ram", core_config={"upstream_mask": ["w"], "downstream_mask": []})]
    g = fg.FlexGrid(recs, width=w)
    e = g.cells[(0, 1)]
    seen = []
    for _ in range(12 * n + 20):
        g.tick()
        if e.ram_data_valid:
            seen.append(e.ram_data_reg)
            e.ram_data_valid = False
        if len(seen) >= n:
            break
    return seen


@pytest.mark.parametrize("w", WIDTHS)
def test_flexgrid_sequencer_equals_the_real_cell_with_the_generators_one_step_rotation(w, tmp_path):
    bad = []
    for values, len_m1 in CONFIGS:
        n = 2 * (len_m1 + 1) + 1
        init, offers = rtl_offers(w, values, len_m1, n, tmp_path)
        mine = vm_offers(w, values, len_m1, n)
        want = [init] + offers[:n - 1]          # the VM offers VALUE_0 first; the cell's pulse k offers the value after it, so the VM's k-th offer is the cell's (k-1)-th
        if mine != want:
            bad.append((values, len_m1, [hex(x) for x in mine], [hex(x) for x in want]))
    assert not bad, f"width {w}: {bad[:2]}"


def test_a_sequencer_is_refused_below_8_bits_where_the_real_cell_cannot_be_built():
    rec = IcmV3Record(cell_id="S", row=0, col=0, core="sequencer", core_config={"VALUE_0": 1, "downstream_mask": ["e"]})
    with pytest.raises(ValueError, match="sequencer"):
        fg.FlexGrid([rec], width=4)
    fg.FlexGrid([rec], width=8)


def test_the_std_vm_still_builds_a_sequencer_at_any_width():
    import unicell_super_automaton_v1 as vm
    rec = IcmV3Record(cell_id="S", row=0, col=0, core="sequencer", core_config={"VALUE_0": 1, "downstream_mask": ["e"]})
    vm.SuperGrid([rec], width=4)


def test_the_comparison_bites_a_rotation_that_is_left_out(tmp_path):
    values, len_m1 = CONFIGS[0]
    init, offers = rtl_offers(18, values, len_m1, 5, tmp_path)
    assert offers[:5] != vm_offers(18, values, len_m1, 5), "the raw cell offers VALUE_1 first; the VM VALUE_0: without the rotation they must differ"
