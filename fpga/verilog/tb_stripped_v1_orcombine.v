// tb_stripped_v1_orcombine.v — points.md #153: two simultaneous arrivals
// on different directions, same cycle, should OR-combine into one value
// feeding the normal two-arrival gate -- the FULL cell's wired-OR bus
// trick, recreated on dedicated point-to-point wires, no shared/addressed
// bus needed. Confirms: the combined value is genuinely the OR of both
// inputs, BOTH directions get acked the same cycle, and arrivals on
// DIFFERENT cycles do NOT combine (unchanged, pre-existing behavior).
`timescale 1ns / 1ps

module tb_stripped_v1_orcombine;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg         cfg_valid = 0;
    reg [127:0] cfg_data  = 0;

    reg [31:0] data_n = 0, data_s = 0;
    reg        arr_n = 0, arr_s = 0;

    wire [31:0] dout_n;
    wire        ack_n_w, ack_s_w;

    unicell_stripped_v1 #(.CELL_ID(16'h0001)) DUT (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(data_n), .data_in_s(data_s), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(arr_n), .arrived_s(arr_s), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(dout_n), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(),
        .ready_out(),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(ack_n_w), .ack_out_s(ack_s_w), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(1'b0),
        .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(1'b0), .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    localparam [9:0] TOPO_NOR = 10'h004;

    task report(input [127:0] label);
        $display("[t=%0t] %0s | a_arrived=%b data_reg=%h out=%h ack_n=%b ack_s=%b",
                  $time, label, DUT.a_arrived, DUT.data_reg, dout_n, ack_n_w, ack_s_w);
    endtask

    initial begin
        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);

        cfg_data = 128'h0; cfg_data[9:0] = TOPO_NOR; cfg_data[69:64] = 6'b000000;
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;
        @(posedge clk);

        // === Test 1: two SIMULTANEOUS arrivals, same cycle, different
        // values on N and S -- should OR-combine into the first capture (A). ===
        data_n = 32'h0000000F; data_s = 32'h000000F0;
        arr_n = 1; arr_s = 1;
        @(posedge clk); #1;
        $display("[t=%0t] DURING consumption | ack_n=%b ack_s=%b (expect BOTH 1)", $time, ack_n_w, ack_s_w);
        arr_n = 0; arr_s = 0;
        report("simultaneous N+S capture");
        // expect: a_arrived=1, data_reg = 0F | F0 = FF (genuine OR-combine)
        // expect: BOTH ack_n and ack_s were asserted during that same cycle

        // === Test 2: two MORE simultaneous arrivals -- second capture,
        // this one triggers the fire (two-arrival gate: NOR(A, this_combined)). ===
        data_n = 32'h00000F00; data_s = 32'h0000F000;
        arr_n = 1; arr_s = 1;
        @(posedge clk); #1;
        arr_n = 0; arr_s = 0;
        repeat(1) @(posedge clk);
        report("simultaneous N+S fire   ");
        // expect: out = NOR(0xFF, 0xFF00) -- computed and checked below by hand

        // === Test 3: SEQUENTIAL arrivals on different cycles -- confirm
        // this does NOT combine (unchanged pre-existing behavior). ===
        data_n = 32'hAAAA0000; arr_n = 1;
        @(posedge clk); #1; arr_n = 0;
        repeat(2) @(posedge clk);
        report("sequential N only (capture)"); // expect data_reg=AAAA0000, no S involved

        data_s = 32'h11110000; arr_s = 1;
        @(posedge clk); #1; arr_s = 0;
        repeat(1) @(posedge clk);
        report("sequential S only (fire)   ");
        // expect out = NOR(AAAA0000, 11110000) = 4444FFFF, matching every
        // prior confirmed hand-computation of this exact pair -- confirming
        // sequential (non-simultaneous) arrivals still behave exactly as
        // before, unaffected by this change.

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
