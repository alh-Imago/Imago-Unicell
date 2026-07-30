// tb_v3_masked_compose.v — verifies the DISTRIBUTED COMMAND ASSEMBLY primitive
// Alan described (2026-07-30): no new RTL, a composition of three already-
// proven mechanisms -- wired-OR same-address fan-in (points.md #32),
// nibble_mask (existing methodology field), and command-emit (existing
// is_command_cell feature).
//
// 4 SOURCE cells (0-3), topology=PASS_B (computed_output = second_val =
// the MASKED trigger value -- confirmed from the RTL that nibble_mask only
// ever touches the second-arrival/trigger operand, never the stored first-
// arrival a_data), each with a DIFFERENT nibble_mask keeping only its own
// nibble of a shared trigger value, all listening at the SAME address
// (TRIG_ADDR) so ONE host injection arms/fires all four simultaneously --
// the exact same-tick requirement tb_v3_wired_or.v already proved is what
// makes the array's OR-combine a genuine reduction rather than a collision.
// All four target the SAME output address (CMD_ADDR) -- cell4's listen
// address.
//
// Cell 4 (the COMMAND-EMIT cell): routing_mask=0 (no cardinal escape --
// "no outs direct", exactly as Alan specified), starts UNARMED (a_arrived=0).
// The four simultaneous masked fires land as its FIRST arrival (composing
// the full word via the array's wired-OR, landing in ONE bus event). A
// separate, later injection at CMD_ADDR is its SECOND arrival (trigger) --
// is_command_cell means this fires by driving the STORED a_data (the
// just-composed word) onto the command-emit outputs, ignoring the
// trigger's own value.
`timescale 1ns/1ps
module tb_v3_masked_compose;
    reg clk=0, rst=0;
    reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] inj_addr=0; reg [31:0] inj_data=0; reg inj_valid=0;
    always #5 clk=~clk;

    wire [15:0] out_addr; wire [31:0] out_data; wire out_valid;

    unicell_array64_v3 #(.NUM_CELLS(5), .CELL_BASE(0)) arr (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .cpu_addr(inj_addr), .cpu_data(inj_data), .cpu_valid(inj_valid),
        .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid),
        .out_routing(), .out_transit(),
        .obs_bus_valid(), .obs_bus_addr(), .obs_bus_data(),
        .armed_count(), .arrived_count(), .output_set_count(), .emit_count(),
        .dbg0_cmd_latch(), .dbg0_input_addr(), .dbg0_output_addr(), .dbg0_a_data(),
        .cycle_count()
    );

    integer errors=0;
    task check32; input [31:0] got, want; input [255:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%08h)", msg, got);
        else begin $display("  FAIL: %0s got=0x%08h want=0x%08h", msg, got, want); errors=errors+1; end
    end endtask
    task check1; input got, want; input [255:0] msg; begin
        if (got===want) $display("  PASS: %0s (%b)", msg, got);
        else begin $display("  FAIL: %0s got=%b want=%b", msg, got, want); errors=errors+1; end
    end endtask

    localparam [7:0] OP_DATA_WRITE   = 8'd1;
    localparam [7:0] OP_SET_IN_ADDR  = 8'd2;
    localparam [7:0] OP_RECONFIGURE  = 8'd4;
    localparam [7:0] OP_BOOT_COMMIT  = 8'd7;
    localparam [7:0] OP_METH_SET_MASK = 8'd30;
    localparam [7:0] OP_TOPO_COMMAND_EMIT = 8'd71; // armed variant

    localparam [15:0] TRIG_ADDR = 16'h0010;  // cells 0-3 listen here (shared)
    localparam [15:0] CMD_ADDR  = 16'h0020;  // cell 4 listens here

    // Broadcast BOOT_COMMIT: all 5 cells -> RUN, initial input_address=TRIG_ADDR,
    // auth_mask=0 (auth_boot stays true throughout -- no token needed below).
    task boot_all; begin
        @(negedge clk); cmd_bus={8'h0,OP_BOOT_COMMIT}; cmd_data={16'h0, TRIG_ADDR}; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // Set bus_addr_r=target (config_match address lane) via a harmless dummy
    // injection -- the cell isn't armed yet at setup time, so this can't
    // accidentally trigger anything.
    task hold_target; input [15:0] target; begin
        @(negedge clk); inj_addr=target; inj_data=32'h0; inj_valid=1'b1;
        @(posedge clk); #1; inj_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // Retarget cell4's listen address to CMD_ADDR (config_match-gated,
    // only cell4 accepts since bus_addr_r==4==its own CELL_ID).
    task retarget_cell4; begin
        hold_target(16'd4);
        @(negedge clk); cmd_bus={8'h0,OP_SET_IN_ADDR}; cmd_data={16'h0, CMD_ADDR}; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // Broadcast: all 5 cells -> PASS_B, armed, output_set (output_address
    // itself set separately via SET_OUTPUT_ADDR below). Cell4 gets this too;
    // overwritten to COMMAND_EMIT right after.
    task config_source_common; begin
        @(negedge clk); cmd_bus={8'h0,OP_RECONFIGURE};
        // topology=PASS_B(0x02C), start_flag(bit11)=1.
        cmd_data = 32'h0000_082C; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // SET_OUTPUT_ADDR (op3) broadcasts output_address+output_set to ALL cells
    // -- fine here, all 5 share CMD_ADDR as their output target (cell4's own
    // output_address is irrelevant since command-emit uses it as EMIT target,
    // not consumed in this test).
    localparam [7:0] OP_SET_OUT_ADDR = 8'd3;
    // CMD_SET_OUTPUT_ADDR is config_match-gated (confirmed from the RTL,
    // NOT a broadcast like CMD_RECONFIGURE) -- must target each cell
    // individually via hold_target, same as nibble_mask below.
    task set_output_addr; input [2:0] cell_id; input [15:0] addr; begin
        hold_target({13'h0, cell_id});
        @(negedge clk); cmd_bus={8'h0,OP_SET_OUT_ADDR}; cmd_data={16'h0, addr}; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // Per-cell distinct nibble_mask (config_match-gated METH_SET_MASK, slot A).
    // mask bit=1 BLOCKS that nibble; keep_nibble is the only bit left clear.
    task set_nibble_mask; input [2:0] cell_id; input [7:0] mask; begin
        hold_target({13'h0, cell_id});
        @(negedge clk); cmd_bus={8'h0,OP_METH_SET_MASK}; cmd_data={24'h0, mask}; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    localparam [7:0] OP_LOAD_AT = 8'd23;

    // Overwrite cell4 to COMMAND_EMIT, armed: CMD_LOAD_AT (config_match-
    // gated on CELL_ID) -- NOT CMD_RECONFIGURE, which broadcasts to all 5
    // cells and would silently undo this the next time it's issued.
    task config_cell4_emit; begin
        hold_target(16'd4);
        @(negedge clk); cmd_bus={8'h0,OP_LOAD_AT};
        // cmd_data[10]=command_cell, cmd_data[11]=start_flag(armed).
        cmd_data = 32'h0000_0C00; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // Prime cells 0-3's first arrival: one shared dummy injection at TRIG_ADDR,
    // seen simultaneously by all 4 (a_arrived=1, a_data=dummy -- irrelevant,
    // PASS_B never reads a_data).
    task prime_sources; begin
        @(negedge clk); inj_addr=TRIG_ADDR; inj_data=32'h0; inj_valid=1'b1;
        @(posedge clk); #1; inj_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // The real payload: ONE shared injection at TRIG_ADDR -- all 4 source
    // cells' second arrival, same tick, each masking it down to its own
    // nibble, array ORs them into one composed word landing at CMD_ADDR.
    task fire_sources; input [31:0] value; begin
        @(negedge clk); inj_addr=TRIG_ADDR; inj_data=value; inj_valid=1'b1;
        @(posedge clk); #1; inj_valid=1'b0;
    end endtask

    // Cell4's second arrival -- any value, discarded, just the trigger.
    task fire_cell4; begin
        @(negedge clk); inj_addr=CMD_ADDR; inj_data=32'hDEAD_BEEF; inj_valid=1'b1;
        @(posedge clk); #1; inj_valid=1'b0;
    end endtask

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== DISTRIBUTED COMMAND ASSEMBLY: 4 masked cells compose 1 word for command-emit ===");

        boot_all;
        retarget_cell4;
        set_output_addr(3'd0, CMD_ADDR);
        set_output_addr(3'd1, CMD_ADDR);
        set_output_addr(3'd2, CMD_ADDR);
        set_output_addr(3'd3, CMD_ADDR);
        // nibble0 (bits3:0) keep on cell0, block rest: mask=8'b1111_1110
        set_nibble_mask(3'd0, 8'b1111_1110);
        // nibble1 (bits7:4) keep on cell1: mask=8'b1111_1101
        set_nibble_mask(3'd1, 8'b1111_1101);
        // nibble2 (bits11:8) keep on cell2: mask=8'b1111_1011
        set_nibble_mask(3'd2, 8'b1111_1011);
        // nibble3 (bits15:12) keep on cell3: mask=8'b1111_0111
        set_nibble_mask(3'd3, 8'b1111_0111);

        // Broadcast common config BEFORE the targeted cell4 overwrite --
        // CMD_RECONFIGURE broadcasts to every cell (auth_ok only, no
        // config_match), so doing this AFTER config_cell4_emit would
        // silently clear cell4's command_cell flag right back to 0.
        config_source_common;
        config_cell4_emit;

        prime_sources;

        // Compose 0x00001234 from 4 independently-masked contributions.
        // Settle wait: the compose (array wired-OR -> bus_addr/bus_data ->
        // cell4's first-arrival store) takes a few cycles through the
        // pipeline, same as every other fire-and-observe pattern in this
        // project's testbenches.
        fire_sources(32'h0000_1234);
        repeat(10) @(posedge clk); #1;
        $display("  after compose: arr.cell4 a_data=0x%08h a_arrived=%b",
                  arr.cell_adata[4], arr.cell_arrived[4]);
        check32(arr.cell_adata[4], 32'h0000_1234, "cell4's a_data == composed word from 4 masked contributions");
        check1(arr.cell_arrived[4], 1'b1, "cell4 armed (first arrival landed)");

        fire_cell4;
        // emit_valid is a single-cycle pulse -- watch from right after the
        // injection, not after a fixed delay (which was skipping past it).
        begin : watch_emit
            integer k; reg saw_emit; reg [31:0] emit_word;
            saw_emit=1'b0; emit_word=32'h0;
            for (k=0;k<20;k=k+1) begin
                if (arr.cell_emit_valid[4]) begin saw_emit=1'b1; emit_word=arr.cell_emit_bus[4]; end
                @(posedge clk); #1;
            end
            check1(saw_emit, 1'b1, "cell4 emitted onto the command bus");
            check32(emit_word, 32'h0000_1234, "emitted word == the composed command");
        end

        if (errors==0) $display(">>> MASKED_COMPOSE PASS: 4 masked cells composed 1 command word, command-emit cell sent it");
        else           $display(">>> MASKED_COMPOSE FAIL: %0d errors", errors);
        $finish;
    end
endmodule
