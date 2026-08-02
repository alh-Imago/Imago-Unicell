// tb_stripped_v1_2cell.v — smallest possible chain test for unicell_stripped_v1
// (points.md #88/#89). A is wired south into B's north. A's other 3 directions
// and B's other 3 directions are tied off/harmless. Drives A with TWO-arrival
// pairs across THREE ROUNDS, back-to-back, WITHOUT resetting the DUTs between
// rounds — exactly to see whether ready/ack/pending_ack state survives repeated
// use or drifts/corrupts. NOT yet run — this is the actual measurement.
`timescale 1ns / 1ps

module tb_stripped_v1_2cell;

    reg clk = 0;
    always #5 clk = ~clk;

    reg rst = 1;

    // ── Config load ports ──
    reg         cfgA_valid = 0, cfgB_valid = 0;
    reg [127:0] cfgA_data  = 128'h0, cfgB_data = 128'h0;

    // ── A <-> B interconnect (A's South = B's North) ──
    wire [31:0] a2b_data;
    wire        a2b_fire;
    wire        b2a_ready, b2a_ack;

    // A's stimulus inputs (north port used to inject test data)
    reg  [31:0] a_data_in_n = 32'h0;
    reg         a_arrived_n = 1'b0;

    // A instance
    wire [31:0] a_data_out_n, a_data_out_s, a_data_out_e, a_data_out_w;
    wire        a_fire_n, a_fire_s, a_fire_e, a_fire_w;
    wire        a_ready_out;
    wire        a_ack_out_n, a_ack_out_s, a_ack_out_e, a_ack_out_w;

    unicell_stripped_v1 #(.CELL_ID(16'h0001)) A (
        .clk(clk), .rst(rst),
        .cfg_valid(cfgA_valid), .cfg_data(cfgA_data),
        .data_in_n(a_data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(a_arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(a_data_out_n), .data_out_s(a_data_out_s),
        .data_out_e(a_data_out_e), .data_out_w(a_data_out_w),
        .fire_n(a_fire_n), .fire_s(a_fire_s), .fire_e(a_fire_e), .fire_w(a_fire_w),
        .ready_out(a_ready_out),
        .ready_in_n(1'b1), .ready_in_s(b2a_ready), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(a_ack_out_n), .ack_out_s(a_ack_out_s),
        .ack_out_e(a_ack_out_e), .ack_out_w(a_ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(b2a_ack), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(1'b0),

        .hold_in(1'b0),


        .fb_internal_in(1'b0)
    );

    assign a2b_data = a_data_out_s;
    assign a2b_fire = a_fire_s;

    // B instance — routing_mask=0 (chain end, "trivially all ready", per #88)
    wire [31:0] b_data_out_n, b_data_out_s, b_data_out_e, b_data_out_w;
    wire        b_fire_n, b_fire_s, b_fire_e, b_fire_w;
    wire        b_ready_out;
    wire        b_ack_out_n, b_ack_out_s, b_ack_out_e, b_ack_out_w;

    unicell_stripped_v1 #(.CELL_ID(16'h0002)) B (
        .clk(clk), .rst(rst),
        .cfg_valid(cfgB_valid), .cfg_data(cfgB_data),
        .data_in_n(a2b_data), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(a2b_fire), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(b_data_out_n), .data_out_s(b_data_out_s),
        .data_out_e(b_data_out_e), .data_out_w(b_data_out_w),
        .fire_n(b_fire_n), .fire_s(b_fire_s), .fire_e(b_fire_e), .fire_w(b_fire_w),
        .ready_out(b_ready_out),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(b_ack_out_n), .ack_out_s(b_ack_out_s),
        .ack_out_e(b_ack_out_e), .ack_out_w(b_ack_out_w),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(1'b0),

        .hold_in(1'b0),


        .fb_internal_in(1'b0)
    );

    assign b2a_ready = b_ready_out;
    assign b2a_ack   = b_ack_out_n;

    // ── Topology: NOR(A,B) = 10'h004 for both cells, routing_mask: A wants
    // South only (bit1=1 -> 6'b000010), B wants nothing (6'b000000). ──
    localparam [9:0] TOPO_NOR = 10'h004;

    task send_round(input [31:0] val1, input [31:0] val2, input integer round_num);
        begin
            $display("[t=%0t] ROUND %0d: sending %h then %h into A", $time, round_num, val1, val2);

            // first arrival
            a_data_in_n = val1; a_arrived_n = 1'b1;
            @(posedge clk); #1;
            a_arrived_n = 1'b0;

            // second arrival (fires A, if ready)
            @(posedge clk); #1;
            a_data_in_n = val2; a_arrived_n = 1'b1;
            @(posedge clk); #1;
            a_arrived_n = 1'b0;

            // let the chain settle: fire -> B captures -> ack -> A recovers
            repeat (5) @(posedge clk);

            $display("[t=%0t] ROUND %0d done: B.data_reg observed via b_data_out_n=%h (routing_mask=0 so no further fire expected), a_ready_out=%b, b_ready_out=%b",
                     $time, round_num, b_data_out_n, a_ready_out, b_ready_out);
        end
    endtask

    initial begin
        $dumpfile("/tmp/tb_stripped_v1_2cell.vcd");
        $dumpvars(0, tb_stripped_v1_2cell);

        // Reset
        rst = 1;
        repeat (3) @(posedge clk);
        rst = 0;
        @(posedge clk);

        // Config A: NOR gate, routing_mask = South only
        cfgA_data  = 128'h0;
        cfgA_data[9:0]   = TOPO_NOR;
        cfgA_data[69:64] = 6'b000010;  // routing_mask: bit1 = South
        cfgA_valid = 1;
        @(posedge clk); #1;
        cfgA_valid = 0;

        // Config B: NOR gate, routing_mask = 0 (chain end)
        cfgB_data  = 128'h0;
        cfgB_data[9:0]   = TOPO_NOR;
        cfgB_data[69:64] = 6'b000000;
        cfgB_valid = 1;
        @(posedge clk); #1;
        cfgB_valid = 0;

        @(posedge clk);
        $display("[t=%0t] Config done. a_ready_out=%b b_ready_out=%b", $time, a_ready_out, b_ready_out);

        // THREE rounds, back-to-back, NO reset between them.
        send_round(32'hAAAA0000, 32'h0000FFFF, 1);
        send_round(32'h11110000, 32'h0000EEEE, 2);
        send_round(32'h55550000, 32'h0000CCCC, 3);

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
