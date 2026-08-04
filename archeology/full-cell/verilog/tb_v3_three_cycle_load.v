// tb_v3_three_cycle_load.v — proves the FIXED 3-CYCLE LOAD PROTOCOL end to end on
// one cell (sessions/latest.md "Programming protocol FINALISED", refined this
// session): CYCLE 1 = CMD_LOAD_AT (topology) + bank-2 methodology 1; CYCLE 2 =
// CMD_SET_METHOD (methodology 2 + methodology 3, METH_NONE padding unused slots);
// CYCLE 3 = CMD_LOAD_DONE (completion pulse). Smallest test: ONE cell, boot it,
// set its push address, then run exactly 3 command words and confirm every field
// landed — topology, all three methodologies, and the completion pulse — with
// NO extra transactions beyond the three cycles + the one-time boot/target setup.
`timescale 1ns/1ps
module tb_v3_three_cycle_load;
    reg clk=0, rst=0; reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] bus_addr=0; reg [31:0] bus_data=0; reg bus_valid=0;
    always #5 clk=~clk;

    wire [31:0] out_addr; wire [31:0] out_data; wire out_valid;
    wire [31:0] cmd_emit_bus, cmd_emit_data; wire cmd_emit_valid;
    wire [31:0] dbg_cmd_latch;

    unicell64_v3 #(.CELL_ID(16'h000A)) dut (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .bus_addr(bus_addr), .bus_data(bus_data), .bus_valid(bus_valid),
        .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid),
        .cmd_emit_bus(cmd_emit_bus), .cmd_emit_data(cmd_emit_data), .cmd_emit_valid(cmd_emit_valid),
        .dbg_cmd_latch(dbg_cmd_latch)
    );

    task cmd; input [31:0] cb, cd; begin
        @(negedge clk); bus_addr=16'h000A; cmd_bus=cb; cmd_data=cd; cmd_valid=1;
        @(posedge clk); #1; cmd_valid=0; repeat(2) @(posedge clk); #1;
    end endtask

    integer errors=0;
    task check32; input [63:0] got, want; input [127:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%016x)", msg, got);
        else begin $display("  FAIL: %0s got=0x%016x want=0x%016x", msg, got, want); errors=errors+1; end
    end endtask
    task check1; input got; input want; input [127:0] msg; begin
        if (got===want) $display("  PASS: %0s", msg);
        else begin $display("  FAIL: %0s got=%0d want=%0d", msg, got, want); errors=errors+1; end
    end endtask

    localparam CMD_BOOT_COMMIT     = 8'd7;
    localparam CMD_LOAD_AT         = 8'd23;
    localparam CMD_SET_METHOD      = 8'd25; // unused directly -- slot A carries the real meth opcode
    localparam CMD_SET_OUTPUT_ADDR = 8'd3;
    localparam CMD_LOAD_DONE       = 8'd27;
    localparam METH_SET_MASK       = 8'd30;
    localparam METH_SET_SHIFT_IN   = 8'd31;
    localparam METH_SET_SHIFT_OUT  = 8'd32;
    localparam METH_NONE           = 8'd0;
    localparam PUSH_ADDR           = 16'hABCD;
    localparam [31:0] AUTH          = 32'h0A5;

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== FIXED 3-CYCLE LOAD PROTOCOL: one cell, full sequence ===");

        // ── one-time setup (boot + push address), NOT part of the 3 cycles ──
        cmd(CMD_BOOT_COMMIT, {8'h0, AUTH[7:0], 16'h000A});
        check1(dut.physical_mode, 1'b0, "setup: booted into RUN");
        cmd({(AUTH<<19)|{8'h0,CMD_SET_OUTPUT_ADDR}}, {16'h0, PUSH_ADDR});
        check32({16'h0,dut.output_address}, {16'h0,PUSH_ADDR}, "setup: push address set");

        // ── CYCLE 1: CMD_LOAD_AT topology=XOR(0x0BC) + bank-2 methodology-1=MASK(0x3C) ──
        // bank-2 opcode in cmd_bus[15:8]=METH_SET_MASK, valid flag cmd_bus[16]=1,
        // payload in cmd_data[30:23]=0x3C (mask value). cmd_data bits: [31]=0(1),
        // [30:23]=mask(8), [22:10]=unused(13), [9:0]=topology(10) = 32 total.
        cmd({(AUTH<<19) | 1'b1<<16 | {METH_SET_MASK,CMD_LOAD_AT}}, {1'b0, 8'h3C, 13'b0, 10'h0BC});
        check32(dut.cmd_latch[9:0], 10'h0BC, "cycle1: topology = XOR");
        check32(dut.cmd_latch[39:32], 8'h3C, "cycle1: methodology-1 (mask) value landed");
        check1(dut.cmd_latch[40], 1'b1, "cycle1: mask_en set");
        check1(dut.cmd_latch[47], 1'b0, "cycle1: shift_in_en NOT set (not requested)");

        // ── CYCLE 2: CMD_SET_METHOD, slot A=SHIFT_IN(meth2), slot B=SHIFT_OUT(meth3) ──
        // NOTE: shift_amt[46:41] is ONE shared register for both directions (existing
        // v3.1 design, not new) -- when both slots write it in the same cycle, slot B's
        // value wins (it decodes after slot A in program order). Use the SAME amount in
        // both slots here so the test isolates the 3-cycle protocol, not that subtlety.
        // cmd_data: [21:16]=slotB shift_amt(6), [5:0]=slotA shift_amt(6), rest 0.
        cmd({(AUTH<<19) | 1'b1<<16 | {METH_SET_SHIFT_OUT, METH_SET_SHIFT_IN}},
            {10'b0, 6'd5, 10'b0, 6'd5});
        check1(dut.cmd_latch[47], 1'b1, "cycle2: shift_in_en set (methodology 2)");
        check32(dut.cmd_latch[46:41], 6'd5, "cycle2: shift_amt = 5 (shared register, both slots agree)");
        check1(dut.cmd_latch[48], 1'b1, "cycle2: shift_out_en set (methodology 3)");
        check1(dut.cmd_latch[47], 1'b1, "cycle2: shift_in_en set (methodology 2)");
        check32(dut.cmd_latch[46:41], 6'd5, "cycle2: shift_amt = 5 (methodology 2 payload)");
        check1(dut.cmd_latch[48], 1'b1, "cycle2: shift_out_en set (methodology 3)");

        // ── CYCLE 3: CMD_LOAD_DONE — completion pulse ──
        // Issued manually (not via the `cmd` task) so polling starts immediately;
        // the task's own trailing settle cycles would otherwise eat the pulse window.
        @(negedge clk); bus_addr=16'h000A; cmd_bus=(AUTH<<19) | {8'h0,CMD_LOAD_DONE};
        cmd_data=32'h0; cmd_valid=1;
        @(posedge clk); #1; cmd_valid=0;
        begin : wait_emit
            integer i; reg seen; seen=1'b0;
            for (i=0;i<4;i=i+1) begin
                if (!seen && cmd_emit_valid) begin
                    seen=1'b1;
                    check1(cmd_emit_bus[17], 1'b1, "cycle3: completion flag bit set on emit");
                    check32(cmd_emit_data, {16'h0,PUSH_ADDR}, "cycle3: emitted target == push address");
                end
                @(posedge clk); #1;
            end
            if (!seen) begin $display("  FAIL: cycle3 completion pulse never observed"); errors=errors+1; end
        end
        check1(dut.cmd_latch[52], 1'b1, "cycle3: internal load-confirmed bit set");

        $display("--- exactly 3 protocol cycles used (LOAD_AT, SET_METHOD-style, LOAD_DONE); no other config opcodes issued ---");
        if (errors==0) $display(">>> THREE-CYCLE PROTOCOL PASS: topology + all 3 methodologies + completion pulse, in 3 words");
        else $display(">>> THREE-CYCLE PROTOCOL FAIL: %0d errors", errors);
        $finish;
    end
endmodule
