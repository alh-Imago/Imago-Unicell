`timescale 1ns/1ps
// tb_cmd_emit.v — bare command-emit conduit proof. Cell 0 is a COMMAND_EMIT cell;
// its cmd_emit_* outputs drive Cell 1's command bus directly. Cell 0 holds a
// SET_LOGICAL command word in a_data and targets Cell 1 via output_address. A
// trigger arrival (value ignored) makes Cell 0 emit -> Cell 1 reconfigures itself.
// No controller in the loop for the reconfigure: the fabric commanded itself.
module tb_cmd_emit;
    reg clk=0, rst=0; always #5 clk=~clk;
    // cell 0 (emit) command + data driven by tb
    reg [31:0] c0_cb=0, c0_cd=0; reg c0_cv=0;
    reg [15:0] c0_ba=0; reg [31:0] c0_bd=0; reg c0_bv=0;
    // cell 0 emit outputs
    wire [31:0] e_bus, e_data; wire e_valid;
    wire [31:0] c0_oa, c0_od; wire c0_ov;

    unicell #(.CELL_ID(0), .ENABLE_LATCH_IN(0)) c0 (
        .clk(clk), .rst(rst),
        .cmd_bus(c0_cb), .cmd_data(c0_cd), .cmd_valid(c0_cv),
        .bus_addr(c0_ba), .bus_data(c0_bd), .bus_valid(c0_bv),
        .out_addr(c0_oa), .out_data(c0_od), .out_valid(c0_ov),
        .cmd_emit_bus(e_bus), .cmd_emit_data(e_data), .cmd_emit_valid(e_valid),
        .dbg_cmd_latch(), .dbg_input_addr(), .dbg_input_addr_short(), .dbg_output_addr(),
        .dbg_start_flag(), .dbg_armed(), .dbg_frozen(), .dbg_priority(), .dbg_trace(),
        .dbg_breakpoint(), .dbg_dtype(), .dbg_output_set(), .dbg_a_arrived(), .dbg_a_data());

    // cell 1 (target): its command bus is driven by cell 0's EMIT outputs.
    wire [31:0] c1_oa, c1_od; wire c1_ov;
    wire [31:0] c1_cl; wire [31:0] c1_ia;
    unicell #(.CELL_ID(1), .ENABLE_LATCH_IN(0)) c1 (
        .clk(clk), .rst(rst),
        .cmd_bus(e_bus), .cmd_data(e_data), .cmd_valid(e_valid),   // <-- emitted command
        .bus_addr(16'h0), .bus_data(32'h0), .bus_valid(1'b0),
        .out_addr(c1_oa), .out_data(c1_od), .out_valid(c1_ov),
        .cmd_emit_bus(), .cmd_emit_data(), .cmd_emit_valid(),
        .dbg_cmd_latch(c1_cl), .dbg_input_addr(c1_ia), .dbg_input_addr_short(),
        .dbg_output_addr(), .dbg_start_flag(), .dbg_armed(), .dbg_frozen(), .dbg_priority(),
        .dbg_trace(), .dbg_breakpoint(), .dbg_dtype(), .dbg_output_set(), .dbg_a_arrived(), .dbg_a_data());

    wire c1_phys = c1.physical_mode;

    task xact0; input [31:0] cb,cd; begin @(negedge clk); c0_cb<=cb; c0_cd<=cd; c0_cv<=1; @(posedge clk);#1; c0_cv<=0; repeat(5)@(posedge clk);#1; end endtask
    task inj0;  input [31:0] d; begin @(negedge clk); c0_cb<=32'h1; c0_cd<=d; c0_cv<=1; c0_bv<=1; c0_ba<=16'h0; c0_bd<=d; @(posedge clk);#1; c0_cv<=0; c0_bv<=0; repeat(5)@(posedge clk);#1; end endtask

    initial begin
        rst=1; repeat(5)@(posedge clk);#1; rst=0; repeat(2)@(posedge clk);#1;
        $display("=== command-emit conduit proof ===");
        $display("  cell1 BEFORE:  input_addr=0x%04x physical_mode=%b (reset: addr=1, phys=1)", c1_ia[15:0], c1_phys);

        // configure cell 0 as a COMMAND_EMIT cell, output_address=7 (target+value)
        xact0(32'h14A00004, 32'h52800BC0);   // RECONFIGURE topology=0x3C0 (COMMAND_EMIT), armed
        xact0(32'h14A00003, 32'h00000007);   // SET_OUTPUT_ADDR=7  -> emitted cmd_data target/value
        // load the command word to emit into a_data (first arrival): SET_LOGICAL=opcode 0x0E
        inj0(32'h0000000E);                  // A = SET_LOGICAL command word (stored)
        $display("  cell0 armed as COMMAND_EMIT, a_data=SET_LOGICAL(0x0E), target=7");
        // trigger (second arrival, value ignored) -> cell 0 EMITS
        inj0(32'hDEADBEEF);                  // B = trigger (ignored), fires the emit
        repeat(6)@(posedge clk);#1;

        $display("  emitted on cmd bus: cmd_emit_bus=0x%08x cmd_emit_data=0x%08x", e_bus, e_data);
        $display("  cell1 AFTER:   input_addr=0x%04x physical_mode=%b", c1_ia[15:0], c1_phys);
        if (c1_ia[15:0]==16'h0007 && c1_phys==1'b0)
            $display("  >>> PASS: cell 0 emitted SET_LOGICAL, cell 1 reconfigured itself (addr->7, phys->0) — fabric commanded itself");
        else
            $display("  >>> FAIL: cell 1 did not take the emitted command");
        $finish;
    end
endmodule
