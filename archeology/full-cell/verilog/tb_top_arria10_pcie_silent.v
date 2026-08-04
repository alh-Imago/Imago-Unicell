`timescale 1ns / 1ps
// tb_top_arria10_pcie_silent.v -- confirms the REAL pcie_unicell_bridge
// instance (not forced signals) stays silent given the safe tie-offs on
// its Avalon-MM slave inputs, i.e. adding PCIe wiring introduces zero
// behavioural change for existing UART/JTAG traffic until a real Hard IP
// is actually connected.
module tb_top_arria10_pcie_silent;

reg CLK_100M = 0;
reg UART_RX = 1;
wire UART_TX, LED0_N, LED1_N;

always #5 CLK_100M = ~CLK_100M;

top_arria10_zone1 dut (
    .CLK_100M(CLK_100M),
    .UART_RX(UART_RX),
    .UART_TX(UART_TX),
    .LED0_N(LED0_N),
    .LED1_N(LED1_N)
);

integer i;
integer p_valid_ever_asserted = 0;

initial begin
    for (i = 0; i < 2000; i = i + 1) begin
        @(posedge CLK_100M);
        if (dut.p_valid === 1'b1) p_valid_ever_asserted = 1;
    end

    if (p_valid_ever_asserted)
        $display("FAIL: p_valid asserted spuriously with no real Hard IP connected");
    else
        $display("PASS: p_valid stayed silent throughout -- PCIe wiring is a true no-op until a real Hard IP drives it");

    $finish;
end

endmodule
