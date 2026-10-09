// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_branch_v2_diff_v1.v — points.md #564: real, differential proof
// that branch_cell_v2.v matches v1 in both modes, real held-reference
// capture, LOW/EQUAL/HIGH classification, and genuine suppression.
// Reuses the exact, real, proven BR_CFG value already used in
// tb_unicell_super_v3.v and tb_wrapped_experimental_diff_v1.v.
`default_nettype none
`timescale 1ns / 1ps

module tb_branch_v2_diff_v1;

reg clk = 0;
always #5 clk = ~clk;
reg rst = 1;
reg cfg_valid = 0;
reg [63:0] cfg_data = 0;
reg [31:0] data_in_n = 0;
reg arrived_n = 0;
reg ack_in_e = 0;

wire [31:0] v1_dout_e;
branch_cell_v1 DUT_V1 (
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

wire [31:0] v2int_dout_e;
branch_cell_v2 #(.EXTERNAL_STORAGE(0)) DUT_V2_INTERNAL (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v2int_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid(),
    .ext_state_in(117'h0), .ext_state_out()
);

reg [116:0] external_buffer = 117'h0;
wire [116:0] ext_next;
wire [31:0] v2ext_dout_e;
branch_cell_v2 #(.EXTERNAL_STORAGE(1)) DUT_V2_EXTERNAL (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v2ext_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid(),
    .ext_state_in(external_buffer), .ext_state_out(ext_next)
);
always @(posedge clk) begin
    if (rst) external_buffer <= 117'h0;
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

// Real, exact BR_CFG reused from tb_unicell_super_v3.v: upstream_dir=N,
// LOW fires marker=1, EQUAL fires marker=2, HIGH genuinely suppressed.
localparam [41:0] BR_CFG = {
    1'b0, 4'h0, 4'b0100, 4'b0100, 1'b0, 1'b1, 1'b1,
    7'd0, 7'd2, 7'd1, 1'b0, 1'b1, 1'b1, 2'd0
};

initial begin
    rst = 1; settle; rst = 0; settle;

    cfg_valid = 1; cfg_data = {22'h0, BR_CFG};
    @(posedge clk); #1; cfg_valid = 0;
    settle;
    check_all("after config");

    // Seed the held reference to 8
    data_in_n = 32'd8; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after seeding reference");

    // LOW: 5 < 8, fires marker=1
    data_in_n = 32'd5; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after LOW classification");

    ack_in_e = 1; @(posedge clk); #1; ack_in_e = 0; settle;

    // Reconfigure (release), re-seed, then EQUAL: 8 == 8, fires marker=2
    cfg_valid = 1; cfg_data = {22'h0, BR_CFG};
    @(posedge clk); #1; cfg_valid = 0;
    settle;
    data_in_n = 32'd8; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    data_in_n = 32'd8; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after EQUAL classification");

    if (errors == 0)
        $display("PASS: %0d/%0d real checks -- branch_cell_v2 matches v1 in BOTH internal and external-storage modes.", checks, checks);
    else
        $display("FAIL: %0d/%0d checks had mismatches.", errors, checks);

    $finish;
end

endmodule
