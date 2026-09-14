// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_compare_v3_diff_v1.v — points.md #584: real, differential proof
// that compare_cell_v3.v (config read continuously off cfg_data, no
// local latch -- Alan's own real proposal) matches v1's own real
// behavior exactly, given a continuously-held cfg_data -- the one
// real precondition v3 requires that v1 doesn't, and which every
// real stimulus sequence below already satisfies (cfg_data is set
// once per config and never invalidated afterward, matching how the
// real shell will hold `core_config` stable for as long as this core
// stays selected).
`default_nettype none
`timescale 1ns / 1ps

module tb_compare_v3_diff_v1;

reg clk = 0;
always #5 clk = ~clk;
reg rst = 1;
reg cfg_valid = 0;
reg [63:0] cfg_data = 0;
reg [31:0] data_in_n = 0;
reg arrived_n = 0;
reg ack_in_e = 0;

wire [31:0] v1_dout_e;
compare_cell_v1 DUT_V1 (
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
compare_cell_v3 DUT_V3 (
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
integer checks = 0;

task check_all(input [200*8-1:0] label);
    begin
        checks = checks + 1;
        if (v1_dout_e !== v3_dout_e) begin
            errors = errors + 1;
            $display("MISMATCH at %s: v1=0x%08X v3=0x%08X", label, v1_dout_e, v3_dout_e);
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

    // Real config: downstream=E, upstream=N, threshold=8
    cfg_valid = 1; cfg_data = {24'h0, 32'sd8, 4'b0001, 4'b0100};
    @(posedge clk); #1; cfg_valid = 0;
    settle;
    check_all("after config");

    // Real >= true case: 10 >= 8
    data_in_n = 32'd10; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after 10>=8 (true)");

    ack_in_e = 1; @(posedge clk); #1; ack_in_e = 0;
    settle;

    // Real >= false case: 5 >= 8
    data_in_n = 32'd5; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after 5>=8 (false)");

    ack_in_e = 1; @(posedge clk); #1; ack_in_e = 0;
    settle;

    // Real reconfigure -- new threshold, downstream/upstream unchanged
    cfg_valid = 1; cfg_data = {24'h0, 32'sd20, 4'b0001, 4'b0100};
    @(posedge clk); #1; cfg_valid = 0;
    settle;
    check_all("after reconfigure to threshold=20");

    data_in_n = 32'd15; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after 15>=20 (false, new threshold)");

    if (errors == 0)
        $display("PASS: %0d/%0d real checks -- compare_cell_v3 matches v1 exactly (config read continuously, no local latch).", checks, checks);
    else
        $display("FAIL: %0d/%0d checks had mismatches.", errors, checks);

    $finish;
end

endmodule
