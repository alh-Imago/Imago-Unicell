// tb_wrapper_v2.v — points.md #127: the wrapper rebuilt with full opcode
// parity. Confirms, against one target cell:
// 1. PROGRAM via the target's ordinary data port (not cfg_data) — same
//    correct values as #125/#126.
// 2. SET_CTRL/CLR_CTRL on hold_in — the target genuinely holds and
//    releases, matching #116's own confirmed hold behavior. Ordinary data
//    for this part arrives on a SEPARATE direction (data_in_s) from a raw
//    stimulus — standing in for "any other source," confirming the
//    wrapper's PROGRAM channel (North) and normal data (South) are
//    genuinely independent.
// 3. COLLECT reads out_buffer correctly.
// 4. DIAG reads back internal state correctly.
`timescale 1ns / 1ps

module tb_wrapper_v2;

    reg clk = 0;
    always #5 clk = ~clk;
    reg rst = 1;

    localparam [2:0] OP_PROGRAM  = 3'b000;
    localparam [2:0] OP_COLLECT  = 3'b001;
    localparam [2:0] OP_SET_CTRL = 3'b010;
    localparam [2:0] OP_CLR_CTRL = 3'b011;
    localparam [2:0] OP_DIAG     = 3'b100;
    localparam [9:0] TOPO_NOR    = 10'h004;

    reg        bus_valid = 0;
    reg [6:0]  bus_addr  = 0;
    reg [2:0]  bus_op    = 0;
    reg [31:0] bus_data  = 0;

    reg [31:0] s_data = 0;
    reg        s_arrived = 0;

    wire        w_prog_data_valid;
    wire [31:0] w_prog_data;
    wire        w_program_out;
    wire        w_freeze, w_hold, w_fbint, w_reemit, w_update, w_selfupd;

    wire        bus_out_valid_w;
    wire [6:0]  bus_out_addr_w;
    wire [2:0]  bus_out_op_w;
    wire [31:0] bus_out_data_w;

    wire [31:0] t_dout_n;
    wire        t_program_done;
    wire        t_ready;
    wire        t_a_arrived_bit;

    wire [31:0] diag_word = {23'h0, t_program_done, t_a_arrived_bit, T.cmd_latch[13], T.pending_ack};

    cell_wrapper_v2 #(.ADDR(5'd0)) WRAP (
        .clk(clk), .rst(rst),
        .bus_in_valid(bus_valid), .bus_in_addr(bus_addr), .bus_in_op(bus_op), .bus_in_data(bus_data),
        .bus_out_valid(bus_out_valid_w), .bus_out_addr(bus_out_addr_w),
        .bus_out_op(bus_out_op_w), .bus_out_data(bus_out_data_w),
        .cell_prog_data_out(w_prog_data), .cell_prog_arrived_out(w_prog_data_valid),
        .cell_program_out(w_program_out), .cell_program_done_in(t_program_done),
        .cell_freeze_out(w_freeze), .cell_hold_out(w_hold), .cell_fb_internal_out(w_fbint),
        .cell_a_reemit_out(w_reemit), .cell_a_update_out(w_update), .cell_a_self_update_out(w_selfupd),
        .cell_out_buffer(t_dout_n), .cell_diag_in(diag_word)
    );

    unicell_stripped_v1 #(.CELL_ID(16'h0001)) T (
        .clk(clk), .rst(rst), .cfg_valid(1'b0), .cfg_data(128'h0),
        .data_in_n(32'h0), .data_in_s(s_data), .data_in_e(32'h0), .data_in_w(32'h0),
        .arrived_n(1'b0), .arrived_s(s_arrived), .arrived_e(1'b0), .arrived_w(1'b0),
        .data_out_n(t_dout_n), .data_out_s(), .data_out_e(), .data_out_w(),
        .fire_n(), .fire_s(), .fire_e(), .fire_w(),
        .ready_out(t_ready),
        .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
        .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
        .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
        .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
        .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),
        .freeze_in(w_freeze),
        .hold_in(w_hold),
        .fb_internal_in(w_fbint),
        .a_reemit_in(w_reemit),
        .a_update_in(w_update),
        .a_self_update_in(w_selfupd),
        .program_in(w_program_out),
        .program_done(t_program_done),
        .prog_data_in_n(w_prog_data), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
        .prog_arrived_in_n(w_prog_data_valid), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
        .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
    );
    assign t_a_arrived_bit = T.a_arrived;

    task send(input [6:0] addr, input [2:0] op, input [31:0] data);
        begin
            bus_addr = addr; bus_op = op; bus_data = data; bus_valid = 1;
            @(posedge clk); #1;
            bus_valid = 0;
        end
    endtask

    task seed_s(input [31:0] v);
        begin
            s_data = v; s_arrived = 1;
            @(posedge clk); #1;
            s_arrived = 0;
        end
    endtask

    task report(input [127:0] label);
        $display("[t=%0t] %0s | topo=%h routing=%b hold=%b program_done=%b bus_out_data=%h A=%h",
                  $time, label, T.cmd_latch[9:0], T.cmd_latch[69:64], w_hold, t_program_done, bus_out_data_w, T.data_reg);
    endtask

    initial begin
        rst = 1; repeat(3) @(posedge clk); rst = 0; @(posedge clk);
        report("start               ");

        // 1. PROGRAM — 3 words via the North channel, not cfg_data.
        send(5'd0, OP_PROGRAM, {13'h0, 3'd0, 6'h0, TOPO_NOR});      // ID_TOPOLOGY
        report("word0               ");
        send(5'd0, OP_PROGRAM, {13'h0, 3'd1, 16'h0002});            // ID_ROUTING_MASK = South
        report("word1               ");
        send(5'd0, OP_PROGRAM, {13'h0, 3'd7, 16'h1});  // points.md #156: LSB=1 arms                // ID_COMPLETE  (leaf, routing_mask=South only)
        repeat(2) @(posedge clk);
        report("word2 + settle      ");   // expect topo=004

        // 2. SET_CTRL hold (index 1). Ordinary data on the South channel —
        // genuinely independent of the wrapper's North program channel.
        send(5'd0, OP_SET_CTRL, 32'h0000_0001);
        repeat(1) @(posedge clk);
        report("hold SET            ");

        seed_s(32'hAAAA0000);
        repeat(2) @(posedge clk);
        report("threshold loaded    ");   // expect A=AAAA0000

        seed_s(32'h11110000);
        repeat(2) @(posedge clk);
        report("fire 1 (held)       ");   // expect A STILL AAAA0000, out=4444FFFF

        seed_s(32'h22220000);
        repeat(2) @(posedge clk);
        report("fire 2 (held)       ");   // expect A STILL AAAA0000, out=5555FFFF

        // CLR_CTRL hold — release.
        send(5'd0, OP_CLR_CTRL, 32'h0000_0001);
        repeat(1) @(posedge clk);
        report("hold CLR            ");

        // 3. COLLECT — read out_buffer back through the bus.
        send(5'd0, OP_COLLECT, 32'h0);
        repeat(1) @(posedge clk);
        report("COLLECT result      ");   // bus_out_data should show current out_buffer

        // 4. DIAG — read internal state back.
        send(5'd0, OP_DIAG, 32'h0);
        repeat(1) @(posedge clk);
        report("DIAG result         ");

        $display("[t=%0t] TEST COMPLETE", $time);
        $finish;
    end

endmodule
