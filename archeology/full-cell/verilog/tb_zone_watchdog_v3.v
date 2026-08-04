// tb_zone_watchdog_v3.v — proves zone_watchdog_v3.v: real stateful hysteresis
// (not just the combinational "raw" signals from the earlier VM prototype),
// one-shot FREEZE/RELEASE pulses on the transition edge only, and a correctly
// auth-bearing emitted command word that a real cell would actually accept.
`timescale 1ns/1ps
module tb_zone_watchdog_v3;
    reg clk=0, rst=0; always #5 clk=~clk;
    reg [15:0] write_count=0, read_count=0;
    wire [31:0] cmd_bus, cmd_data; wire cmd_valid; wire frozen;

    localparam [10:0] AUTH = 11'h0A5;

    zone_watchdog_v3 #(.HIGH(16'd12), .LOW(16'd4), .AUTH(AUTH)) dut (
        .clk(clk), .rst(rst),
        .write_count(write_count), .read_count(read_count),
        .cmd_bus(cmd_bus), .cmd_data(cmd_data), .cmd_valid(cmd_valid),
        .frozen(frozen)
    );

    integer errors=0;
    task check; input got; input want; input [255:0] msg; begin
        if (got===want) $display("  PASS: %0s", msg);
        else begin $display("  FAIL: %0s got=%0d want=%0d", msg, got, want); errors=errors+1; end
    end endtask
    task check32; input [31:0] got, want; input [255:0] msg; begin
        if (got===want) $display("  PASS: %0s (0x%08x)", msg, got);
        else begin $display("  FAIL: %0s got=0x%08x want=0x%08x", msg, got, want); errors=errors+1; end
    end endtask

    task step; input [15:0] wc, rc; begin
        @(negedge clk); write_count = wc; read_count = rc;
        @(posedge clk); #1;
    end endtask

    initial begin
        rst=1; repeat(4) @(posedge clk); #1; rst=0; repeat(2) @(posedge clk); #1;
        $display("=== ZONE WATCHDOG: hysteresis + one-shot FREEZE/RELEASE ===");

        check(frozen, 1'b0, "initial state: not frozen");

        // Rise through the deadband -- no freeze until level actually hits HIGH.
        step(3, 0);  check(cmd_valid, 1'b0, "level=3 (below LOW): no pulse");
        step(8, 0);  check(cmd_valid, 1'b0, "level=8 (mid deadband): no pulse");
        step(11, 0); check(cmd_valid, 1'b0, "level=11 (just below HIGH): no pulse");
        check(frozen, 1'b0, "still not frozen approaching HIGH");

        // Cross HIGH: exactly one FREEZE pulse, auth-bearing, correct opcode.
        step(12, 0);
        check(cmd_valid, 1'b1, "level=12 (== HIGH): FREEZE pulses");
        check32(cmd_bus, {2'b0, AUTH, 11'h0, 8'd5}, "FREEZE word: auth + opcode 5 correct");
        check(frozen, 1'b1, "frozen state now set");

        // Hold above HIGH: must NOT re-pulse (one-shot, not level-triggered).
        step(12, 0); check(cmd_valid, 1'b0, "held at HIGH: no re-pulse (one-shot)");
        step(15, 0); check(cmd_valid, 1'b0, "level=15 (above HIGH): no re-pulse");
        check(frozen, 1'b1, "still frozen");

        // Descend through the deadband: must STAY frozen (real hysteresis,
        // not a single shared threshold) until LOW is actually reached.
        step(10, 0); check(cmd_valid, 1'b0, "level=10 (deadband, descending): still no pulse");
        check(frozen, 1'b1, "still frozen in the deadband (hysteresis holds)");
        step(5, 0);  check(cmd_valid, 1'b0, "level=5 (just above LOW): still no pulse");
        check(frozen, 1'b1, "still frozen just above LOW");

        // Cross LOW: exactly one RELEASE pulse.
        step(4, 0);
        check(cmd_valid, 1'b1, "level=4 (== LOW): RELEASE pulses");
        check32(cmd_bus, {2'b0, AUTH, 11'h0, 8'd6}, "RELEASE word: auth + opcode 6 correct");
        check(frozen, 1'b0, "frozen state now cleared");

        // Hold at/below LOW: must not re-pulse.
        step(4, 0); check(cmd_valid, 1'b0, "held at LOW: no re-pulse");
        step(0, 0); check(cmd_valid, 1'b0, "level=0: no re-pulse");

        // Nonzero read_count case (level = write-read, not just write).
        step(20, 12); // level=8, deadband
        check(cmd_valid, 1'b0, "write=20 read=12 (level=8, deadband): no pulse");
        step(20, 4);  // level=16, above HIGH
        check(cmd_valid, 1'b1, "write=20 read=4 (level=16, above HIGH): FREEZE pulses");
        check(frozen, 1'b1, "frozen from nonzero-read-count case too");

        if (errors==0) $display(">>> ZONE WATCHDOG PASS: hysteresis, one-shot pulses, auth encoding all correct");
        else $display(">>> ZONE WATCHDOG FAIL: %0d errors", errors);
        $finish;
    end
endmodule
