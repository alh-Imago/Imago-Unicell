// tb_stripped_v1_memcell.v — points.md #119: the last two pieces of the
// persistent, updatable memory cell. Tests, in sequence:
// 1. a_reemit_in: a trigger (value ignored) pushes A unprocessed to the
//    output — confirmed by triggering with DIFFERENT values and checking
//    the SAME A always comes out, never the trigger's own value.
// 2. a_update_in: an arriving value REPLACES A directly.
// 3. Switching back to re-emit after an update, confirming the NEWLY
//    updated A (not the original) is what gets re-emitted.
`timescale 1ns / 1ps

module tb_stripped_v1_memcell;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg         cfg_valid = 0;
    reg [127:0] cfg_data  = 0;
    reg         hold = 0;
    reg         reemit = 0;
    reg         update = 0;

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
        .fb_internal_in(1'b0),
        .a_reemit_in(reemit),
        .a_update_in(update)
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

        // routing_mask=0 -- watching internal state directly, no external delivery needed.
        cfg_data = 128'h0; cfg_data[9:0] = TOPO_NOR; cfg_data[69:64] = 6'b000000;
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;
        @(posedge clk);

        // Load A = 0xDEAD0000, then hold.
        seed(32'hDEAD0000);
        hold = 1;
        repeat(2) @(posedge clk);
        report("A loaded, held      ");   // expect A=DEAD0000

        // === Test 1: a_reemit_in — trigger's VALUE should be ignored ===
        reemit = 1;
        seed(32'h11111111);   // trigger with a DIFFERENT value than A
        repeat(2) @(posedge clk);
        report("reemit trigger 1    ");   // expect out_buffer=DEAD0000 (A, NOT the trigger 11111111!)

        seed(32'h22222222);   // trigger again with yet another different value
        repeat(2) @(posedge clk);
        report("reemit trigger 2    ");   // expect out_buffer STILL DEAD0000, A unchanged

        // === Test 2: a_update_in — arriving value REPLACES A ===
        reemit = 0;
        update = 1;
        seed(32'hBEEF0000);
        repeat(2) @(posedge clk);
        report("update -> A=BEEF0000");  // expect A=BEEF0000 now (changed!)

        seed(32'hCAFE0000);
        repeat(2) @(posedge clk);
        report("update -> A=CAFE0000");  // expect A=CAFE0000 (changed again)

        // === Test 3: switch back to re-emit — should emit the NEW A ===
        update = 0;
        reemit = 1;
        seed(32'h99999999);   // trigger value, still should be ignored
        repeat(2) @(posedge clk);
        report("reemit AFTER update ");  // expect out_buffer=CAFE0000 (the UPDATED A, not the trigger)

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
