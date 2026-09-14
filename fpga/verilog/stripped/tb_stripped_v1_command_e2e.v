// tb_stripped_v1_command_e2e.v — points.md #123's full picture, end to
// end: a genuine command cell (cell_command_v1) triggers, holds
// program_in on a target, watches for program_done, releases. The
// target's 3 config words arrive from a COMPLETELY SEPARATE stimulus
// than the trigger — confirming decoupling is real, not just designed:
// the command cell never sees or touches the data itself.
`timescale 1ns / 1ps

module tb_stripped_v1_command_e2e;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    // ── Command cell side ──
    reg  trigger = 0;
    wire program_out_w;

    cell_command_v1 CMD (
        .clk(clk), .rst(rst),
        .trigger_in(trigger),
        .program_done_in(program_done_w),
        .program_out(program_out_w)
    );

    // ── Target cell ──
    reg  [31:0] data_in = 0;
    reg         arrived = 0;
    wire [31:0] dout_n;
    wire        ready_w, ack_n_w, program_done_w;

    unicell_stripped_v1 #(.CELL_ID(16'h0001)) T (
        .clk(clk), .rst(rst), .cfg_valid(1'b0), .cfg_data(128'h0),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
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
        .program_in(program_out_w),   // <── driven by the command cell, not the testbench directly
        .program_done(program_done_w),
        .prog_data_in_n(data_in), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(arrived), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    localparam [9:0] TOPO_NOR = 10'h004;
    localparam [2:0] ID_TOPOLOGY = 3'd0, ID_ROUTING = 3'd1, ID_COMPLETE = 3'd7;

    task seed(input [31:0] v);
        begin
            data_in = v; arrived = 1;
            @(posedge clk); #1;
            arrived = 0;
        end
    endtask

    task report(input [127:0] label);
        $display("[t=%0t] %0s | CMD.program_out=%b T.program_done=%b topology=%h routing_mask=%b",
                  $time, label, program_out_w, program_done_w, T.cmd_latch[9:0], T.cmd_latch[69:64]);
    endtask

    initial begin
        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);
        report("start               ");

        // Trigger the command cell — a single pulse, decoupled entirely
        // from the data stream that follows.
        trigger = 1;
        @(posedge clk); #1;
        trigger = 0;
        repeat(1) @(posedge clk);
        report("triggered           ");   // expect CMD.program_out=1 now

        // Data arrives from a totally separate stimulus, on its own
        // schedule — the command cell never touches this.
        seed({13'h0, ID_TOPOLOGY, 6'h0, TOPO_NOR});
        report("word0 arrived       ");
        seed({13'h0, ID_ROUTING, 16'h0002});
        report("word1 arrived       ");
        seed({13'h0, ID_COMPLETE, 16'h1});  // points.md #156: LSB=1 arms
        report("COMPLETE            ");   // expect program_done=1, topology/routing_mask set

        repeat(2) @(posedge clk);
        report("settled             ");   // expect CMD saw program_done, released -- program_out back to 0

        repeat(2) @(posedge clk); report("extra settle        "); $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
