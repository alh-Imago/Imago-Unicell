// tb_stripped_v1_relaymismatch.v — points.md #154: a genuine relay/
// consume mismatch on simultaneously-arriving directions should self-
// freeze the cell (a real error, per Alan -- a well-formed model never
// has this by construction). Confirms:
// 1. Mismatch (one relay-tagged, one consume-tagged direction, arriving
//    together) -> error_frozen asserts, cell stops accepting further work.
// 2. A reprogram's COMPLETE marker auto-clears the error.
`timescale 1ns / 1ps

module tb_stripped_v1_relaymismatch;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg         cfg_valid = 0;
    reg [127:0] cfg_data  = 0;
    reg         program_in = 0;

    reg [31:0] data_n = 0, data_s = 0;
    reg        arr_n = 0, arr_s = 0;
    reg [31:0] pdata = 0;
    reg        parr = 0;

    wire [31:0] dout_n;
    wire        ready_w, program_done_w;

    unicell_stripped_v1 #(.CELL_ID(16'h0001)) DUT (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(data_n), .data_in_s(data_s), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(arr_n), .arrived_s(arr_s), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(dout_n), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(),
        .ready_out(ready_w),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(1'b0),
        .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(program_in), .program_done(program_done_w),
        .prog_data_in_n(pdata), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(parr), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    localparam [9:0] TOPO_NOR = 10'h004;
    localparam [2:0] ID_TOPOLOGY = 3'd0, ID_CARDEDGE = 3'd2, ID_COMPLETE = 3'd7;

    task prog_word(input [2:0] id, input [15:0] data);
        begin
            pdata = {13'h0, id, data};
            parr = 1;
            @(posedge clk); #1;
            parr = 0;
        end
    endtask

    task report(input [127:0] label);
        $display("[t=%0t] %0s | error_frozen=%b a_arrived=%b out=%h",
                  $time, label, DUT.error_frozen, DUT.a_arrived, dout_n);
    endtask

    initial begin
        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);

        // === Test 1: MISMATCH -- N=relay(bit0=1), S=consume(bit1=0) ===
        cfg_data = 128'h0; cfg_data[9:0] = TOPO_NOR; cfg_data[75:70] = 6'b000001; // N=relay, rest=consume
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;
        @(posedge clk);
        report("configured (N=relay,S=consume)");

        data_n = 32'hDEAD0000; data_s = 32'hBEEF0000;
        arr_n = 1; arr_s = 1;
        @(posedge clk); #1;
        arr_n = 0; arr_s = 0;
        report("after mismatched arrival");   // expect error_frozen=1

        // Confirm the cell is now genuinely stuck -- feed more data, nothing changes.
        data_n = 32'h11111111; arr_n = 1;
        @(posedge clk); #1; arr_n = 0;
        repeat(1) @(posedge clk);
        report("still frozen, no progress");  // expect a_arrived STILL 0 (capture blocked)

        // Reprogram -- COMPLETE should auto-clear the error.
        program_in = 1;
        prog_word(ID_TOPOLOGY, {6'h0, TOPO_NOR});
        prog_word(ID_CARDEDGE, 16'h0000);   // both directions consume now
        prog_word(ID_COMPLETE, 16'h0);
        program_in = 0;
        repeat(2) @(posedge clk);
        report("reprogrammed, error cleared?");  // expect error_frozen=0

        // Confirm normal operation genuinely resumes.
        data_n = 32'hAAAA0000; arr_n = 1;
        @(posedge clk); #1; arr_n = 0;
        repeat(1) @(posedge clk);
        report("normal capture resumes");  // expect a_arrived=1

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
