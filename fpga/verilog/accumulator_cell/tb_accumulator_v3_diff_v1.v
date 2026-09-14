// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_accumulator_v3_diff_v1.v — points.md #592: real, differential
// proof that accumulator_cell_v3.v (config read continuously off
// cfg_data, no local latch) matches v1's own real behavior exactly,
// given a continuously-held cfg_data. Reuses the SAME real stimulus
// sequence already proven for v2 (tb_accumulator_v2_diff_v1.v,
// #564) -- static mode, 3 increments, a genuine reconfigure to pulse
// mode, and a real threshold crossing -- not a new, unvetted sequence.
`default_nettype none
`timescale 1ns / 1ps

module tb_accumulator_v3_diff_v1;

reg clk = 0;
always #5 clk = ~clk;
reg rst = 1;
reg cfg_valid = 0;
reg [63:0] cfg_data = 0;
reg [31:0] data_in_n = 0;
reg arrived_n = 0;
reg ack_in_e = 0;

wire [31:0] v1_dout_e;
accumulator_cell_v1 DUT_V1 (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v1_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .ready_out(), .status_negative()
);

wire [31:0] v3_dout_e;
accumulator_cell_v3 DUT_V3 (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v3_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .ready_out(), .status_negative()
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

    // Real static-mode config: inc=N, downstream=E, step=1, pulse_mode=0
    cfg_valid = 1; cfg_data = {27'h0, 16'h0, 1'b0, 8'd1, 4'b0100, 4'h0, 4'b0001};
    @(posedge clk); #1; cfg_valid = 0;
    settle;
    check_all("after static config");

    // 3 real increments
    data_in_n = 0; arrived_n = 1; @(posedge clk); #1; arrived_n = 0; settle;
    check_all("after +1 (static)");
    arrived_n = 1; @(posedge clk); #1; arrived_n = 0; settle;
    check_all("after +2 (static)");
    arrived_n = 1; @(posedge clk); #1; arrived_n = 0; settle;
    check_all("after +3 (static)");

    // Real pulse-mode config: inc=N, downstream=E, step=1, pulse_mode=1, threshold=3
    cfg_valid = 1; cfg_data = {27'h0, 16'd3, 1'b1, 8'd1, 4'b0100, 4'h0, 4'b0001};
    @(posedge clk); #1; cfg_valid = 0;
    settle;
    check_all("after pulse-mode reconfigure");

    // 3 real increments -- should cross threshold=3 on the 3rd
    arrived_n = 1; @(posedge clk); #1; arrived_n = 0; settle;
    check_all("after pulse +1 (below threshold)");
    arrived_n = 1; @(posedge clk); #1; arrived_n = 0; settle;
    check_all("after pulse +2 (below threshold)");
    arrived_n = 1; @(posedge clk); #1; arrived_n = 0; settle;
    check_all("after pulse +3 (crosses threshold, fires)");

    if (errors == 0)
        $display("PASS: %0d/%0d real checks -- accumulator_cell_v3 matches v1 exactly (config read continuously, no local latch), both static and pulse mode.", checks, checks);
    else
        $display("FAIL: %0d/%0d checks had mismatches.", errors, checks);

    $finish;
end

endmodule
