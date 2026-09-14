`timescale 1ns / 1ps
// tb_uart_bridge_idle.v -- confirms uart_bridge, driven with uart_rx tied to
// constant 1'b1 (idle-high), NEVER asserts cpu_valid or produces any RX
// activity over a long run. This is the exact connection now used in
// top_arria10_zone1_v3.v's UART bridge instance (see commit tying uart_rx
// to 1'b1 instead of the floating UART_RX pin). A truly floating pin
// wandering below the input threshold would eventually trip the RX state
// machine's start-bit detect (`!uart_rx`); a constant 1 by construction
// never can. This does not re-run the RX decode path itself (see
// tb_v3_twoslot / existing UART regression for that) -- it isolates the one
// property this fix depends on: idle-high in means the RX state machine
// never leaves state 0.

module tb_uart_bridge_idle;

reg clk = 0;
reg rst = 1;
wire [31:0] cpu_bus, cpu_data;
wire cpu_valid, array_rst, array_freeze, uart_tx;

always #20 clk = ~clk; // 25MHz-ish, doesn't need to be exact for this check

uart_bridge #(
    .CLK_FREQ  (25_000_000),
    .BAUD_RATE (115_200)
) dut (
    .clk         (clk),
    .rst         (rst),
    .uart_rx     (1'b1),        // <-- the fix under test: constant idle-high
    .uart_tx     (uart_tx),
    .cpu_bus     (cpu_bus),
    .cpu_data    (cpu_data),
    .cpu_valid   (cpu_valid),
    .array_rst   (array_rst),
    .array_freeze(array_freeze),
    .out_addr    (16'h0),
    .out_data    (32'h0),
    .out_valid   (1'b0),
    .armed_count (16'h0),
    .cycle_count (32'h0)
);

integer i;
integer valid_ever_asserted = 0;
integer rst_ever_asserted   = 0;

initial begin
    rst = 1;
    repeat (5) @(posedge clk);
    rst = 0;

    // Run for a long window -- long enough to cover the RX startup counter
    // (stup_cnt is a full 12-bit counter, &stup_cnt at 4095) several times
    // over, so this isn't just "too short to see a glitch".
    for (i = 0; i < 200000; i = i + 1) begin
        @(posedge clk);
        if (cpu_valid === 1'b1) valid_ever_asserted = 1;
        if (array_rst === 1'b1) rst_ever_asserted   = 1;
    end

    if (valid_ever_asserted || rst_ever_asserted) begin
        $display("FAIL: uart_bridge produced cpu_valid or array_rst with uart_rx tied idle-high");
        $display("  cpu_valid ever asserted: %0d", valid_ever_asserted);
        $display("  array_rst ever asserted: %0d", rst_ever_asserted);
    end else begin
        $display("PASS: uart_bridge stayed fully silent (no cpu_valid, no array_rst) over 200000 cycles with uart_rx=1'b1");
    end

    $finish;
end

endmodule
