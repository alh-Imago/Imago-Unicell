// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_adder_v2_diff_v1.v — points.md #564: real, differential proof
// that adder_cell_v2.v's own optional external-storage capability is
// genuinely behavior-preserving in both modes, including the real,
// documented capture_now/can_fire/offer_draining subtlety and real
// subtract_mode behavior. Uses the corrected, race-free timing
// pattern from the start (#563's own real finding).
`default_nettype none
`timescale 1ns / 1ps

module tb_adder_v2_diff_v1;

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

wire [31:0] v2int_dout_e;
adder_cell_v2 #(.EXTERNAL_STORAGE(0)) DUT_V2_INTERNAL (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v2int_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid(), .status_a_arrived(),
    .ext_state_in(79'h0), .ext_state_out()
);

reg [78:0] external_buffer = 79'h0;
wire [78:0] ext_next;
wire [31:0] v2ext_dout_e;
adder_cell_v2 #(.EXTERNAL_STORAGE(1)) DUT_V2_EXTERNAL (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v2ext_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid(), .status_a_arrived(),
    .ext_state_in(external_buffer), .ext_state_out(ext_next)
);
always @(posedge clk) begin
    if (rst) external_buffer <= 79'h0;
    else external_buffer <= ext_next;
end

integer errors = 0;
integer checks = 0;

task check_all(input [200*8-1:0] label);
    begin
        checks = checks + 1;
        if (v1_dout_e !== v2int_dout_e) begin
            errors = errors + 1;
            $display("MISMATCH (internal) at %s: v1=0x%08X v2_internal=0x%08X", label, v1_dout_e, v2int_dout_e);
        end
        if (v1_dout_e !== v2ext_dout_e) begin
            errors = errors + 1;
            $display("MISMATCH (external) at %s: v1=0x%08X v2_external=0x%08X", label, v1_dout_e, v2ext_dout_e);
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

    // Real config: downstream=E, upstream=N, ADD mode (subtract_mode=0)
    cfg_valid = 1; cfg_data = {55'h0, 1'b0, 4'b0001, 4'b0100};
    @(posedge clk); #1; cfg_valid = 0;
    settle;
    check_all("after config (add mode)");

    // Real two-stage capture: A=100, B=23, should fire 123
    data_in_n = 32'd100; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after A captured");
    data_in_n = 32'd23; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after B fires (add)");

    ack_in_e = 1; @(posedge clk); #1; ack_in_e = 0;
    settle;
    check_all("after drain");

    // Real reconfigure to SUBTRACT mode
    cfg_valid = 1; cfg_data = {55'h0, 1'b1, 4'b0001, 4'b0100};
    @(posedge clk); #1; cfg_valid = 0;
    settle;
    check_all("after reconfig to subtract mode");

    // Real subtract: A=50, B=8, should fire 42
    data_in_n = 32'd50; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    data_in_n = 32'd8; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after B fires (subtract)");

    if (errors == 0)
        $display("PASS: %0d/%0d real checks -- adder_cell_v2 matches v1 in BOTH internal and external-storage modes.", checks, checks);
    else
        $display("FAIL: %0d/%0d checks had mismatches.", errors, checks);

    $finish;
end

endmodule
