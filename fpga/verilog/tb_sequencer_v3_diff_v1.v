// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_sequencer_v3_diff_v1.v — points.md #699: real, differential proof
// that sequencer_cell_v3.v's own config-off-shell change (all six real
// config fields now continuous, not just the routing/mode ones --
// value_0-3/sequence_len_m1 are read repeatedly, every real advance,
// #699's own found distinction) is genuinely behavior-preserving
// under normal driving, including a real wrap-around cycle, plus the
// new live-config-reflection capability.
`default_nettype none
`timescale 1ns / 1ps

module tb_sequencer_v3_diff_v1;

reg clk = 0;
always #5 clk = ~clk;
reg rst = 1;
reg cfg_valid = 0;
reg [63:0] cfg_data = 0;
reg ack_in_e = 0;

wire [31:0] v1_dout_e;
sequencer_cell_v1 DUT_V1 (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v1_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .ready_out(), .status_seq_index()
);

wire [31:0] v3_dout_e;
sequencer_cell_v3 DUT_V3 (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v3_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .ready_out(), .status_seq_index()
);

integer errors = 0;
integer i;

task ack_and_check(input [7:0] expected);
    begin
        @(posedge clk); ack_in_e = 1;
        @(posedge clk); #1 ack_in_e = 0;
        #10;
        if (v1_dout_e[7:0] !== expected || v3_dout_e[7:0] !== expected) begin
            $display("FAIL: expected %0d, got v1=%0d v3=%0d", expected, v1_dout_e[7:0], v3_dout_e[7:0]);
            errors = errors + 1;
        end
    end
endtask

initial begin
    #12 rst = 0;

    // Real sequence: 11,22,33,44 (SEQUENCE_LEN=4, stored as 3),
    // downstream=e. A real, full wrap-around cycle.
    @(posedge clk); cfg_valid = 1;
    cfg_data = {26'b0, 4'b0100 /*downstream=e*/, 2'd3 /*len-1=3*/, 8'd44, 8'd33, 8'd22, 8'd11};
    @(posedge clk); #1 cfg_valid = 0;
    #10;

    if (v1_dout_e[7:0] !== 8'd11 || v3_dout_e[7:0] !== 8'd11) begin
        $display("FAIL: initial value should be 11, got v1=%0d v3=%0d", v1_dout_e[7:0], v3_dout_e[7:0]);
        errors = errors + 1;
    end
    ack_and_check(8'd22);
    ack_and_check(8'd33);
    ack_and_check(8'd44);
    ack_and_check(8'd11);   // real wrap-around back to the first value

    // ── The real, new capability -- v3 reflects a live change to
    // VALUE_0 with NO fresh cfg_valid pulse; v1's own local latch
    // stays stale. ──
    cfg_data = {26'b0, 4'b0100, 2'd3, 8'd44, 8'd33, 8'd22, 8'd99 /*VALUE_0 changed live*/};
    #10;
    // Force both to the wrap point so the NEXT advance reads VALUE_0 again.
    @(posedge clk); ack_in_e = 1;   // completes the current (11) offer -> advances to 22
    @(posedge clk); #1 ack_in_e = 0;
    #10;
    for (i = 0; i < 3; i = i + 1) begin
        @(posedge clk); ack_in_e = 1;
        @(posedge clk); #1 ack_in_e = 0;
        #10;
    end
    // Now both should be back at index 0 -- v1 re-offers its own
    // stale, LATCHED value_0 (11); v3 re-offers the LIVE value_0 (99).
    if (DUT_V1.value_0 !== 8'd11) begin
        $display("FAIL: v1's own local latch should STILL read VALUE_0=11 (stale) -- got %0d", DUT_V1.value_0);
        errors = errors + 1;
    end
    if (v3_dout_e[7:0] !== 8'd99) begin
        $display("FAIL: v3 should offer the LIVE VALUE_0=99 with no new cfg_valid pulse -- got %0d", v3_dout_e[7:0]);
        errors = errors + 1;
    end

    if (errors == 0)
        $display("PASS: tb_sequencer_v3_diff_v1 -- v3 preserves v1's real behavior (full wrap-around), AND reflects live config changes v1's own local latch cannot see");
    else
        $display("FAIL: tb_sequencer_v3_diff_v1 -- %0d real mismatch(es)", errors);
    $finish;
end

endmodule
