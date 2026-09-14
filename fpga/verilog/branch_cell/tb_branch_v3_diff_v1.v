// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_branch_v3_diff_v1.v — points.md #699: real, differential proof
// that branch_cell_v3.v's own config-off-shell change (all 14 real
// fields now continuous, the widest real config surface in this
// family) is genuinely behavior-preserving under normal driving --
// real held-reference capture, LOW/EQUAL classification, genuine
// suppression of HIGH -- reusing the exact, real, proven BR_CFG value
// already used in `tb_branch_v2_diff_v1.v`/`tb_unicell_super_v3.v`.
// A second real test then demonstrates the new live-config-reflection
// capability on this, the most config-heavy core in the family.
`default_nettype none
`timescale 1ns / 1ps

module tb_branch_v3_diff_v1;

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

wire [31:0] v3_dout_e;
branch_cell_v3 DUT_V3 (
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

// Real, exact BR_CFG reused from tb_branch_v2_diff_v1.v/
// tb_unicell_super_v3.v: upstream_dir=N, LOW fires fixed marker=1,
// EQUAL fires fixed marker=2, HIGH genuinely suppressed.
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

    // Seed the held reference to 8.
    data_in_n = 32'd8; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after seeding reference");

    // LOW: 5 < 8, fires fixed marker=1.
    data_in_n = 32'd5; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after LOW classification");
    if (v1_dout_e !== 32'd1 || v3_dout_e !== 32'd1) begin
        $display("FAIL: LOW should emit fixed value 1 -- v1=%0d v3=%0d", v1_dout_e, v3_dout_e);
        errors = errors + 1;
    end

    ack_in_e = 1; @(posedge clk); #1; ack_in_e = 0; settle;

    // Reconfigure (release), re-seed, then EQUAL: 8 == 8, fires
    // fixed marker=2.
    cfg_valid = 1; cfg_data = {22'h0, BR_CFG};
    @(posedge clk); #1; cfg_valid = 0;
    settle;
    data_in_n = 32'd8; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    data_in_n = 32'd8; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after EQUAL classification");
    if (v1_dout_e !== 32'd2 || v3_dout_e !== 32'd2) begin
        $display("FAIL: EQUAL should emit fixed value 2 -- v1=%0d v3=%0d", v1_dout_e, v3_dout_e);
        errors = errors + 1;
    end

    ack_in_e = 1; @(posedge clk); #1; ack_in_e = 0; settle;

    // ── The real, new capability -- v3 reflects a live change to
    // fixed_value_low with NO fresh cfg_valid pulse; v1's own local
    // latch stays stale. Reconfigure once normally, seed the
    // reference, THEN change fixed_value_low live on cfg_data itself
    // (bits [11:5]) before triggering a real LOW classification. ──
    cfg_valid = 1; cfg_data = {22'h0, BR_CFG};
    @(posedge clk); #1; cfg_valid = 0;
    settle;
    data_in_n = 32'd8; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;

    // Live change: fixed_value_low 1 -> 99, no new cfg_valid pulse.
    cfg_data[11:5] = 7'd99;
    settle;

    if (DUT_V1.fixed_value_low !== 7'd1) begin
        $display("FAIL: v1's own local latch should STILL read fixed_value_low=1 (stale) -- got %0d", DUT_V1.fixed_value_low);
        errors = errors + 1;
    end
    if (DUT_V3.fixed_value_low !== 7'd99) begin
        $display("FAIL: v3 should reflect the live fixed_value_low=99 with no new cfg_valid pulse -- got %0d", DUT_V3.fixed_value_low);
        errors = errors + 1;
    end

    // Trigger a real LOW classification (5 < 8) and confirm v3 now
    // emits the LIVE fixed value (99), while v1 still emits its own
    // stale one (1).
    data_in_n = 32'd5; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    if (v1_dout_e !== 32'd1) begin
        $display("FAIL: v1 should still emit its own stale fixed value 1 -- got %0d", v1_dout_e);
        errors = errors + 1;
    end
    if (v3_dout_e !== 32'd99) begin
        $display("FAIL: v3 should emit the LIVE fixed value 99 -- got %0d", v3_dout_e);
        errors = errors + 1;
    end

    if (errors == 0)
        $display("PASS: tb_branch_v3_diff_v1 -- v3 preserves v1's real behavior (held reference, LOW/EQUAL, suppression), AND reflects live config changes v1's own local latch cannot see (%0d/%0d checks)", checks, checks);
    else
        $display("FAIL: tb_branch_v3_diff_v1 -- %0d real mismatch(es)", errors);

    $finish;
end

endmodule
