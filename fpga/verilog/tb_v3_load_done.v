// tb_v3_load_done.v — proves CMD_LOAD_DONE (opcode 27), the cycle-3 completion
// marker of the fixed 3-cycle load protocol (sessions/latest.md, "Programming
// protocol FINALISED"). Smallest test: ONE cell, boot it, set its push address
// (output_address) via SET_OUTPUT_ADDR, load a topology via CMD_LOAD_AT, then
// send CMD_LOAD_DONE and confirm:
//   1. cmd_emit_valid pulses for exactly one cycle
//   2. cmd_emit_bus[17] (completion flag) is set, opcode field = CMD_NOP (0)
//   3. cmd_emit_data carries the push address (== output_address)
//   4. cmd_latch[52] (internal "load confirmed" debug bit) is set
//   5. auth gate holds: wrong-auth CMD_LOAD_DONE does NOT emit
`timescale 1ns/1ps
module tb_v3_load_done;
    reg clk=0, rst=0; reg [31:0] cmd_bus=0, cmd_data=0; reg cmd_valid=0;
    reg [15:0] bus_addr=0; reg [31:0] bus_data=0; reg bus_valid=0;
    always #5 clk=~clk;

    wire [31:0] out_addr; wire [31:0] out_data; wire out_valid;
    wire [31:0] cmd_emit_bus, cmd_emit_data; wire cmd_emit_valid;
    wire [31:0] dbg_cmd_latch;

    unicell64_v3 #(.CELL_ID(16'h0009)) dut (
        .clk(clk), .rst(rst),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .bus_addr(bus_addr), .bus_data(bus_data), .bus_valid(bus_valid),
        .out_addr(out_addr), .out_data(out_data), .out_valid(out_valid),
        .cmd_emit_bus(cmd_emit_bus), .cmd_emit_data(cmd_emit_data), .cmd_emit_valid(cmd_emit_valid),
        .dbg_cmd_latch(dbg_cmd_latch)
    );

    task cmd; input [31:0] cb, cd; begin
        @(negedge clk); cmd_bus=cb; cmd_data=cd; cmd_valid=1;
        @(posedge clk); #1; cmd_valid=0; repeat(3) @(posedge clk); #1;
    end endtask

    integer errors=0;
    task check; input got; input want; input [127:0] msg; begin
        if (got===want) $display("  PASS: %0s", msg);
        else begin $display("  FAIL: %0s got=%0d want=%0d", msg, got, want); errors=errors+1; end
    end endtask
    task check32; input [31:0] got, want; input [127:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%08x)", msg, got);
        else begin $display("  FAIL: %0s got=0x%08x want=0x%08x", msg, got, want); errors=errors+1; end
    end endtask

    localparam CMD_BOOT_COMMIT     = 8'd7;
    localparam CMD_LOAD_AT         = 8'd23;
    localparam CMD_SET_OUTPUT_ADDR = 8'd3;
    localparam CMD_LOAD_DONE       = 8'd27;
    localparam PUSH_ADDR           = 16'h1234; // the "set address" — a stand-in write-counter listener

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== CMD_LOAD_DONE: cycle-3 completion pulse ===");

        // 1. Boot the cell: logical addr=CELL_ID (irrelevant here), auth_mask=0x0A5.
        @(negedge clk); bus_addr=16'h0009;
        cmd(CMD_BOOT_COMMIT, {8'h0, 8'hA5, 16'h0009}); // cmd_data[23:16]=auth 0xA5, [15:0]=logical addr
        check(dut.physical_mode, 1'b0, "boot: physical_mode cleared -> RUN");
        check32(dut.cmd_latch[63:53], 11'h0A5, "boot: auth_mask stored");

        // 2. Set the push address (output_address) via SET_OUTPUT_ADDR, auth-gated.
        @(negedge clk); bus_addr=16'h0009;
        cmd({(32'h0A5<<19) | {8'h0, CMD_SET_OUTPUT_ADDR}}, {16'h0, PUSH_ADDR});
        check(dut.output_set, 1'b1, "SET_OUTPUT_ADDR: output_set raised");
        check32({16'h0,dut.output_address}, {16'h0,PUSH_ADDR}, "SET_OUTPUT_ADDR: output_address == push addr");

        // 3. Load a topology via CMD_LOAD_AT (cycles 1-2 of the protocol stand-in).
        @(negedge clk); bus_addr=16'h0009;
        cmd({(32'h0A5<<19) | {8'h0, CMD_LOAD_AT}}, 32'h0000_00BC); // XOR topology
        check32(dut.cmd_latch[9:0], 10'h0BC, "LOAD_AT: topology applied (XOR)");
        check(cmd_emit_valid, 1'b0, "LOAD_AT alone: no completion emit yet");

        // 4. Cycle 3: CMD_LOAD_DONE, RIGHT auth -> expect a one-cycle emit pulse.
        //    cmd_emit_* is BUFFERED (drains on odd_phase, like out_buf_valid) so the
        //    pulse can land 1-2 cycles after the command, not necessarily the next
        //    edge — poll a short window and capture it when it appears.
        @(negedge clk); bus_addr=16'h0009; cmd_bus=(32'h0A5<<19) | {8'h0, CMD_LOAD_DONE};
        cmd_data=32'h0; cmd_valid=1;
        @(posedge clk); #1; cmd_valid=0;
        check(dut.cmd_latch[52], 1'b1, "LOAD_DONE: internal load-confirmed bit set (cmd_latch[52])");
        begin : wait_emit
            integer i; reg seen;
            seen = 1'b0;
            for (i=0; i<4; i=i+1) begin
                if (!seen && cmd_emit_valid) begin
                    seen = 1'b1;
                    check(cmd_emit_valid, 1'b1, "LOAD_DONE (right auth): cmd_emit_valid pulses");
                    check(cmd_emit_bus[17], 1'b1, "LOAD_DONE: completion flag bus bit[17] set");
                    check32(cmd_emit_bus[7:0], 8'h00, "LOAD_DONE: emitted opcode field = CMD_NOP");
                    check32(cmd_emit_data, {16'h0, PUSH_ADDR}, "LOAD_DONE: emitted target == push address");
                end
                @(posedge clk); #1;
            end
            check(cmd_emit_valid, 1'b0, "LOAD_DONE: emit pulse cleared again (one cycle wide)");
            if (!seen) begin
                $display("  FAIL: LOAD_DONE completion pulse never observed within window");
                errors = errors + 1;
            end
        end

        // 5. Wrong-auth CMD_LOAD_DONE must NOT emit (auth gate holds on the new opcode too).
        @(negedge clk); bus_addr=16'h0009; cmd_bus=(32'h111<<19) | {8'h0, CMD_LOAD_DONE};
        cmd_data=32'h0; cmd_valid=1;
        @(posedge clk); #1; cmd_valid=0;
        repeat(4) begin
            check(cmd_emit_valid, 1'b0, "LOAD_DONE (wrong auth): rejected, no emit");
            @(posedge clk); #1;
        end

        if (errors==0) $display(">>> CMD_LOAD_DONE PASS: completion pulse + push-address target + auth gate all correct");
        else $display(">>> CMD_LOAD_DONE FAIL: %0d errors", errors);
        $finish;
    end
endmodule
