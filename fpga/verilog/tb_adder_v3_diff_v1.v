// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_adder_v3_diff_v1.v — points.md #699: real, differential proof
// that adder_cell_v3.v's own config-off-shell change is genuinely
// behavior-preserving under normal driving (two real operands via the
// same real two-stage A/B capture, real subtract_mode behavior), plus
// a second real test demonstrating the new live-config-reflection
// capability.
`default_nettype none
`timescale 1ns / 1ps

module tb_adder_v3_diff_v1;

reg clk = 0;
always #5 clk = ~clk;
reg rst = 1;
reg cfg_valid = 0;
reg [63:0] cfg_data = 0;
reg [31:0] data_in_n = 0;
reg arrived_n = 0;
reg ack_in_e = 0;

wire [31:0] v1_dout_e;
adder_cell_v1 DUT_V1 (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v1_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid(), .status_a_arrived()
);

wire [31:0] v3_dout_e;
adder_cell_v3 DUT_V3 (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v3_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid(), .status_a_arrived()
);

integer errors = 0;

initial begin
    #12 rst = 0;

    // ── Part 1: behavior-preserving, real add then real subtract,
    // under normal driving. downstream=e, upstream=n. ──
    @(posedge clk); cfg_valid = 1;
    cfg_data = {55'b0, 1'b0 /*subtract_mode*/, 4'b0001 /*upstream=n*/, 4'b0100 /*downstream=e*/};
    @(posedge clk); #1 cfg_valid = 0;
    #10;

    // A=100, B=23 -> 123
    @(posedge clk); arrived_n = 1; data_in_n = 32'd100;
    @(posedge clk); #1 arrived_n = 0;
    #10;
    @(posedge clk); arrived_n = 1; data_in_n = 32'd23;
    @(posedge clk); #1 arrived_n = 0;
    #10;
    if (v1_dout_e !== 32'd123 || v3_dout_e !== 32'd123) begin
        $display("FAIL: real add -- v1=%0d v3=%0d, expected 123", v1_dout_e, v3_dout_e);
        errors = errors + 1;
    end
    @(posedge clk); ack_in_e = 1;
    @(posedge clk); #1 ack_in_e = 0;
    #10;

    // Real subtract mode: A=100, B=23 -> 77
    @(posedge clk); cfg_valid = 1;
    cfg_data = {55'b0, 1'b1 /*subtract_mode*/, 4'b0001, 4'b0100};
    @(posedge clk); #1 cfg_valid = 0;
    #10;
    @(posedge clk); arrived_n = 1; data_in_n = 32'd100;
    @(posedge clk); #1 arrived_n = 0;
    #10;
    @(posedge clk); arrived_n = 1; data_in_n = 32'd23;
    @(posedge clk); #1 arrived_n = 0;
    #10;
    if (v1_dout_e !== 32'd77 || v3_dout_e !== 32'd77) begin
        $display("FAIL: real subtract -- v1=%0d v3=%0d, expected 77", v1_dout_e, v3_dout_e);
        errors = errors + 1;
    end
    @(posedge clk); ack_in_e = 1;
    @(posedge clk); #1 ack_in_e = 0;
    #10;

    // ── Part 2: the real, new capability -- v3 reflects a live
    // subtract_mode change with NO fresh cfg_valid pulse; v1's own
    // local latch stays stale. ──
    cfg_data = {55'b0, 1'b0 /*subtract_mode back to 0, no new pulse*/, 4'b0001, 4'b0100};
    #10;
    if (DUT_V1.subtract_mode !== 1'b1) begin
        $display("FAIL: v1's own local latch should STILL read subtract_mode=1 (stale) -- got %b", DUT_V1.subtract_mode);
        errors = errors + 1;
    end
    if (DUT_V3.subtract_mode !== 1'b0) begin
        $display("FAIL: v3 should reflect the live config change (subtract_mode=0) with no new cfg_valid pulse -- got %b", DUT_V3.subtract_mode);
        errors = errors + 1;
    end

    if (errors == 0)
        $display("PASS: tb_adder_v3_diff_v1 -- v3 preserves v1's real behavior (add+subtract), AND reflects live config changes v1's own local latch cannot see");
    else
        $display("FAIL: tb_adder_v3_diff_v1 -- %0d real mismatch(es)", errors);
    $finish;
end

endmodule
