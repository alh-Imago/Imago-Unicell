// tb_stripped_v1_selfupdate.v — points.md #120: the threshold (A) itself
// evolves via internal feedback, rather than staying fixed. Confirms:
// 1. A genuinely changes each cycle while self-update runs, based on its
//    own accumulated history (NOR against a fixed comparand, out_buffer).
// 2. Pausing self-update and reading via a_reemit_in correctly reports
//    whatever the CURRENT (evolved) A is, not the original.
`timescale 1ns / 1ps

module tb_stripped_v1_selfupdate;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg         cfg_valid = 0;
    reg [127:0] cfg_data  = 0;
    reg         hold = 0;
    reg         fb_int = 0;
    reg         self_upd = 0;
    reg         reemit = 0;

    reg [31:0]  data_in = 0;
    reg         arrived = 0;

    wire [31:0] dout_n;
    wire        ready_w;

    unicell_stripped_v1 #(.CELL_ID(16'h0001)) DUT (
        .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(data_in), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(arrived), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(dout_n), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(),
        .ready_out(ready_w),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(1'b0),
        .hold_in(hold),
        .fb_internal_in(fb_int),
        .a_reemit_in(reemit),
        .a_update_in(1'b0),
        .a_self_update_in(self_upd),

        .program_in(1'b0),

        .program_done(),


        .prog_data_in(32'h0),


        .prog_arrived_in(1'b0),


        .prog_ack_out()
    );

    localparam [9:0] TOPO_NOR = 10'h004;

    task seed(input [31:0] v);
        begin
            data_in = v; arrived = 1;
            @(posedge clk); #1;
            arrived = 0;
        end
    endtask

    task report(input [127:0] label);
        $display("[t=%0t] %0s | A(data_reg)=%h out_buffer=%h ready=%b",
                  $time, label, DUT.data_reg, dout_n, ready_w);
    endtask

    initial begin
        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);

        cfg_data = 128'h0; cfg_data[9:0] = TOPO_NOR; cfg_data[69:64] = 6'b000000;
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;
        @(posedge clk);

        // Load threshold, hold, kick ONCE (normal fire) to set out_buffer.
        seed(32'hAAAA0000);
        hold = 1;
        seed(32'h11110000);   // normal fire: out_buffer = NOR(AAAA0000,11110000) = 4444FFFF
        repeat(2) @(posedge clk);
        report("after kick (A fixed)");   // expect A=AAAA0000, out_buffer=4444FFFF

        // Start self-update: A itself now evolves against the FIXED
        // out_buffer (4444FFFF), which self-update mode never touches.
        fb_int = 1; self_upd = 1;
        repeat(1) @(posedge clk); report("self-update cycle 1 ");
        repeat(1) @(posedge clk); report("self-update cycle 2 ");
        repeat(1) @(posedge clk); report("self-update cycle 3 ");
        repeat(1) @(posedge clk); report("self-update cycle 4 ");

        // Pause self-update, read current A via reemit.
        fb_int = 0; self_upd = 0;
        reemit = 1;
        seed(32'hFFFFFFFF);   // trigger value, should be ignored (per #119)
        repeat(2) @(posedge clk);
        report("reemit snapshot     ");   // out_buffer should now show CURRENT A

        // Resume self-update -- confirm it continues, not reset.
        reemit = 0;
        fb_int = 1; self_upd = 1;
        repeat(1) @(posedge clk); report("resumed cycle 1     ");
        repeat(1) @(posedge clk); report("resumed cycle 2     ");

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
