// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_sequencer_v2_diff_v1.v — points.md #564: real, differential
// proof that sequencer_cell_v2.v matches v1 in both modes, including
// a real wrap-around cycle.
`default_nettype none
`timescale 1ns / 1ps

module tb_sequencer_v2_diff_v1;

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

wire [31:0] v2int_dout_e;
sequencer_cell_v2 #(.EXTERNAL_STORAGE(0)) DUT_V2_INTERNAL (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v2int_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .ready_out(), .status_seq_index(),
    .ext_state_in(53'h0), .ext_state_out()
);

reg [52:0] external_buffer = 53'h0;
wire [52:0] ext_next;
wire [31:0] v2ext_dout_e;
sequencer_cell_v2 #(.EXTERNAL_STORAGE(1)) DUT_V2_EXTERNAL (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v2ext_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .ready_out(), .status_seq_index(),
    .ext_state_in(external_buffer), .ext_state_out(ext_next)
);
always @(posedge clk) begin
    if (rst) external_buffer <= 53'h0;
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

    // Real config: values 10,20,30,_ length-1=2 (real length 3), downstream=E
    cfg_valid = 1; cfg_data = {26'h0, 4'b0100, 2'd2, 8'd0, 8'd30, 8'd20, 8'd10};
    @(posedge clk); #1; cfg_valid = 0;
    settle;
    check_all("after config (offers 10)");

    // Ack -> advance to 20
    ack_in_e = 1; @(posedge clk); #1; ack_in_e = 0; settle;
    check_all("after ack 1 (offers 20)");

    // Ack -> advance to 30
    ack_in_e = 1; @(posedge clk); #1; ack_in_e = 0; settle;
    check_all("after ack 2 (offers 30)");

    // Ack -> real wrap back to 10
    ack_in_e = 1; @(posedge clk); #1; ack_in_e = 0; settle;
    check_all("after ack 3 (wraps back to 10)");

    if (errors == 0)
        $display("PASS: %0d/%0d real checks -- sequencer_cell_v2 matches v1 in BOTH internal and external-storage modes, including real wrap-around.", checks, checks);
    else
        $display("FAIL: %0d/%0d checks had mismatches.", errors, checks);

    $finish;
end

endmodule
