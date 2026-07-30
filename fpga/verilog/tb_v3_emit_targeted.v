// tb_v3_emit_targeted.v — proves the array-level fix (2026-07-30, Alan):
// emitted commands are now genuinely TARGETED via output_address, not
// broadcast to every cell regardless of opcode content.
//
// Recreates the exact "dangerous payload" scenario from points.md #65
// (a command-emit cell's a_data, low byte 0x34 = CMD_TOPO_NOR_COLD,
// armed=0) -- but this time with a properly configured target, and an
// INNOCENT BYSTANDER cell listening at a different address to prove the
// fix actually contains the blast radius rather than just getting lucky.
//
// cell0 = TARGET: listens at addr A, starts PASS_B+armed. Should receive
//         the emitted command and end up disarmed (topology=NOR, armed=0)
//         -- proves the emission correctly REACHES its intended target.
// cell1 = BYSTANDER: listens at addr B != A, starts PASS_B+armed
//         identically to cell0. Should be COMPLETELY UNTOUCHED by the
//         emission -- proves it's genuinely targeted, not broadcast.
// cell2 = SENDER (command-emit): primed with a_data = 0x00000034 (opcode
//         52 = CMD_TOPO_NOR_COLD when read as a command), output_address
//         = A (cell0's listen address, NOT cell1's).
`timescale 1ns/1ps
module tb_v3_emit_targeted;
    reg clk=0, rst=0;
    reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] inj_addr=0; reg [31:0] inj_data=0; reg inj_valid=0;
    always #5 clk=~clk;

    wire [15:0] out_addr; wire [31:0] out_data; wire out_valid;

    unicell_array64_v3 #(.NUM_CELLS(3), .CELL_BASE(0)) arr (
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
    task check1; input got, want; input [255:0] msg; begin
        if (got===want) $display("  PASS: %0s (%b)", msg, got);
        else begin $display("  FAIL: %0s got=%b want=%b", msg, got, want); errors=errors+1; end
    end endtask

    localparam [7:0] OP_SET_IN_ADDR  = 8'd2;
    localparam [7:0] OP_SET_OUT_ADDR = 8'd3;
    localparam [7:0] OP_RECONFIGURE  = 8'd4;
    localparam [7:0] OP_BOOT_COMMIT  = 8'd7;
    localparam [7:0] OP_LOAD_AT      = 8'd23;
    localparam [7:0] OP_SWAP_AB      = 8'd18;

    localparam [15:0] ADDR_A = 16'h0010;  // cell0 (TARGET) listens here
    localparam [15:0] ADDR_B = 16'h0020;  // cell1 (BYSTANDER) listens here
    localparam [15:0] ADDR_C = 16'h0030;  // cell2 (SENDER) listens here for its own trigger

    task boot_all; begin
        @(negedge clk); cmd_bus={8'h0,OP_BOOT_COMMIT}; cmd_data={16'h0, ADDR_A}; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    task hold_target; input [15:0] target; begin
        @(negedge clk); inj_addr=target; inj_data=32'h0; inj_valid=1'b1;
        @(posedge clk); #1; inj_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    task set_input_addr; input [2:0] cell_id; input [15:0] addr; begin
        hold_target({13'h0, cell_id});
        @(negedge clk); cmd_bus={8'h0,OP_SET_IN_ADDR}; cmd_data={16'h0, addr}; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    task set_output_addr; input [2:0] cell_id; input [15:0] addr; begin
        hold_target({13'h0, cell_id});
        @(negedge clk); cmd_bus={8'h0,OP_SET_OUT_ADDR}; cmd_data={16'h0, addr}; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // cell0 and cell1: identical PASS_B + armed config, so any difference
    // in their post-emission state is attributable ONLY to the emission's
    // targeting, not to different starting conditions.
    task config_target_and_bystander_common; begin
        @(negedge clk); cmd_bus={8'h0,OP_RECONFIGURE}; cmd_data = 32'h0000_082C; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // cell2 -> command-emit, armed, listens at ADDR_C for its own trigger.
    task config_sender; begin
        hold_target(16'd2);
        @(negedge clk); cmd_bus={8'h0,OP_LOAD_AT}; cmd_data = 32'h0000_0C00; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // Prime cell2's a_data directly to the "dangerous" payload (0x34 =
    // CMD_TOPO_NOR_COLD when read as a command) via SWAP_AB.
    task prime_sender_payload; begin
        hold_target(16'd2);
        @(negedge clk); cmd_bus={8'h0,OP_SWAP_AB}; cmd_data=32'h0000_0034; cmd_valid=1'b1;
        @(posedge clk); #1; cmd_valid=1'b0; repeat(2) @(posedge clk); #1;
    end endtask

    // Trigger cell2 to fire (its second arrival) -- any value, discarded.
    task fire_sender; begin
        @(negedge clk); inj_addr=ADDR_C; inj_data=32'hFFFF_FFFF; inj_valid=1'b1;
        @(posedge clk); #1; inj_valid=1'b0;
    end endtask

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== EMITTED COMMANDS ARE NOW TARGETED, NOT BROADCAST (Alan, 2026-07-30) ===");

        boot_all;  // all 3 cells initially listen at ADDR_A (shared BOOT_COMMIT payload)
        config_target_and_bystander_common;  // cell0/1/2 all PASS_B+armed (cell2 overwritten next)
        set_input_addr(3'd1, ADDR_B);  // cell1 (BYSTANDER) retargeted to its own address
        set_input_addr(3'd2, ADDR_C);  // cell2 (SENDER) retargeted to its own trigger address
        config_sender;                // cell2 -> command-emit, armed
        set_output_addr(3'd2, ADDR_A); // cell2's emission targets ADDR_A (cell0's address) -- NOT cell1's
        prime_sender_payload;         // cell2's a_data = 0x00000034 (CMD_TOPO_NOR_COLD's opcode)

        $display("  before emission: cell0.start_flag=%b (armed) cell1.start_flag=%b (armed)",
            arr.cell_array[0].cell_inst.start_flag, arr.cell_array[1].cell_inst.start_flag);
        check1(arr.cell_array[0].cell_inst.start_flag, 1'b1, "cell0 armed before emission (sanity)");
        check1(arr.cell_array[1].cell_inst.start_flag, 1'b1, "cell1 armed before emission (sanity)");

        fire_sender;
        repeat(6) @(posedge clk); #1;

        $display("  after emission:  cell0.start_flag=%b (target)  cell1.start_flag=%b (bystander)",
            arr.cell_array[0].cell_inst.start_flag, arr.cell_array[1].cell_inst.start_flag);
        check1(arr.cell_array[0].cell_inst.start_flag, 1'b0, "TARGET (cell0, addr==output_address) DID receive the emitted command -- disarmed");
        check1(arr.cell_array[1].cell_inst.start_flag, 1'b1, "BYSTANDER (cell1, different addr) UNTOUCHED -- emission did not broadcast to it");

        if (errors==0) $display(">>> EMIT_TARGETED PASS: emission reached exactly its intended target, bystander unaffected by the same 'dangerous' payload");
        else           $display(">>> EMIT_TARGETED FAIL: %0d errors", errors);
        $finish;
    end
endmodule
