// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_ram_v3_diff_v1.v — points.md #699: real, differential proof that
// ram_cell_v3.v's own config-off-shell change (downstream_mask/
// upstream_mask/fixed_mode read continuously, no local latch) is
// genuinely behavior-preserving under NORMAL driving (a real
// cfg_valid pulse, matching exactly how a real shell drives either
// version), same real discipline `tb_ram_v2_diff_v1.v` already used
// for a different real change to this same core. A SECOND, separate
// real test then demonstrates the actual NEW capability this fix
// provides: v3 reflects a config change on `cfg_data` immediately,
// with no fresh `cfg_valid` pulse at all -- v1 provably does not.
`default_nettype none
`timescale 1ns / 1ps

module tb_ram_v3_diff_v1;

reg clk = 0;
always #5 clk = ~clk;
reg rst = 1;
reg cfg_valid = 0;
reg [63:0] cfg_data = 0;
reg [31:0] data_in_n = 0;
reg arrived_n = 0;
reg ack_in_e = 0;

wire [31:0] v1_dout_e;
ram_cell_v1 DUT_V1 (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v1_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid()
);

wire [31:0] v3_dout_e;
ram_cell_v3 DUT_V3 (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v3_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid()
);

integer errors = 0;

task check_match(input [255:0] label);
    begin
        if (v1_dout_e !== v3_dout_e) begin
            $display("FAIL (%0s): v1_dout_e=%h v3_dout_e=%h", label, v1_dout_e, v3_dout_e);
            errors = errors + 1;
        end
    end
endtask

initial begin
    #12 rst = 0;

    // ── Part 1: behavior-preserving under NORMAL driving (a real
    // cfg_valid pulse, exactly how a real shell drives either
    // version) -- downstream=e, upstream=n, fixed_mode=0,
    // load_data_valid=0, init_data=0. ──
    @(posedge clk); cfg_valid = 1;
    cfg_data = {22'b0, 32'h0, 1'b0, 1'b0, 4'b0001 /*upstream=n*/, 4'b0100 /*downstream=e*/};
    @(posedge clk); #1 cfg_valid = 0;
    #10;
    check_match("after config, both empty");

    // Deliver a real value from the north, confirm both capture and
    // offer it identically east.
    @(posedge clk); arrived_n = 1; data_in_n = 32'hCAFEBEEF;
    @(posedge clk); #1 arrived_n = 0;
    #10;
    check_match("after real capture+offer");
    if (v1_dout_e !== 32'hCAFEBEEF) begin
        $display("FAIL: v1_dout_e should be CAFEBEEF, got %h", v1_dout_e);
        errors = errors + 1;
    end

    // Ack it, confirm both drain identically.
    @(posedge clk); ack_in_e = 1;
    @(posedge clk); #1 ack_in_e = 0;
    #10;
    check_match("after real drain");

    // ── Part 2: the real, NEW capability -- v3 reflects a config
    // change on cfg_data with NO fresh cfg_valid pulse at all; v1
    // provably does not (its own local latch stays exactly as it was
    // last configured). Change downstream_mask from east to west on
    // the live wire, without ever pulsing cfg_valid again. ──
    cfg_data = {22'b0, 32'h0, 1'b0, 1'b0, 4'b0001 /*upstream=n*/, 4'b1000 /*downstream=w, changed*/};
    #10;

    if (DUT_V1.downstream_mask !== 4'b0100) begin
        $display("FAIL: v1's own local latch should STILL read east (stale) -- got %b", DUT_V1.downstream_mask);
        errors = errors + 1;
    end
    if (DUT_V3.downstream_mask !== 4'b1000) begin
        $display("FAIL: v3 should reflect the live config change (west) with no new cfg_valid pulse -- got %b", DUT_V3.downstream_mask);
        errors = errors + 1;
    end

    if (errors == 0)
        $display("PASS: tb_ram_v3_diff_v1 -- v3 preserves v1's real behavior under normal driving, AND reflects live config changes v1's own local latch cannot see");
    else
        $display("FAIL: tb_ram_v3_diff_v1 -- %0d real mismatch(es)", errors);
    $finish;
end

endmodule
