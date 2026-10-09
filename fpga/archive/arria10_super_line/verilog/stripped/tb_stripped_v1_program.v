// tb_stripped_v1_program.v — REBUILT (points.md #140) for the new
// variable-length, ID-tagged programming mechanism, replacing the old
// fixed-3-word test. Confirms:
// 1. A cell can go from blank to fully configured using ONLY the fields
//    it actually needs (a genuine "scalpel" reprogram, not all-96-bits).
// 2. The reserved COMPLETE marker correctly triggers program_done.
// 3. Normal operation resumes correctly afterward, using the newly
//    programmed topology/routing.
`timescale 1ns / 1ps

module tb_stripped_v1_program;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg         cfg_valid = 0;
    reg [127:0] cfg_data  = 0;
    reg         program_in = 0;

    reg [31:0] pdata = 0;
    reg        parrived = 0;

    reg [31:0]  normal_data = 0;
    reg         normal_arrived = 0;

    wire [31:0] dout_n;
    wire        ready_w;
    wire        ack_n_w;
    wire        program_done_w;

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
        .prog_data_in_n(pdata), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(parrived), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    localparam [2:0] ID_TOPOLOGY = 3'd0, ID_ROUTING = 3'd1, ID_CARDEDGE = 3'd2,
                     ID_PATLOW = 3'd3, ID_PATEQ = 3'd4, ID_PATHIGH = 3'd5,
                     ID_DYNEN = 3'd6, ID_COMPLETE = 3'd7;
    localparam [9:0] TOPO_NOR = 10'h004;

    task prog_word(input [2:0] id, input [15:0] data);
        begin
            pdata = {13'h0, id, data};
            parrived = 1;
            @(posedge clk); #1;
            parrived = 0;
        end
    endtask

    task seed_normal(input [31:0] v);
        begin
            normal_data = v; normal_arrived = 1;
            @(posedge clk); #1;
            normal_arrived = 0;
        end
    endtask

    task report(input [127:0] label);
        $display("[t=%0t] %0s | topo=%h routing=%b program_done=%b ready=%b",
                  $time, label, T.cmd_latch[9:0], T.cmd_latch[69:64], program_done_w, ready_w);
    endtask

    initial begin
        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);
        report("blank cell start    ");   // expect topo=0, routing=0

        // Genuine "scalpel": touch ONLY topology and routing_mask, skip
        // everything else entirely (no wasted 96-bit overwrite).
        program_in = 1;
        prog_word(ID_TOPOLOGY, {6'h0, TOPO_NOR});
        report("topology written    ");   // expect topo=004, program_done still 0

        prog_word(ID_ROUTING, 16'h0002);  // routing_mask = South (bit1)
        report("routing written     ");   // expect routing=000010, program_done still 0

        prog_word(ID_COMPLETE, 16'h1);  // points.md #156: LSB=1 arms
        report("COMPLETE            ");   // expect program_done=1

        program_in = 0;
        repeat(2) @(posedge clk);
        report("program_in released ");   // expect program_done back to 0, config preserved

        // Confirm normal operation resumes correctly with the newly
        // programmed topology.
        seed_normal(32'hAAAA0000);
        repeat(2) @(posedge clk);
        $display("[t=%0t]   a_arrived=%b (expect 1, genuine fresh capture)", $time, T.a_arrived);

        seed_normal(32'h11110000);
        repeat(2) @(posedge clk);
        $display("[t=%0t]   out_buffer=%h (expect NOR(AAAA0000,11110000)=4444FFFF)", $time, dout_n);

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
