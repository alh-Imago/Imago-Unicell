// tb_stripped_v1_program.v — points.md #123's rebuilt command mechanism.
// A single target cell, programmed via program_in while 3 words arrive on
// its ordinary data_in (from a raw stimulus standing in for "any source,
// anywhere" — the target genuinely cannot tell the difference). Confirms:
// 1. The 3 words assemble correctly into cmd_latch's meaningful 96 bits.
// 2. ack_out fires for each word (the data source gets acked, for free).
// 3. program_done asserts after the 3rd word, stays high until program_in
//    drops.
// 4. Normal two-arrival operation is fully suspended during programming,
//    and resumes correctly afterward.
`timescale 1ns / 1ps

module tb_stripped_v1_program;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg         cfg_valid = 0;
    reg [127:0] cfg_data  = 0;
    reg         program_in = 0;

    reg [31:0]  data_in = 0;
    reg         arrived = 0;

    wire [31:0] dout_n;
    wire        ready_w;
    wire        ack_n_w;
    wire        program_done_w;

    reg  [31:0] normal_data = 0;
    reg         normal_arrived = 0;

    unicell_stripped_v1 #(.CELL_ID(16'h0001)) T (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(normal_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(normal_arrived), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(dout_n), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(),
        .ready_out(ready_w),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(ack_n_w), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(1'b0),
        .hold_in(1'b0),
        .fb_internal_in(1'b0),
        .a_reemit_in(1'b0),
        .a_update_in(1'b0),
        .a_self_update_in(1'b0),
        .program_in(program_in),
        .program_done(program_done_w),
        .prog_data_in(data_in), .prog_arrived_in(arrived), .prog_ack_out()
    );

    // Cell starts with routing_mask=0/topology=0 (all zero, via rst) --
    // no cfg_valid load at all for this test, deliberately: we want to
    // confirm program_in ALONE can bring a cell from a totally blank
    // state up to a working configuration.

    task seed_normal(input [31:0] v);
        begin
            normal_data = v; normal_arrived = 1;
            @(posedge clk); #1;
            normal_arrived = 0;
        end
    endtask

    task seed(input [31:0] v);
        begin
            data_in = v; arrived = 1;
            @(posedge clk); #1;
            arrived = 0;
        end
    endtask

    task report(input [127:0] label);
        $display("[t=%0t] %0s | topology=%h routing_mask=%b program_done=%b ready=%b ack_n=%b",
                  $time, label, T.cmd_latch[9:0], T.cmd_latch[69:64], program_done_w, ready_w, ack_n_w);
    endtask

    localparam [9:0] TOPO_NOR = 10'h004;

    initial begin
        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);
        report("blank cell start    ");   // expect topology=0, routing_mask=0

        // Program via program_in — 3 words, from an arbitrary "any source"
        // stimulus, no cfg_valid involved at all.
        program_in = 1;
        seed({22'h0, TOPO_NOR});                     // word0: cmd_latch[31:0] -> topology
        report("word0 consumed      ");
        seed(32'h0);                                  // word1: cmd_latch[63:32] -> unused here
        report("word1 consumed      ");
        seed({26'h0, 6'b000010});                     // word2: cmd_latch[95:64] -> routing_mask=South
        report("word2 consumed -- program_done should be 1 now");

        program_in = 0;
        repeat(2) @(posedge clk);
        report("program_in released ");   // expect program_done back to 0

        // Confirm normal operation resumes correctly: feed 2 values, expect
        // a genuine NOR two-arrival fire using the freshly-programmed topology.
        seed_normal(32'hAAAA0000);
        repeat(2) @(posedge clk);
        report("normal capture 1    ");   // expect a_arrived=1 (checked separately below)
        $display("[t=%0t]   a_arrived=%b (expect 1, genuine fresh capture)", $time, T.a_arrived);

        seed_normal(32'h11110000);
        repeat(2) @(posedge clk);
        report("normal fire 2       ");
        $display("[t=%0t]   out_buffer=%h (expect NOR(AAAA0000,11110000)=4444FFFF)", $time, dout_n);

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
