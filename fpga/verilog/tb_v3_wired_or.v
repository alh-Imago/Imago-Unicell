// tb_v3_wired_or.v — verifies points.md #32: the wired-OR bus is a free N-way OR
// reduction when simultaneous firers share an output address, and confirms the
// exact corruption mode when they don't.
//
// unicell_array64_v3.v (line ~308):
//   for (i = 0; i < NUM_CELLS; i = i + 1)
//       if (cell_out_valid[i]) begin
//           or_addr = cell_out_addr[i];                 // LAST firer's address wins
//           or_data = or_data | cell_out_data[i];        // ALL firers' data OR'd, always
//       end
//
// Two runs, same 3-cell setup (cells 0,1,2, topology=PASS_A so each outputs its
// own preloaded a_data untouched), all listening on a SHARED input address so
// ONE host injection triggers all three simultaneously (same tick):
//
//   RUN 1 (same output address, all three -> 100):
//     EXPECT: exactly one out_valid pulse, out_addr==100,
//             out_data == a0 | a1 | a2   -- a genuine N-way OR reduction, free.
//
//   RUN 2 (cell0,1 -> 100, cell2 -> 101 -- a genuine address mismatch):
//     EXPECT: exactly one out_valid pulse, out_addr==101 (the LAST firer's
//             address, i.e. cell2's, not 100 as cell0/1 intended),
//             out_data == a0 | a1 | a2  STILL -- the data is contaminated with
//             cell0/1's values even though it lands at cell2's address. This is
//             the corruption mode #32 predicts: not a garbage read, a plausible
//             but wrong value.
`timescale 1ns/1ps
module tb_v3_wired_or;
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
    task check16; input [15:0] got, want; input [255:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%04h)", msg, got);
        else begin $display("  FAIL: %0s got=0x%04h want=0x%04h", msg, got, want); errors=errors+1; end
    end endtask
    task check32; input [31:0] got, want; input [255:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%08h)", msg, got);
        else begin $display("  FAIL: %0s got=0x%08h want=0x%08h", msg, got, want); errors=errors+1; end
    end endtask

    localparam [7:0] OP_BOOT_COMMIT     = 8'd7;
    localparam [7:0] OP_LOAD_AT         = 8'd23;
    localparam [7:0] OP_SET_OUTPUT_ADDR = 8'd3;
    localparam [7:0] OP_SWAP_AB         = 8'd18;
    localparam [15:0] SHARED_LISTEN_ADDR = 16'h0000; // all cells' input_address after boot

    // Broadcast BOOT_COMMIT once: every cell (still physical_mode=1) accepts it,
    // sets input_address=SHARED_LISTEN_ADDR, auth_mask=0 (auth_boot -> no token
    // needed later), flips to RUN.
    task boot_all; begin
        @(negedge clk);
        cmd_bus  = {24'h0, OP_BOOT_COMMIT};
        cmd_data = {8'h0, 8'h00, SHARED_LISTEN_ADDR}; // [23:16]=auth_mask=0, [15:0]=addr
        cmd_valid = 1'b1;
        @(posedge clk); #1; cmd_valid = 1'b0;
        repeat(2) @(posedge clk); #1;
    end endtask

    // Point the shared config-target comparator (bus_addr_r) at CELL_ID=target
    // by injecting a throwaway data write to that address. Two cycles to settle
    // through the array's bus_addr register + the cell's own bus_addr_r register.
    task target_cell; input [15:0] target; begin
        @(negedge clk); inj_addr = target; inj_data = 32'h0; inj_valid = 1'b1;
        @(posedge clk); #1; inj_valid = 1'b0;
        repeat(2) @(posedge clk); #1;
    end endtask

    // Configure one cell (already targeted via target_cell): topology=PASS_A
    // (output = a_data, ignores the second arrival's value -- so the shared
    // trigger's data is irrelevant, only its ADDRESS match matters), armed,
    // latch_in; then its own output_address; then preload a_data + a_arrived
    // via SWAP_AB (must be LAST -- LOAD_AT and SET_OUTPUT_ADDR both clear
    // a_arrived as a side effect).
    task configure_cell; input [15:0] target; input [15:0] out_addr_val; input [12:0] a_val; begin
        target_cell(target);

        // LOAD_AT: topology=PASS_A(0), start_flag[11]=1, latch_in[17]=1
        @(negedge clk);
        cmd_bus  = {24'h0, OP_LOAD_AT};
        cmd_data = (32'h1 << 11) | (32'h1 << 17);
        cmd_valid = 1'b1; @(posedge clk); #1; cmd_valid = 1'b0;
        repeat(2) @(posedge clk); #1;

        // SET_OUTPUT_ADDR
        @(negedge clk);
        cmd_bus  = {24'h0, OP_SET_OUTPUT_ADDR};
        cmd_data = {16'h0, out_addr_val};
        cmd_valid = 1'b1; @(posedge clk); #1; cmd_valid = 1'b0;
        repeat(2) @(posedge clk); #1;

        // SWAP_AB: a_data = a_val (13-bit), a_arrived = 1 (first arrival, primed)
        @(negedge clk);
        cmd_bus  = {24'h0, OP_SWAP_AB};
        cmd_data = {19'h0, a_val};
        cmd_valid = 1'b1; @(posedge clk); #1; cmd_valid = 1'b0;
        repeat(2) @(posedge clk); #1;
    end endtask

    // Single shared trigger: one host injection to the common listen address.
    // All primed cells see it on the SAME registered cycle -> simultaneous
    // second arrival -> simultaneous fire -> one combinational OR this cycle.
    reg pulse_count; reg [15:0] seen_addr; reg [31:0] seen_data;
    task fire_and_observe; begin : body
        integer k;
        pulse_count = 0; seen_addr = 16'h0; seen_data = 32'h0;
        @(negedge clk); inj_addr = SHARED_LISTEN_ADDR; inj_data = 32'hDEAD_0000; inj_valid = 1'b1;
        @(posedge clk); #1; inj_valid = 1'b0;
        for (k = 0; k < 8; k = k + 1) begin
            if (out_valid) begin
                pulse_count = pulse_count + 1'b1;
                seen_addr = out_addr;
                seen_data = out_data;
            end
            @(posedge clk); #1;
        end
    end endtask

    initial begin
        rst = 1; repeat(4) @(posedge clk); #1; rst = 0; repeat(2) @(posedge clk); #1;
        $display("=== WIRED-OR BUS: N-way OR reduction (same addr) vs corruption (different addr) ===");

        // ---- RUN 1: same output address (100) for all three -> free OR reduction ----
        boot_all;
        configure_cell(16'd0, 16'd100, 13'h001);
        configure_cell(16'd1, 16'd100, 13'h002);
        configure_cell(16'd2, 16'd100, 13'h004);
        fire_and_observe;
        $display("  [same-addr] pulses=%0d out_addr=0x%04h out_data=0x%08h", pulse_count, seen_addr, seen_data);
        check1(pulse_count == 1, 1'b1, "same-addr: exactly ONE out_valid pulse (one tick)");
        check16(seen_addr, 16'd100, "same-addr: out_addr == the shared output address");
        check32(seen_data, 32'h0000_0007, "same-addr: out_data == OR(0x1,0x2,0x4) = 0x7 -- free N-way OR reduction");

        // ---- RUN 2: cell0,1 -> 100, cell2 -> 101 -- genuine address mismatch ----
        rst = 1; repeat(4) @(posedge clk); #1; rst = 0; repeat(2) @(posedge clk); #1;
        boot_all;
        configure_cell(16'd0, 16'd100, 13'h001);
        configure_cell(16'd1, 16'd100, 13'h002);
        configure_cell(16'd2, 16'd101, 13'h004);
        fire_and_observe;
        $display("  [diff-addr] pulses=%0d out_addr=0x%04h out_data=0x%08h", pulse_count, seen_addr, seen_data);
        check1(pulse_count == 1, 1'b1, "diff-addr: still exactly ONE out_valid pulse (silently, no fault flag)");
        check16(seen_addr, 16'd101, "diff-addr: out_addr == LAST firer's address (cell2's 101), NOT cell0/1's 100");
        check32(seen_data, 32'h0000_0007, "diff-addr: out_data STILL == OR(0x1,0x2,0x4) -- cell0/1's data bled into cell2's address");

        if (errors == 0) begin
            $display(">>> WIRED-OR PASS: same-address fan-in is a genuine free OR reduction;");
            $display("    different-address collision silently delivers OR'd data to the LAST firer's address.");
        end else
            $display(">>> WIRED-OR FAIL: %0d errors", errors);
        $finish;
    end
endmodule
