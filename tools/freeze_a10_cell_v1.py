#!/usr/bin/env python3
"""freeze_a10_cell_v1.py -- ledger #1036 addendum 67: does `freeze_in` HOLD the state of an Arria 10 line cell (adder_cell_v4c, fpga/verilog)?

The Tang flex cells treat freeze_in as a clock enable on every register (addenda 63, 64). The Arria 10 (v4c) cells gate captures, firing, offers and ready on freeze_in, but their
register block has other branches. This tool tests one v4c adder cell in simulation (iverilog): the cell runs one add with a two-operand handshake and a consumer; the driver and consumer
advance only on cycles when freeze is low (the environment stops with the freeze). For a freeze window of 8 cycles starting at every cycle 0..30 it checks (1) that no register of the cell changes during the
window (read by hierarchical name, 14 registers) and (2) that the outputs, in their own un-frozen cycle count, equal the un-frozen run. SIMULATION OF ONE CELL ONLY: not a design, not hardware.
"""
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = os.path.join(ROOT, "fpga", "verilog")
REGS = ["a_reg", "a_arrived", "out_buffer", "data_valid", "downstream_mask", "upstream_mask", "subtract_mode", "second_output", "second_downstream_mask",
        "captured_carry", "delivering_carry", "phase1_offered", "pending_ack", "armed"]
W = 8   # freeze window, cycles

TB = """`timescale 1ns/1ps
module tb;
  reg clk = 0; always #5 clk = ~clk;
  reg rst = 1, cfg = 0, frz = 0; reg [63:0] cfg_d = 0;
  localparam [5:0] DIR_N6 = 6'b000001, DIR_E6 = 6'b000100, DIR_W6 = 6'b001000;
  localparam [63:0] CFG_DUT = {51'h0, 1'b0, (DIR_N6 | DIR_W6), DIR_E6};
  reg [31:0] opA = 0, opB = 0; reg pulse_a = 0, pulse_b = 0;
  wire [31:0] sum_out_e; wire fire_e, ready_o, ack_out_n, ack_out_w, status_dv, status_aa, program_done;
  wire pn, ps, pe, pw; reg cons_ack = 0;
  adder_cell_v4c #(.CELL_ID(16'h0000)) DUT (
    .clk(clk), .rst(rst), .active(1'b1), .cfg_valid(cfg), .cfg_data(cfg_d),
    .data_in_n(opA), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(opB),
    .arrived_n(pulse_a), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(pulse_b),
    .data_out_n(), .data_out_s(), .data_out_e(sum_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(), .ready_out(ready_o),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(ack_out_w),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
    .program_in(1'b0), .program_done(program_done),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .prog_ack_out_n(pn), .prog_ack_out_s(ps), .prog_ack_out_e(pe), .prog_ack_out_w(pw),
    .freeze_in(frz), .status_data_valid(status_dv), .status_a_arrived(status_aa));
  // driver and consumer advance only on cycles with freeze low, so the environment stops with the freeze
  integer cyc = 0, t0, tend;
  reg [1:0] cs = 0; reg go = 0;
  always @(posedge clk) if (!rst && go && !frz) begin
    cyc <= cyc + 1;
    pulse_a <= (cyc == 2); opA <= 32'd1000;
    pulse_b <= (cyc == 7); opB <= 32'd234;
    cons_ack <= 1'b0;
    case (cs)
      0: if (fire_e) begin $display("OUT %0d %0d", cyc, sum_out_e); cs <= 1; end
      1: begin cons_ack <= 1'b1; cs <= 2; end
      2: cs <= 0;
    endcase
  end
  function [511:0] snap(input dummy);
    snap = {DUT.a_reg, DUT.a_arrived, DUT.out_buffer, DUT.data_valid, DUT.downstream_mask, DUT.upstream_mask, DUT.subtract_mode, DUT.second_output,
            DUT.second_downstream_mask, DUT.captured_carry, DUT.delivering_carry, DUT.phase1_offered, DUT.pending_ack, DUT.armed};
  endfunction
  reg [511:0] s0, s1;
  integer k;
  initial begin
    if (!$value$plusargs("t=%d", t0)) t0 = -1;
    #12 rst = 0; #10 cfg = 1; cfg_d = CFG_DUT; #10 cfg = 0; @(negedge clk); go = 1;
    // run until the un-frozen cycle counter reaches the freeze point, freeze at a negedge, hold W cycles, release
    if (t0 >= 0) begin
      wait (cyc == t0); @(negedge clk);
      s0 = snap(0); frz = 1;
      repeat (WIN) @(negedge clk);
      s1 = snap(0);
      $display("HOLD %0d", s0 === s1);
      frz = 0;
    end
    repeat (40) @(negedge clk);
    $display("END");
    $finish;
  end
endmodule
""".replace("WIN", str(W))


def main():
    if not (shutil.which("iverilog") and shutil.which("vvp")):
        print("iverilog REQUIRED")
        return 2
    d = tempfile.mkdtemp(prefix="a10frz_")
    try:
        tb = os.path.join(d, "tb.v")
        open(tb, "w").write(TB)
        vvp = os.path.join(d, "t.vvp")
        srcs = [os.path.join(V, f) for f in ("adder_cell_v4c.v", "adder_v1.v") if os.path.exists(os.path.join(V, f))]
        r = subprocess.run(["iverilog", "-g2012", "-o", vvp, tb] + srcs + [os.path.join(V, f) for f in os.listdir(V) if f.endswith("_addon_v1.v")], capture_output=True, text=True)
        if r.returncode != 0:
            print(r.stderr[-1500:])
            return 1

        def run(t):
            o = subprocess.run(["vvp", vvp] + ([f"+t={t}"] if t is not None else []), capture_output=True, text=True, timeout=30).stdout
            outs = [tuple(map(int, l.split()[1:])) for l in o.splitlines() if l.startswith("OUT")]
            hold = [l.split()[1] for l in o.splitlines() if l.startswith("HOLD")]
            return outs, hold
        base, _ = run(None)
        print("un-frozen run:", base)
        held = changed = same_out = diff_out = 0
        bad_hold, bad_out = [], []
        for t in range(0, 31):
            outs, hold = run(t)
            if hold:
                if hold[0] == "1":
                    held += 1
                else:
                    changed += 1
                    bad_hold.append(t)
            if outs == base:
                same_out += 1
            else:
                diff_out += 1
                bad_out.append((t, outs))
        print(f"registers unchanged during the {W}-cycle freeze at {held} of {held + changed} start cycles; changed at {changed} {bad_hold}")
        print(f"outputs equal to the un-frozen run at {same_out} of {same_out + diff_out} start cycles; differ at {diff_out} {bad_out[:4]}")
        main.result = (held, changed, same_out, diff_out, bad_hold)
        return 0
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
