// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// tb_nano_v3_diff_v1.v — points.md #566: real, differential proof
// that unicell_stripped_v3.v matches v1 in both modes, covering three
// structurally distinct real mechanisms: basic two-arrival capture/
// fire (the NOR-gate computation itself), hold + a_reemit (the memory-
// cell behavior), and the real programming channel (field writes +
// COMPLETE arming).
`default_nettype none
`timescale 1ns / 1ps

module tb_nano_v3_diff_v1;

reg clk = 0;
always #5 clk = ~clk;
reg rst = 1;
reg cfg_valid = 0;
reg [127:0] cfg_data = 0;
reg [31:0] data_in_n = 0, data_in_s = 0;
reg arrived_n = 0, arrived_s = 0;
reg ack_in_e = 0;
reg hold_in = 0, a_reemit_in = 0;
reg program_in = 0;
reg [31:0] prog_data_in_n = 0;
reg prog_arrived_in_n = 0;

wire [31:0] v1_dout_e;
unicell_stripped_v1 DUT_V1 (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(arrived_s), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v1_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
    .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
    .freeze_in(1'b0), .hold_in(hold_in), .fb_internal_in(1'b0),
    .a_reemit_in(a_reemit_in), .a_update_in(1'b0), .a_self_update_in(1'b0),
    .program_in(program_in), .program_done(),
    .prog_data_in_n(prog_data_in_n), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(prog_arrived_in_n), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
);

wire [31:0] v3int_dout_e;
unicell_stripped_v3 #(.EXTERNAL_STORAGE(0)) DUT_V3_INTERNAL (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(arrived_s), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v3int_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
    .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
    .freeze_in(1'b0), .hold_in(hold_in), .fb_internal_in(1'b0),
    .a_reemit_in(a_reemit_in), .a_update_in(1'b0), .a_self_update_in(1'b0),
    .program_in(program_in), .program_done(),
    .prog_data_in_n(prog_data_in_n), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(prog_arrived_in_n), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
    .ext_state_in(170'h0), .ext_state_out()
);

reg [169:0] external_buffer = 170'h0;
wire [169:0] ext_next;
wire [31:0] v3ext_dout_e;
unicell_stripped_v3 #(.EXTERNAL_STORAGE(1)) DUT_V3_EXTERNAL (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(arrived_s), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(v3ext_dout_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
    .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
    .freeze_in(1'b0), .hold_in(hold_in), .fb_internal_in(1'b0),
    .a_reemit_in(a_reemit_in), .a_update_in(1'b0), .a_self_update_in(1'b0),
    .program_in(program_in), .program_done(),
    .prog_data_in_n(prog_data_in_n), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(prog_arrived_in_n), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w(),
    .ext_state_in(external_buffer), .ext_state_out(ext_next)
);
always @(posedge clk) begin
    if (rst) external_buffer <= 170'h0;
    else external_buffer <= ext_next;
end

integer errors = 0;
integer checks = 0;

task check_all(input [200*8-1:0] label);
    begin
        checks = checks + 1;
        if (v1_dout_e !== v3int_dout_e) begin
            errors = errors + 1;
            $display("MISMATCH (internal) at %s: v1=0x%08X v3_internal=0x%08X", label, v1_dout_e, v3int_dout_e);
        end
        if (v1_dout_e !== v3ext_dout_e) begin
            errors = errors + 1;
            $display("MISMATCH (external) at %s: v1=0x%08X v3_external=0x%08X", label, v1_dout_e, v3ext_dout_e);
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

    // ── Real basic capture/fire: topology=NOR(g4), routing=E, ready=1 ──
    // cmd_latch[9:0]=topology=10'h004, [69:64]=routing_mask, [13]=ready(forced anyway)
    cfg_data = 128'h0;
    cfg_data[9:0] = 10'h004;      // topology: g4 = NOR(input,second)
    cfg_data[67:64] = 4'b0100;    // routing_mask: E
    cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;
    settle;
    check_all("after config");

    data_in_n = 32'h0; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after first arrival (capture)");

    data_in_n = 32'h0; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after second arrival (fires g4=NOR(0,0)=all-1s)");

    ack_in_e = 1; @(posedge clk); #1; ack_in_e = 0;
    settle;

    // ── Real hold + a_reemit: hold data, reemit A unprocessed ──
    hold_in = 1;
    data_in_n = 32'hABCDEF01; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after hold capture");

    a_reemit_in = 1;
    data_in_n = 32'h0; arrived_n = 1; @(posedge clk); #1; arrived_n = 0; a_reemit_in = 0;
    settle;
    check_all("after a_reemit (should offer 0xABCDEF01 unprocessed)");

    ack_in_e = 1; @(posedge clk); #1; ack_in_e = 0;
    settle;
    hold_in = 0;

    // ── Real programming channel: write topology via PROG_ID_TOPOLOGY,
    // then COMPLETE with arm bit set ──
    rst = 1; settle; rst = 0; settle;
    cfg_data = 128'h0;
    cfg_data[9:0] = 10'h000;  // start with pass-through topology
    cfg_data[67:64] = 4'b0100;
    cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;
    settle;

    program_in = 1;
    // PROG_ID_TOPOLOGY=0, write topology=g1 (10'h002)
    prog_data_in_n = {13'h0, 3'd0, 3'h0, 10'h002};
    prog_arrived_in_n = 1; @(posedge clk); #1; prog_arrived_in_n = 0;
    settle;

    // COMPLETE (PROG_ID=7) with arm bit=1
    prog_data_in_n = {13'h0, 3'd7, 15'h0, 1'b1};
    prog_arrived_in_n = 1; @(posedge clk); #1; prog_arrived_in_n = 0;
    settle;
    program_in = 0;
    settle;
    check_all("after reprogram to g1 topology + rearm");

    data_in_n = 32'hFFFFFFFF; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    data_in_n = 32'hFFFFFFFF; arrived_n = 1; @(posedge clk); #1; arrived_n = 0;
    settle;
    check_all("after fire with reprogrammed topology (g1=NOR(second,second))");

    if (errors == 0)
        $display("PASS: %0d/%0d real checks -- unicell_stripped_v3 matches v1 in BOTH internal and external-storage modes, covering capture/fire, hold+reemit, and the real programming channel.", checks, checks);
    else
        $display("FAIL: %0d/%0d checks had mismatches.", errors, checks);

    $finish;
end

endmodule
