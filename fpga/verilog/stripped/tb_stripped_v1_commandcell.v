// tb_stripped_v1_commandcell.v — points.md #143: bit [10], aligned with
// the FULL cell's own command_cell/COMMAND_EMIT concept. Confirms a cell
// configured with cmd_latch[10]=1 behaves as a permanent re-emitter --
// holds A, re-emits on trigger, value ignored -- with NO hold_in or
// a_reemit_in wire asserted at all, purely from config.
`timescale 1ns / 1ps

module tb_stripped_v1_commandcell;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    reg         cfg_valid = 0;
    reg [127:0] cfg_data  = 0;

    reg [31:0] data_in = 0;
    reg        arrived = 0;

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
        // NOTE: freeze_in/hold_in/fb_internal_in/a_reemit_in/a_update_in/
        // a_self_update_in ALL tied to 0 -- NOTHING external asserted at
        // all. Only cmd_latch[10], set via cfg_data below, drives this.
        .freeze_in(1'b0),
        .hold_in(1'b0),
        .fb_internal_in(1'b0),
        .a_reemit_in(1'b0),
        .a_update_in(1'b0),
        .a_self_update_in(1'b0),
        .program_in(1'b0),
        .program_done(),
        .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
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
        $display("[t=%0t] %0s | A(data_reg)=%h out_buffer=%h is_cmd_cell=%b",
                  $time, label, DUT.data_reg, dout_n, DUT.is_command_cell);
    endtask

    initial begin
        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);

        // topology irrelevant for a pure command-emit cell (reemit
        // bypasses gate computation entirely, per #94/#119). Set
        // cmd_latch[10]=1 -- the ONLY thing enabling command-cell mode.
        cfg_data = 128'h0;
        cfg_data[9:0]   = TOPO_NOR;
        cfg_data[69:64] = 6'b000000;   // no routing needed for this test
        cfg_data[10]    = 1'b1;        // <-- is_command_cell, config-time only
        cfg_valid = 1; @(posedge clk); #1; cfg_valid = 0;
        @(posedge clk);
        report("configured as cmd cell");

        // Load A = 0xDEAD0000 (first arrival).
        seed(32'hDEAD0000);
        report("A loaded             ");   // expect A=DEAD0000

        // Trigger with a DIFFERENT value -- should be IGNORED (pure
        // re-emit of A), with NO hold_in/a_reemit_in asserted anywhere.
        seed(32'h11111111);
        report("trigger 1 (val ignored)"); // expect out_buffer=DEAD0000, NOT 11111111

        seed(32'h22222222);
        report("trigger 2 (val ignored)"); // expect out_buffer STILL DEAD0000

        seed(32'h33333333);
        report("trigger 3 (val ignored)"); // expect out_buffer STILL DEAD0000, A unchanged

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
