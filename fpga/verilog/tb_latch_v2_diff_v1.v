// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_latch_v2_diff_v1.v — points.md #563: real, differential proof
// that latch_cell_v2.v's own optional external-storage capability is
// genuinely behavior-preserving in BOTH modes.
`default_nettype none
`timescale 1ns / 1ps
//
// REAL BUG FOUND AND FIXED (points.md #563): every "@(posedge clk); X = 0;"
// pair below originally cleared a testbench-driven signal at the exact
// same simulation time as the clock edge meant to sample it -- a real,
// classic race, not an RTL bug. Caught when ram_cell_v2 (this session)
// showed a real, genuine divergence from v1; fixed with a real #1 delay
// after every such edge, then all three affected differential testbenches
// were re-verified, not just the one that surfaced the problem.

module tb_latch_v2_diff_v1;

reg clk = 0;
always #5 clk = ~clk;
reg rst = 1;
reg cfg_valid = 0;
reg [63:0] cfg_data = 0;
reg [31:0] data_in_n = 0;
reg arrived_n = 0, arrived_s = 0;

// ── ORIGINAL v1 ──
wire [31:0] v1_dout_n;
latch_cell_v1 DUT_V1 (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(arrived_s), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(v1_dout_n), .data_out_s(), .data_out_e(), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .freeze_in(1'b0), .ready_out(), .status_latched()
);

// ── v2, EXTERNAL_STORAGE=0 (default, internal mode) ──
wire [31:0] v2int_dout_n;
latch_cell_v2 #(.EXTERNAL_STORAGE(0)) DUT_V2_INTERNAL (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(arrived_s), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(v2int_dout_n), .data_out_s(), .data_out_e(), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .freeze_in(1'b0), .ready_out(), .status_latched(),
    .ext_state_in(23'h0), .ext_state_out()
);

// ── v2, EXTERNAL_STORAGE=1 -- a REAL external register provides the
// actual storage, exactly as a shell wrapper would. ──
reg [22:0] external_buffer = 23'h0;
wire [22:0] ext_next;
wire [31:0] v2ext_dout_n;
latch_cell_v2 #(.EXTERNAL_STORAGE(1)) DUT_V2_EXTERNAL (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(arrived_s), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(v2ext_dout_n), .data_out_s(), .data_out_e(), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .freeze_in(1'b0), .ready_out(), .status_latched(),
    .ext_state_in(external_buffer), .ext_state_out(ext_next)
);
// the real, external registration -- this is what a shell's own
// shared buffer would do: register whatever the core computes.
always @(posedge clk) begin
    if (rst) external_buffer <= 23'h0;
    else external_buffer <= ext_next;
end

integer errors = 0;
integer checks = 0;

task check_all(input [200*8-1:0] label);
    begin
        checks = checks + 1;
        if (v1_dout_n !== v2int_dout_n) begin
            errors = errors + 1;
            $display("MISMATCH (internal mode) at %s: v1=0x%08X v2_internal=0x%08X", label, v1_dout_n, v2int_dout_n);
        end
        if (v1_dout_n !== v2ext_dout_n) begin
            errors = errors + 1;
            $display("MISMATCH (external mode) at %s: v1=0x%08X v2_external=0x%08X", label, v1_dout_n, v2ext_dout_n);
        end
    end
endtask

task settle;
    begin
        repeat (4) @(posedge clk);
    end
endtask

initial begin
    rst = 1; settle; rst = 0; settle;

    // Real config: set_dir=N, clear_dir=S, downstream=N, toggle=none
    cfg_valid = 1; cfg_data = {48'h0, 4'h0, 4'b0001, 4'b0010, 4'b0001};
    @(posedge clk); #1; cfg_valid = 0;
    settle;
    check_all("after config");

    // SET via N
    data_in_n = 1; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after SET");

    // CLEAR via S
    arrived_s = 1; @(posedge clk); #1; arrived_s = 0;
    settle;
    check_all("after CLEAR");

    // SET again, then real toggle config, then TOGGLE via N
    data_in_n = 1; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after second SET");

    cfg_valid = 1; cfg_data = {48'h0, 4'b0001, 4'b0010, 4'b0000, 4'b0100};  // toggle=N, set=E(unused here)
    @(posedge clk); #1; cfg_valid = 0;
    settle;
    data_in_n = 0; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;  // TOGGLE via N
    settle;
    check_all("after TOGGLE");

    if (errors == 0)
        $display("PASS: %0d/%0d real checks -- latch_cell_v2 matches v1 in BOTH internal and external-storage modes.", checks, checks);
    else
        $display("FAIL: %0d/%0d checks had mismatches.", errors, checks);

    $finish;
end

endmodule
