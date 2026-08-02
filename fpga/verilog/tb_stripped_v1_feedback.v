// tb_stripped_v1_feedback.v — points.md #118's internal feedback path.
// A single held cell, using the NEW fb_internal_in mechanism: second_val
// is drawn directly from the cell's own out_buffer (last result), fully
// bypassing the ack/pending_ack machinery. Should genuinely iterate --
// each cycle recomputing NOR(threshold, previous_output) -- rather than
// the deadlock found when this was attempted through the normal cardinal
// delivery/ack path (external, two-different-cells mechanism).
`timescale 1ns / 1ps

module tb_stripped_v1_feedback;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg         cfg_valid = 0;
    reg [127:0] cfg_data  = 0;
    reg         hold = 0;
    reg         fb_internal = 0;

    reg [31:0]  ext_data = 0;
    reg         ext_arrived = 0;

    wire [31:0] h_dout_s;
    wire        h_ready;

    unicell_stripped_v1 #(.CELL_ID(16'h0001)) H (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(ext_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(ext_arrived), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(h_dout_s), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(),
        .ready_out(h_ready),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(1'b0),
        .hold_in(hold),
        .fb_internal_in(fb_internal),

        .a_reemit_in(1'b0),

        .a_update_in(1'b0)
    );

    localparam [9:0] TOPO_NOR = 10'h004;

    task seed(input [31:0] v);
        begin
            ext_data = v; ext_arrived = 1;
            @(posedge clk); #1;
            ext_arrived = 0;
        end
    endtask

    task report(input [127:0] label);
        $display("[t=%0t] %0s | threshold(data_reg)=%h a_arrived=%b out_buffer=%h ready=%b",
                  $time, label, H.data_reg, H.a_arrived, h_dout_s, h_ready);
    endtask

    initial begin
        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);

        // routing_mask=0 -- no external delivery needed at all for this test.
        cfg_data = 128'h0; cfg_data[9:0] = TOPO_NOR; cfg_data[69:64] = 6'b000000;
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;
        @(posedge clk);

        // Load threshold.
        seed(32'hAAAA0000);
        repeat(2) @(posedge clk);
        report("threshold loaded   ");

        // Hold, then kick with ONE external second-arrival to seed the
        // first real output value (out_buffer starts at 0 otherwise).
        hold = 1;
        seed(32'h11110000);
        repeat(2) @(posedge clk);
        report("after kick         ");

        // Now switch to internal feedback -- no further external
        // stimulus at all, genuinely bypassing ack/pending_ack.
        fb_internal = 1;
        repeat(1) @(posedge clk);
        report("iteration 1        ");
        repeat(1) @(posedge clk);
        report("iteration 2        ");
        repeat(1) @(posedge clk);
        report("iteration 3        ");
        repeat(1) @(posedge clk);
        report("iteration 4        ");
        repeat(1) @(posedge clk);
        report("iteration 5        ");
        repeat(1) @(posedge clk);
        report("iteration 6        ");
        repeat(10) @(posedge clk);
        report("still running?     ");

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
