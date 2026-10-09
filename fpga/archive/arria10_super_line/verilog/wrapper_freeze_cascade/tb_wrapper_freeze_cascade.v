// tb_wrapper_freeze_cascade.v — points.md #152: demonstrates the freeze
// mechanism driven through the wrapper's SET_CTRL (the real, host-driven
// path, #127), and confirms the ALREADY-PROVEN backpressure cascade
// (#91/#92) does the "freeze the whole upstream chain" work for free --
// no new zone-targeting RTL needed. Freeze the downstream cell (B); the
// upstream cell (A) should stall on its own, via ordinary ready/ack,
// exactly matching #92's original confirmation, now shown via the real
// host-facing control path instead of a raw testbench wire.
`timescale 1ns / 1ps

module tb_wrapper_freeze_cascade;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [2:0] OP_PROGRAM  = 3'b000;
    localparam [2:0] OP_SET_CTRL = 3'b010;
    localparam [2:0] OP_CLR_CTRL = 3'b011;
    localparam [9:0] TOPO_NOR    = 10'h004;
    localparam [2:0] PID_TOPOLOGY = 3'd0, PID_ROUTING_MASK = 3'd1, PID_COMPLETE = 3'd7;

    reg        bus_valid = 0;
    reg [9:0]  bus_addr  = 0;
    reg [2:0]  bus_op    = 0;
    reg [31:0] bus_data  = 0;

    wire        wA_out_valid;
    wire [9:0]  wA_out_addr;
    wire [2:0]  wA_out_op;
    wire [31:0] wA_out_data;
    wire        wB_out_valid;
    wire [9:0]  wB_out_addr;
    wire [2:0]  wB_out_op;
    wire [31:0] wB_out_data;

    wire [31:0] wA_prog_data, wB_prog_data;
    wire        wA_prog_valid, wB_prog_valid;
    wire        wA_program_out, wB_program_out;
    wire        wA_freeze, wB_freeze;
    wire        A_program_done, B_program_done;
    wire [31:0] A_dout, B_dout;
    wire        A_ready, B_ready;
    wire        A_fire_e, A_ack_e_in;

    // ── Two wrappers, daisy-chained, one per cell (A then B) ──
    cell_wrapper_v2 #(.ADDR(10'd0)) WRAP_A (
        .clk(clk), .rst(rst),
        .bus_in_valid(bus_valid), .bus_in_addr(bus_addr), .bus_in_op(bus_op), .bus_in_data(bus_data),
        .bus_out_valid(wA_out_valid), .bus_out_addr(wA_out_addr), .bus_out_op(wA_out_op), .bus_out_data(wA_out_data),
        .cell_prog_data_out(wA_prog_data), .cell_prog_arrived_out(wA_prog_valid),
        .cell_program_out(wA_program_out), .cell_program_done_in(A_program_done),
        .cell_freeze_out(wA_freeze), .cell_hold_out(), .cell_fb_internal_out(),
        .cell_a_reemit_out(), .cell_a_update_out(), .cell_a_self_update_out(),
        .cell_out_buffer(A_dout), .cell_diag_in(32'h0)
    );
    cell_wrapper_v2 #(.ADDR(10'd1)) WRAP_B (
        .clk(clk), .rst(rst),
        .bus_in_valid(wA_out_valid), .bus_in_addr(wA_out_addr), .bus_in_op(wA_out_op), .bus_in_data(wA_out_data),
        .bus_out_valid(wB_out_valid), .bus_out_addr(wB_out_addr), .bus_out_op(wB_out_op), .bus_out_data(wB_out_data),
        .cell_prog_data_out(wB_prog_data), .cell_prog_arrived_out(wB_prog_valid),
        .cell_program_out(wB_program_out), .cell_program_done_in(B_program_done),
        .cell_freeze_out(wB_freeze), .cell_hold_out(), .cell_fb_internal_out(),
        .cell_a_reemit_out(), .cell_a_update_out(), .cell_a_self_update_out(),
        .cell_out_buffer(B_dout), .cell_diag_in(32'h0)
    );

    // ── Cell A: routes East into B ──
    unicell_stripped_v1 #(.CELL_ID(16'hA)) A (
        .clk(clk), .rst(rst), .cfg_valid(1'b0), .cfg_data(128'h0),
        .data_in_n(a_seed), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(a_arrived_stim), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(), .data_out_s(), .data_out_e(A_dout), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(A_fire_e), .fire_w(),
        .ready_out(A_ready),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(B_ready), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(A_ack_e_in), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(wA_freeze),
        .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(wA_program_out), .program_done(A_program_done),
        .prog_data_in_n(wA_prog_data), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(wA_prog_valid), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    // ── Cell B: receives from A's East on its West ──
    unicell_stripped_v1 #(.CELL_ID(16'hB)) B (
        .clk(clk), .rst(rst), .cfg_valid(1'b0), .cfg_data(128'h0),
        .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(A_dout),
        .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(A_fire_e),
        .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(),
        .ready_out(B_ready),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(A_ack_e_in),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(wB_freeze),
        .hold_in(1'b0), .fb_internal_in(1'b0), .a_reemit_in(1'b0),
        .a_update_in(1'b0), .a_self_update_in(1'b0),
        .program_in(wB_program_out), .program_done(B_program_done),
        .prog_data_in_n(wB_prog_data), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(wB_prog_valid), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );

    reg [31:0] a_seed = 0;
    reg        a_arrived_stim = 0;

    task seed_a(input [31:0] v);
        begin
            a_seed = v; a_arrived_stim = 1;
            @(posedge clk); #1;
            a_arrived_stim = 0;
        end
    endtask

    task send(input [9:0] addr, input [2:0] op, input [31:0] data);
        begin
            bus_addr = addr; bus_op = op; bus_data = data; bus_valid = 1;
            @(posedge clk); #1;
            bus_valid = 0;
        end
    endtask

    task report(input [127:0] label);
        $display("[t=%0t] %0s | A.ready=%b A.out=%h wB_freeze=%b B.ready=%b",
                  $time, label, A_ready, A_dout, wB_freeze, B_ready);
    endtask

    initial begin
        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);

        // Program A: topology=NOR, routing_mask=East (bit2), via the wrapper.
        send(10'd0, OP_PROGRAM, {13'h0, PID_TOPOLOGY, 6'h0, TOPO_NOR});
        send(10'd0, OP_PROGRAM, {13'h0, PID_ROUTING_MASK, 16'h0004});
        send(10'd0, OP_PROGRAM, {13'h0, PID_COMPLETE, 16'h1});
        repeat(2) @(posedge clk);
        report("A programmed        ");

        // Program B: topology=NOR, no routing needed (just a sink here).
        send(10'd1, OP_PROGRAM, {13'h0, PID_TOPOLOGY, 6'h0, TOPO_NOR});
        send(10'd1, OP_PROGRAM, {13'h0, PID_ROUTING_MASK, 16'h0000});
        send(10'd1, OP_PROGRAM, {13'h0, PID_COMPLETE, 16'h1});
        repeat(2) @(posedge clk);
        report("B programmed         ");

        // Freeze B via the wrapper's SET_CTRL (index 0 = freeze) BEFORE A
        // ever fires -- so A's fire attempt genuinely targets an already-
        // frozen B.
        send(10'd1, OP_SET_CTRL, 32'h0000_0000);
        repeat(2) @(posedge clk);
        report("B frozen via wrapper ");

        // Seed A (two-arrival model: first captures, second triggers fire).
        seed_a(32'hAAAA0000);
        repeat(2) @(posedge clk);
        seed_a(32'h11110000);
        repeat(2) @(posedge clk);
        report("A fired -> offered to frozen B");
        $display("[t=%0t]   A_ready=%b (expect 0 -- B never acked, since frozen)", $time, A_ready);

        // Release B -- B should now consume/ack A's pending offer, and
        // A's readiness should recover.
        send(10'd1, OP_CLR_CTRL, 32'h0000_0000);
        repeat(3) @(posedge clk);
        report("B released           ");
        $display("[t=%0t]   A_ready=%b (expect 1, recovered once B consumed the pending offer)", $time, A_ready);

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
